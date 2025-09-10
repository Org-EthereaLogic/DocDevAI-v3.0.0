"""
M010 SBOM Generator - Main Orchestrator
DevDocAI v3.0.0 - Software Bill of Materials Generation with Digital Signatures

This module orchestrates SBOM generation using modular components for scanning,
license detection, vulnerability scanning, and format building.

Performance Targets:
    - Complete generation within 30 seconds for <500 dependencies
    - 100% dependency coverage
    - Support for both SPDX 2.3 and CycloneDX 1.4 formats

Security Features:
    - Ed25519 digital signatures
    - Tamper-evident SBOM documents
    - Cryptographic validation support
"""

import asyncio
import json
import logging
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import ConfigurationManager
from .sbom_core import (
    Ed25519Signer,
    LicenseDetector,
    SBOMValidator,
    VulnerabilityScanner,
)
from .sbom_performance import (
    MemoryManager,
    PerformanceOptimizer,
    StreamingExporter,
    measure_performance,
)
from .sbom_security import (
    MAX_DEPENDENCY_COUNT,
    MAX_FILE_SIZE,
    MAX_PROCESSING_TIME,
    PIIDetector,
    SecurityManager,
)
from .sbom_strategies import (
    FormatBuilderFactory,
    PackageScannerFactory,
)
from .sbom_types import (
    SBOM,
    SBOMError,
    SBOMFormat,
    SBOMSignature,
    Package,
    Vulnerability,
)

logger = logging.getLogger(__name__)
audit_logger = logging.getLogger(f"{__name__}.audit")


# ============================================================================
# Dependency Scanner
# ============================================================================


