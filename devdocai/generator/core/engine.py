"""
M004 Document Generator - Core generation engine.

Provides the main DocumentGenerator class that orchestrates the document generation
workflow using templates, content processing, and output formatting.
"""

import logging
import time
import uuid
import asyncio
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from concurrent.futures import ThreadPoolExecutor, as_completed

from ..utils.validators import InputValidator, ValidationError
from ..utils.security_validator import EnhancedSecurityValidator
from .template_loader import TemplateLoader, TemplateMetadata
from .secure_template_loader import SecureTemplateLoader
from .content_processor import ContentProcessor
from ..outputs.markdown import MarkdownOutput
from ..outputs.html import HtmlOutput
from ..outputs.secure_html_output import SecureHtmlOutput
from ..security.security_monitor import SecurityMonitor
from ..security.pii_protection import PIIProtectionEngine
from ..security.access_control import AccessController, ResourceType

# Import existing modules
from ...core.config import ConfigurationManager
from ...storage import LocalStorageSystem, Document
from ...common.errors import DevDocAIError
from ...common.logging import get_logger
from ...common.performance import ParallelExecutor

logger = get_logger(__name__)


@dataclass 
class GenerationConfig:
    """Configuration for document generation."""
    
    output_format: str = "markdown"  # markdown, html, pdf (future)
    save_to_storage: bool = True
    include_metadata: bool = True
    validate_inputs: bool = True
    project_name: Optional[str] = None
    author: Optional[str] = None
    version: str = "1.0"
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        valid_formats = {"markdown", "html", "pdf"}
        if self.output_format not in valid_formats:
            raise ValidationError(f"Invalid output format: {self.output_format}. Must be one of {valid_formats}")


@dataclass
class GenerationResult:
    """Result of a document generation operation."""
    
    success: bool
    document_id: Optional[str] = None
    content: Optional[str] = None
    format: Optional[str] = None
    generation_time: Optional[float] = None
    template_name: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    warnings: Optional[List[str]] = None
    
    def __post_init__(self):
        """Initialize warnings list if not provided."""
        if self.warnings is None:
            self.warnings = []


@dataclass
class BatchGenerationRequest:
    """Request for batch document generation (Pass 2 feature)."""
    
    template_name: str
    inputs: Dict[str, Any]
    config: Optional[GenerationConfig] = None
    request_id: Optional[str] = None
    
    def __post_init__(self):
        """Initialize request ID if not provided."""
        if self.request_id is None:
            self.request_id = str(uuid.uuid4())


@dataclass 
class BatchGenerationResult:
    """Result of batch document generation (Pass 2 feature)."""
    
    total_requests: int
    successful: int
    failed: int
    total_time: float
    average_time_per_document: float
    throughput_docs_per_sec: float
    results: List[GenerationResult]
    errors: List[str]
    
    def __post_init__(self):
        """Initialize errors list if not provided."""
        if self.errors is None:
            self.errors = []


