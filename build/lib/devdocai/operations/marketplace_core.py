"""
M013 Template Marketplace - Core Operations
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

This module contains core marketplace operations extracted from the main module,
focusing on essential template management functionality.
"""

import base64
import json
import logging
from typing import Any, Dict, List, Optional, Tuple

from .marketplace_types import NetworkError, TemplateMetadata

logger = logging.getLogger(__name__)


class MarketplaceNetworkClient:
    """Network client for marketplace API communication."""

    def __init__(self, base_url: str, api_key: Optional[str] = None, timeout: int = 30):
        """
        Initialize network client.

        Args:
            base_url: Base URL for marketplace API
            api_key: Optional API key for authentication
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.api_key = api_key
        self.timeout = timeout
        self._session = None

        # Initialize session if requests available
        try:
            import requests

            self._session = requests.Session()
            self._session.headers.update(
                {"User-Agent": "DevDocAI/3.0.0", "Accept": "application/json"}
            )
            if self.api_key:
                self._session.headers["Authorization"] = f"Bearer {self.api_key}"
        except ImportError:
            logger.warning("requests library not available - network features disabled")

    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Make GET request to marketplace API.

        Args:
            endpoint: API endpoint
            params: Query parameters

        Returns:
            Response data

        Raises:
            NetworkError: On network failures
        """
        if not self._session:
            raise NetworkError("Network client not initialized")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self._session.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise NetworkError(f"GET request failed: {e}")

    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make POST request to marketplace API.

        Args:
            endpoint: API endpoint
            data: Request data

        Returns:
            Response data

        Raises:
            NetworkError: On network failures
        """
        if not self._session:
            raise NetworkError("Network client not initialized")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self._session.post(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise NetworkError(f"POST request failed: {e}")

    def put(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Make PUT request to marketplace API.

        Args:
            endpoint: API endpoint
            data: Request data

        Returns:
            Response data

        Raises:
            NetworkError: On network failures
        """
        if not self._session:
            raise NetworkError("Network client not initialized")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self._session.put(url, json=data, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise NetworkError(f"PUT request failed: {e}")

    def delete(self, endpoint: str) -> bool:
        """
        Make DELETE request to marketplace API.

        Args:
            endpoint: API endpoint

        Returns:
            True if successful

        Raises:
            NetworkError: On network failures
        """
        if not self._session:
            raise NetworkError("Network client not initialized")

        url = f"{self.base_url}/{endpoint.lstrip('/')}"

        try:
            response = self._session.delete(url, timeout=self.timeout)
            response.raise_for_status()
            return True
        except Exception as e:
            raise NetworkError(f"DELETE request failed: {e}")

    def close(self):
        """Close network session."""
        if self._session:
            self._session.close()


class TemplateOperations:
    """Core template operations."""

    def __init__(self, network_client: MarketplaceNetworkClient):
        """
        Initialize template operations.

        Args:
            network_client: Network client for API communication
        """
        self.network_client = network_client

    def discover(
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
        params = {}
        if query:
            params["q"] = query
        if tags:
            params["tags"] = ",".join(tags)
        if min_rating:
            params["min_rating"] = min_rating
        params["sort"] = sort_by

        try:
            response = self.network_client.get("/templates", params=params)

            templates = []
            for template_data in response.get("templates", []):
                template = TemplateMetadata.from_dict(template_data)
                templates.append(template)

            return templates
        except NetworkError as e:
            logger.error(f"Template discovery failed: {e}")
            return []

    def download(self, template_id: str) -> Optional[TemplateMetadata]:
        """
        Download a template from marketplace.

        Args:
            template_id: Template ID

        Returns:
            Template metadata with content
        """
        try:
            response = self.network_client.get(f"/templates/{template_id}")

            # Decode content if encoded
            if "content" in response and response["content"]:
                try:
                    response["content"] = base64.b64decode(response["content"]).decode("utf-8")
                except Exception:
                    pass  # Content might not be encoded

            return TemplateMetadata.from_dict(response)
        except NetworkError as e:
            logger.error(f"Template download failed for {template_id}: {e}")
            return None

    def publish(self, template: TemplateMetadata) -> Dict[str, Any]:
        """
        Publish a template to marketplace.

        Args:
            template: Template to publish

        Returns:
            Publication result
        """
        # Prepare template data
        template_data = template.to_dict()

        # Encode content
        if template_data.get("content"):
            template_data["content"] = base64.b64encode(template_data["content"].encode()).decode()

        return self.network_client.post("/templates", template_data)

    def update(self, template_id: str, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update an existing template.

        Args:
            template_id: Template ID
            updates: Update data

        Returns:
            Update result
        """
        # Encode content if present
        if "content" in updates:
            updates["content"] = base64.b64encode(updates["content"].encode()).decode()

        return self.network_client.put(f"/templates/{template_id}", updates)

    def delete(self, template_id: str) -> bool:
        """
        Delete a template from marketplace.

        Args:
            template_id: Template ID

        Returns:
            True if deleted successfully
        """
        return self.network_client.delete(f"/templates/{template_id}")

    def get_versions(self, template_id: str) -> List[Dict[str, Any]]:
        """
        Get available versions of a template.

        Args:
            template_id: Template ID

        Returns:
            List of version information
        """
        response = self.network_client.get(f"/templates/{template_id}/versions")
        return response.get("versions", [])

    def get_statistics(self, template_id: str) -> Dict[str, Any]:
        """
        Get statistics for a template.

        Args:
            template_id: Template ID

        Returns:
            Template statistics
        """
        return self.network_client.get(f"/templates/{template_id}/stats")


class TemplateValidator:
    """Template validation utilities."""

    @staticmethod
    def validate_metadata(template: TemplateMetadata) -> Tuple[bool, List[str]]:
        """
        Validate template metadata.

        Args:
            template: Template to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Required fields
        if not template.id:
            errors.append("Template ID is required")
        if not template.name:
            errors.append("Template name is required")
        if not template.version:
            errors.append("Template version is required")
        if not template.author:
            errors.append("Template author is required")

        # Version format (semver)
        import re

        if template.version and not re.match(r"^\d+\.\d+\.\d+(-\w+)?$", template.version):
            errors.append(f"Invalid version format: {template.version}")

        return len(errors) == 0, errors

    @staticmethod
    def validate_content(content: str) -> Tuple[bool, List[str]]:
        """
        Validate template content for security issues.

        Args:
            content: Template content

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        if not content:
            errors.append("Template content is empty")
            return False, errors

        # Check for dangerous patterns
        import re

        dangerous_patterns = [
            (r"<script[^>]*>", "Script tags not allowed"),
            (r"javascript:", "JavaScript URLs not allowed"),
            (r"on\w+\s*=", "Event handlers not allowed"),
            (r"eval\s*\(", "eval() not allowed"),
            (r"exec\s*\(", "exec() not allowed"),
        ]

        for pattern, message in dangerous_patterns:
            if re.search(pattern, content, re.IGNORECASE):
                errors.append(message)

        # Check size
        if len(content) > 10 * 1024 * 1024:  # 10MB
            errors.append("Template content exceeds maximum size (10MB)")

        return len(errors) == 0, errors

    @staticmethod
    def sanitize_content(content: str) -> str:
        """
        Sanitize template content by removing dangerous patterns.

        Args:
            content: Content to sanitize

        Returns:
            Sanitized content
        """
        import re

        # Remove script tags
        content = re.sub(r"<script[^>]*>.*?</script>", "", content, flags=re.IGNORECASE | re.DOTALL)

        # Remove event handlers
        content = re.sub(r'\son\w+\s*=\s*["\'][^"\']*["\']', "", content, flags=re.IGNORECASE)

        # Remove javascript: URLs
        content = re.sub(r"javascript:", "", content, flags=re.IGNORECASE)

        # Remove eval and exec calls
        content = re.sub(r"\b(eval|exec)\s*\([^)]*\)", "", content, flags=re.IGNORECASE)

        return content


class TemplateSerializer:
    """Template serialization utilities."""

    @staticmethod
    def serialize(template: TemplateMetadata) -> str:
        """
        Serialize template to JSON string.

        Args:
            template: Template to serialize

        Returns:
            JSON string
        """
        return json.dumps(template.to_dict(), indent=2, default=str)

    @staticmethod
    def deserialize(data: str) -> TemplateMetadata:
        """
        Deserialize template from JSON string.

        Args:
            data: JSON string

        Returns:
            Template metadata
        """
        template_dict = json.loads(data)
        return TemplateMetadata.from_dict(template_dict)

    @staticmethod
    def encode_content(content: str) -> str:
        """
        Encode template content for transmission.

        Args:
            content: Content to encode

        Returns:
            Base64 encoded content
        """
        return base64.b64encode(content.encode()).decode()

    @staticmethod
    def decode_content(encoded: str) -> str:
        """
        Decode template content from transmission format.

        Args:
            encoded: Base64 encoded content

        Returns:
            Decoded content
        """
        return base64.b64decode(encoded).decode()


class TemplateIntegration:
    """Template integration with M004 Document Generator."""

    @staticmethod
    def apply_to_generator(template: TemplateMetadata, generator: Any) -> bool:
        """
        Apply template to document generator.

        Args:
            template: Template to apply
            generator: Document Generator instance

        Returns:
            True if applied successfully
        """
        try:
            # Set template content
            if hasattr(generator, "set_template"):
                generator.set_template(template.content)

            # Set metadata
            if hasattr(generator, "set_metadata"):
                generator.set_metadata(
                    {
                        "template_id": template.id,
                        "template_name": template.name,
                        "template_version": template.version,
                        "template_author": template.author,
                    }
                )

            logger.info(f"Applied template {template.id} to generator")
            return True

        except Exception as e:
            logger.error(f"Failed to apply template: {e}")
            return False

    @staticmethod
    def extract_from_generator(generator: Any) -> Optional[TemplateMetadata]:
        """
        Extract current template from document generator.

        Args:
            generator: Document Generator instance

        Returns:
            Template metadata if available
        """
        try:
            if not hasattr(generator, "get_template"):
                return None

            template_content = generator.get_template()
            if not template_content:
                return None

            # Get metadata if available
            metadata = {}
            if hasattr(generator, "get_metadata"):
                metadata = generator.get_metadata() or {}

            # Create template
            return TemplateMetadata(
                id=metadata.get("template_id", "generated"),
                name=metadata.get("template_name", "Generated Template"),
                description="Template extracted from Document Generator",
                version=metadata.get("template_version", "1.0.0"),
                author=metadata.get("template_author", "DevDocAI"),
                content=template_content,
            )

        except Exception as e:
            logger.error(f"Failed to extract template: {e}")
            return None
