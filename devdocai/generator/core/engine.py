"""
M004 Document Generator - Core generation engine.

Provides the main DocumentGenerator class that orchestrates the document generation
workflow using templates, content processing, and output formatting.
"""

import logging
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Union

from ..utils.validators import InputValidator, ValidationError
from .template_loader import TemplateLoader, TemplateMetadata
from .content_processor import ContentProcessor
from ..outputs.markdown import MarkdownOutput
from ..outputs.html import HtmlOutput

# Import existing modules
from ...core.config import ConfigurationManager
from ...storage import LocalStorageSystem, Document
from ...common.errors import DevDocAIError
from ...common.logging import get_logger

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
        template_dir: Optional[Union[str, Path]] = None
    ):
        """Initialize the document generator.
        
        Args:
            config_manager: Configuration manager instance (M001)
            storage_system: Storage system instance (M002)
            template_dir: Custom template directory path
        """
        self.config_manager = config_manager or ConfigurationManager()
        self.storage_system = storage_system or LocalStorageSystem()
        
        # Set template directory
        if template_dir:
            self.template_dir = Path(template_dir)
        else:
            # Default to templates directory relative to this file
            self.template_dir = Path(__file__).parent.parent / "templates"
            
        # Initialize components
        self.template_loader = TemplateLoader(self.template_dir)
        self.content_processor = ContentProcessor()
        self.input_validator = InputValidator()
        
        # Initialize output formatters
        self.formatters = {
            "markdown": MarkdownOutput(),
            "html": HtmlOutput()
        }
        
        logger.info(f"DocumentGenerator initialized with template directory: {self.template_dir}")
    
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