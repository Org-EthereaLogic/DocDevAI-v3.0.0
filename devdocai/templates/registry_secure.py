"""
Security-hardened Template Registry for M006.

This module provides the secure version of the template registry with
comprehensive security features integrated.
"""

from typing import Dict, List, Optional, Union, Any, Callable
from pathlib import Path
import logging
from datetime import datetime
import threading
import hashlib

from ..core.config import ConfigurationManager  # M001 integration
from ..storage.secure_storage import SecureStorageLayer  # M002 integration
from ..storage.pii_detector import PIIDetector  # M002 PII detection
from .models import (
    Template as TemplateModel,
    TemplateMetadata,
    TemplateSearchCriteria,
    TemplateCategory,
    TemplateType,
    TemplateRenderContext,
    TemplateValidationResult
)
from .template import Template
from .loader import TemplateLoader
from .validator import TemplateValidator
from .categories import CategoryManager
from .template_security import TemplateSecurity, TemplatePermissionManager
from .template_sandbox import TemplateSandbox
from .secure_parser import SecureTemplateParser
from .registry_optimized import OptimizedTemplateRegistry
from .exceptions import (
    TemplateNotFoundError,
    TemplateDuplicateError,
    TemplateStorageError,
    TemplateValidationError,
    TemplateSecurityError,
    TemplateSSTIError,
    TemplateRateLimitError,
    TemplatePermissionError
)

logger = logging.getLogger(__name__)