class DependencyScanner:
    """
    Orchestrates package scanning across multiple package managers.
    
    Uses strategy pattern for extensible scanning support.
    """

    def __init__(self):
        """Initialize dependency scanner."""
        self._lock = threading.RLock()
        self._cache: Dict[str, List[Package]] = {}
        self._security = SecurityManager()
        self._memory_manager = MemoryManager()
        self._start_time = None
        self._scanned_count = 0

    @measure_performance("dependency_scan")
    def scan_project(self, project_path: Path) -> List[Package]:
        """
        Scan project directory for all dependencies.
        
        Uses parallel scanning across package managers with security validation.
        
        Args:
            project_path: Root directory of the project
            
        Returns:
            List of discovered packages with metadata
            
        Raises:
            SBOMError: If scanning fails or security violation detected
        """
        with self._lock:
            # Security: Rate limiting
            if not self._security.check_rate_limit("dependency_scan"):
                raise SBOMError("Rate limit exceeded for dependency scanning")
            
            # Security: Path validation
            if not self._security.validate_path(project_path):
                audit_logger.error(
                    f"Invalid project path: {project_path}",
                    extra={"security_event": "invalid_project_path"}
                )
                raise SBOMError(f"Invalid project path: {project_path}")
            
            # Check cache
            cache_key = str(project_path)
            if cache_key in self._cache:
                logger.debug(f"Using cached scan results for {project_path}")
                return self._cache[cache_key]

            # Security: Processing time limit
            self._start_time = time.time()
            self._scanned_count = 0
            
            # Check memory before starting
            if not self._memory_manager.check_memory():
                logger.warning("Memory limit approaching, running garbage collection")
                import gc
                gc.collect()
            
            audit_logger.info(
                f"Starting parallel dependency scan: {project_path}",
                extra={"security_event": "scan_started", "path": str(project_path)}
            )
            
            logger.info(f"Scanning project with parallel processing: {project_path}")
            
            # Get applicable scanners using factory
            scanners = PackageScannerFactory.get_scanners(project_path)
            
            if not scanners:
                logger.warning(f"No applicable scanners found for {project_path}")
                return []
            
            # Parallel scanning across package managers
            packages = []
            with ThreadPoolExecutor(max_workers=6) as executor:
                # Submit all scan tasks
                future_to_scanner = {
                    executor.submit(scanner.scan, project_path): scanner.__class__.__name__
                    for scanner in scanners
                }
                
                # Collect results as they complete
                for future in as_completed(future_to_scanner):
                    scanner_name = future_to_scanner[future]
                    try:
                        scan_start = time.time()
                        result = future.result(timeout=30)
                        scan_duration = time.time() - scan_start
                        
                        packages.extend(result)
                        self._scanned_count += len(result)
                        
                        logger.debug(f"{scanner_name} found {len(result)} packages in {scan_duration:.2f}s")
                        
                    except Exception as e:
                        logger.error(f"{scanner_name} scan failed: {e}")

            # Security: Check processing limits
            if self._scanned_count > MAX_DEPENDENCY_COUNT:
                audit_logger.error(
                    f"Dependency count exceeds limit: {self._scanned_count}",
                    extra={"security_event": "dependency_limit_exceeded"}
                )
                raise SBOMError(f"Too many dependencies: {self._scanned_count}")
            
            elapsed = time.time() - self._start_time
            if elapsed > MAX_PROCESSING_TIME:
                audit_logger.error(
                    f"Processing time exceeded: {elapsed}s",
                    extra={"security_event": "processing_timeout"}
                )
                raise SBOMError(f"Processing timeout: {elapsed}s")
            
            # Remove duplicates
            packages = self._deduplicate_packages(packages)

            # Security: Sanitize package data
            packages = self._sanitize_packages(packages)
            
            # Cache results
            self._cache[cache_key] = packages
            
            audit_logger.info(
                f"Parallel dependency scan completed: {len(packages)} packages in {elapsed:.2f}s",
                extra={"security_event": "scan_completed", "package_count": len(packages), "duration": elapsed}
            )
            logger.info(f"Found {len(packages)} total dependencies in {elapsed:.2f}s")

            return packages

    def _deduplicate_packages(self, packages: List[Package]) -> List[Package]:
        """Remove duplicate packages."""
        seen = set()
        unique = []
        for pkg in packages:
            key = f"{pkg.name}@{pkg.version}"
            if key not in seen:
                seen.add(key)
                unique.append(pkg)
        return unique
    
    def _sanitize_packages(self, packages: List[Package]) -> List[Package]:
        """Sanitize package data for security."""
        sanitized = []
        pii_detector = PIIDetector()
        
        for pkg in packages:
            try:
                # Check for PII in package metadata
                if pkg.copyright_text:
                    pii_found = pii_detector.detect(pkg.copyright_text)
                    if pii_found:
                        pkg.copyright_text = pii_detector.sanitize(pkg.copyright_text)
                        audit_logger.warning(
                            f"PII sanitized in package: {pkg.name}",
                            extra={"security_event": "pii_sanitized", "package": pkg.name}
                        )
                
                # Sanitize package name and version
                pkg.name = self._security.sanitize_input(pkg.name, "package_name")
                pkg.version = self._security.sanitize_input(pkg.version, "version")
                
                sanitized.append(pkg)
            except Exception as e:
                logger.warning(f"Error sanitizing package {pkg.name}: {e}")
                
        return sanitized


# ============================================================================
# Main SBOM Generator
# ============================================================================


