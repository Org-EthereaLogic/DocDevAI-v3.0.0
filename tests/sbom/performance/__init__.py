"""
SBOM Performance Testing Modules.

Performance test modules for SBOM testing including:
- Generation speed testing (<30s targets)
- Scalability validation
- Memory usage optimization
"""

from .test_generation_speed import TestSBOMGenerationPerformance

__all__ = [
    'TestSBOMGenerationPerformance'
]