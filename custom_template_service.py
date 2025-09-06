"""
Custom Template Service for DevDocAI
Scans and provides access to user's custom templates from /DevDocAI-templete-examples/
"""

import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class CustomTemplateService:
    """Service to manage custom user templates"""
    
    def __init__(self, template_dir: str = "/workspaces/DocDevAI-v3.0.0/DevDocAI-templete-examples"):
        self.template_dir = Path(template_dir)
        self.templates_cache: Dict[str, Dict[str, Any]] = {}
        self.scan_templates()
    
    def scan_templates(self) -> Dict[str, Dict[str, Any]]:
        """Scan the template directory and load all available templates"""
        self.templates_cache = {}
        
        if not self.template_dir.exists():
            logger.warning(f"Template directory does not exist: {self.template_dir}")
            return self.templates_cache
        
        for template_file in self.template_dir.glob("*.md"):
            try:
                template_id = self._generate_template_id(template_file.stem)
                template_content = template_file.read_text(encoding='utf-8')
                
                # Parse template to extract structure and variables
                template_info = self._parse_template(template_content)
                
                self.templates_cache[template_id] = {
                    'id': template_id,
                    'name': template_file.stem,
                    'file_path': str(template_file),
                    'content': template_content,
                    'sections': template_info['sections'],
                    'variables': template_info['variables'],
                    'description': template_info['description'],
                    'category': self._determine_category(template_file.stem)
                }
                
                logger.info(f"Loaded custom template: {template_file.stem}")
                
            except Exception as e:
                logger.error(f"Failed to load template {template_file}: {e}")
        
        return self.templates_cache
    
    def _generate_template_id(self, name: str) -> str:
        """Generate a consistent ID from template name"""
        # Map custom template names to IDs matching frontend expectations
        id_map = {
            'Product Requirements Document Creation': 'prd_custom',
            'Project Plan WBS Creation': 'wbs_custom',
            'Software Architecture Documentation Creation': 'architecture_custom',
            'Software Requirements Specification Creation': 'srs_custom'
        }
        return id_map.get(name, name.lower().replace(' ', '_'))
    
    def _determine_category(self, name: str) -> str:
        """Determine template category based on name"""
        if 'Requirements' in name or 'PRD' in name or 'SRS' in name:
            return 'requirements'
        elif 'Architecture' in name:
            return 'architecture'
        elif 'Plan' in name or 'WBS' in name:
            return 'planning'
        else:
            return 'general'
    
    def _parse_template(self, content: str) -> Dict[str, Any]:
        """Parse template content to extract structure and variables"""
        sections = []
        variables = []
        description = ""
        
        # Extract variables (looking for {{VARIABLE_NAME}} patterns)
        variable_pattern = r'\{\{([A-Z_]+)\}\}'
        variables = list(set(re.findall(variable_pattern, content)))
        
        # Extract sections (looking for numbered lists in instructions)
        lines = content.split('\n')
        in_steps = False
        for line in lines:
            if 'Follow these steps:' in line or 'steps:' in line.lower():
                in_steps = True
            elif in_steps and re.match(r'^\d+\.', line.strip()):
                # Extract section name from numbered list
                section_text = line.strip()[3:].strip()  # Remove number and dot
                if section_text:
                    # Clean up section name
                    section_name = section_text.split(':')[0] if ':' in section_text else section_text
                    sections.append(section_name)
        
        # Extract description from first paragraph
        for line in lines:
            if line.strip() and not line.startswith('#'):
                description = line.strip()
                if len(description) > 200:
                    description = description[:197] + "..."
                break
        
        # If no sections found, extract from PRD structure in content
        if not sections and 'PRD sections:' in content:
            section_start = content.find('PRD sections:')
            if section_start > 0:
                section_text = content[section_start:section_start + 500]
                section_items = re.findall(r'[a-z]\.\s+([^:]+)', section_text)
                sections = section_items[:12]  # Take first 12 sections
        
        return {
            'sections': sections,
            'variables': variables,
            'description': description or "Custom template for documentation generation"
        }
    
    def get_template(self, template_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific template by ID"""
        return self.templates_cache.get(template_id)
    
    def list_templates(self) -> List[Dict[str, str]]:
        """List all available templates with metadata"""
        template_list = []
        for tid, template in self.templates_cache.items():
            template_list.append({
                'id': tid,
                'name': template['name'],
                'description': template['description'],
                'category': template['category'],
                'sections_count': len(template['sections']),
                'variables_count': len(template['variables'])
            })
        return template_list
    
    def render_template(self, template_id: str, variables: Dict[str, str], writing_style: str = 'verbose_prose') -> str:
        """
        Render a template with given variables and writing style
        
        Args:
            template_id: ID of the template to render
            variables: Dictionary of variable values to substitute
            writing_style: Either 'verbose_prose' or 'structured'
        
        Returns:
            Rendered template content with style instructions
        """
        template = self.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")
        
        content = template['content']
        
        # Substitute variables
        for var_name, var_value in variables.items():
            placeholder = f"{{{{{var_name}}}}}"
            content = content.replace(placeholder, var_value)
        
        # Add writing style instructions
        style_instructions = self._get_style_instructions(writing_style)
        
        # Inject style instructions into the template
        if writing_style == 'verbose_prose':
            # For verbose prose, modify the template to emphasize narrative writing
            content = self._enhance_for_verbose_prose(content)
        
        return content
    
    def _get_style_instructions(self, writing_style: str) -> str:
        """Get specific instructions for the writing style"""
        if writing_style == 'verbose_prose':
            return """
CRITICAL WRITING STYLE REQUIREMENT:
Write the ENTIRE document in rich, flowing narrative prose. Use complete paragraphs with smooth transitions between ideas.
DO NOT use bullet points, lists, or short fragments. Every section must be written in professional, descriptive paragraphs.
Focus on storytelling, context, and thorough explanations. Make the document engaging and comprehensive.
"""
        else:
            return """
WRITING STYLE:
Use a structured format with clear headings, bullet points, and concise descriptions.
Organize information for quick scanning and easy reference.
Balance detail with brevity for maximum clarity.
"""
    
    def _enhance_for_verbose_prose(self, content: str) -> str:
        """Enhance template content for verbose prose generation"""
        # Add explicit prose instructions to the template
        prose_enhancement = """

IMPORTANT: Transform ALL sections into rich, narrative prose:
- Convert any lists or bullet points into flowing paragraphs
- Expand brief descriptions into comprehensive narratives
- Add context, background, and detailed explanations
- Use transitional phrases to connect ideas smoothly
- Write in a professional, engaging tone throughout

"""
        
        # Find a good insertion point (after initial instructions)
        if "Follow these steps:" in content:
            parts = content.split("Follow these steps:")
            content = parts[0] + "Follow these steps:" + prose_enhancement + parts[1]
        elif "Begin your response with" in content:
            parts = content.split("Begin your response with")
            content = parts[0] + prose_enhancement + "Begin your response with" + parts[1]
        else:
            # Insert after first paragraph
            lines = content.split('\n')
            if len(lines) > 2:
                content = '\n'.join(lines[:2]) + prose_enhancement + '\n'.join(lines[2:])
        
        return content
    
    def get_template_preview(self, template_id: str) -> Dict[str, Any]:
        """Get a preview of template structure for UI display"""
        template = self.get_template(template_id)
        if not template:
            return {}
        
        return {
            'id': template_id,
            'name': template['name'],
            'description': template['description'],
            'sections': template['sections'][:10],  # Show first 10 sections
            'total_sections': len(template['sections']),
            'required_inputs': template['variables'],
            'category': template['category']
        }


# Singleton instance
_custom_template_service = None

def get_custom_template_service() -> CustomTemplateService:
    """Get or create the singleton template service instance"""
    global _custom_template_service
    if _custom_template_service is None:
        _custom_template_service = CustomTemplateService()
    return _custom_template_service