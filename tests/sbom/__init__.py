"""
SBOM Testing Framework for M010 Security Module.

Comprehensive testing infrastructure for Software Bill of Materials (SBOM)
generation, validation, and security analysis.

Supports:
- SPDX 2.3 (JSON-LD, RDF/XML, YAML, Tag-Value)
- CycloneDX 1.4 (JSON, XML)
- Dependency tree completeness (100% coverage)
- License identification (≥95% accuracy)
- CVE vulnerability scanning (≥98% precision/recall)
- Ed25519 digital signatures (100% verification)
- Performance testing (<30s generation)

Quality targets:
- Test Coverage: 95% (matching M001-M008 standards)
- Format Compliance: 100% schema validation
- Security: Enterprise-grade validation
"""

# Version information
__version__ = "1.0.0"
__author__ = "DevDocAI Team"

# Framework components
from .core import SBOMTestFramework
from .validators import SPDXValidator, CycloneDXValidator
from .generators import SBOMTestDataGenerator
from .assertions import SBOMAssertions

__all__ = [
    'SBOMTestFramework',
    'SPDXValidator', 
    'CycloneDXValidator',
    'SBOMTestDataGenerator',
    'SBOMAssertions'
]