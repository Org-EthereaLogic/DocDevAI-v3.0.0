"""
Template Publisher
Handles publishing templates to the marketplace.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class TemplatePublisher:
    """
    Template publishing functionality for the marketplace.
    
    Handles template validation, signing, and submission to the marketplace.
    """
    
    def __init__(
        self,
        api_client,
        signature_verifier
    ):
        """
        Initialize the template publisher.
        
        Args:
            api_client: MarketplaceAPIClient instance
            signature_verifier: Ed25519Verifier instance
        """
        self.api_client = api_client
        self.signature_verifier = signature_verifier
        
        # Statistics
        self.templates_published = 0
        self.publish_failures = 0
        
        logger.info("Template publisher initialized")
    
    def publish(
        self,
        template: Dict[str, Any],
        sign: bool = True,
        private_key_path: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Publish a template to the marketplace.
        
        Args:
            template: Template data to publish
            sign: Whether to sign the template
            private_key_path: Path to private key file
            
        Returns:
            Tuple of (success, template_id or error_message)
        """
        try:
            # Validate template
            validation_result = self._validate_template(template)
            if not validation_result[0]:
                return validation_result
            
            # Add metadata
            template = self._add_metadata(template)
            
            # Sign template if requested
            signature = None
            if sign:
                signature = self._sign_template(template, private_key_path)
                if not signature:
                    return False, "Failed to sign template"
            
            # Publish to marketplace
            response = self.api_client.publish_template(template, signature)
            
            if response.get("error"):
                self.publish_failures += 1
                return False, response.get("message", "Unknown error")
            
            template_id = response.get("template_id")
            if not template_id:
                # Generate demo ID for offline mode
                template_id = f"template-{datetime.now().strftime('%Y%m%d-%H%M%S')}"
            
            self.templates_published += 1
            logger.info(f"Template published successfully: {template_id}")
            
            return True, template_id
            
        except Exception as e:
            self.publish_failures += 1
            logger.error(f"Publishing error: {e}")
            return False, str(e)
    
    def _validate_template(
        self,
        template: Dict[str, Any]
    ) -> Tuple[bool, str]:
        """
        Validate template structure and content.
        
        Args:
            template: Template to validate
            
        Returns:
            Tuple of (valid, error_message)
        """
        # Check required fields
        required_fields = [
            "name",
            "version",
            "description",
            "content",
            "category"
        ]
        
        for field in required_fields:
            if field not in template:
                return False, f"Missing required field: {field}"
        
        # Validate name
        name = template.get("name", "")
        if not name or len(name) < 3 or len(name) > 100:
            return False, "Name must be between 3 and 100 characters"
        
        # Validate version (semver)
        version = template.get("version", "")
        if not self._is_valid_semver(version):
            return False, f"Invalid version format: {version}"
        
        # Validate description
        description = template.get("description", "")
        if not description or len(description) < 10 or len(description) > 500:
            return False, "Description must be between 10 and 500 characters"
        
        # Validate category
        valid_categories = [
            "documentation",
            "api",
            "readme",
            "tutorial",
            "guide",
            "specification",
            "architecture",
            "other"
        ]
        
        category = template.get("category", "")
        if category not in valid_categories:
            return False, f"Invalid category: {category}. Must be one of: {', '.join(valid_categories)}"
        
        # Validate content
        content = template.get("content")
        if not content:
            return False, "Content cannot be empty"
        
        if isinstance(content, dict):
            if not content.get("template_text"):
                return False, "Content must include template_text"
        elif isinstance(content, str):
            if len(content) < 50:
                return False, "Content too short (minimum 50 characters)"
        else:
            return False, "Content must be string or dictionary"
        
        # Validate tags (optional)
        tags = template.get("tags", [])
        if tags and not isinstance(tags, list):
            return False, "Tags must be a list"
        
        if len(tags) > 10:
            return False, "Maximum 10 tags allowed"
        
        return True, "Valid"
    
    def _add_metadata(
        self,
        template: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Add publishing metadata to template.
        
        Args:
            template: Template to enhance
            
        Returns:
            Template with metadata
        """
        # Add timestamps
        now = datetime.utcnow().isoformat() + "Z"
        
        if "created_at" not in template:
            template["created_at"] = now
        
        template["updated_at"] = now
        
        # Add author info (demo)
        if "author" not in template:
            template["author"] = "DevDocAI User"
        
        # Add default tags if missing
        if "tags" not in template:
            template["tags"] = [template.get("category", "other")]
        
        # Add schema version
        template["schema_version"] = "1.0.0"
        
        return template
    
    def _sign_template(
        self,
        template: Dict[str, Any],
        private_key_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Sign template with Ed25519.
        
        Args:
            template: Template to sign
            private_key_path: Path to private key
            
        Returns:
            Base64-encoded signature or None
        """
        try:
            # Get private key
            private_key = self._load_private_key(private_key_path)
            if not private_key:
                # Generate new keypair for demo
                private_key, public_key = self.signature_verifier.generate_keypair()
                logger.info("Generated new keypair for signing")
                
                # Save public key in template
                template["public_key"] = public_key
            
            # Create content to sign
            content = json.dumps(
                template.get("content", {}),
                sort_keys=True
            ).encode()
            
            # Sign content
            signature = self.signature_verifier.sign(content, private_key)
            
            return signature
            
        except Exception as e:
            logger.error(f"Signing error: {e}")
            return None
    
    def _load_private_key(
        self,
        private_key_path: Optional[str] = None
    ) -> Optional[str]:
        """
        Load private key from file.
        
        Args:
            private_key_path: Path to key file
            
        Returns:
            Private key or None
        """
        if not private_key_path:
            # Check default location
            default_path = Path.home() / ".devdocai" / "marketplace_key.pem"
            if default_path.exists():
                private_key_path = str(default_path)
            else:
                return None
        
        try:
            with open(private_key_path, 'r') as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load private key: {e}")
            return None
    
    def _is_valid_semver(self, version: str) -> bool:
        """
        Check if version string is valid semver.
        
        Args:
            version: Version string
            
        Returns:
            True if valid semver
        """
        import re
        # Simplified semver pattern
        pattern = r"^\d+\.\d+\.\d+(-[a-zA-Z0-9]+)?(\+[a-zA-Z0-9]+)?$"
        return bool(re.match(pattern, version))
    
    def get_stats(self) -> Dict:
        """Get publisher statistics."""
        total = self.templates_published + self.publish_failures
        return {
            "templates_published": self.templates_published,
            "publish_failures": self.publish_failures,
            "success_rate": self.templates_published / max(1, total)
        }