"""
M004 Document Generator - Unified Generation Engine (Refactored).

Simplified document generation engine that uses unified components
with configurable security and performance levels.

Pass 4 Refactoring: Consolidates engine.py complexity and uses unified components
for cleaner architecture and reduced duplication.
"""

import logging
import time
import uuid
import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union, Tuple
from concurrent.futures import ThreadPoolExecutor, as_completed
from enum import Enum

# Import unified components
from .unified_template_loader import UnifiedTemplateLoader, SecurityLevel as TemplateSecurityLevel
from ..outputs.unified_html_output import UnifiedHTMLOutput, SecurityLevel as OutputSecurityLevel
from ..outputs.markdown import MarkdownOutput
from ..utils.unified_validators import UnifiedValidator, ValidationLevel
from .content_processor import ContentProcessor

# Import common modules
from ...core.config import ConfigurationManager
from ...storage import LocalStorageSystem, Document
from ...common.errors import DevDocAIError
from ...common.logging import get_logger
from ...common.performance import ParallelExecutor, LRUCache
from ...common.security import get_audit_logger

logger = get_logger(__name__)


class EngineMode(Enum):
    """Operating modes for the generation engine."""
    DEVELOPMENT = "development"  # Fast, minimal security
    STANDARD = "standard"  # Balanced performance and security
    PRODUCTION = "production"  # Full security, optimized performance
    STRICT = "strict"  # Maximum security, validation at every step


@dataclass
class UnifiedGenerationConfig:
    """Unified configuration for document generation."""
    
    # Core settings
    output_format: str = "markdown"  # markdown, html, pdf
    engine_mode: EngineMode = EngineMode.STANDARD
    
    # Feature flags
    save_to_storage: bool = True
    include_metadata: bool = True
    enable_caching: bool = True
    enable_audit: bool = None  # Auto-determined by mode
    enable_pii_detection: bool = None  # Auto-determined by mode
    
    # Project metadata
    project_name: Optional[str] = None
    author: Optional[str] = None
    version: str = "1.0"
    
    # Performance settings
    max_parallel_jobs: int = 5
    cache_size: int = 100
    timeout: Optional[int] = None
    
    # Security settings (auto-configured by mode)
    template_security: Optional[TemplateSecurityLevel] = None
    output_security: Optional[OutputSecurityLevel] = None
    validation_level: Optional[ValidationLevel] = None
    
    def __post_init__(self):
        """Configure settings based on engine mode."""
        # Auto-configure security levels based on mode
        if self.engine_mode == EngineMode.DEVELOPMENT:
            self.template_security = self.template_security or TemplateSecurityLevel.NONE
            self.output_security = self.output_security or OutputSecurityLevel.BASIC
            self.validation_level = self.validation_level or ValidationLevel.BASIC
            self.enable_audit = self.enable_audit or False
            self.enable_pii_detection = self.enable_pii_detection or False
            
        elif self.engine_mode == EngineMode.STANDARD:
            self.template_security = self.template_security or TemplateSecurityLevel.STANDARD
            self.output_security = self.output_security or OutputSecurityLevel.STANDARD
            self.validation_level = self.validation_level or ValidationLevel.STANDARD
            self.enable_audit = self.enable_audit or True
            self.enable_pii_detection = self.enable_pii_detection or True
            
        elif self.engine_mode == EngineMode.PRODUCTION:
            self.template_security = self.template_security or TemplateSecurityLevel.STANDARD
            self.output_security = self.output_security or OutputSecurityLevel.STANDARD
            self.validation_level = self.validation_level or ValidationLevel.STANDARD
            self.enable_audit = True
            self.enable_pii_detection = True
            self.enable_caching = True  # Force caching in production
            
        elif self.engine_mode == EngineMode.STRICT:
            self.template_security = TemplateSecurityLevel.STRICT
            self.output_security = OutputSecurityLevel.STRICT
            self.validation_level = ValidationLevel.STRICT
            self.enable_audit = True
            self.enable_pii_detection = True
            self.timeout = self.timeout or 30  # Add timeout in strict mode
        
        # Validate output format
        valid_formats = {"markdown", "html", "pdf"}
        if self.output_format not in valid_formats:
            raise DevDocAIError(f"Invalid output format: {self.output_format}")


