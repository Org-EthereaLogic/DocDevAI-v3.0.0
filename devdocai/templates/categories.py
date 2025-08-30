"""
Category management for M006 Template Registry.

This module provides category organization and management
for templates, enabling efficient template discovery and organization.
"""

from typing import Dict, List, Optional, Set
from collections import defaultdict
import logging

from .models import TemplateCategory, TemplateType, Template, TemplateMetadata
from .exceptions import TemplateCategoryError

logger = logging.getLogger(__name__)


class CategoryManager:
    """Manager for template categories and organization."""
    
    # Mapping of template types to categories
    TYPE_CATEGORY_MAP = {
        # API Templates
        TemplateType.API_REFERENCE: TemplateCategory.API,
        TemplateType.API_ENDPOINT: TemplateCategory.API,
        TemplateType.OPENAPI_SPEC: TemplateCategory.API,
        TemplateType.REST_API: TemplateCategory.API,
        TemplateType.GRAPHQL_SCHEMA: TemplateCategory.API,
        
        # Documentation Templates
        TemplateType.README: TemplateCategory.DOCUMENTATION,
        TemplateType.USER_MANUAL: TemplateCategory.DOCUMENTATION,
        TemplateType.TECHNICAL_SPEC: TemplateCategory.DOCUMENTATION,
        TemplateType.ARCHITECTURE_DOC: TemplateCategory.DOCUMENTATION,
        TemplateType.DATABASE_SCHEMA: TemplateCategory.DOCUMENTATION,
        
        # Guide Templates
        TemplateType.INSTALLATION_GUIDE: TemplateCategory.GUIDES,
        TemplateType.CONFIGURATION_GUIDE: TemplateCategory.GUIDES,
        TemplateType.DEPLOYMENT_GUIDE: TemplateCategory.GUIDES,
        TemplateType.MIGRATION_GUIDE: TemplateCategory.GUIDES,
        TemplateType.INTEGRATION_GUIDE: TemplateCategory.GUIDES,
        TemplateType.QUICK_START: TemplateCategory.GUIDES,
        TemplateType.TUTORIAL: TemplateCategory.GUIDES,
        TemplateType.TROUBLESHOOTING: TemplateCategory.GUIDES,
        
        # Specification Templates
        TemplateType.REQUIREMENTS_DOC: TemplateCategory.SPECIFICATIONS,
        TemplateType.DESIGN_DOC: TemplateCategory.SPECIFICATIONS,
        TemplateType.PROJECT_PROPOSAL: TemplateCategory.SPECIFICATIONS,
        TemplateType.SECURITY_DOC: TemplateCategory.SPECIFICATIONS,
        
        # Project Templates
        TemplateType.CONTRIBUTING: TemplateCategory.PROJECTS,
        TemplateType.CODE_OF_CONDUCT: TemplateCategory.PROJECTS,
        TemplateType.LICENSE: TemplateCategory.PROJECTS,
        TemplateType.CHANGELOG: TemplateCategory.PROJECTS,
        TemplateType.RELEASE_NOTES: TemplateCategory.PROJECTS,
        
        # Development Templates
        TemplateType.DEVELOPMENT_GUIDE: TemplateCategory.DEVELOPMENT,
        TemplateType.STYLE_GUIDE: TemplateCategory.DEVELOPMENT,
        TemplateType.BEST_PRACTICES: TemplateCategory.DEVELOPMENT,
        TemplateType.CODE_REVIEW: TemplateCategory.DEVELOPMENT,
        
        # Testing Templates
        TemplateType.TEST_PLAN: TemplateCategory.TESTING,
        TemplateType.TEST_CASES: TemplateCategory.TESTING,
        TemplateType.PERFORMANCE_REPORT: TemplateCategory.TESTING,
        TemplateType.BUG_REPORT: TemplateCategory.TESTING,
        
        # Miscellaneous
        TemplateType.FAQ: TemplateCategory.MISC,
        TemplateType.REFERENCE_GUIDE: TemplateCategory.MISC,
        TemplateType.GLOSSARY: TemplateCategory.MISC,
        TemplateType.MEETING_NOTES: TemplateCategory.MISC,
    }
    
    def __init__(self):
        """Initialize category manager."""
        self._templates_by_category: Dict[TemplateCategory, List[Template]] = defaultdict(list)
        self._templates_by_type: Dict[TemplateType, List[Template]] = defaultdict(list)
        self._category_metadata: Dict[TemplateCategory, Dict] = self._init_category_metadata()
        
    def _init_category_metadata(self) -> Dict[TemplateCategory, Dict]:
        """Initialize category metadata."""
        return {
            TemplateCategory.API: {
                "name": "API Documentation",
                "description": "Templates for API documentation, specifications, and references",
                "icon": "📡",
                "priority": 1
            },
            TemplateCategory.DOCUMENTATION: {
                "name": "Documentation",
                "description": "General documentation templates for various purposes",
                "icon": "📚",
                "priority": 2
            },
            TemplateCategory.GUIDES: {
                "name": "Guides",
                "description": "Step-by-step guides and tutorials",
                "icon": "📖",
                "priority": 3
            },
            TemplateCategory.SPECIFICATIONS: {
                "name": "Specifications",
                "description": "Technical and project specifications",
                "icon": "📋",
                "priority": 4
            },
            TemplateCategory.PROJECTS: {
                "name": "Project Files",
                "description": "Project-level documentation and files",
                "icon": "📁",
                "priority": 5
            },
            TemplateCategory.DEVELOPMENT: {
                "name": "Development",
                "description": "Development guidelines and best practices",
                "icon": "💻",
                "priority": 6
            },
            TemplateCategory.TESTING: {
                "name": "Testing",
                "description": "Test plans, reports, and testing documentation",
                "icon": "🧪",
                "priority": 7
            },
            TemplateCategory.MISC: {
                "name": "Miscellaneous",
                "description": "Other documentation templates",
                "icon": "📄",
                "priority": 8
            }
        }
    
    def add_template(self, template: Template) -> None:
        """
        Add a template to the category manager.
        
        Args:
            template: Template to add
            
        Raises:
            TemplateCategoryError: If category is invalid
        """
        category = template.metadata.category
        template_type = template.metadata.type
        
        if category not in TemplateCategory:
            raise TemplateCategoryError(str(category), "Invalid category")
        
        # Add to category index
        self._templates_by_category[category].append(template)
        
        # Add to type index
        self._templates_by_type[template_type].append(template)
        
        logger.info(f"Added template '{template.metadata.name}' to category '{category.value}'")
    
    def remove_template(self, template_id: str) -> bool:
        """
        Remove a template from the category manager.
        
        Args:
            template_id: ID of template to remove
            
        Returns:
            True if removed, False if not found
        """
        removed = False
        
        for category_templates in self._templates_by_category.values():
            for i, template in enumerate(category_templates):
                if template.metadata.id == template_id:
                    category_templates.pop(i)
                    removed = True
                    break
        
        for type_templates in self._templates_by_type.values():
            for i, template in enumerate(type_templates):
                if template.metadata.id == template_id:
                    type_templates.pop(i)
                    break
        
        return removed
    
    def get_templates_by_category(self, category: TemplateCategory) -> List[Template]:
        """
        Get all templates in a category.
        
        Args:
            category: Category to get templates for
            
        Returns:
            List of templates in the category
        """
        return self._templates_by_category.get(category, [])
    
    def get_templates_by_type(self, template_type: TemplateType) -> List[Template]:
        """
        Get all templates of a specific type.
        
        Args:
            template_type: Type to get templates for
            
        Returns:
            List of templates of the type
        """
        return self._templates_by_type.get(template_type, [])
    
    def get_category_for_type(self, template_type: TemplateType) -> Optional[TemplateCategory]:
        """
        Get the category for a template type.
        
        Args:
            template_type: Template type
            
        Returns:
            Category for the type, or None if not found
        """
        return self.TYPE_CATEGORY_MAP.get(template_type)
    
    def get_types_in_category(self, category: TemplateCategory) -> List[TemplateType]:
        """
        Get all template types in a category.
        
        Args:
            category: Category to get types for
            
        Returns:
            List of template types in the category
        """
        types = []
        for template_type, cat in self.TYPE_CATEGORY_MAP.items():
            if cat == category:
                types.append(template_type)
        return types
    
    def get_category_metadata(self, category: TemplateCategory) -> Dict:
        """
        Get metadata for a category.
        
        Args:
            category: Category to get metadata for
            
        Returns:
            Category metadata dictionary
        """
        return self._category_metadata.get(category, {})
    
    def get_all_categories(self) -> List[TemplateCategory]:
        """
        Get all available categories.
        
        Returns:
            List of all categories sorted by priority
        """
        categories = list(TemplateCategory)
        # Sort by priority from metadata
        categories.sort(key=lambda c: self._category_metadata.get(c, {}).get("priority", 999))
        return categories
    
    def get_category_statistics(self) -> Dict[TemplateCategory, Dict]:
        """
        Get statistics for all categories.
        
        Returns:
            Dictionary of category statistics
        """
        stats = {}
        for category in TemplateCategory:
            templates = self._templates_by_category.get(category, [])
            stats[category] = {
                "total": len(templates),
                "active": sum(1 for t in templates if t.metadata.is_active),
                "custom": sum(1 for t in templates if t.metadata.is_custom),
                "usage": sum(t.metadata.usage_count for t in templates)
            }
        return stats
    
    def search_templates(self, query: str, category: Optional[TemplateCategory] = None) -> List[Template]:
        """
        Search templates by query string.
        
        Args:
            query: Search query
            category: Optional category to limit search to
            
        Returns:
            List of matching templates
        """
        query_lower = query.lower()
        results = []
        
        # Determine which templates to search
        if category:
            templates_to_search = self._templates_by_category.get(category, [])
        else:
            templates_to_search = []
            for cat_templates in self._templates_by_category.values():
                templates_to_search.extend(cat_templates)
        
        # Search in name, description, and tags
        seen_ids = set()
        for template in templates_to_search:
            if template.metadata.id in seen_ids:
                continue
                
            if (query_lower in template.metadata.name.lower() or
                query_lower in template.metadata.description.lower() or
                any(query_lower in tag.lower() for tag in template.metadata.tags)):
                results.append(template)
                seen_ids.add(template.metadata.id)
        
        return results
    
    def get_popular_templates(self, limit: int = 10) -> List[Template]:
        """
        Get most popular templates by usage count.
        
        Args:
            limit: Maximum number of templates to return
            
        Returns:
            List of popular templates
        """
        all_templates = []
        seen_ids = set()
        
        for cat_templates in self._templates_by_category.values():
            for template in cat_templates:
                if template.metadata.id not in seen_ids:
                    all_templates.append(template)
                    seen_ids.add(template.metadata.id)
        
        # Sort by usage count
        all_templates.sort(key=lambda t: t.metadata.usage_count, reverse=True)
        
        return all_templates[:limit]
    
    def clear(self) -> None:
        """Clear all templates from the manager."""
        self._templates_by_category.clear()
        self._templates_by_type.clear()
        logger.info("Cleared all templates from category manager")