"""
M010 SBOM Generator - Type Definitions Module
DevDocAI v3.0.0 - Data models and type definitions for SBOM generation

This module contains all data models, enums, and type definitions used by
the SBOM Generator including Package, License, Vulnerability, and SBOM models.
"""

from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse

from pydantic import BaseModel, Field, field_validator

# ============================================================================
# Enums
# ============================================================================


class SBOMFormat(str, Enum):
    """Supported SBOM formats."""

    SPDX = "spdx-2.3"
    CYCLONEDX = "cyclonedx-1.4"


# ============================================================================
# Data Models
# ============================================================================


class LicenseInfo(BaseModel):
    """License information model with security validation."""

    license_id: str = Field(description="SPDX license identifier", max_length=256)
    license_name: str = Field(description="Human-readable license name", max_length=512)
    license_text: Optional[str] = Field(
        None, description="Full license text", max_length=1048576
    )  # 1MB limit
    is_osi_approved: bool = Field(False, description="OSI approved license")
    is_deprecated: bool = Field(False, description="Deprecated license")

    @field_validator("license_id", "license_name")
    def validate_no_injection(cls, v):
        """Validate against injection attacks."""
        if v and any(char in v for char in ["<", ">", "&", '"', "'", "\x00"]):
            raise ValueError("Invalid characters in license field")
        return v


class Vulnerability(BaseModel):
    """Security vulnerability model with validation."""

    cve_id: str = Field(description="CVE identifier", pattern=r"^CVE-\d{4}-\d{4,}$")
    severity: str = Field(description="Severity level", pattern=r"^(CRITICAL|HIGH|MEDIUM|LOW)$")
    cvss_score: float = Field(description="CVSS v3.1 score", ge=0.0, le=10.0)
    description: str = Field(description="Vulnerability description", max_length=4096)
    affected_versions: List[str] = Field(
        default_factory=list, description="Affected versions", max_length=100
    )
    fixed_versions: List[str] = Field(
        default_factory=list, description="Fixed versions", max_length=100
    )
    published_date: datetime = Field(description="Publication date")
    references: List[str] = Field(default_factory=list, description="Reference URLs", max_length=20)

    @field_validator("references")
    def validate_url(cls, v):
        """Validate reference URLs."""
        if v:
            validated = []
            for url in v:
                if url:
                    parsed = urlparse(url)
                    if parsed.scheme not in ["http", "https"]:
                        raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
                    if not parsed.netloc:
                        raise ValueError("Invalid URL: missing domain")
                    validated.append(url)
            return validated
        return v


class Package(BaseModel):
    """Software package/dependency model with security validation."""

    name: str = Field(description="Package name", max_length=256)
    version: str = Field(description="Package version", max_length=128)
    purl: Optional[str] = Field(None, description="Package URL (PURL)", max_length=512)
    file_path: Optional[Path] = Field(None, description="Local file path")
    hash_value: Optional[str] = Field(None, description="SHA-256 hash", pattern=r"^[a-f0-9]{64}$")
    license: Optional[LicenseInfo] = Field(None, description="License information")
    dependencies: List[str] = Field(
        default_factory=list, description="Direct dependencies", max_length=1000
    )
    vulnerabilities: List[Vulnerability] = Field(
        default_factory=list, description="Known vulnerabilities", max_length=100
    )
    download_location: Optional[str] = Field(None, description="Download URL", max_length=2048)
    homepage: Optional[str] = Field(None, description="Project homepage", max_length=2048)
    copyright_text: Optional[str] = Field(
        None, description="Copyright information", max_length=4096
    )

    @field_validator("name", "version")
    def sanitize_package_info(cls, v):
        """Sanitize package name and version."""
        if v:
            # Remove null bytes and control characters
            v = v.replace("\x00", "").strip()
            # Check for path traversal attempts (but allow forward slash for package names)
            if ".." in v or "\\" in v:
                raise ValueError("Invalid characters in package field")
        return v

    @field_validator("download_location", "homepage")
    def validate_urls(cls, v):
        """Validate and sanitize URLs."""
        if v:
            parsed = urlparse(v)
            if parsed.scheme not in ["http", "https", "git", "ftp"]:
                raise ValueError(f"Invalid URL scheme: {parsed.scheme}")
            if not parsed.netloc:
                raise ValueError("Invalid URL: missing domain")
        return v


class Relationship(BaseModel):
    """Package relationship model."""

    source: str = Field(description="Source package SPDX ID")
    target: str = Field(description="Target package SPDX ID")
    relationship_type: str = Field(description="Relationship type (e.g., DEPENDS_ON)")


class SBOMSignature(BaseModel):
    """Digital signature for SBOM."""

    algorithm: str = Field("Ed25519", description="Signature algorithm")
    value: str = Field(description="Base64-encoded signature")
    public_key: str = Field(description="Base64-encoded public key")
    timestamp: datetime = Field(description="Signature timestamp")
    signer: str = Field(description="Signer identity")


class SBOM(BaseModel):
    """Software Bill of Materials model."""

    format: SBOMFormat = Field(description="SBOM format")
    spec_version: str = Field(description="Format specification version")
    created: datetime = Field(description="Creation timestamp")
    creator: str = Field(description="Creator identity")
    document_namespace: str = Field(description="Document namespace/URI")
    name: str = Field(description="SBOM name")
    packages: List[Package] = Field(default_factory=list, description="Software packages")
    relationships: List[Relationship] = Field(
        default_factory=list, description="Package relationships"
    )
    vulnerabilities: List[Vulnerability] = Field(
        default_factory=list, description="All vulnerabilities"
    )
    signature: Optional[SBOMSignature] = Field(None, description="Digital signature")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


# ============================================================================
# Error Classes
# ============================================================================


class SBOMError(Exception):
    """Base exception for SBOM operations."""

    pass


class DependencyScanError(SBOMError):
    """Error during dependency scanning."""

    pass


class LicenseDetectionError(SBOMError):
    """Error during license detection."""

    pass


class VulnerabilityScanError(SBOMError):
    """Error during vulnerability scanning."""

    pass


class SignatureError(SBOMError):
    """Error during digital signature operations."""

    pass
