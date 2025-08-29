"""
M004 Document Generator - Template loading system.

Handles loading, parsing, and validation of Jinja2 templates with YAML frontmatter.
Supports template discovery, metadata extraction, and caching.
"""

import os
import yaml
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from functools import lru_cache

import jinja2
from jinja2 import Environment, FileSystemLoader, Template, meta

from ...common.errors import DevDocAIError
from ...common.logging import get_logger

logger = get_logger(__name__)


@dataclass
class TemplateMetadata:
    """Metadata for a document template."""
    
    name: str
    title: str
    type: str  # template type (technical, user, project, etc.)
    category: str  # subcategory within type
    description: Optional[str] = None
    version: str = "1.0"
    author: Optional[str] = None
    created_date: Optional[str] = None
    variables: Optional[List[str]] = None  # Required template variables
    optional_variables: Optional[List[str]] = None  # Optional template variables
    sections: Optional[List[str]] = None  # Document sections
    tags: Optional[List[str]] = None
    metadata: Optional[Dict[str, Any]] = None  # Additional metadata
    content: Optional[str] = None  # Template content (loaded separately)
    file_path: Optional[Path] = None  # Source file path
    
    def __post_init__(self):
        """Initialize default values after creation."""
        if self.variables is None:
            self.variables = []
        if self.optional_variables is None:
            self.optional_variables = []
        if self.sections is None:
            self.sections = []
        if self.tags is None:
            self.tags = []
        if self.metadata is None:
            self.metadata = {}