@dataclass
class GenerationResult:
    """Result of a document generation operation."""
    
    success: bool
    document_id: Optional[str] = None
    content: Optional[str] = None
    format: Optional[str] = None
    generation_time: Optional[float] = None
    template_name: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    error_message: Optional[str] = None
    warnings: List[str] = field(default_factory=list)
    security_report: Dict[str, Any] = field(default_factory=dict)


class UnifiedDocumentGenerator:
    """
    Unified document generation engine with configurable modes.
    
    Features:
    - Single engine with multiple operating modes
    - Unified components for reduced complexity
    - Configurable security and performance levels
    - Backward compatible with existing APIs
    """
    
    def __init__(
        self,
        config: Optional[UnifiedGenerationConfig] = None,
        template_dir: Optional[Path] = None,
        output_dir: Optional[Path] = None,
        storage_system: Optional[LocalStorageSystem] = None,
        config_manager: Optional[ConfigurationManager] = None
    ):
        """
        Initialize unified document generator.
        
        Args:
            config: Generation configuration
            template_dir: Directory containing templates
            output_dir: Directory for output files
            storage_system: Storage system for documents
            config_manager: Configuration manager instance
        """
        self.config = config or UnifiedGenerationConfig()
        
        # Initialize configuration manager
        self.config_manager = config_manager or ConfigurationManager()
        
        # Initialize storage system
        self.storage = storage_system
        
        # Initialize unified components with appropriate security levels
        self.template_loader = UnifiedTemplateLoader(
            template_dir=template_dir,
            security_level=self.config.template_security,
            enable_caching=self.config.enable_caching,
            cache_size=self.config.cache_size,
            enable_audit=self.config.enable_audit
        )
        
        self.validator = UnifiedValidator(
            validation_level=self.config.validation_level,
            enable_pii_detection=self.config.enable_pii_detection,
            enable_audit=self.config.enable_audit
        )
        
        self.html_output = UnifiedHTMLOutput(
            output_dir=output_dir,
            security_level=self.config.output_security,
            enable_caching=self.config.enable_caching,
            cache_size=self.config.cache_size,
            enable_audit=self.config.enable_audit
        )
        
        self.markdown_output = MarkdownOutput(output_dir=output_dir)
        
        self.content_processor = ContentProcessor(
            enable_caching=self.config.enable_caching
        )
        
        # Initialize audit logger if needed
        if self.config.enable_audit:
            self.audit_logger = get_audit_logger()
        
        # Initialize parallel executor for batch operations
        self.executor = ParallelExecutor(max_workers=self.config.max_parallel_jobs)
        
        # Performance tracking
        self._generation_times = []
        self._cache_hits = 0
        self._cache_misses = 0
        
        logger.info(
            f"Initialized UnifiedDocumentGenerator with mode={self.config.engine_mode.value}, "
            f"template_security={self.config.template_security.value}, "
            f"validation={self.config.validation_level.value}"
        )
    
    def generate(
        self,
        template_name: str,
        inputs: Dict[str, Any],
        output_format: Optional[str] = None,
        custom_config: Optional[UnifiedGenerationConfig] = None
    ) -> GenerationResult:
        """
        Generate a document using the specified template and inputs.
        
        Args:
            template_name: Name of template to use
            inputs: Template input variables
            output_format: Override output format
            custom_config: Override configuration for this generation
            
        Returns:
            GenerationResult with generated document
        """
        start_time = time.time()
        result = GenerationResult(success=False)
        
        # Use custom config if provided
        config = custom_config or self.config
        output_format = output_format or config.output_format
        
        try:
            # Step 1: Validate inputs
            if config.validation_level != ValidationLevel.NONE:
                validation_errors = self._validate_inputs(inputs, template_name)
                if validation_errors:
                    result.error_message = f"Validation failed: {', '.join(validation_errors)}"
                    return result
            
            # Step 2: Load template
            template, metadata = self.template_loader.load_template(
                template_name,
                validate=(config.validation_level != ValidationLevel.NONE)
            )
            
            # Step 3: Process content
            context = self._prepare_context(inputs, metadata, config)
            
            # Step 4: Render template
            rendered_content = self.template_loader.render_template(
                template_name,
                context,
                validate_context=(config.validation_level != ValidationLevel.NONE),
                timeout=config.timeout
            )
            
            # Step 5: Process rendered content
            processed_content = self.content_processor.process(
                rendered_content,
                metadata=metadata.to_dict()
            )
            
            # Step 6: Generate output
            if output_format == "html":
                final_content = self.html_output.generate(
                    processed_content,
                    title=metadata.title,
                    metadata=metadata.to_dict(),
                    format_type="markdown"
                )
            else:
                final_content = self.markdown_output.generate(
                    processed_content,
                    metadata=metadata.to_dict()
                )
            
            # Step 7: Save to storage if configured
            document_id = None
            if config.save_to_storage and self.storage:
                document_id = self._save_to_storage(
                    final_content,
                    template_name,
                    metadata.to_dict()
                )
            
            # Step 8: Prepare result
            generation_time = time.time() - start_time
            self._generation_times.append(generation_time)
            
            result = GenerationResult(
                success=True,
                document_id=document_id,
                content=final_content,
                format=output_format,
                generation_time=generation_time,
                template_name=template_name,
                metadata=metadata.to_dict()
            )
            
            # Add security report in strict mode
            if config.engine_mode == EngineMode.STRICT:
                result.security_report = self._generate_security_report(
                    inputs, final_content
                )
            
            # Audit logging
            if config.enable_audit:
                self.audit_logger.log_event(
                    "document_generated",
                    template=template_name,
                    format=output_format,
                    generation_time=generation_time,
                    mode=config.engine_mode.value
                )
            
            return result
            
        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            result.error_message = str(e)
            return result
    
    async def generate_async(
        self,
        template_name: str,
        inputs: Dict[str, Any],
        **kwargs
    ) -> GenerationResult:
        """Async version of generate method."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.generate,
            template_name,
            inputs,
            **kwargs
        )
    
    def generate_batch(
        self,
        requests: List[Tuple[str, Dict[str, Any]]],
        output_format: Optional[str] = None
    ) -> List[GenerationResult]:
        """
        Generate multiple documents in parallel.
        
        Args:
            requests: List of (template_name, inputs) tuples
            output_format: Output format for all documents
            
        Returns:
            List of GenerationResult objects
        """
        results = []
        
        with ThreadPoolExecutor(max_workers=self.config.max_parallel_jobs) as executor:
            futures = []
            for template_name, inputs in requests:
                future = executor.submit(
                    self.generate,
                    template_name,
                    inputs,
                    output_format
                )
                futures.append(future)
            
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=self.config.timeout)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch generation error: {e}")
                    results.append(GenerationResult(
                        success=False,
                        error_message=str(e)
                    ))
        
        return results
    
    def _validate_inputs(
        self,
        inputs: Dict[str, Any],
        template_name: str
    ) -> List[str]:
        """Validate inputs for template."""
        errors = []
        
        # Get template metadata for validation
        metadata = self.template_loader.get_metadata(template_name)
        
        # Validate using unified validator
        for key, value in inputs.items():
            is_valid, sanitized, validation_errors = self.validator.validate(
                value,
                data_type="template_input"
            )
            if not is_valid:
                errors.extend([f"{key}: {e}" for e in validation_errors])
        
        # Check required variables
        missing_vars = set(metadata.variables) - set(inputs.keys())
        if missing_vars:
            errors.append(f"Missing required variables: {', '.join(missing_vars)}")
        
        return errors
    
    def _prepare_context(
        self,
        inputs: Dict[str, Any],
        metadata: Any,
        config: UnifiedGenerationConfig
    ) -> Dict[str, Any]:
        """Prepare template context with inputs and metadata."""
        context = inputs.copy()
        
        # Add standard context variables
        context['project_name'] = config.project_name or "Untitled Project"
        context['author'] = config.author or "Unknown Author"
        context['version'] = config.version
        context['generation_date'] = datetime.now().strftime('%Y-%m-%d')
        context['generation_time'] = datetime.now().strftime('%H:%M:%S')
        
        # Add metadata if configured
        if config.include_metadata:
            context['template_metadata'] = metadata.to_dict()
        
        return context
    
    def _save_to_storage(
        self,
        content: str,
        template_name: str,
        metadata: Dict[str, Any]
    ) -> str:
        """Save generated document to storage."""
        if not self.storage:
            return None
        
        try:
            document = Document(
                content=content,
                metadata={
                    'template': template_name,
                    'generated_at': datetime.now().isoformat(),
                    **metadata
                }
            )
            
            doc_id = self.storage.create(document)
            logger.info(f"Document saved to storage with ID: {doc_id}")
            return doc_id
            
        except Exception as e:
            logger.error(f"Failed to save document to storage: {e}")
            return None
    
    def _generate_security_report(
        self,
        inputs: Dict[str, Any],
        output: str
    ) -> Dict[str, Any]:
        """Generate security report for strict mode."""
        report = {
            'timestamp': datetime.now().isoformat(),
            'mode': self.config.engine_mode.value,
            'validations_performed': []
        }
        
        # Check for PII in inputs
        for key, value in inputs.items():
            if isinstance(value, str):
                _, _, errors = self.validator.validate(value, "pii_check")
                if errors:
                    report['validations_performed'].append({
                        'type': 'pii_detection',
                        'field': key,
                        'issues': errors
                    })
        
        # Check output for security issues
        _, _, output_errors = self.validator.validate(output, "output_security")
        if output_errors:
            report['validations_performed'].append({
                'type': 'output_validation',
                'issues': output_errors
            })
        
        report['issues_found'] = len(report['validations_performed']) > 0
        
        return report
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get performance statistics."""
        if not self._generation_times:
            return {}
        
        return {
            'total_generations': len(self._generation_times),
            'average_time': sum(self._generation_times) / len(self._generation_times),
            'min_time': min(self._generation_times),
            'max_time': max(self._generation_times),
            'cache_hits': self._cache_hits,
            'cache_misses': self._cache_misses,
            'cache_hit_rate': self._cache_hits / (self._cache_hits + self._cache_misses) 
                             if (self._cache_hits + self._cache_misses) > 0 else 0
        }
    
    def clear_caches(self):
        """Clear all caches."""
        self.template_loader.clear_cache()
        self.html_output.clear_cache()
        self.content_processor.clear_cache()
        logger.info("All caches cleared")
    
    def list_templates(self, filter_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """List available templates."""
        templates = self.template_loader.list_templates(filter_type)
        return [t.to_dict() for t in templates]
    
    # Backward compatibility methods
    
    def generate_document(self, template_name: str, **inputs) -> GenerationResult:
        """Backward compatible generation method."""
        return self.generate(template_name, inputs)
    
    def set_security_level(self, level: str):
        """Change security level (backward compatibility)."""
        if level == "high":
            self.config.engine_mode = EngineMode.STRICT
        elif level == "medium":
            self.config.engine_mode = EngineMode.STANDARD
        else:
            self.config.engine_mode = EngineMode.DEVELOPMENT
        
        # Reinitialize components with new settings
        self.__init__(self.config)


# Backward compatibility aliases
DocumentGenerator = UnifiedDocumentGenerator  # Alias for compatibility
GenerationConfig = UnifiedGenerationConfig  # Alias for compatibility


def create_generator(
    mode: Union[str, EngineMode] = "standard",
    **kwargs
) -> UnifiedDocumentGenerator:
    """
    Factory function to create a document generator with specified mode.
    
    Args:
        mode: Engine mode (development/standard/production/strict)
        **kwargs: Additional configuration options
        
    Returns:
        Configured UnifiedDocumentGenerator instance
    """
    if isinstance(mode, str):
        mode = EngineMode(mode.lower())
    
    config = UnifiedGenerationConfig(engine_mode=mode, **kwargs)
    return UnifiedDocumentGenerator(config=config)