class SecureTemplateRegistry(OptimizedTemplateRegistry):
    """
    Security-hardened template registry with comprehensive protection.
    
    Features:
    - SSTI prevention
    - XSS protection
    - Path traversal prevention
    - Rate limiting
    - Permission management
    - PII detection and masking
    - Audit logging
    - Sandboxed execution
    """
    
    def __init__(self,
                 config_manager: Optional[ConfigurationManager] = None,
                 storage: Optional[SecureStorageLayer] = None,
                 auto_load_defaults: bool = True,
                 enable_security: bool = True,
                 enable_pii_detection: bool = True,
                 enable_rate_limiting: bool = True,
                 enable_sandbox: bool = True,
                 enable_audit_logging: bool = True):
        """
        Initialize secure template registry.
        
        Args:
            config_manager: Configuration manager (M001)
            storage: Storage system (M002)
            auto_load_defaults: Whether to auto-load default templates
            enable_security: Enable security features
            enable_pii_detection: Enable PII detection
            enable_rate_limiting: Enable rate limiting
            enable_sandbox: Enable sandboxed execution
            enable_audit_logging: Enable audit logging
        """
        # Initialize parent (optimized registry)
        super().__init__(config_manager, storage, auto_load_defaults)
        
        # Security configuration
        self.enable_security = enable_security
        self.enable_pii_detection = enable_pii_detection
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_sandbox = enable_sandbox
        self.enable_audit_logging = enable_audit_logging
        
        # Initialize security components
        if self.enable_security:
            self._init_security_components()
        
        # Security metrics
        self._security_metrics = {
            'attacks_blocked': 0,
            'ssti_attempts': 0,
            'xss_attempts': 0,
            'path_traversal_attempts': 0,
            'rate_limit_violations': 0,
            'permission_denials': 0,
            'pii_detections': 0
        }
        
        logger.info(f"Initialized SecureTemplateRegistry with security={enable_security}")
    
    def _init_security_components(self) -> None:
        """Initialize security components."""
        # PII detector from M002
        self.pii_detector = PIIDetector() if self.enable_pii_detection else None
        
        # Security manager
        self.security = TemplateSecurity(
            pii_detector=self.pii_detector,
            audit_logger=logger if self.enable_audit_logging else None
        )
        
        # Permission manager
        self.permission_manager = TemplatePermissionManager()
        
        # Sandbox
        self.sandbox = TemplateSandbox() if self.enable_sandbox else None
        
        # Secure parser
        self.secure_parser = SecureTemplateParser(
            security=self.security,
            sandbox=self.sandbox,
            permission_manager=self.permission_manager,
            template_base_dir=Path.cwd() / "templates"
        )
        
        # Default admin user (for testing)
        self._set_default_permissions()
    
    def _set_default_permissions(self) -> None:
        """Set default permissions for templates."""
        # Grant admin full access to all default templates
        for template_id in self._templates.keys():
            self.permission_manager.grant_permission("admin", template_id, "admin")
            # Grant read permission to all users for default templates
            self.permission_manager.grant_permission("*", template_id, "read")
    
    def create_template(self, template_model: TemplateModel,
                       user_id: Optional[str] = None) -> Template:
        """
        Create a new template with security validation.
        
        Args:
            template_model: Template model to create
            user_id: User creating the template
            
        Returns:
            Created template
            
        Raises:
            TemplateSecurityError: If security validation fails
            TemplateRateLimitError: If rate limit exceeded
        """
        user_id = user_id or "anonymous"
        
        # Check rate limit
        if self.enable_rate_limiting:
            try:
                self.security.check_rate_limit(user_id, "create")
            except TemplateRateLimitError as e:
                self._security_metrics['rate_limit_violations'] += 1
                raise
        
        # Validate template security
        if self.enable_security:
            is_valid, issues = self.security.validate_template_content(
                template_model.content,
                template_model.metadata.id
            )
            
            if not is_valid:
                self._security_metrics['attacks_blocked'] += 1
                
                # Check for specific attack types
                for issue in issues:
                    if "SSTI" in issue:
                        self._security_metrics['ssti_attempts'] += 1
                    elif "XSS" in issue:
                        self._security_metrics['xss_attempts'] += 1
                    elif "traversal" in issue.lower():
                        self._security_metrics['path_traversal_attempts'] += 1
                
                # Log security event
                if self.enable_audit_logging:
                    self.security.audit_log(
                        'template_creation_blocked',
                        user_id,
                        template_model.metadata.id,
                        {'issues': issues}
                    )
                
                raise TemplateSecurityError(
                    f"Template failed security validation: {issues}"
                )
        
        # Check for PII
        if self.enable_pii_detection and self.pii_detector:
            pii_result = self.pii_detector.detect(template_model.content)
            if pii_result['contains_pii']:
                self._security_metrics['pii_detections'] += 1
                
                # Log PII detection
                if self.enable_audit_logging:
                    self.security.audit_log(
                        'pii_detected',
                        user_id,
                        template_model.metadata.id,
                        {'pii_types': pii_result['pii_types']}
                    )
                
                # Optionally mask PII before storage
                if template_model.metadata.mask_pii:
                    template_model.content = self.security.mask_pii(
                        template_model.content
                    )
        
        # Create template using parent method
        template = super().create_template(template_model)
        
        # Set permissions for creator
        if self.enable_security:
            self.permission_manager.grant_permission(
                user_id,
                template_model.metadata.id,
                "admin"
            )
        
        # Log successful creation
        if self.enable_audit_logging:
            self.security.audit_log(
                'template_created',
                user_id,
                template_model.metadata.id,
                {}
            )
        
        return template
    
    def render_template(self, template_id: str,
                       context: Optional[Dict[str, Any]] = None,
                       user_id: Optional[str] = None,
                       validate_context: bool = True,
                       use_cache: bool = True) -> str:
        """
        Render template with comprehensive security checks.
        
        Args:
            template_id: Template ID to render
            context: Variable context
            user_id: User requesting render
            validate_context: Whether to validate context
            use_cache: Whether to use cache
            
        Returns:
            Rendered and sanitized template content
            
        Raises:
            TemplatePermissionError: If user lacks permission
            TemplateSecurityError: If security violation detected
            TemplateRateLimitError: If rate limit exceeded
        """
        user_id = user_id or "anonymous"
        
        # Get template
        template = self.get_template(template_id)
        if not template:
            raise TemplateNotFoundError(template_id)
        
        # Check permissions
        if self.enable_security:
            if not self.permission_manager.has_permission(
                user_id, template_id, "execute"
            ):
                self._security_metrics['permission_denials'] += 1
                
                if self.enable_audit_logging:
                    self.security.audit_log(
                        'permission_denied',
                        user_id,
                        template_id,
                        {'action': 'execute'}
                    )
                
                raise TemplatePermissionError("execute", template_id)
        
        # Check rate limit
        if self.enable_rate_limiting:
            try:
                self.security.check_rate_limit(user_id, "render")
            except TemplateRateLimitError as e:
                self._security_metrics['rate_limit_violations'] += 1
                raise
        
        # Create render context
        render_context = TemplateRenderContext(
            variables=context or {},
            sections={},
            loops={}
        )
        
        # Sanitize all input variables
        if self.enable_security:
            for key, value in render_context.variables.items():
                render_context.variables[key] = self.security.sanitize_variable_value(
                    value, key
                )
        
        # Use secure parser if security enabled
        if self.enable_security:
            try:
                rendered = self.secure_parser.parse(
                    template,
                    render_context,
                    user_id=user_id
                )
            except (TemplateSSTIError, TemplateSecurityError) as e:
                self._security_metrics['attacks_blocked'] += 1
                
                if isinstance(e, TemplateSSTIError):
                    self._security_metrics['ssti_attempts'] += 1
                
                if self.enable_audit_logging:
                    self.security.audit_log(
                        'template_attack_blocked',
                        user_id,
                        template_id,
                        {'error': str(e)}
                    )
                
                raise
        else:
            # Use regular rendering from parent
            rendered = template.render(context, validate_context)
        
        # Additional XSS protection on output
        if self.enable_security:
            rendered = self.security.sanitize_html_output(rendered)
        
        # Mask PII if configured
        if self.enable_pii_detection and template.metadata.mask_pii:
            rendered = self.security.mask_pii(rendered)
        
        # Log successful render
        if self.enable_audit_logging:
            self.security.audit_log(
                'template_rendered',
                user_id,
                template_id,
                {'length': len(rendered)}
            )
        
        return rendered
    
    def update_template(self, template_id: str,
                       updates: Dict[str, Any],
                       user_id: Optional[str] = None) -> Template:
        """
        Update template with security validation.
        
        Args:
            template_id: Template to update
            updates: Updates to apply
            user_id: User performing update
            
        Returns:
            Updated template
            
        Raises:
            TemplatePermissionError: If user lacks permission
            TemplateSecurityError: If security validation fails
        """
        user_id = user_id or "anonymous"
        
        # Check permissions
        if self.enable_security:
            if not self.permission_manager.has_permission(
                user_id, template_id, "write"
            ):
                self._security_metrics['permission_denials'] += 1
                raise TemplatePermissionError("write", template_id)
        
        # Check rate limit
        if self.enable_rate_limiting:
            self.security.check_rate_limit(user_id, "update")
        
        # Validate new content if provided
        if 'content' in updates and self.enable_security:
            is_valid, issues = self.security.validate_template_content(
                updates['content'],
                template_id
            )
            
            if not is_valid:
                self._security_metrics['attacks_blocked'] += 1
                raise TemplateSecurityError(
                    f"Updated content failed security validation: {issues}"
                )
        
        # Update using parent method
        template = super().update_template(template_id, updates)
        
        # Log update
        if self.enable_audit_logging:
            self.security.audit_log(
                'template_updated',
                user_id,
                template_id,
                {'updates': list(updates.keys())}
            )
        
        return template
    
    def delete_template(self, template_id: str,
                       user_id: Optional[str] = None) -> bool:
        """
        Delete template with permission check.
        
        Args:
            template_id: Template to delete
            user_id: User performing deletion
            
        Returns:
            True if deleted
            
        Raises:
            TemplatePermissionError: If user lacks permission
        """
        user_id = user_id or "anonymous"
        
        # Check permissions
        if self.enable_security:
            if not self.permission_manager.has_permission(
                user_id, template_id, "delete"
            ):
                self._security_metrics['permission_denials'] += 1
                raise TemplatePermissionError("delete", template_id)
        
        # Delete using parent method
        result = super().delete_template(template_id)
        
        # Log deletion
        if self.enable_audit_logging:
            self.security.audit_log(
                'template_deleted',
                user_id,
                template_id,
                {}
            )
        
        return result
    
    def grant_permission(self, user_id: str, template_id: str,
                        permission: str, granting_user: Optional[str] = None) -> None:
        """
        Grant permission to user for template.
        
        Args:
            user_id: User to grant permission to
            template_id: Template ID
            permission: Permission to grant
            granting_user: User granting permission
        """
        granting_user = granting_user or "admin"
        
        # Check if granting user has admin permission
        if self.enable_security:
            if not self.permission_manager.has_permission(
                granting_user, template_id, "admin"
            ):
                raise TemplatePermissionError("admin", template_id)
        
        # Grant permission
        self.permission_manager.grant_permission(user_id, template_id, permission)
        
        # Log permission grant
        if self.enable_audit_logging:
            self.security.audit_log(
                'permission_granted',
                granting_user,
                template_id,
                {'target_user': user_id, 'permission': permission}
            )
    
    def revoke_permission(self, user_id: str, template_id: str,
                         permission: str, revoking_user: Optional[str] = None) -> None:
        """
        Revoke permission from user for template.
        
        Args:
            user_id: User to revoke permission from
            template_id: Template ID
            permission: Permission to revoke
            revoking_user: User revoking permission
        """
        revoking_user = revoking_user or "admin"
        
        # Check if revoking user has admin permission
        if self.enable_security:
            if not self.permission_manager.has_permission(
                revoking_user, template_id, "admin"
            ):
                raise TemplatePermissionError("admin", template_id)
        
        # Revoke permission
        self.permission_manager.revoke_permission(user_id, template_id, permission)
        
        # Log permission revocation
        if self.enable_audit_logging:
            self.security.audit_log(
                'permission_revoked',
                revoking_user,
                template_id,
                {'target_user': user_id, 'permission': permission}
            )
    
    def get_security_metrics(self) -> Dict[str, Any]:
        """
        Get security metrics.
        
        Returns:
            Security metrics dictionary
        """
        return {
            **self._security_metrics,
            'security_enabled': self.enable_security,
            'pii_detection_enabled': self.enable_pii_detection,
            'rate_limiting_enabled': self.enable_rate_limiting,
            'sandbox_enabled': self.enable_sandbox,
            'audit_logging_enabled': self.enable_audit_logging
        }
    
    def validate_template_batch(self, templates: List[TemplateModel],
                               user_id: Optional[str] = None) -> List[TemplateValidationResult]:
        """
        Validate multiple templates for security issues.
        
        Args:
            templates: Templates to validate
            user_id: User requesting validation
            
        Returns:
            List of validation results
        """
        results = []
        
        for template in templates:
            try:
                is_valid, issues = self.security.validate_template_content(
                    template.content,
                    template.metadata.id
                )
                
                # Check for PII
                pii_detected = False
                if self.enable_pii_detection:
                    pii_result = self.pii_detector.detect(template.content)
                    pii_detected = pii_result['contains_pii']
                
                results.append(TemplateValidationResult(
                    template_id=template.metadata.id,
                    is_valid=is_valid,
                    errors=issues if not is_valid else [],
                    warnings=['Contains PII'] if pii_detected else []
                ))
                
            except Exception as e:
                results.append(TemplateValidationResult(
                    template_id=template.metadata.id,
                    is_valid=False,
                    errors=[str(e)],
                    warnings=[]
                ))
        
        return results