class TemplateLoader:
    """
    Loads and manages document templates.
    
    Templates are stored as Jinja2 files with YAML frontmatter:
    
    ---
    title: "Product Requirements Document"
    type: "technical"
    category: "requirements"
    version: "1.0"
    author: "DevDocAI"
    variables: ["title", "project_name", "overview"]
    sections: ["overview", "requirements", "specifications"]
    ---
    # {{ title }}
    
    ## Overview
    {{ overview_content }}
    """
    
    def __init__(self, template_dir: Path):
        """Initialize the template loader.
        
        Args:
            template_dir: Directory containing template files
        """
        self.template_dir = Path(template_dir)
        self._template_cache = {}  # Cache for loaded templates
        self._metadata_cache = {}  # Cache for template metadata
        
        # Create Jinja2 environment
        self.jinja_env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            autoescape=False,  # We're generating documentation, not HTML
            trim_blocks=True,
            lstrip_blocks=True
        )
        
        # Add custom filters
        self._register_custom_filters()
        
        logger.info(f"TemplateLoader initialized with directory: {self.template_dir}")
    
    def load_template(self, template_name: str) -> Optional[TemplateMetadata]:
        """
        Load a template and its metadata.
        
        Args:
            template_name: Name of the template file (without .j2 extension)
            
        Returns:
            TemplateMetadata object with content, or None if not found
        """
        # Check cache first
        if template_name in self._template_cache:
            return self._template_cache[template_name]
        
        try:
            # Find template file
            template_file = self._find_template_file(template_name)
            if not template_file:
                logger.warning(f"Template not found: {template_name}")
                return None
            
            # Read and parse template file
            with open(template_file, 'r', encoding='utf-8') as f:
                file_content = f.read()
            
            # Split frontmatter and content
            frontmatter, content = self._parse_template_file(file_content)
            
            # Extract template variables
            variables = self._extract_template_variables(content)
            
            # Create metadata object
            metadata = TemplateMetadata(
                name=template_name,
                title=frontmatter.get('title', template_name.title()),
                type=frontmatter.get('type', 'unknown'),
                category=frontmatter.get('category', 'general'),
                description=frontmatter.get('description'),
                version=frontmatter.get('version', '1.0'),
                author=frontmatter.get('author'),
                created_date=frontmatter.get('created_date'),
                variables=frontmatter.get('variables', variables['required']),
                optional_variables=frontmatter.get('optional_variables', variables['optional']),
                sections=frontmatter.get('sections', []),
                tags=frontmatter.get('tags', []),
                metadata=frontmatter.get('metadata', {}),
                content=content,
                file_path=template_file
            )
            
            # Cache the template
            self._template_cache[template_name] = metadata
            self._metadata_cache[template_name] = metadata
            
            logger.debug(f"Template loaded: {template_name} ({metadata.type}/{metadata.category})")
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            return None
    
    def get_template_metadata(self, template_name: str) -> Optional[TemplateMetadata]:
        """
        Get template metadata without loading content.
        
        Args:
            template_name: Name of the template
            
        Returns:
            TemplateMetadata object without content, or None if not found
        """
        # Check cache first
        if template_name in self._metadata_cache:
            return self._metadata_cache[template_name]
        
        # Load full template (which caches metadata)
        template = self.load_template(template_name)
        return template
    
    def list_templates(self) -> List[TemplateMetadata]:
        """
        List all available templates.
        
        Returns:
            List of TemplateMetadata objects (without content loaded)
        """
        templates = []
        
        try:
            # Walk through template directory
            for template_file in self.template_dir.rglob("*.j2"):
                # Extract template name from file path
                relative_path = template_file.relative_to(self.template_dir)
                template_name = str(relative_path.with_suffix(''))
                
                # Load metadata only
                metadata = self.get_template_metadata(template_name)
                if metadata:
                    # Create a copy without content for listing
                    listing_metadata = TemplateMetadata(
                        name=metadata.name,
                        title=metadata.title,
                        type=metadata.type,
                        category=metadata.category,
                        description=metadata.description,
                        version=metadata.version,
                        author=metadata.author,
                        created_date=metadata.created_date,
                        variables=metadata.variables,
                        optional_variables=metadata.optional_variables,
                        sections=metadata.sections,
                        tags=metadata.tags,
                        metadata=metadata.metadata,
                        file_path=metadata.file_path
                    )
                    templates.append(listing_metadata)
            
            logger.debug(f"Listed {len(templates)} templates")
            return templates
            
        except Exception as e:
            logger.error(f"Failed to list templates: {e}")
            return []
    
    def get_template_categories(self) -> Dict[str, List[str]]:
        """
        Get available template types and categories.
        
        Returns:
            Dictionary mapping template types to list of categories
        """
        categories = {}
        
        for template in self.list_templates():
            if template.type not in categories:
                categories[template.type] = []
            if template.category not in categories[template.type]:
                categories[template.type].append(template.category)
        
        return categories
    
    def clear_cache(self) -> None:
        """Clear template cache."""
        self._template_cache.clear()
        self._metadata_cache.clear()
        logger.debug("Template cache cleared")
    
    def _find_template_file(self, template_name: str) -> Optional[Path]:
        """Find template file by name, searching in subdirectories."""
        template_file = self.template_dir / f"{template_name}.j2"
        
        if template_file.exists():
            return template_file
        
        # Search in subdirectories
        for template_file in self.template_dir.rglob(f"{template_name}.j2"):
            return template_file
        
        # Try with different path formats
        for template_file in self.template_dir.rglob("*.j2"):
            relative_path = template_file.relative_to(self.template_dir)
            if str(relative_path.with_suffix('')) == template_name:
                return template_file
        
        return None
    
    def _parse_template_file(self, file_content: str) -> tuple[Dict[str, Any], str]:
        """Parse template file with YAML frontmatter."""
        parts = file_content.split('---', 2)
        
        if len(parts) >= 3 and parts[0].strip() == '':
            # Has frontmatter
            try:
                frontmatter = yaml.safe_load(parts[1]) or {}
                content = parts[2].strip()
            except yaml.YAMLError as e:
                logger.warning(f"Invalid YAML frontmatter: {e}")
                frontmatter = {}
                content = file_content
        else:
            # No frontmatter
            frontmatter = {}
            content = file_content
        
        return frontmatter, content
    
    def _extract_template_variables(self, template_content: str) -> Dict[str, List[str]]:
        """Extract required and optional variables from template content."""
        try:
            # Parse template to find undefined variables
            template = self.jinja_env.from_string(template_content)
            undefined_vars = meta.find_undeclared_variables(template.module.__dict__)
            
            # For now, all undefined variables are considered required
            # In the future, we could analyze default values and conditionals
            # to distinguish between required and optional variables
            
            return {
                'required': list(undefined_vars),
                'optional': []
            }
            
        except Exception as e:
            logger.warning(f"Failed to extract template variables: {e}")
            return {'required': [], 'optional': []}
    
    def _register_custom_filters(self) -> None:
        """Register custom Jinja2 filters for document generation."""
        
        def markdown_table(data: List[Dict[str, Any]], headers: Optional[List[str]] = None) -> str:
            """Convert list of dictionaries to markdown table."""
            if not data:
                return ""
            
            if not headers:
                headers = list(data[0].keys())
            
            # Create header row
            header_row = "| " + " | ".join(headers) + " |"
            separator_row = "|" + "|".join([" --- " for _ in headers]) + "|"
            
            # Create data rows
            data_rows = []
            for row in data:
                row_values = [str(row.get(header, "")) for header in headers]
                data_rows.append("| " + " | ".join(row_values) + " |")
            
            return "\n".join([header_row, separator_row] + data_rows)
        
        def format_date(date_str: str, format_str: str = "%Y-%m-%d") -> str:
            """Format date string."""
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime(format_str)
            except Exception:
                return date_str
        
        def slugify(text: str) -> str:
            """Convert text to URL-friendly slug."""
            import re
            text = text.lower()
            text = re.sub(r'[^\w\s-]', '', text)
            text = re.sub(r'[-\s]+', '-', text)
            return text.strip('-')
        
        # Register filters
        self.jinja_env.filters['markdown_table'] = markdown_table
        self.jinja_env.filters['format_date'] = format_date
        self.jinja_env.filters['slugify'] = slugify