class DocumentGenerator:
    """
    Main document generation engine.
    
    Orchestrates the complete document generation workflow:
    1. Load and validate templates
    2. Process content with user inputs
    3. Format output according to specifications
    4. Save to storage system (M002)
    5. Return generation results
    """
    
    def __init__(
        self, 
        config_manager: Optional[ConfigurationManager] = None,
        storage_system: Optional[LocalStorageSystem] = None,
        template_dir: Optional[Union[str, Path]] = None,
        security_enabled: bool = True,
        strict_mode: bool = True
    ):
        """Initialize the secure document generator.
        
        Args:
            config_manager: Configuration manager instance (M001)
            storage_system: Storage system instance (M002)  
            template_dir: Custom template directory path
            security_enabled: Enable comprehensive security features
            strict_mode: Enable strict security mode
        """
        self.config_manager = config_manager or ConfigurationManager()
        self.storage_system = storage_system or LocalStorageSystem()
        self.security_enabled = security_enabled
        self.strict_mode = strict_mode
        
        # Set template directory
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default to templates directory relative to this file
            self.template_dir = Path(__file__).parent.parent / "templates"
            
        # Initialize security components (Pass 3 enhancement)
        if security_enabled:
            self.security_monitor = SecurityMonitor()
            self.pii_protection = PIIProtectionEngine()
            self.access_controller = AccessController()
            self.secure_validator = EnhancedSecurityValidator()
            self.secure_template_loader = SecureTemplateLoader(self.template_dir, strict_mode)
        
        # Initialize standard components
        self.template_loader = TemplateLoader(self.template_dir)
        self.content_processor = ContentProcessor()
        self.input_validator = InputValidator()
        
        # Initialize output formatters with security enhancement
        if security_enabled:
            self.formatters = {
                "markdown": MarkdownOutput(),
                "html": SecureHtmlOutput(strict_mode)
            }
        else:
            self.formatters = {
                "markdown": MarkdownOutput(),
                "html": HtmlOutput()
            }
        
        # Initialize performance utilities (Pass 2 optimization)
        self._parallel_executor = ParallelExecutor(max_workers=4, use_processes=False)
        
        logger.info(f"DocumentGenerator initialized - security_enabled={security_enabled}, "
                   f"strict_mode={strict_mode}, template_directory={self.template_dir}")
    
    def generate_document_secure(
        self,
        template_name: str,
        inputs: Dict[str, Any],
        client_id: str = "anonymous",
        config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """
        Generate a document with comprehensive security controls (Pass 3).
        
        Args:
            template_name: Name of the template to use
            inputs: Dictionary of input values for template variables
            client_id: Client identifier for access control and audit
            config: Generation configuration options
            
        Returns:
            GenerationResult with success status and generated content
        """
        if not self.security_enabled:
            return self.generate_document(template_name, inputs, config)
        
        start_time = time.time()
        config = config or GenerationConfig()
        
        # Security metadata for tracking
        security_metadata = {
            'client_id': client_id,
            'template_name': template_name,
            'timestamp': datetime.now().isoformat(),
            'security_checks': [],
            'warnings': []
        }
        
        try:
            logger.info(f"Starting secure document generation: template={template_name}, "
                       f"client={client_id}, format={config.output_format}")
            
            # Step 1: Access control check
            access_allowed, access_reason, access_metadata = self.access_controller.check_access(
                client_id, ResourceType.TEMPLATE, "read"
            )
            if not access_allowed:
                error_msg = f"Access denied: {access_reason}"
                self.security_monitor.report_security_event(
                    'access_denied', 'medium', client_id, template_name,
                    error_msg, {'reason': access_reason}
                )
                return GenerationResult(
                    success=False,
                    error_message=error_msg,
                    generation_time=time.time() - start_time,
                    template_name=template_name
                )
            security_metadata['security_checks'].append('access_control_passed')
            
            # Step 2: Rate limiting check
            rate_allowed, rate_reason, rate_stats = self.access_controller.check_rate_limit(
                client_id, 'template_render'
            )
            if not rate_allowed:
                error_msg = f"Rate limit exceeded: {rate_reason}"
                self.security_monitor.report_rate_limit_exceeded(
                    client_id, 'template_render', 
                    rate_stats.get('current_usage', 0),
                    rate_stats.get('rate_limit', 0)
                )
                return GenerationResult(
                    success=False,
                    error_message=error_msg,
                    generation_time=time.time() - start_time,
                    template_name=template_name
                )
            security_metadata['security_checks'].append('rate_limit_passed')
            
            # Step 3: Enhanced input validation
            validation_result = self.secure_validator.validate_template_inputs_secure(
                inputs, [], client_id, template_name
            )
            if not validation_result['valid']:
                error_msg = f"Input validation failed: {'; '.join(validation_result['errors'])}"
                for error in validation_result['errors']:
                    if 'injection' in error.lower():
                        self.security_monitor.report_injection_attempt(
                            client_id, template_name, 'template', error
                        )
                    elif 'xss' in error.lower():
                        self.security_monitor.report_xss_attempt(
                            client_id, template_name, error, 'input'
                        )
                
                return GenerationResult(
                    success=False,
                    error_message=error_msg,
                    generation_time=time.time() - start_time,
                    template_name=template_name,
                    warnings=validation_result['warnings']
                )
            
            security_metadata['security_checks'].append('input_validation_passed')
            security_metadata['warnings'].extend(validation_result['warnings'])
            
            # Step 4: PII scanning and protection
            pii_result = self.pii_protection.scan_and_protect(
                json.dumps(inputs), 'input', client_id
            )
            if pii_result['processing_blocked']:
                error_msg = "Processing blocked due to PII policy violation"
                self.security_monitor.report_pii_exposure(
                    client_id, template_name, 
                    pii_result['pii_types_found'], 'input'
                )
                return GenerationResult(
                    success=False,
                    error_message=error_msg,
                    generation_time=time.time() - start_time,
                    template_name=template_name,
                    warnings=[f"PII detected: {', '.join(pii_result['pii_types_found'])}"]
                )
            
            # Use sanitized inputs
            sanitized_inputs = validation_result['sanitized_inputs']
            security_metadata['security_checks'].append('pii_scan_passed')
            
            # Step 5: Secure template rendering
            rendered_content, template_security = self.secure_template_loader.render_template_secure(
                template_name, sanitized_inputs, client_id
            )
            security_metadata['security_checks'].append('template_render_passed')
            security_metadata['template_security'] = template_security
            
            # Step 6: Secure output formatting
            if config.output_format == "html":
                format_result = self.formatters["html"].format_content_secure(
                    rendered_content, self.template_loader.get_template_metadata(template_name),
                    client_id, True, False, True
                )
                formatted_content = format_result['html_content']
                security_metadata.update(format_result['security_metadata'])
            else:
                # Markdown is safer, but still scan for issues
                formatted_content = self.formatters["markdown"].format_content(
                    rendered_content, self.template_loader.get_template_metadata(template_name)
                )
            
            security_metadata['security_checks'].append('output_format_passed')
            
            # Step 7: Final PII scan of generated content
            final_pii_result = self.pii_protection.scan_and_protect(
                formatted_content, 'output', client_id
            )
            if final_pii_result['pii_detected']:
                security_metadata['warnings'].append(
                    f"PII detected in output: {', '.join(final_pii_result['pii_types_found'])}"
                )
            
            # Step 8: Save to storage if required
            document_id = None
            if config.save_to_storage:
                # Check write access
                write_allowed, write_reason, _ = self.access_controller.check_access(
                    client_id, ResourceType.DOCUMENT, "write"
                )
                if write_allowed:
                    template_metadata = self.template_loader.load_template(template_name)
                    document_id = self._save_document(
                        final_pii_result['protected_content'], 
                        template_metadata, 
                        config, 
                        sanitized_inputs
                    )
                    self.access_controller.record_access(
                        client_id, ResourceType.DOCUMENT, "write", True
                    )
                else:
                    security_metadata['warnings'].append(f"Document save failed: {write_reason}")
            
            generation_time = time.time() - start_time
            
            # Record successful generation
            self.access_controller.record_access(
                client_id, ResourceType.TEMPLATE, "read", True,
                {'generation_time': generation_time, 'output_format': config.output_format}
            )
            
            result = GenerationResult(
                success=True,
                document_id=document_id,
                content=final_pii_result['protected_content'],
                format=config.output_format,
                generation_time=generation_time,
                template_name=template_name,
                metadata={**template_metadata.metadata, **security_metadata} if hasattr(template_metadata, 'metadata') else security_metadata,
                warnings=security_metadata['warnings']
            )
            
            logger.info(f"Secure document generation completed in {generation_time:.3f}s: "
                       f"client={client_id}, security_checks={len(security_metadata['security_checks'])}")
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = str(e)
            
            # Log security incident for unexpected errors
            self.security_monitor.report_security_event(
                'generation_error', 'medium', client_id, template_name,
                f"Generation failed: {error_msg}", {'exception': error_msg}
            )
            
            logger.error(f"Secure document generation failed: {error_msg}")
            
            return GenerationResult(
                success=False,
                error_message=error_msg,
                generation_time=generation_time,
                template_name=template_name
            )
    
    def generate_document(
        self,
        template_name: str,
        inputs: Dict[str, Any],
        config: Optional[GenerationConfig] = None
    ) -> GenerationResult:
        """
        Generate a document from a template and inputs.
        
        Args:
            template_name: Name of the template to use
            inputs: Dictionary of input values for template variables
            config: Generation configuration options
            
        Returns:
            GenerationResult with success status and generated content
        """
        start_time = time.time()
        config = config or GenerationConfig()
        
        try:
            logger.info(f"Starting document generation: template={template_name}, format={config.output_format}")
            
            # Step 1: Validate inputs if required
            if config.validate_inputs:
                self._validate_inputs(inputs, template_name)
            
            # Step 2: Load template
            template_metadata = self.template_loader.load_template(template_name)
            if not template_metadata:
                raise DevDocAIError(f"Template not found: {template_name}")
                
            logger.debug(f"Template loaded: {template_metadata.name}")
            
            # Step 3: Process content with inputs
            processed_content = self.content_processor.process_content(
                template_metadata.content,
                inputs,
                template_metadata.variables
            )
            
            # Step 4: Format output
            formatter = self.formatters.get(config.output_format)
            if not formatter:
                raise DevDocAIError(f"Unsupported output format: {config.output_format}")
                
            formatted_content = formatter.format_content(processed_content, template_metadata)
            
            # Step 5: Save to storage if required
            document_id = None
            if config.save_to_storage:
                document_id = self._save_document(
                    formatted_content, 
                    template_metadata, 
                    config, 
                    inputs
                )
            
            generation_time = time.time() - start_time
            
            result = GenerationResult(
                success=True,
                document_id=document_id,
                content=formatted_content,
                format=config.output_format,
                generation_time=generation_time,
                template_name=template_name,
                metadata=template_metadata.metadata
            )
            
            logger.info(f"Document generation completed in {generation_time:.3f}s")
            return result
            
        except Exception as e:
            generation_time = time.time() - start_time
            error_msg = str(e)
            logger.error(f"Document generation failed: {error_msg}")
            
            return GenerationResult(
                success=False,
                error_message=error_msg,
                generation_time=generation_time,
                template_name=template_name
            )
    
    def list_templates(self, category: Optional[str] = None) -> List[TemplateMetadata]:
        """
        List available templates.
        
        Args:
            category: Optional category filter (technical, user, project, etc.)
            
        Returns:
            List of template metadata objects
        """
        try:
            templates = self.template_loader.list_templates()
            
            if category:
                templates = [t for t in templates if t.category == category]
                
            logger.debug(f"Listed {len(templates)} templates (category: {category})")
            return templates
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    def get_template_info(self, template_name: str) -> Optional[TemplateMetadata]:
        """
        Get detailed information about a specific template.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Template metadata or None if not found
        """
        try:
            return self.template_loader.get_template_metadata(template_name)
        except Exception as e:
            logger.error(f"Failed to get template info for {template_name}: {e}")
            return None
    
    def validate_template_inputs(
        self, 
        template_name: str, 
        inputs: Dict[str, Any]
    ) -> List[str]:
        """
        Validate inputs for a specific template without generating the document.
        
        Args:
            template_name: Name of the template
            inputs: Input values to validate
            
        Returns:
            List of validation error messages (empty if valid)
        """
        try:
            template_metadata = self.template_loader.load_template(template_name)
            if not template_metadata:
                return [f"Template not found: {template_name}"]
                
            return self.input_validator.validate_template_inputs(
                inputs, 
                template_metadata.variables
            )
            
        except Exception as e:
            logger.error(f"Input validation failed for {template_name}: {e}")
            return [f"Validation error: {str(e)}"]
    
    def generate_batch(
        self,
        requests: List[BatchGenerationRequest],
        max_workers: Optional[int] = None
    ) -> BatchGenerationResult:
        """
        Generate multiple documents in parallel (Pass 2 feature).
        
        Args:
            requests: List of batch generation requests
            max_workers: Maximum number of concurrent workers
            
        Returns:
            BatchGenerationResult with aggregated results
        """
        if not requests:
            return BatchGenerationResult(
                total_requests=0,
                successful=0,
                failed=0,
                total_time=0.0,
                average_time_per_document=0.0,
                throughput_docs_per_sec=0.0,
                results=[],
                errors=[]
            )
        
        start_time = time.time()
        results = []
        errors = []
        
        logger.info(f"Starting batch generation of {len(requests)} documents")
        
        # Use custom max_workers or default
        if max_workers is None:
            max_workers = min(len(requests), 8)  # Cap at 8 workers
        
        # Generate documents concurrently
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all generation tasks
            future_to_request = {
                executor.submit(self._generate_single_for_batch, req): req 
                for req in requests
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_request):
                request = future_to_request[future]
                try:
                    result = future.result()
                    results.append(result)
                    if not result.success:
                        errors.append(f"Request {request.request_id}: {result.error_message}")
                except Exception as e:
                    error_msg = f"Request {request.request_id} failed with exception: {str(e)}"
                    errors.append(error_msg)
                    logger.error(error_msg)
                    # Create failed result
                    results.append(GenerationResult(
                        success=False,
                        template_name=request.template_name,
                        error_message=str(e)
                    ))
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate statistics
        successful = sum(1 for r in results if r.success)
        failed = len(results) - successful
        average_time = total_time / len(results) if results else 0.0
        throughput = successful / total_time if total_time > 0 else 0.0
        
        batch_result = BatchGenerationResult(
            total_requests=len(requests),
            successful=successful,
            failed=failed,
            total_time=total_time,
            average_time_per_document=average_time,
            throughput_docs_per_sec=throughput,
            results=results,
            errors=errors
        )
        
        logger.info(f"Batch generation completed: {successful}/{len(requests)} successful, "
                   f"{throughput:.1f} docs/sec, {total_time:.2f}s total")
        
        return batch_result
    
    def generate_many_same_template(
        self,
        template_name: str,
        inputs_list: List[Dict[str, Any]],
        config: Optional[GenerationConfig] = None,
        max_workers: Optional[int] = None
    ) -> BatchGenerationResult:
        """
        Generate multiple documents using the same template (Pass 2 optimization).
        
        This method is optimized for generating many documents with the same template
        but different inputs, allowing for template compilation reuse.
        
        Args:
            template_name: Name of the template to use for all documents
            inputs_list: List of input dictionaries for each document
            config: Generation configuration (applied to all)
            max_workers: Maximum concurrent workers
            
        Returns:
            BatchGenerationResult with aggregated results
        """
        # Convert to batch requests
        requests = [
            BatchGenerationRequest(
                template_name=template_name,
                inputs=inputs,
                config=config or GenerationConfig()
            )
            for inputs in inputs_list
        ]
        
        return self.generate_batch(requests, max_workers)
    
    async def generate_batch_async(
        self,
        requests: List[BatchGenerationRequest]
    ) -> BatchGenerationResult:
        """
        Async version of batch generation (Pass 2 feature).
        
        Args:
            requests: List of batch generation requests
            
        Returns:
            BatchGenerationResult with aggregated results
        """
        if not requests:
            return BatchGenerationResult(
                total_requests=0,
                successful=0,
                failed=0, 
                total_time=0.0,
                average_time_per_document=0.0,
                throughput_docs_per_sec=0.0,
                results=[],
                errors=[]
            )
        
        start_time = time.time()
        logger.info(f"Starting async batch generation of {len(requests)} documents")
        
        # Create tasks for async execution
        tasks = [
            asyncio.create_task(self._generate_single_async(req))
            for req in requests
        ]
        
        # Wait for all tasks to complete
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and handle exceptions
        processed_results = []
        errors = []
        
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                error_msg = f"Request {requests[i].request_id} failed: {str(result)}"
                errors.append(error_msg)
                processed_results.append(GenerationResult(
                    success=False,
                    template_name=requests[i].template_name,
                    error_message=str(result)
                ))
            else:
                processed_results.append(result)
                if not result.success:
                    errors.append(f"Request {requests[i].request_id}: {result.error_message}")
        
        end_time = time.time()
        total_time = end_time - start_time
        
        # Calculate statistics
        successful = sum(1 for r in processed_results if r.success)
        failed = len(processed_results) - successful
        average_time = total_time / len(processed_results) if processed_results else 0.0
        throughput = successful / total_time if total_time > 0 else 0.0
        
        batch_result = BatchGenerationResult(
            total_requests=len(requests),
            successful=successful,
            failed=failed,
            total_time=total_time,
            average_time_per_document=average_time,
            throughput_docs_per_sec=throughput,
            results=processed_results,
            errors=errors
        )
        
        logger.info(f"Async batch generation completed: {successful}/{len(requests)} successful, "
                   f"{throughput:.1f} docs/sec, {total_time:.2f}s total")
        
        return batch_result
    
    def _generate_single_for_batch(self, request: BatchGenerationRequest) -> GenerationResult:
        """Generate a single document for batch processing."""
        try:
            return self.generate_document(
                request.template_name,
                request.inputs,
                request.config
            )
        except Exception as e:
            logger.error(f"Batch generation failed for request {request.request_id}: {e}")
            return GenerationResult(
                success=False,
                template_name=request.template_name,
                error_message=str(e)
            )
    
    async def _generate_single_async(self, request: BatchGenerationRequest) -> GenerationResult:
        """Generate a single document asynchronously."""
        loop = asyncio.get_event_loop()
        try:
            # Run the synchronous generation in a thread pool
            return await loop.run_in_executor(
                None,
                self._generate_single_for_batch,
                request
            )
        except Exception as e:
            logger.error(f"Async generation failed for request {request.request_id}: {e}")
            return GenerationResult(
                success=False,
                template_name=request.template_name,
                error_message=str(e)
            )
    
    def _validate_inputs(self, inputs: Dict[str, Any], template_name: str) -> None:
        """Validate inputs for the specified template."""
        validation_errors = self.validate_template_inputs(template_name, inputs)
        if validation_errors:
            raise ValidationError(f"Input validation failed: {'; '.join(validation_errors)}")
    
    def _save_document(
        self,
        content: str,
        template_metadata: TemplateMetadata,
        config: GenerationConfig,
        inputs: Dict[str, Any]
    ) -> str:
        """Save the generated document to storage system."""
        try:
            # Prepare document metadata
            doc_metadata = {
                "template_name": template_metadata.name,
                "template_version": template_metadata.version,
                "template_category": template_metadata.category,
                "output_format": config.output_format,
                "generation_date": datetime.now().isoformat(),
                "inputs": inputs,
                **template_metadata.metadata
            }
            
            if config.project_name:
                doc_metadata["project_name"] = config.project_name
            if config.author:
                doc_metadata["author"] = config.author
                
            # Generate document title
            title = inputs.get("title", f"{template_metadata.name} - {datetime.now().strftime('%Y-%m-%d')}")
            
            # Save to storage
            document_id = self.storage_system.create_document(
                title=title,
                content=content,
                document_type=f"generated_{config.output_format}",
                metadata=doc_metadata
            )
            
            logger.debug(f"Document saved to storage: {document_id}")
            return document_id
            
        except Exception as e:
            logger.error(f"Failed to save document: {e}")
            raise DevDocAIError(f"Document save failed: {str(e)}")