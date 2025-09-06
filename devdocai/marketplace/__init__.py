"""
DevDocAI Template Marketplace Client - M013
Access and share community templates with signature verification.
"""

from .marketplace_client import TemplateMarketplaceClient
from .signature_verifier import Ed25519Verifier
from .template_cache import TemplateCache
from .certificate_manager import CertificateManager
from .api_client import MarketplaceAPIClient
from .template_publisher import TemplatePublisher

__version__ = "3.0.0"
__all__ = [
    "TemplateMarketplaceClient",
    "Ed25519Verifier",
    "TemplateCache",
    "CertificateManager",
    "MarketplaceAPIClient",
    "TemplatePublisher"
]