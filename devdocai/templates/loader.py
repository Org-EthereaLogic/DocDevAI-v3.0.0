"""
Template loader for M006 Template Registry.

This module provides loading capabilities for templates from
files, directories, and database storage.
"""

import os
import json
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging
from datetime import datetime

from .models import (
    Template,
    TemplateMetadata,
    TemplateVariable,
    TemplateSection,
    TemplateCategory,
    TemplateType
)
from .exceptions import TemplateStorageError, TemplateParseError

logger = logging.getLogger(__name__)


class TemplateLoader:
    """Loader for templates from various sources."""
    
    SUPPORTED_FORMATS = {'.md', '.txt', '.html', '.json', '.yaml', '.yml'}
    
    def __init__(self, base_path: Optional[Path] = None):
        """
        Initialize template loader.
        
        Args:
            base_path: Base path for template files
        """
        self.base_path = base_path or Path(__file__).parent / "defaults"
        self._template_cache: Dict[str, Template] = {}
        
    def load_from_file(self, file_path: Union[str, Path]) -> Template:
        """
        Load a template from a file.
        
        Args:
            file_path: Path to template file
            
        Returns:
            Loaded template
            
        Raises:
            TemplateStorageError: If file cannot be loaded
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise TemplateStorageError("load", f"File not found: {file_path}")
        
        if file_path.suffix not in self.SUPPORTED_FORMATS:
            raise TemplateStorageError("load", f"Unsupported format: {file_path.suffix}")
        
        try:
            # Check cache
            cache_key = str(file_path.absolute())
            if cache_key in self._template_cache:
                return self._template_cache[cache_key]
            
            # Load based on format
            if file_path.suffix in {'.json'}:
                template = self._load_json_template(file_path)
            elif file_path.suffix in {'.yaml', '.yml'}:
                template = self._load_yaml_template(file_path)
            else:
                template = self._load_text_template(file_path)
            
            # Cache the loaded template
            self._template_cache[cache_key] = template
            
            return template
            
        except Exception as e:
            raise TemplateStorageError("load", f"Failed to load {file_path}: {str(e)}")
    
    def _load_json_template(self, file_path: Path) -> Template:
        """Load template from JSON file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        return self._parse_template_data(data, file_path)
    
    def _load_yaml_template(self, file_path: Path) -> Template:
        """Load template from YAML file."""
        with open(file_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        
        return self._parse_template_data(data, file_path)
    
    def _load_text_template(self, file_path: Path) -> Template:
        """Load template from text file with frontmatter."""
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse frontmatter if present
        if content.startswith('---'):
            parts = content.split('---', 2)
            if len(parts) >= 3:
                frontmatter = yaml.safe_load(parts[1])
                template_content = parts[2].strip()
            else:
                frontmatter = {}
                template_content = content
        else:
            frontmatter = {}
            template_content = content
        
        # Create template from frontmatter and content
        data = frontmatter.copy()
        data['content'] = template_content
        
        return self._parse_template_data(data, file_path)
    
    def _parse_template_data(self, data: Dict, file_path: Path) -> Template:
        """Parse template data into Template object."""
        # For JSON templates with top-level structure
        if 'id' in data and 'template' in data:
            # This is our new JSON format
            metadata_data = {
                'id': data.get('id'),
                'name': data.get('name'),
                'description': data.get('description'),
                'category': data.get('category', self._infer_category(file_path).value),
                'type': data.get('type', self._infer_template_type(file_path).value),
                'version': data.get('version', '1.0.0'),
                'author': data.get('author', 'DevDocAI'),
                'tags': data.get('tags', [])
            }
            
            # Extract variables
            variables = []
            for var_data in data.get('variables', []):
                variables.append(TemplateVariable(**var_data))
            
            # Extract sections
            sections = []
            for section_data in data.get('sections', []):
                sections.append(TemplateSection(
                    id=section_data.get('id'),
                    name=section_data.get('title', section_data.get('id')),
                    content=section_data.get('content', ''),
                    optional=not section_data.get('required', True),
                    order=section_data.get('order', 0)
                ))
            
            metadata = TemplateMetadata(**metadata_data)
            
            return Template(
                metadata=metadata,
                content=data.get('template', ''),
                variables=variables,
                sections=sections,
                includes=data.get('includes', [])
            )
        else:
            # Legacy format handling
            metadata_data = data.get('metadata', {})
            
            # Infer template type and category from file path if not specified
            if 'type' not in metadata_data:
                metadata_data['type'] = self._infer_template_type(file_path)
            if 'category' not in metadata_data:
                metadata_data['category'] = self._infer_category(file_path)
            
            # Set default values
            metadata_data.setdefault('id', file_path.stem)
            metadata_data.setdefault('name', file_path.stem.replace('_', ' ').title())
            metadata_data.setdefault('description', f"Template loaded from {file_path.name}")
            
            metadata = TemplateMetadata(**metadata_data)
            
            # Extract variables
            variables = []
            for var_data in data.get('variables', []):
                variables.append(TemplateVariable(**var_data))
            
            # Extract sections
            sections = []
            for section_data in data.get('sections', []):
                sections.append(TemplateSection(**section_data))
            
            # Create template
            return Template(
                metadata=metadata,
                content=data.get('content', ''),
                variables=variables,
                sections=sections,
                includes=data.get('includes', [])
            )
    
    def _infer_template_type(self, file_path: Path) -> TemplateType:
        """Infer template type from file path."""
        stem = file_path.stem.lower()
        
        # Map common file names to template types
        type_map = {
            'readme': TemplateType.README,
            'api': TemplateType.API_REFERENCE,
            'api_reference': TemplateType.API_REFERENCE,
            'openapi': TemplateType.OPENAPI_SPEC,
            'install': TemplateType.INSTALLATION_GUIDE,
            'installation': TemplateType.INSTALLATION_GUIDE,
            'config': TemplateType.CONFIGURATION_GUIDE,
            'configuration': TemplateType.CONFIGURATION_GUIDE,
            'deploy': TemplateType.DEPLOYMENT_GUIDE,
            'deployment': TemplateType.DEPLOYMENT_GUIDE,
            'contributing': TemplateType.CONTRIBUTING,
            'changelog': TemplateType.CHANGELOG,
            'license': TemplateType.LICENSE,
            'test': TemplateType.TEST_PLAN,
            'test_plan': TemplateType.TEST_PLAN,
            'faq': TemplateType.FAQ,
            'tutorial': TemplateType.TUTORIAL,
            'guide': TemplateType.REFERENCE_GUIDE,
            'requirements': TemplateType.REQUIREMENTS_DOC,
            'design': TemplateType.DESIGN_DOC,
            'architecture': TemplateType.ARCHITECTURE_DOC,
            'security': TemplateType.SECURITY_DOC,
        }
        
        for key, template_type in type_map.items():
            if key in stem:
                return template_type
        
        # Default to reference guide
        return TemplateType.REFERENCE_GUIDE
    
    def _infer_category(self, file_path: Path) -> TemplateCategory:
        """Infer category from file path."""
        # Check parent directory name
        if file_path.parent.name in [cat.value for cat in TemplateCategory]:
            return TemplateCategory(file_path.parent.name)
        
        # Infer from template type
        template_type = self._infer_template_type(file_path)
        
        # Use category manager mapping
        from .categories import CategoryManager
        manager = CategoryManager()
        category = manager.get_category_for_type(template_type)
        
        return category or TemplateCategory.MISC
    
    def load_from_directory(self, directory: Union[str, Path], 
                           recursive: bool = True) -> List[Template]:
        """
        Load all templates from a directory.
        
        Args:
            directory: Directory path
            recursive: Whether to search recursively
            
        Returns:
            List of loaded templates
        """
        directory = Path(directory)
        
        if not directory.exists():
            raise TemplateStorageError("load", f"Directory not found: {directory}")
        
        templates = []
        
        # Get all template files
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for file_path in directory.glob(pattern):
            if file_path.is_file() and file_path.suffix in self.SUPPORTED_FORMATS:
                try:
                    template = self.load_from_file(file_path)
                    templates.append(template)
                    logger.info(f"Loaded template from {file_path}")
                except Exception as e:
                    logger.warning(f"Failed to load template from {file_path}: {e}")
        
        return templates
    
    def load_defaults(self) -> List[Template]:
        """
        Load all default templates.
        
        Returns:
            List of default templates
        """
        return self.load_from_directory(self.base_path, recursive=True)
    
    def save_to_file(self, template: Template, file_path: Union[str, Path], 
                    format: Optional[str] = None) -> None:
        """
        Save a template to a file.
        
        Args:
            template: Template to save
            file_path: Path to save to
            format: Output format (json, yaml, or text)
        """
        file_path = Path(file_path)
        
        # Determine format from extension if not specified
        if format is None:
            if file_path.suffix in {'.json'}:
                format = 'json'
            elif file_path.suffix in {'.yaml', '.yml'}:
                format = 'yaml'
            else:
                format = 'text'
        
        # Create directory if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        try:
            if format == 'json':
                self._save_json_template(template, file_path)
            elif format == 'yaml':
                self._save_yaml_template(template, file_path)
            else:
                self._save_text_template(template, file_path)
                
            logger.info(f"Saved template to {file_path}")
            
        except Exception as e:
            raise TemplateStorageError("save", f"Failed to save to {file_path}: {str(e)}")
    
    def _save_json_template(self, template: Template, file_path: Path) -> None:
        """Save template as JSON."""
        data = self._template_to_dict(template)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, default=str)
    
    def _save_yaml_template(self, template: Template, file_path: Path) -> None:
        """Save template as YAML."""
        data = self._template_to_dict(template)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False)
    
    def _save_text_template(self, template: Template, file_path: Path) -> None:
        """Save template as text with frontmatter."""
        # Create frontmatter
        frontmatter = self._template_to_dict(template)
        # Remove content from frontmatter as it goes in the body
        content = frontmatter.pop('content', '')
        
        with open(file_path, 'w', encoding='utf-8') as f:
            # Write frontmatter
            f.write('---\n')
            yaml.dump(frontmatter, f, default_flow_style=False)
            f.write('---\n\n')
            # Write content
            f.write(content)
    
    def _template_to_dict(self, template: Template) -> Dict:
        """Convert template to dictionary for serialization."""
        return {
            'metadata': {
                'id': template.metadata.id,
                'name': template.metadata.name,
                'description': template.metadata.description,
                'category': template.metadata.category.value,
                'type': template.metadata.type.value,
                'version': template.metadata.version,
                'author': template.metadata.author,
                'tags': template.metadata.tags,
                'created_at': template.metadata.created_at.isoformat(),
                'updated_at': template.metadata.updated_at.isoformat(),
                'is_custom': template.metadata.is_custom,
                'is_active': template.metadata.is_active,
                'usage_count': template.metadata.usage_count
            },
            'content': template.content,
            'variables': [
                {
                    'name': var.name,
                    'description': var.description,
                    'required': var.required,
                    'default': var.default,
                    'type': var.type,
                    'validation_pattern': var.validation_pattern
                }
                for var in template.variables
            ],
            'sections': [
                {
                    'name': section.name,
                    'content': section.content,
                    'optional': section.optional,
                    'repeatable': section.repeatable,
                    'conditions': section.conditions
                }
                for section in template.sections
            ],
            'includes': template.includes
        }
    
    def clear_cache(self) -> None:
        """Clear the template cache."""
        self._template_cache.clear()
        logger.info("Cleared template cache")