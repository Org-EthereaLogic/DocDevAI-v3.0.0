"""
M013 Template Marketplace Client - Refactored Main Orchestrator
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

This is the clean, refactored main orchestrator module that delegates to
specialized modules following the successful patterns from previous modules.
Target: <400 lines with clean delegation to specialized components.
"""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from ..core.config import ConfigurationManager
from .marketplace_cache import create_cache
from .marketplace_core import MarketplaceNetworkClient, TemplateIntegration, TemplateOperations
from .marketplace_crypto import TemplateSignatureManager, create_crypto_manager
from .marketplace_strategies import (
    DownloadStrategyFactory,
    MarketplaceStrategyManager,
    ValidationStrategyFactory,
)
from .marketplace_types import MarketplaceError, NetworkError, TemplateMetadata, ValidationLevel
from .marketplace_validators import ContentValidator, InputValidator, RateLimitValidator

logger = logging.getLogger(__name__)


class TemplateMarketplace:
    """
    Clean orchestrator for template marketplace operations.
    Delegates to specialized modules for all functionality.
    """

    def __init__(
        self,
        config: Optional[ConfigurationManager] = None,
        cache_dir: Optional[Path] = None,
        offline_mode: bool = False,
        validation_level: ValidationLevel = ValidationLevel.STANDARD,
        enable_crypto: bool = True,
    ):
        """
        Initialize marketplace orchestrator.

        Args:
            config: Configuration manager instance
            cache_dir: Directory for template cache
            offline_mode: Work offline with cached templates only
            validation_level: Validation strictness level
            enable_crypto: Enable cryptographic operations
        """
        # Configuration
        self.config = config or ConfigurationManager()
        self.offline_mode = offline_mode
        self.validation_level = validation_level

        # Load marketplace configuration
        self._load_config()

        # Initialize components
        self._initialize_components(cache_dir, enable_crypto)

        logger.info(
            f"Marketplace initialized - Validation: {validation_level.name}, Crypto: {enable_crypto}"
        )

    def _load_config(self):
        """Load configuration from M001 ConfigurationManager."""
        try:
            marketplace_config = self.config.get("marketplace", {})

            self.marketplace_url = marketplace_config.get(
                "url", "https://api.devdocai.com/templates"
            )
            self.api_key = marketplace_config.get("api_key")
            self.cache_ttl = marketplace_config.get("cache_ttl", 3600)
            self.max_cache_size_mb = marketplace_config.get("max_cache_size_mb", 100)
            self.verify_signatures = marketplace_config.get("verify_signatures", True)
            self.request_timeout = marketplace_config.get("request_timeout", 30)

        except Exception as e:
            logger.warning(f"Failed to load config, using defaults: {e}")
            self.marketplace_url = "https://api.devdocai.com/templates"
            self.api_key = None
            self.cache_ttl = 3600
            self.max_cache_size_mb = 100
            self.verify_signatures = True
            self.request_timeout = 30

    def _initialize_components(self, cache_dir: Optional[Path], enable_crypto: bool):
        """Initialize all marketplace components."""
        # Network client
        if not self.offline_mode:
            self.network_client = MarketplaceNetworkClient(
                base_url=self.marketplace_url, api_key=self.api_key, timeout=self.request_timeout
            )
            self.template_ops = TemplateOperations(self.network_client)
        else:
            self.network_client = None
            self.template_ops = None

        # Cache
        cache_dir = cache_dir or Path.home() / ".devdocai" / "template_cache"
        self.cache = create_cache(
            cache_type="multi",
            cache_dir=cache_dir,
            memory_size=100,
            disk_size_mb=self.max_cache_size_mb,
            ttl_seconds=self.cache_ttl,
        )

        # Crypto manager
        if enable_crypto and self.verify_signatures:
            self.crypto_manager = create_crypto_manager()
            self.signature_manager = (
                TemplateSignatureManager(self.crypto_manager) if self.crypto_manager else None
            )
        else:
            self.crypto_manager = None
            self.signature_manager = None

        # Validators
        self.input_validator = InputValidator()
        self.content_validator = ContentValidator()
        self.rate_limiter = RateLimitValidator()

        # Strategy manager
        self.strategy_manager = MarketplaceStrategyManager()
        self._register_strategies()

    def _register_strategies(self):
        """Register all strategies with the strategy manager."""
        # Register download strategies
        if self.network_client:
            self.strategy_manager.register_download_strategy(
                "standard", DownloadStrategyFactory.create("standard", self.network_client)
            )
            self.strategy_manager.register_download_strategy(
                "batch",
                DownloadStrategyFactory.create("batch", self.network_client, max_concurrent=4),
            )

        # Register validation strategies
        for level in ValidationLevel:
            strategy = ValidationStrategyFactory.create(level)
            self.strategy_manager.register_validation_strategy(level, strategy)

    # ========================================================================
    # Public API Methods
    # ========================================================================

    def discover_templates(
        self,
        query: Optional[str] = None,
        tags: Optional[List[str]] = None,
        min_rating: Optional[float] = None,
        sort_by: str = "downloads",
    ) -> List[TemplateMetadata]:
        """
        Discover templates from marketplace.

        Args:
            query: Search query
            tags: Filter by tags
            min_rating: Minimum rating filter
            sort_by: Sort field

        Returns:
            List of template metadata
        """
        # Check cache first
        cache_key = f"discover_{query}_{tags}_{min_rating}_{sort_by}"
        cached = self.cache.get(cache_key)
        if cached:
            return cached

        # Fetch from marketplace
        if self.template_ops and not self.offline_mode:
            try:
                templates = self.template_ops.discover(query, tags, min_rating, sort_by)

                # Validate and filter templates
                validated_templates = []
                for template in templates:
                    if self._validate_template(template):
                        validated_templates.append(template)

                # Cache results
                self.cache.set(cache_key, validated_templates, self.cache_ttl)

                return validated_templates

            except NetworkError as e:
                logger.error(f"Discovery failed: {e}")

        # Fall back to cached templates
        return self._list_cached_templates()

    def download_template(
        self, template_id: str, client_id: Optional[str] = None
    ) -> Optional[TemplateMetadata]:
        """
        Download a template from marketplace.

        Args:
            template_id: Template ID
            client_id: Client identifier for rate limiting

        Returns:
            Template metadata with content
        """
        # Validate input
        valid, error = self.input_validator.validate_template_id(template_id)
        if not valid:
            raise MarketplaceError(error)

        # Check rate limit
        client_id = client_id or "anonymous"
        allowed, retry_after = self.rate_limiter.check_rate_limit(client_id, "download")
        if not allowed:
            raise MarketplaceError(f"Rate limit exceeded. Retry after {retry_after} seconds")

        # Check cache
        cached = self.cache.get(f"template_{template_id}")
        if cached:
            return cached

        # Download from marketplace
        if self.template_ops and not self.offline_mode:
            try:
                template = self.template_ops.download(template_id)

                if template:
                    # Validate template
                    if self._validate_template(template):
                        # Verify signature if enabled
                        if self.signature_manager and template.signature:
                            if not self._verify_signature(template):
                                logger.warning(
                                    f"Template {template_id} signature verification failed"
                                )
                                if self.validation_level == ValidationLevel.STRICT:
                                    return None

                        # Cache template
                        self.cache.set(f"template_{template_id}", template)

                        return template

            except NetworkError as e:
                logger.error(f"Download failed for {template_id}: {e}")

        return cached  # Return cached version if available

    def publish_template(
        self, template: TemplateMetadata, client_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Publish a template to marketplace.

        Args:
            template: Template to publish
            client_id: Client identifier for rate limiting

        Returns:
            Publication result
        """
        if self.offline_mode:
            raise MarketplaceError("Cannot publish in offline mode")

        # Validate template
        if not self._validate_template(template):
            raise MarketplaceError("Template validation failed")

        # Check rate limit
        client_id = client_id or "anonymous"
        allowed, retry_after = self.rate_limiter.check_rate_limit(client_id, "upload")
        if not allowed:
            raise MarketplaceError(f"Rate limit exceeded. Retry after {retry_after} seconds")

        # Sign template if crypto available
        if self.signature_manager and self.crypto_manager:
            private_key, public_key = self.crypto_manager.generate_keypair()
            signature, public_key_b64 = self.signature_manager.sign_template(
                template.to_dict(), private_key
            )
            template.signature = signature
            template.public_key = public_key_b64

        # Publish
        if self.template_ops:
            result = self.template_ops.publish(template)
            logger.info(f"Published template: {result.get('id')}")
            return result

        raise MarketplaceError("Template operations not available")

    def apply_to_generator(self, template: TemplateMetadata, generator: Any) -> bool:
        """
        Apply template to M004 Document Generator.

        Args:
            template: Template to apply
            generator: Document Generator instance

        Returns:
            True if applied successfully
        """
        return TemplateIntegration.apply_to_generator(template, generator)

    def cleanup_cache(self) -> int:
        """
        Clean up expired cache entries.

        Returns:
            Number of entries removed
        """
        return self.cache.cleanup()

    def get_metrics(self) -> Dict[str, Any]:
        """
        Get marketplace metrics.

        Returns:
            Metrics dictionary
        """
        metrics = {
            "cache": self.cache.get_metrics() if hasattr(self.cache, "get_metrics") else {},
            "validation_level": self.validation_level.name,
            "offline_mode": self.offline_mode,
        }

        # Add rate limit info
        if hasattr(self.rate_limiter, "get_remaining_quota"):
            metrics["rate_limits"] = {
                "download": self.rate_limiter.get_remaining_quota("anonymous", "download"),
                "upload": self.rate_limiter.get_remaining_quota("anonymous", "upload"),
            }

        return metrics

    # ========================================================================
    # Private Helper Methods
    # ========================================================================

    def _validate_template(self, template: TemplateMetadata) -> bool:
        """Validate a template using configured validation strategy."""
        strategy = self.strategy_manager.get_validation_strategy(self.validation_level)
        if strategy:
            result = strategy.validate(template)
            if not result.is_valid:
                logger.warning(f"Template {template.id} validation failed: {result.errors}")
            return result.is_valid
        return True

    def _verify_signature(self, template: TemplateMetadata) -> bool:
        """Verify template signature."""
        if not self.signature_manager or not template.signature:
            return True

        return self.signature_manager.verify_template(
            template.to_dict(), template.signature, template.public_key or ""
        )

    def _list_cached_templates(self) -> List[TemplateMetadata]:
        """List all cached templates."""
        templates = []

        # This is simplified - real implementation would scan cache properly
        # For now, return empty list in offline mode
        return templates

    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, "network_client") and self.network_client:
            self.network_client.close()


# ============================================================================
# Factory Function
# ============================================================================


def create_marketplace(
    config: Optional[ConfigurationManager] = None, **kwargs
) -> TemplateMarketplace:
    """
    Factory function to create marketplace instance.

    Args:
        config: Configuration manager
        **kwargs: Additional marketplace parameters

    Returns:
        Configured marketplace instance
    """
    return TemplateMarketplace(config=config, **kwargs)
