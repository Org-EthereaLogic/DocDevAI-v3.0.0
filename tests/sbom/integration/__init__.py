"""
SBOM Integration Testing Modules.

Integration test modules for SBOM testing including:
- M001 Configuration Manager integration
- M002 Local Storage System integration
- M003 MIAIR Engine integration
- Cross-module workflow validation
"""

from .test_sbom_integration import TestSBOMIntegration

__all__ = [
    'TestSBOMIntegration'
]