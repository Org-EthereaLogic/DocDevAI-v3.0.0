"""
Prompt Template Engine for AI-powered document generation.

This engine processes YAML-based prompt templates that define how to
query LLMs for document generation and review tasks.
"""

import yaml
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from jinja2 import Template, Environment, FileSystemLoader, select_autoescape
import re

logger = logging.getLogger(__name__)


@dataclass
class PromptTemplate:
    """Represents a loaded prompt template."""
    name: str
    description: str
    category: str
    version: str
    inputs: List[Dict[str, Any]]
    llm_config: Dict[str, Any]
    prompt: Dict[str, str]  # system and user prompts
    output: Dict[str, Any]
    miair_config: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RenderedPrompt:
    """A prompt ready for LLM execution."""
    system_prompt: str
    user_prompt: str
    llm_config: Dict[str, Any]
    output_config: Dict[str, Any]
    miair_config: Optional[Dict[str, Any]] = None


class PromptTemplateEngine:
    """
    Engine for managing and rendering prompt templates for LLM queries.
    
    This replaces simple variable substitution with sophisticated
    prompt engineering for AI-powered document generation.
    """
    
    def __init__(
        self,
        template_dir: Path = None,
        cache_templates: bool = True
    ):
        """
        Initialize the prompt template engine.
        
        Args:
            template_dir: Directory containing prompt templates
            cache_templates: Whether to cache loaded templates
        """
        self.template_dir = template_dir or Path("devdocai/templates/prompt_templates")
        self.cache_templates = cache_templates
        self._template_cache: Dict[str, PromptTemplate] = {}
        
        # Initialize Jinja2 environment for variable substitution
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=select_autoescape(),
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        logger.info(f"Initialized PromptTemplateEngine with directory: {self.template_dir}")
    
    def load_template(self, template_name: str) -> PromptTemplate:
        """
        Load a prompt template from YAML file.
        
        Args:
            template_name: Name of the template file (with or without .yaml)
            
        Returns:
            Loaded PromptTemplate object
        """
        # Check cache first
        if self.cache_templates and template_name in self._template_cache:
            return self._template_cache[template_name]
        
        # Ensure .yaml extension
        if not template_name.endswith('.yaml'):
            template_name += '.yaml'
        
        template_path = self.template_dir / template_name
        
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        # Load YAML template
        with open(template_path, 'r') as f:
            template_data = yaml.safe_load(f)
        
        # Create PromptTemplate object
        template = PromptTemplate(
            name=template_data.get('name', ''),
            description=template_data.get('description', ''),
            category=template_data.get('category', 'general'),
            version=template_data.get('version', '1.0.0'),
            inputs=template_data.get('inputs', []),
            llm_config=template_data.get('llm_config', {}),
            prompt=template_data.get('prompt', {}),
            output=template_data.get('output', {}),
            miair_config=template_data.get('miair_config'),
            metadata=template_data.get('metadata', {})
        )
        
        # Validate template
        self._validate_template(template)
        
        # Cache if enabled
        if self.cache_templates:
            self._template_cache[template_name] = template
        
        logger.info(f"Loaded template: {template.name} (v{template.version})")
        return template
    
    def render(
        self,
        template: Union[str, PromptTemplate],
        context: Dict[str, Any],
        validate_inputs: bool = True
    ) -> RenderedPrompt:
        """
        Render a prompt template with the provided context.
        
        Args:
            template: Template name or PromptTemplate object
            context: Variables to substitute into the template
            validate_inputs: Whether to validate required inputs
            
        Returns:
            RenderedPrompt ready for LLM execution
        """
        # Load template if string provided
        if isinstance(template, str):
            template = self.load_template(template)
        
        # Validate inputs if requested
        if validate_inputs:
            self._validate_inputs(template, context)
        
        # Process context to handle document objects
        processed_context = self._process_context(context)
        
        # Render system prompt
        system_prompt = self._render_prompt_section(
            template.prompt.get('system', ''),
            processed_context
        )
        
        # Render user prompt
        user_prompt = self._render_prompt_section(
            template.prompt.get('user', ''),
            processed_context
        )
        
        # Prepare LLM configuration with context-specific overrides
        llm_config = self._prepare_llm_config(template.llm_config, context)
        
        # Prepare output configuration
        output_config = template.output.copy()
        
        # Create rendered prompt
        rendered = RenderedPrompt(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            llm_config=llm_config,
            output_config=output_config,
            miair_config=template.miair_config
        )
        
        logger.debug(f"Rendered template: {template.name}")
        return rendered
    
    def _validate_template(self, template: PromptTemplate) -> None:
        """Validate template structure and required fields."""
        if not template.name:
            raise ValueError("Template must have a name")
        
        if not template.prompt:
            raise ValueError(f"Template {template.name} must have prompt section")
        
        if 'system' not in template.prompt and 'user' not in template.prompt:
            raise ValueError(f"Template {template.name} must have system or user prompt")
        
        # Validate LLM config
        if template.llm_config:
            if 'providers' in template.llm_config:
                total_weight = sum(
                    p.get('weight', 0) 
                    for p in template.llm_config['providers']
                )
                if abs(total_weight - 1.0) > 0.01:  # Allow small float errors
                    raise ValueError(
                        f"Template {template.name}: Provider weights must sum to 1.0, "
                        f"got {total_weight}"
                    )
    
    def _validate_inputs(
        self,
        template: PromptTemplate,
        context: Dict[str, Any]
    ) -> None:
        """Validate that all required inputs are provided."""
        for input_spec in template.inputs:
            input_name = input_spec.get('name')
            is_required = input_spec.get('required', False)
            
            if is_required and input_name not in context:
                # Check for default value
                if 'default' not in input_spec:
                    raise ValueError(
                        f"Required input '{input_name}' not provided for "
                        f"template '{template.name}'"
                    )
                else:
                    # Use default value
                    context[input_name] = input_spec['default']
    
    def _process_context(self, context: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process context to handle special types like document objects.
        
        Converts document objects to string representations suitable
        for LLM consumption.
        """
        processed = {}
        
        for key, value in context.items():
            if hasattr(value, 'to_prompt_format'):
                # Custom document objects with prompt formatting
                processed[key] = value.to_prompt_format()
            elif hasattr(value, '__dict__'):
                # Convert objects to readable format
                processed[key] = self._object_to_prompt_format(value)
            elif isinstance(value, dict):
                # Recursively process nested dicts
                processed[key] = self._process_context(value)
            elif isinstance(value, list):
                # Process list items
                processed[key] = [
                    self._process_context({'item': item})['item']
                    if isinstance(item, (dict, object)) else item
                    for item in value
                ]
            else:
                # Use as-is for simple types
                processed[key] = value
        
        return processed
    
    def _object_to_prompt_format(self, obj: Any) -> str:
        """Convert an object to a readable string format for LLM."""
        # This would be customized based on object types
        # For now, simple string representation
        return str(obj)
    
    def _render_prompt_section(
        self,
        prompt_template: str,
        context: Dict[str, Any]
    ) -> str:
        """Render a prompt section with Jinja2 variable substitution."""
        template = Template(prompt_template)
        return template.render(**context)
    
    def _prepare_llm_config(
        self,
        base_config: Dict[str, Any],
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Prepare LLM configuration with any context-specific overrides.
        """
        config = base_config.copy()
        
        # Check for runtime overrides in context
        overrides = context.get('_llm_config_overrides', {})
        config.update(overrides)
        
        return config
    
    def extract_output_sections(
        self,
        llm_response: str,
        output_config: Dict[str, Any]
    ) -> Dict[str, str]:
        """
        Extract structured output sections from LLM response.
        
        Args:
            llm_response: Raw LLM response text
            output_config: Output configuration from template
            
        Returns:
            Dictionary of extracted sections
        """
        sections = {}
        
        for section in output_config.get('sections', []):
            section_name = section.get('name')
            extract_tag = section.get('extract_tag')
            
            if extract_tag:
                # Extract content between XML tags
                pattern = f"<{extract_tag}>(.*?)</{extract_tag}>"
                match = re.search(pattern, llm_response, re.DOTALL)
                if match:
                    sections[section_name] = match.group(1).strip()
                else:
                    logger.warning(f"Could not extract section '{section_name}' with tag '{extract_tag}'")
            else:
                # Use the whole response for this section
                sections[section_name] = llm_response
        
        return sections
    
    def list_templates(self, category: Optional[str] = None) -> List[str]:
        """
        List available templates.
        
        Args:
            category: Optional category filter
            
        Returns:
            List of template names
        """
        templates = []
        
        for yaml_file in self.template_dir.glob("*.yaml"):
            if category:
                # Load to check category
                try:
                    template = self.load_template(yaml_file.stem)
                    if template.category == category:
                        templates.append(yaml_file.stem)
                except Exception as e:
                    logger.error(f"Error loading template {yaml_file}: {e}")
            else:
                templates.append(yaml_file.stem)
        
        return sorted(templates)
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """
        Get information about a template without fully loading it.
        
        Args:
            template_name: Name of the template
            
        Returns:
            Dictionary with template metadata
        """
        template = self.load_template(template_name)
        
        return {
            'name': template.name,
            'description': template.description,
            'category': template.category,
            'version': template.version,
            'required_inputs': [
                inp['name'] for inp in template.inputs
                if inp.get('required', False)
            ],
            'optional_inputs': [
                inp['name'] for inp in template.inputs
                if not inp.get('required', False)
            ],
            'output_sections': [
                section['name']
                for section in template.output.get('sections', [])
            ],
            'uses_miair': template.miair_config is not None,
            'multi_llm': len(template.llm_config.get('providers', [])) > 1
        }