"""
M010: SBOM Generator Module
Software Bill of Materials generation with digital signatures
Per SDD Section 5.5 specifications
"""

from .sbom_generator import SBOMGenerator
from .dependency_scanner import DependencyScanner
from .license_detector import LicenseDetector
from .vulnerability_scanner import VulnerabilityScanner
from .signer import Ed25519Signer

__all__ = [
    'SBOMGenerator',
    'DependencyScanner',
    'LicenseDetector',
    'VulnerabilityScanner',
    'Ed25519Signer'
]

__version__ = '3.5.0'