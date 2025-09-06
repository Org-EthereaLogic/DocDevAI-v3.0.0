"""
Template Marketplace Client - M013
Core module for accessing and sharing community templates.

This module provides the main TemplateMarketplaceClient class that interfaces
with the DevDocAI template marketplace, handling browsing, downloading,
publishing, and signature verification of templates.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import urljoin

from .api_client import MarketplaceAPIClient
from .certificate_manager import CertificateManager
from .signature_verifier import Ed25519Verifier
from .template_cache import TemplateCache
from .template_publisher import TemplatePublisher

logger = logging.getLogger(__name__)


class TemplateMarketplaceClient:
    """
    Main client for interacting with the DevDocAI Template Marketplace.
    
    This client provides comprehensive functionality for:
    - Browsing and searching templates
    - Downloading templates with signature verification
    - Publishing templates to the marketplace
    - Managing local template cache
    - Certificate and revocation checking
    """
    
    def __init__(
        self,
        marketplace_url: str = "https://marketplace.devdocai.org",
        cache_dir: Optional[Path] = None,
        api_key: Optional[str] = None,
        offline_mode: bool = False
    ):
        """
        Initialize the Template Marketplace Client.
        
        Args:
            marketplace_url: Base URL of the marketplace API
            cache_dir: Directory for local template cache
            api_key: Optional API key for authenticated operations
            offline_mode: Enable offline/cache-only mode
        """
        self.marketplace_url = marketplace_url
        self.offline_mode = offline_mode
        
        # Initialize components
        self.api_client = MarketplaceAPIClient(
            base_url=marketplace_url,
            api_key=api_key,
            offline_mode=offline_mode
        )
        
        self.local_cache = TemplateCache(cache_dir)
        self.signature_verifier = Ed25519Verifier()
        self.certificate_manager = CertificateManager()
        self.publisher = TemplatePublisher(self.api_client, self.signature_verifier)
        
        # Statistics and metrics
        self.stats = {
            "templates_browsed": 0,
            "templates_downloaded": 0,
            "templates_published": 0,
            "cache_hits": 0,
            "signature_verifications": 0,
            "failed_verifications": 0
        }
        
        logger.info(f"Marketplace client initialized (offline_mode={offline_mode})")
    
    def browse_templates(
        self,
        category: Optional[str] = None,
        search: Optional[str] = None,
        sort_by: str = "popularity",
        page: int = 1,
        per_page: int = 20
    ) -> Dict[str, Any]:
        """
        Browse templates in the marketplace.
        
        Args:
            category: Filter by category (e.g., "documentation", "api", "readme")
            search: Search query string
            sort_by: Sort criteria ("popularity", "recent", "rating")
            page: Page number for pagination
            per_page: Items per page
            
        Returns:
            Dictionary containing templates and pagination info
        """
        self.stats["templates_browsed"] += 1
        
        # Check cache first for offline mode
        if self.offline_mode:
            logger.info("Browsing templates from local cache (offline mode)")
            return self.local_cache.browse_cached_templates(
                category=category,
                search=search,
                sort_by=sort_by,
                page=page,
                per_page=per_page
            )
        
        try:
            # Fetch from marketplace API
            result = self.api_client.browse_templates(
                category=category,
                search=search,
                sort_by=sort_by,
                page=page,
                per_page=per_page
            )
            
            # Cache the results for offline access
            if result and "templates" in result:
                for template in result["templates"]:
                    self.local_cache.cache_template_metadata(template)
            
            return result
            
        except Exception as e:
            logger.warning(f"Failed to browse from marketplace: {e}, falling back to cache")
            return self.local_cache.browse_cached_templates(
                category=category,
                search=search,
                sort_by=sort_by,
                page=page,
                per_page=per_page
            )
    
    def search_templates(self, query: str, **kwargs) -> Dict[str, Any]:
        """
        Search for templates matching a query.
        
        Args:
            query: Search query string
            **kwargs: Additional search parameters
            
        Returns:
            Search results with matching templates
        """
        return self.browse_templates(search=query, **kwargs)
    
    def download_template(
        self,
        template_id: str,
        verify_signature: bool = True,
        force_download: bool = False
    ) -> Tuple[Dict[str, Any], bool]:
        """
        Download a template from the marketplace with signature verification.
        
        Args:
            template_id: Unique identifier of the template
            verify_signature: Whether to verify Ed25519 signature
            force_download: Force download even if cached
            
        Returns:
            Tuple of (template_data, verification_success)
        """
        self.stats["templates_downloaded"] += 1
        
        # Check local cache first
        if not force_download:
            cached_template = self.local_cache.get_template(template_id)
            if cached_template:
                logger.info(f"Template {template_id} loaded from cache")
                self.stats["cache_hits"] += 1
                return cached_template, True
        
        if self.offline_mode:
            logger.warning(f"Cannot download {template_id} in offline mode")
            cached = self.local_cache.get_template(template_id)
            if cached:
                return cached, True
            return {}, False
        
        try:
            # Download from marketplace
            template_data = self.api_client.download_template(template_id)
            
            if not template_data:
                logger.error(f"Failed to download template {template_id}")
                return {}, False
            
            # Verify signature if requested
            verification_success = True
            if verify_signature and "signature" in template_data:
                self.stats["signature_verifications"] += 1
                
                # Check certificate revocation
                if not self.certificate_manager.check_certificate(
                    template_data.get("author_certificate", "")
                ):
                    logger.warning(f"Certificate revoked for template {template_id}")
                    verification_success = False
                    self.stats["failed_verifications"] += 1
                else:
                    # Verify Ed25519 signature
                    content_bytes = json.dumps(
                        template_data.get("content", {}),
                        sort_keys=True
                    ).encode()
                    
                    verification_success = self.signature_verifier.verify(
                        content_bytes,
                        template_data["signature"],
                        template_data.get("public_key", "")
                    )
                    
                    if not verification_success:
                        logger.warning(f"Signature verification failed for {template_id}")
                        self.stats["failed_verifications"] += 1
            
            # Cache the template
            if verification_success:
                self.local_cache.save_template(template_id, template_data)
                logger.info(f"Template {template_id} downloaded and cached")
            
            return template_data, verification_success
            
        except Exception as e:
            logger.error(f"Error downloading template {template_id}: {e}")
            # Try to return cached version as fallback
            cached = self.local_cache.get_template(template_id)
            if cached:
                return cached, True
            return {}, False
    
    def publish_template(
        self,
        template: Dict[str, Any],
        sign: bool = True,
        private_key_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Publish a template to the marketplace.
        
        Args:
            template: Template data to publish
            sign: Whether to sign the template with Ed25519
            private_key_path: Path to private key for signing
            
        Returns:
            Tuple of (success, template_id or error_message)
        """
        if self.offline_mode:
            logger.error("Cannot publish templates in offline mode")
            return False, "Offline mode enabled"
        
        self.stats["templates_published"] += 1
        
        try:
            # Validate template structure
            if not self._validate_template_structure(template):
                return False, "Invalid template structure"
            
            # Publish through the publisher component
            success, result = self.publisher.publish(
                template=template,
                sign=sign,
                private_key_path=private_key_path
            )
            
            if success:
                # Cache the published template locally
                self.local_cache.save_template(result, template)
                logger.info(f"Template published successfully with ID: {result}")
            
            return success, result
            
        except Exception as e:
            logger.error(f"Error publishing template: {e}")
            return False, str(e)
    
    def get_template_info(self, template_id: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a template.
        
        Args:
            template_id: Template identifier
            
        Returns:
            Template information or None if not found
        """
        # Try cache first
        cached = self.local_cache.get_template_metadata(template_id)
        if cached:
            return cached
        
        if self.offline_mode:
            return None
        
        try:
            # Fetch from API
            info = self.api_client.get_template_info(template_id)
            if info:
                self.local_cache.cache_template_metadata(info)
            return info
        except Exception as e:
            logger.error(f"Error fetching template info: {e}")
            return None
    
    def verify_signature(
        self,
        content: bytes,
        signature: str,
        public_key: str
    ) -> bool:
        """
        Verify an Ed25519 signature.
        
        Args:
            content: Content that was signed
            signature: Ed25519 signature
            public_key: Public key for verification
            
        Returns:
            True if signature is valid
        """
        return self.signature_verifier.verify(content, signature, public_key)
    
    def clear_cache(self) -> bool:
        """Clear the local template cache."""
        return self.local_cache.clear()
    
    def get_cache_info(self) -> Dict[str, Any]:
        """Get information about the local cache."""
        return self.local_cache.get_cache_info()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics."""
        return {
            **self.stats,
            "cache_info": self.get_cache_info(),
            "offline_mode": self.offline_mode,
            "marketplace_url": self.marketplace_url
        }
    
    def _validate_template_structure(self, template: Dict[str, Any]) -> bool:
        """
        Validate template structure before publishing.
        
        Args:
            template: Template to validate
            
        Returns:
            True if valid
        """
        required_fields = ["name", "version", "description", "content", "category"]
        
        for field in required_fields:
            if field not in template:
                logger.error(f"Template missing required field: {field}")
                return False
        
        # Validate version format (semver)
        version = template.get("version", "")
        if not self._is_valid_semver(version):
            logger.error(f"Invalid version format: {version}")
            return False
        
        # Validate category
        valid_categories = [
            "documentation", "api", "readme", "tutorial",
            "guide", "specification", "architecture", "other"
        ]
        if template.get("category") not in valid_categories:
            logger.error(f"Invalid category: {template.get('category')}")
            return False
        
        return True
    
    def _is_valid_semver(self, version: str) -> bool:
        """Check if version string is valid semver."""
        import re
        pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?(\+[a-zA-Z0-9]+(\.[a-zA-Z0-9]+)*)?$"
        return bool(re.match(pattern, version))
    
    def __repr__(self) -> str:
        """String representation of the client."""
        return (
            f"TemplateMarketplaceClient("
            f"url={self.marketplace_url}, "
            f"offline={self.offline_mode}, "
            f"cached_templates={len(self.local_cache)})"
        )