class SBOMGenerator:
    """
    Software Bill of Materials generator with digital signatures.
    
    Orchestrates dependency scanning, license detection, vulnerability scanning,
    and format building using modular components and design patterns.
    
    Supports SPDX 2.3 and CycloneDX 1.4 formats with Ed25519 signatures.
    """

    def __init__(self, config: Optional[ConfigurationManager] = None):
        """
        Initialize SBOM generator with security and performance features.
        
        Args:
            config: Configuration manager for settings
        """
        self._config = config or ConfigurationManager()
        self._scanner = DependencyScanner()
        self._license_detector = LicenseDetector()
        self._vulnerability_scanner = VulnerabilityScanner()
        self._signer = Ed25519Signer(self._config)
        self._validator = SBOMValidator(self._signer)
        self._lock = threading.RLock()
        self._security = SecurityManager()
        self._generation_count = 0
        self._last_generation = None
        
        # Performance optimization
        self._perf_optimizer = PerformanceOptimizer()
        self._perf_monitor = self._perf_optimizer.perf_monitor
        self._cache_manager = self._perf_optimizer.cache_manager

    def generate(
        self,
        project_path: Path,
        format: SBOMFormat = SBOMFormat.SPDX,
        sign: bool = True,
        scan_vulnerabilities: bool = True,
    ) -> SBOM:
        """
        Generate SBOM for a project with comprehensive security controls.
        
        Args:
            project_path: Root directory of the project
            format: SBOM format (SPDX or CycloneDX)
            sign: Whether to digitally sign the SBOM
            scan_vulnerabilities: Whether to scan for vulnerabilities
            
        Returns:
            Generated SBOM with optional signature
            
        Raises:
            ValueError: If project path doesn't exist or is invalid
            RuntimeError: If generation fails
            SBOMError: If security violation detected
        """
        with self._lock:
            start_time = time.time()
            
            # Security: Rate limiting
            if not self._security.check_rate_limit("sbom_generation"):
                audit_logger.error(
                    "SBOM generation rate limit exceeded",
                    extra={"security_event": "sbom_rate_limit_exceeded"}
                )
                raise SBOMError("Rate limit exceeded for SBOM generation")
            
            # Security: Generation frequency check
            if self._last_generation:
                elapsed = time.time() - self._last_generation
                if elapsed < 1.0:  # Minimum 1 second between generations
                    audit_logger.warning(
                        "SBOM generation too frequent",
                        extra={"security_event": "sbom_generation_throttled"}
                    )
                    time.sleep(1.0 - elapsed)
            
            # Security: Path validation
            if not self._security.validate_path(project_path):
                audit_logger.error(
                    f"Invalid project path: {project_path}",
                    extra={"security_event": "invalid_sbom_path"}
                )
                raise ValueError(f"Invalid project path: {project_path}")
            
            # Validate project path existence
            if not project_path.exists():
                raise ValueError(f"Project path does not exist: {project_path}")

            if not project_path.is_dir():
                raise ValueError(f"Project path is not a directory: {project_path}")
            
            # Security: Check project size
            try:
                total_size = sum(
                    f.stat().st_size for f in project_path.rglob('*') if f.is_file()
                )
                if total_size > MAX_FILE_SIZE * 10:  # 1GB limit for entire project
                    audit_logger.error(
                        f"Project too large: {total_size} bytes",
                        extra={"security_event": "project_size_exceeded"}
                    )
                    raise SBOMError(f"Project too large: {total_size} bytes")
            except Exception as e:
                logger.warning(f"Could not calculate project size: {e}")
            
            audit_logger.info(
                f"Starting SBOM generation: {project_path}",
                extra={
                    "security_event": "sbom_generation_started",
                    "format": format.value,
                    "sign": sign,
                    "scan_vulnerabilities": scan_vulnerabilities
                }
            )

            logger.info(f"Generating {format} SBOM for {project_path}")

            try:
                # Scan dependencies
                packages = self._scanner.scan_project(project_path)
                logger.info(f"Scanned {len(packages)} dependencies")

                # Detect licenses in parallel batches
                logger.info("Starting parallel license detection...")
                license_start = time.time()
                
                # Use batch detection for efficiency
                license_results = self._license_detector.detect_batch(packages)
                for package in packages:
                    key = f"{package.name}@{package.version}"
                    if key in license_results and license_results[key]:
                        package.license = license_results[key]
                
                license_duration = time.time() - license_start
                licenses_detected = sum(1 for p in packages if p.license)
                
                self._perf_monitor.record_operation(
                    "license_detection_batch",
                    license_duration,
                    size=licenses_detected
                )
                
                logger.info(
                    f"Detected licenses for {licenses_detected}/{len(packages)} packages "
                    f"in {license_duration:.2f}s"
                )

                # Scan for vulnerabilities using batch processing
                vulnerabilities = []
                if scan_vulnerabilities:
                    logger.info("Starting batch vulnerability scanning...")
                    vuln_start = time.time()
                    
                    vulnerabilities = self._vulnerability_scanner.scan(packages)
                    
                    vuln_duration = time.time() - vuln_start
                    self._perf_monitor.record_operation(
                        "vulnerability_scan_batch",
                        vuln_duration,
                        size=len(vulnerabilities)
                    )
                    
                    if vulnerabilities:
                        logger.warning(
                            f"Found {len(vulnerabilities)} vulnerabilities "
                            f"in {vuln_duration:.2f}s"
                        )

                # Build SBOM using factory pattern
                builder = FormatBuilderFactory.get_builder(format)
                sbom = builder.build(project_path, packages, vulnerabilities)

                # Sign SBOM if requested
                if sign:
                    signature_value = self._signer.sign(sbom)
                    sbom.signature = SBOMSignature(
                        algorithm="Ed25519",
                        value=signature_value,
                        public_key=self._signer.public_key,
                        timestamp=datetime.now(timezone.utc),
                        signer="DevDocAI SBOM Generator",
                    )
                    logger.info("SBOM digitally signed with Ed25519")

                # Security: Check generation time
                elapsed = time.time() - start_time
                if elapsed > MAX_PROCESSING_TIME:
                    audit_logger.error(
                        f"SBOM generation timeout: {elapsed}s",
                        extra={"security_event": "sbom_generation_timeout"}
                    )
                    raise SBOMError(f"SBOM generation timeout: {elapsed}s")
                
                # Update generation tracking
                self._generation_count += 1
                self._last_generation = time.time()
                
                # Record overall performance metrics
                self._perf_monitor.record_operation(
                    "sbom_generation_total",
                    elapsed,
                    size=len(sbom.packages)
                )
                
                # Generate performance report
                perf_report = self._perf_optimizer.get_performance_report()
                logger.info(
                    f"Performance Report - "
                    f"Cache hit ratio: {perf_report['cache_stats']['overall_hit_ratio']:.1%}, "
                    f"Total operations: {perf_report['performance_metrics']['total_operations']}, "
                    f"Memory usage: {perf_report['memory_stats']['rss_mb']:.1f}MB"
                )
                
                audit_logger.info(
                    f"SBOM generation completed in {elapsed:.2f}s",
                    extra={
                        "security_event": "sbom_generation_completed",
                        "duration": elapsed,
                        "package_count": len(sbom.packages),
                        "vulnerability_count": len(sbom.vulnerabilities),
                        "signed": sbom.signature is not None,
                        "cache_hit_ratio": perf_report['cache_stats']['overall_hit_ratio']
                    }
                )
                
                logger.info(
                    f"Successfully generated {format} SBOM with {len(sbom.packages)} packages "
                    f"in {elapsed:.2f}s (Throughput: {len(sbom.packages)/elapsed:.1f} packages/s)"
                )
                return sbom

            except Exception as e:
                audit_logger.error(
                    f"SBOM generation failed: {e}",
                    extra={"security_event": "sbom_generation_failed", "error": str(e)}
                )
                logger.error(f"Error generating SBOM: {e}")
                raise RuntimeError(f"SBOM generation failed: {e}") from e

    @measure_performance("sbom_export")
    def export(self, sbom: SBOM, output_path: Path, pretty: bool = True, 
               use_streaming: bool = True) -> None:
        """
        Export SBOM to file with streaming support for large files.
        
        Args:
            sbom: SBOM to export
            output_path: Output file path
            pretty: Whether to pretty-print JSON
            use_streaming: Use streaming export for large SBOMs
            
        Raises:
            RuntimeError: If export fails
            SBOMError: If security violation detected
        """
        with self._lock:
            # Security: Path validation
            if not self._security.validate_path(output_path.parent):
                audit_logger.error(
                    f"Invalid export path: {output_path}",
                    extra={"security_event": "invalid_export_path"}
                )
                raise SBOMError(f"Invalid export path: {output_path}")
            
            # Security: Check file extension
            allowed_extensions = ['.json', '.spdx', '.cdx', '.sbom']
            if output_path.suffix.lower() not in allowed_extensions:
                audit_logger.warning(
                    f"Unusual SBOM file extension: {output_path.suffix}",
                    extra={"security_event": "unusual_sbom_extension"}
                )
            
            export_start = time.time()
            logger.info(f"Exporting SBOM to {output_path} (streaming={use_streaming})")

            try:
                # Convert to JSON
                json_data = sbom.model_dump(mode="json")
                
                # Security: Detect and sanitize PII before export
                json_str = json.dumps(json_data, default=str)
                pii_found = self._security.detect_pii(json_str)
                if pii_found:
                    audit_logger.warning(
                        f"PII detected in SBOM export: {len(pii_found)} instances",
                        extra={"security_event": "pii_in_sbom_export"}
                    )
                    # Optionally sanitize
                    pii_detector = PIIDetector()
                    json_str = pii_detector.sanitize(json_str)
                    json_data = json.loads(json_str)
                
                # Check if streaming is beneficial (>10MB or >1000 packages)
                estimated_size = len(json_str)
                should_stream = (
                    use_streaming and 
                    (estimated_size > 10 * 1024 * 1024 or len(sbom.packages) > 1000)
                )
                
                if should_stream:
                    # Use async streaming export for large files
                    logger.info(f"Using streaming export for large SBOM ({estimated_size} bytes)")
                    
                    # Run async export in sync context
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    try:
                        loop.run_until_complete(
                            StreamingExporter.stream_json_export(
                                json_data, output_path
                            )
                        )
                    finally:
                        loop.close()
                else:
                    # Standard export for smaller files
                    output_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    with open(output_path, "w", encoding="utf-8") as f:
                        if pretty:
                            json.dump(json_data, f, indent=2, default=str)
                        else:
                            json.dump(json_data, f, default=str)
                
                # Set restrictive permissions on output file
                output_path.chmod(0o644)
                
                export_duration = time.time() - export_start
                file_size = output_path.stat().st_size
                
                # Record performance metrics
                self._perf_monitor.record_operation(
                    "sbom_export",
                    export_duration,
                    size=file_size
                )
                
                audit_logger.info(
                    f"SBOM exported successfully in {export_duration:.2f}s",
                    extra={
                        "security_event": "sbom_exported",
                        "path": str(output_path),
                        "size": file_size,
                        "duration": export_duration,
                        "streaming": should_stream
                    }
                )
                
                logger.info(
                    f"SBOM exported successfully to {output_path} "
                    f"({file_size/1024/1024:.1f}MB in {export_duration:.2f}s, "
                    f"throughput: {file_size/1024/1024/export_duration:.1f}MB/s)"
                )

            except Exception as e:
                audit_logger.error(
                    f"SBOM export failed: {e}",
                    extra={"security_event": "sbom_export_failed", "error": str(e)}
                )
                logger.error(f"Error exporting SBOM: {e}")
                raise RuntimeError(f"SBOM export failed: {e}") from e
    
    def validate(self, sbom: SBOM) -> tuple[bool, List[str]]:
        """
        Validate SBOM against format specifications.
        
        Args:
            sbom: SBOM to validate
            
        Returns:
            Tuple of (is_valid, list_of_errors)
        """
        return self._validator.validate(sbom)
    
    def get_performance_report(self) -> Dict[str, Any]:
        """
        Get comprehensive performance report.
        
        Returns:
            Performance metrics and statistics
        """
        return self._perf_optimizer.get_performance_report()
    
    def cleanup(self):
        """
        Cleanup resources and save performance data.
        """
        # Log final performance report
        report = self.get_performance_report()
        logger.info(f"Final Performance Report: {report}")
        
        # Cleanup resources
        self._perf_optimizer.cleanup()