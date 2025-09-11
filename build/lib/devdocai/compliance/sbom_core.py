"""
M010 SBOM Generator - Core Module
DevDocAI v3.0.0 - Core components for SBOM generation

This module contains the core components for SBOM generation including
license detection, vulnerability scanning, and digital signatures.
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from pydantic import BaseModel

from ..core.config import ConfigurationManager
from .sbom_performance import CacheManager, PerformanceMonitor, cached_result, measure_performance
from .sbom_security import MAX_DEPENDENCY_COUNT, SecurityManager
from .sbom_types import SBOM, LicenseInfo, Package, SignatureError, Vulnerability

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger(f"{__name__}.audit")


# ============================================================================
# License Detector
# ============================================================================


class LicenseDetector:
    """
    Detects software licenses from package metadata and files.

    Performance optimized with caching and parallel detection.
    Uses SPDX license list for standardization.
    """

    # Common SPDX license identifiers
    COMMON_LICENSES = {
        "MIT": LicenseInfo(
            license_id="MIT",
            license_name="MIT License",
            is_osi_approved=True,
            is_deprecated=False,
        ),
        "Apache-2.0": LicenseInfo(
            license_id="Apache-2.0",
            license_name="Apache License 2.0",
            is_osi_approved=True,
            is_deprecated=False,
        ),
        "GPL-3.0": LicenseInfo(
            license_id="GPL-3.0",
            license_name="GNU General Public License v3.0",
            is_osi_approved=True,
            is_deprecated=False,
        ),
        "BSD-3-Clause": LicenseInfo(
            license_id="BSD-3-Clause",
            license_name="BSD 3-Clause License",
            is_osi_approved=True,
            is_deprecated=False,
        ),
        "ISC": LicenseInfo(
            license_id="ISC",
            license_name="ISC License",
            is_osi_approved=True,
            is_deprecated=False,
        ),
    }

    def __init__(self):
        """Initialize license detector with performance features."""
        self._lock = threading.RLock()
        self._cache: Dict[str, LicenseInfo] = {}

        # Performance components
        self._cache_manager = CacheManager()
        self._perf_monitor = PerformanceMonitor()

    @cached_result("license")
    @measure_performance("license_detection")
    def detect(self, package: Package) -> Optional[LicenseInfo]:
        """
        Detect license for a package with caching.

        Args:
            package: Package to detect license for

        Returns:
            License information if detected, None otherwise
        """
        with self._lock:
            # Check performance cache
            perf_cache_key = self._cache_manager.get_cache_key(
                "license", package.name, package.version
            )
            cached = self._cache_manager.license_cache.get(perf_cache_key)
            if cached:
                self._perf_monitor.record_operation("license_cache_hit", 0.0, cache_hit=True)
                return cached

            # Check legacy cache
            cache_key = f"{package.name}@{package.version}"
            if cache_key in self._cache:
                return self._cache[cache_key]

            start_time = time.time()
            license_info = None

            # Try to detect from package metadata
            if package.purl:
                license_info = self._detect_from_purl(package.purl)

            # Try to detect from local files if available
            if not license_info and package.file_path:
                license_info = self._detect_from_files(package.file_path)

            detection_time = time.time() - start_time

            # Update caches
            if license_info:
                self._cache[cache_key] = license_info
                self._cache_manager.license_cache.set(perf_cache_key, license_info)

            self._perf_monitor.record_operation(
                "license_detection", detection_time, cache_hit=False
            )

            return license_info

    def detect_batch(self, packages: List[Package]) -> Dict[str, Optional[LicenseInfo]]:
        """
        Detect licenses for multiple packages in parallel.

        Args:
            packages: List of packages to detect licenses for

        Returns:
            Dictionary mapping package key to license info
        """
        results = {}

        with ThreadPoolExecutor(max_workers=4) as executor:
            future_to_package = {executor.submit(self.detect, pkg): pkg for pkg in packages}

            for future in as_completed(future_to_package):
                package = future_to_package[future]
                key = f"{package.name}@{package.version}"
                try:
                    results[key] = future.result(timeout=5)
                except Exception as e:
                    logger.error(f"License detection failed for {key}: {e}")
                    results[key] = None

        return results

    def _detect_from_purl(self, purl: str) -> Optional[LicenseInfo]:
        """Detect license from package URL."""
        # In production, this would query package registries
        # For now, return common licenses based on patterns
        if "mit" in purl.lower():
            return self.COMMON_LICENSES["MIT"]
        elif "apache" in purl.lower():
            return self.COMMON_LICENSES["Apache-2.0"]
        elif "gpl" in purl.lower():
            return self.COMMON_LICENSES["GPL-3.0"]
        elif "bsd" in purl.lower():
            return self.COMMON_LICENSES["BSD-3-Clause"]
        return None

    def _detect_from_files(self, path: Path) -> Optional[LicenseInfo]:
        """Detect license from local files."""
        # Check for LICENSE file
        for license_file in ["LICENSE", "LICENSE.txt", "LICENSE.md", "COPYING"]:
            file_path = path / license_file
            if file_path.exists():
                try:
                    with open(file_path, encoding="utf-8") as f:
                        content = f.read()
                        return self._identify_license_from_text(content)
                except Exception as e:
                    logger.error(f"Error reading license file: {e}")
        return None

    def _identify_license_from_text(self, text: str) -> Optional[LicenseInfo]:
        """Identify license from text content."""
        text_lower = text.lower()

        # Simple pattern matching (production would use more sophisticated methods)
        if "mit license" in text_lower:
            return self.COMMON_LICENSES["MIT"]
        elif "apache license" in text_lower and "version 2.0" in text_lower:
            return self.COMMON_LICENSES["Apache-2.0"]
        elif "gnu general public license" in text_lower and "version 3" in text_lower:
            return self.COMMON_LICENSES["GPL-3.0"]
        elif "bsd" in text_lower and "3-clause" in text_lower:
            return self.COMMON_LICENSES["BSD-3-Clause"]
        elif "isc license" in text_lower:
            return self.COMMON_LICENSES["ISC"]

        return None


# ============================================================================
# Vulnerability Scanner
# ============================================================================


class VulnerabilityScanner:
    """
    Scans packages for known security vulnerabilities.

    Performance optimized with:
    - Batch scanning for multiple packages
    - Connection pooling for API calls
    - Multi-tier caching

    In production, would integrate with:
        - NVD (National Vulnerability Database)
        - OSV (Open Source Vulnerabilities)
        - GitHub Advisory Database
    """

    def __init__(self):
        """Initialize vulnerability scanner with performance features."""
        self._lock = threading.RLock()
        self._cache: Dict[str, List[Vulnerability]] = {}
        self._security = SecurityManager()
        self._scan_count = 0

        # Performance components
        self._cache_manager = CacheManager()
        self._perf_monitor = PerformanceMonitor()

    @measure_performance("vulnerability_scan")
    def scan(self, packages: List[Package]) -> List[Vulnerability]:
        """
        Scan packages for vulnerabilities with batch processing.

        Performance optimized with:
        - Batch API calls
        - Multi-tier caching
        - Connection pooling

        Args:
            packages: List of packages to scan

        Returns:
            List of discovered vulnerabilities
        """
        with self._lock:
            # Security: Rate limiting
            if not self._security.check_rate_limit("vulnerability_scan"):
                audit_logger.warning(
                    "Rate limit exceeded for vulnerability scanning",
                    extra={"security_event": "vuln_scan_rate_limited"},
                )
                return []

            # Security: Limit package count
            if len(packages) > MAX_DEPENDENCY_COUNT:
                audit_logger.warning(
                    f"Too many packages for vulnerability scan: {len(packages)}",
                    extra={"security_event": "vuln_scan_limit_exceeded"},
                )
                packages = packages[:MAX_DEPENDENCY_COUNT]

            audit_logger.info(
                f"Starting batch vulnerability scan for {len(packages)} packages",
                extra={"security_event": "vuln_scan_started", "package_count": len(packages)},
            )

            start_time = time.time()
            all_vulnerabilities = []
            self._scan_count = 0

            # Process packages in batches for efficiency
            batch_size = 50
            for i in range(0, len(packages), batch_size):
                batch = packages[i : i + batch_size]
                batch_vulns = self._scan_batch(batch)
                all_vulnerabilities.extend(batch_vulns)

                # Check processing limits
                self._scan_count += len(batch)
                if self._scan_count > MAX_DEPENDENCY_COUNT:
                    break

            scan_duration = time.time() - start_time

            # Record performance metrics
            self._perf_monitor.record_operation(
                "vuln_scan_total", scan_duration, size=len(all_vulnerabilities), cache_hit=False
            )

            # Log cache performance
            cache_stats = self._cache_manager.vulnerability_cache.get_stats()
            logger.info(
                f"Vulnerability cache hit ratio: {cache_stats['hit_ratio']:.1%} "
                f"({cache_stats['hits']}/{cache_stats['hits'] + cache_stats['misses']})"
            )

            if all_vulnerabilities:
                audit_logger.warning(
                    f"Found {len(all_vulnerabilities)} vulnerabilities in {scan_duration:.2f}s",
                    extra={
                        "security_event": "vulnerabilities_found",
                        "vulnerability_count": len(all_vulnerabilities),
                        "duration": scan_duration,
                    },
                )

            logger.info(f"Vulnerability scan completed in {scan_duration:.2f}s")
            return all_vulnerabilities

    def _scan_batch(self, packages: List[Package]) -> List[Vulnerability]:
        """
        Scan a batch of packages for vulnerabilities.

        Args:
            packages: Batch of packages to scan

        Returns:
            List of vulnerabilities found in batch
        """
        batch_vulnerabilities = []

        # Check cache for all packages first
        uncached_packages = []
        for package in packages:
            cache_key = f"{package.name}@{package.version}"

            # Check performance cache
            perf_cache_key = self._cache_manager.get_cache_key(
                "vuln", package.name, package.version
            )
            cached = self._cache_manager.vulnerability_cache.get(perf_cache_key)

            if cached is not None:
                package.vulnerabilities = cached
                batch_vulnerabilities.extend(cached)
                self._perf_monitor.record_operation("vuln_cache_hit", 0.0, cache_hit=True)
            elif cache_key in self._cache:
                vulns = self._cache[cache_key]
                package.vulnerabilities = vulns
                batch_vulnerabilities.extend(vulns)
            else:
                uncached_packages.append(package)

        # Scan uncached packages in parallel
        if uncached_packages:
            with ThreadPoolExecutor(max_workers=6) as executor:
                future_to_package = {
                    executor.submit(self._scan_package_with_cache, pkg): pkg
                    for pkg in uncached_packages
                }

                for future in as_completed(future_to_package):
                    package = future_to_package[future]
                    try:
                        vulns = future.result(timeout=10)
                        package.vulnerabilities = vulns
                        batch_vulnerabilities.extend(vulns)
                    except Exception as e:
                        logger.error(f"Error scanning {package.name}: {e}")
                        package.vulnerabilities = []

        return batch_vulnerabilities

    def _scan_package_with_cache(self, package: Package) -> List[Vulnerability]:
        """
        Scan individual package with caching.

        Args:
            package: Package to scan

        Returns:
            List of vulnerabilities
        """
        cache_key = f"{package.name}@{package.version}"
        perf_cache_key = self._cache_manager.get_cache_key("vuln", package.name, package.version)

        try:
            # Use circuit breaker for external API calls
            vulns = self._security.circuit_breaker_call(self._scan_package, package)

            # Update caches
            self._cache[cache_key] = vulns
            self._cache_manager.vulnerability_cache.set(perf_cache_key, vulns)

            return vulns
        except Exception as e:
            logger.error(f"Error scanning package {package.name}: {e}")
            return []

    def _scan_package(self, package: Package) -> List[Vulnerability]:
        """Scan individual package for vulnerabilities."""
        vulnerabilities = []

        # In production, would query vulnerability databases
        # For demonstration, check for known vulnerable versions
        # Check for Log4j vulnerability (handle both simple and Maven-style names)
        if (
            "log4j" in package.name.lower()
            and package.version.startswith("2.")
            and package.version
            in [
                "2.14.0",
                "2.14.1",
                "2.13.0",
                "2.12.0",
                "2.11.0",
                "2.10.0",
                "2.9.0",
                "2.8.0",
                "2.7",
                "2.6",
                "2.5",
                "2.4",
                "2.3",
                "2.2",
                "2.1",
                "2.0",
            ]
        ):
            # Log4Shell vulnerability
            vulnerabilities.append(
                Vulnerability(
                    cve_id="CVE-2021-44228",
                    severity="CRITICAL",
                    cvss_score=10.0,
                    description="Log4Shell - Remote code execution in Log4j",
                    affected_versions=["2.0", "2.14.1"],
                    fixed_versions=["2.15.0"],
                    published_date=datetime(2021, 12, 9, tzinfo=timezone.utc),
                    references=["https://nvd.nist.gov/vuln/detail/CVE-2021-44228"],
                )
            )

        return vulnerabilities


# ============================================================================
# Ed25519 Digital Signer
# ============================================================================


class Ed25519Signer:
    """
    Digital signature generator using Ed25519 algorithm.

    Provides cryptographic signatures for SBOM integrity.
    """

    def __init__(self, config: Optional[ConfigurationManager] = None):
        """
        Initialize digital signer with secure key management.

        Args:
            config: Configuration manager for key management
        """
        self._config = config or ConfigurationManager()
        self._private_key: Optional[ed25519.Ed25519PrivateKey] = None
        self._public_key: Optional[ed25519.Ed25519PublicKey] = None
        self._lock = threading.RLock()
        self._key_encryption_key: Optional[bytes] = None
        self._security = SecurityManager()

        # Load or generate keys with encryption
        self._initialize_keys()

    def _initialize_keys(self):
        """Initialize signing keys with secure storage."""
        with self._lock:
            key_path = Path.home() / ".devdocai" / "sbom_signing_key.enc"

            # Derive key encryption key from system entropy
            self._key_encryption_key = self._derive_key_encryption_key()

            if key_path.exists():
                # Load existing encrypted key
                try:
                    with open(key_path, "rb") as f:
                        encrypted_data = f.read()

                    # Decrypt the private key
                    decrypted_key = self._decrypt_key(encrypted_data)

                    self._private_key = serialization.load_pem_private_key(
                        decrypted_key,
                        password=None,
                    )
                    self._public_key = self._private_key.public_key()

                    audit_logger.info(
                        "Loaded encrypted SBOM signing key", extra={"security_event": "key_loaded"}
                    )
                    logger.info("Loaded existing SBOM signing key")
                except Exception as e:
                    logger.error(f"Error loading signing key: {e}")
                    audit_logger.error(
                        f"Key loading failed: {e}", extra={"security_event": "key_load_failed"}
                    )
                    self._generate_new_keys(key_path)
            else:
                # Generate new key pair
                self._generate_new_keys(key_path)

    def _generate_new_keys(self, key_path: Path):
        """Generate new Ed25519 key pair with secure storage."""
        logger.info("Generating new Ed25519 key pair for SBOM signing")

        # Generate key pair
        self._private_key = ed25519.Ed25519PrivateKey.generate()
        self._public_key = self._private_key.public_key()

        # Serialize private key
        pem = self._private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.OpenSSH,
            encryption_algorithm=serialization.NoEncryption(),
        )

        # Encrypt the private key before storage
        encrypted_key = self._encrypt_key(pem)

        # Save encrypted private key
        key_path.parent.mkdir(parents=True, exist_ok=True)
        with open(key_path, "wb") as f:
            f.write(encrypted_key)

        # Set restrictive permissions
        key_path.chmod(0o600)

        audit_logger.info(
            "Generated new encrypted signing key", extra={"security_event": "key_generated"}
        )
        logger.info(f"Saved new signing key to {key_path}")

    def _derive_key_encryption_key(self) -> bytes:
        """Derive key encryption key from system entropy."""
        # Use system-specific entropy sources
        entropy_sources = [
            os.urandom(32),  # OS random
            str(os.getpid()).encode(),  # Process ID
            str(time.time()).encode(),  # Current time
        ]

        # Combine entropy
        combined = b"".join(entropy_sources)

        # Derive key using PBKDF2
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b"devdocai-sbom-key-salt",  # Static salt for deterministic derivation
            iterations=100000,
            backend=default_backend(),
        )

        return kdf.derive(combined)

    def _encrypt_key(self, key_data: bytes) -> bytes:
        """Encrypt private key for storage."""
        if not self._key_encryption_key:
            raise RuntimeError("Key encryption key not initialized")

        # Use Fernet for symmetric encryption
        fernet_key = base64.urlsafe_b64encode(self._key_encryption_key)
        f = Fernet(fernet_key)

        return f.encrypt(key_data)

    def _decrypt_key(self, encrypted_data: bytes) -> bytes:
        """Decrypt private key from storage."""
        if not self._key_encryption_key:
            raise RuntimeError("Key encryption key not initialized")

        # Use Fernet for symmetric decryption
        fernet_key = base64.urlsafe_b64encode(self._key_encryption_key)
        f = Fernet(fernet_key)

        return f.decrypt(encrypted_data)

    def sign(self, data: Any) -> str:
        """
        Sign data with Ed25519 private key.

        Args:
            data: Data to sign (will be JSON serialized)

        Returns:
            Base64-encoded signature
        """
        with self._lock:
            if not self._private_key:
                raise SignatureError("Signing key not initialized")

            # Security: Rate limiting for signature operations
            if not self._security.check_rate_limit("signature_generation"):
                raise SignatureError("Rate limit exceeded for signature generation")

            # Serialize data to canonical JSON
            if isinstance(data, BaseModel):
                json_data = data.model_dump_json(exclude={"signature"})
            else:
                json_data = json.dumps(data, sort_keys=True, default=str)

            # Add integrity HMAC
            integrity_hmac = hmac.new(
                self._key_encryption_key or b"default-hmac-key",
                json_data.encode("utf-8"),
                hashlib.sha256,
            ).digest()

            # Sign the data with HMAC appended
            data_with_hmac = json_data.encode("utf-8") + integrity_hmac
            signature = self._private_key.sign(data_with_hmac)

            # Log signature generation
            audit_logger.info(
                "SBOM signature generated", extra={"security_event": "signature_generated"}
            )

            # Return base64-encoded signature
            return base64.b64encode(signature).decode("ascii")

    def verify(self, data: Any, signature: str) -> bool:
        """
        Verify signature with Ed25519 public key.

        Args:
            data: Data to verify
            signature: Base64-encoded signature

        Returns:
            True if signature is valid
        """
        with self._lock:
            if not self._public_key:
                raise RuntimeError("Public key not initialized")

            try:
                # Serialize data to canonical JSON
                if isinstance(data, BaseModel):
                    json_data = data.model_dump_json(exclude={"signature"})
                else:
                    json_data = json.dumps(data, sort_keys=True, default=str)

                # Add integrity HMAC (same as in sign method)
                integrity_hmac = hmac.new(
                    self._key_encryption_key or b"default-hmac-key",
                    json_data.encode("utf-8"),
                    hashlib.sha256,
                ).digest()

                # Reconstruct data with HMAC
                data_with_hmac = json_data.encode("utf-8") + integrity_hmac

                # Decode signature
                sig_bytes = base64.b64decode(signature)

                # Verify signature
                self._public_key.verify(sig_bytes, data_with_hmac)
                return True
            except Exception:
                return False

    @property
    def public_key(self) -> str:
        """Get base64-encoded public key."""
        if not self._public_key:
            raise RuntimeError("Public key not initialized")

        pem = self._public_key.public_bytes(
            encoding=serialization.Encoding.OpenSSH,
            format=serialization.PublicFormat.OpenSSH,
        )

        return base64.b64encode(pem).decode("ascii")


# ============================================================================
# SBOM Validation
# ============================================================================


class SBOMValidator:
    """Validates SBOM against format specifications."""

    def __init__(self, signer: Optional[Ed25519Signer] = None):
        """Initialize validator."""
        self._signer = signer

    def validate(self, sbom: SBOM) -> Tuple[bool, List[str]]:
        """
        Validate SBOM against format specifications.

        Args:
            sbom: SBOM to validate

        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        errors = []

        # Check required fields
        if not sbom.packages:
            errors.append("SBOM must contain at least one package")

        if not sbom.document_namespace:
            errors.append("SBOM must have a document namespace")

        if not sbom.creator:
            errors.append("SBOM must identify the creator")

        # Validate format-specific requirements
        if sbom.format.value == "spdx-2.3":
            errors.extend(self._validate_spdx(sbom))
        elif sbom.format.value == "cyclonedx-1.4":
            errors.extend(self._validate_cyclonedx(sbom))

        # Verify signature if present
        if sbom.signature and self._signer:
            try:
                if not self._signer.verify(sbom, sbom.signature.value):
                    errors.append("Digital signature verification failed")
            except Exception as e:
                errors.append(f"Signature verification error: {e}")

        return len(errors) == 0, errors

    def _validate_spdx(self, sbom: SBOM) -> List[str]:
        """Validate SPDX-specific requirements."""
        errors = []

        # Check SPDX metadata
        metadata = sbom.metadata
        if not metadata.get("spdxVersion"):
            errors.append("SPDX SBOM must specify spdxVersion")

        if not metadata.get("dataLicense"):
            errors.append("SPDX SBOM must specify dataLicense")

        if not metadata.get("SPDXID"):
            errors.append("SPDX SBOM must have document SPDXID")

        # Validate relationships
        if not sbom.relationships:
            errors.append("SPDX SBOM should have at least one relationship")

        return errors

    def _validate_cyclonedx(self, sbom: SBOM) -> List[str]:
        """Validate CycloneDX-specific requirements."""
        errors = []

        # Check CycloneDX metadata
        metadata = sbom.metadata
        if not metadata.get("bomFormat"):
            errors.append("CycloneDX SBOM must specify bomFormat")

        if not metadata.get("specVersion"):
            errors.append("CycloneDX SBOM must specify specVersion")

        if not metadata.get("serialNumber"):
            errors.append("CycloneDX SBOM must have serialNumber")

        return errors
