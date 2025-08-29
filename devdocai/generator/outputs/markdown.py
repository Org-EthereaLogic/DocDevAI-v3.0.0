"""
M004 Document Generator - Markdown output formatter.

Handles markdown-specific formatting, cleanup, and optimization for generated documents.
"""

import re
import logging
from typing import Optional, Dict, Any
from pathlib import Path

from ..core.template_loader import TemplateMetadata
from ...common.logging import get_logger

logger = get_logger(__name__)


class MarkdownOutput:
    """
    Formats document content for Markdown output.
    
    Features:
    - Markdown syntax validation and cleanup
    - Table of contents generation
    - Link validation and formatting
    - Metadata header generation
    """
    
    def __init__(self):
        """Initialize the markdown formatter."""
        logger.debug("MarkdownOutput initialized")
    
    def format_content(
        self, 
        content: str, 
        template_metadata: TemplateMetadata,
        include_metadata: bool = True,
        generate_toc: bool = False
    ) -> str:
        """
        Format content for markdown output.
        
        Args:
            content: Raw processed content
            template_metadata: Template metadata for formatting context
            include_metadata: Whether to include metadata header
            generate_toc: Whether to generate table of contents
            
        Returns:
            Formatted markdown content
        """
        try:
            # Start with content
            formatted_content = content
            
            # Apply markdown-specific formatting
            formatted_content = self._format_markdown_syntax(formatted_content)
            
            # Generate table of contents if requested
            toc = ""
            if generate_toc:
                toc = self._generate_table_of_contents(formatted_content)
            
            # Generate metadata header if requested
            metadata_header = ""
            if include_metadata:
                metadata_header = self._generate_metadata_header(template_metadata)
            
            # Combine all parts
            final_content = []
            
            if metadata_header:
                final_content.append(metadata_header)
            
            if toc:
                final_content.append("## Table of Contents\n")
                final_content.append(toc)
                final_content.append("---\n")
            
            final_content.append(formatted_content)
            
            result = "\n".join(final_content)
            
            # Final cleanup
            result = self._cleanup_markdown(result)
            
            logger.debug(f"Markdown formatting completed ({len(result)} characters)")
            return result
            
        except Exception as e:
            logger.error(f"Markdown formatting failed: {e}")
            # Return original content if formatting fails
            return content
    
    def validate_markdown(self, content: str) -> Dict[str, Any]:
        """
        Validate markdown content and return analysis.
        
        Args:
            content: Markdown content to validate
            
        Returns:
            Dictionary with validation results
        """
        validation_results = {
            'valid': True,
            'warnings': [],
            'errors': [],
            'stats': {
                'lines': 0,
                'headers': 0,
                'links': 0,
                'code_blocks': 0,
                'tables': 0
            }
        }
        
        try:
            lines = content.split('\n')
            validation_results['stats']['lines'] = len(lines)
            
            for line_num, line in enumerate(lines, 1):
                # Check for common markdown issues
                self._validate_line(line, line_num, validation_results)
            
            # Check overall structure
            self._validate_structure(content, validation_results)
            
            logger.debug(f"Markdown validation completed with {len(validation_results['errors'])} errors")
            
        except Exception as e:
            validation_results['errors'].append(f"Validation failed: {str(e)}")
            validation_results['valid'] = False
            logger.error(f"Markdown validation error: {e}")
        
        return validation_results
    
    def _format_markdown_syntax(self, content: str) -> str:
        """Apply markdown-specific formatting improvements."""
        # Fix common spacing issues
        content = re.sub(r'#{1,6}\s*([^\n]+)', lambda m: f"{m.group(0).split()[0]} {' '.join(m.group(0).split()[1:])}", content)
        
        # Ensure proper spacing around headers
        content = re.sub(r'\n(#{1,6}\s+[^\n]+)\n', r'\n\n\1\n\n', content)
        content = re.sub(r'^(#{1,6}\s+[^\n]+)\n', r'\1\n\n', content)
        
        # Fix list formatting
        content = re.sub(r'\n([*\-+]\s+)', r'\n\1', content)  # Bullet lists
        content = re.sub(r'\n(\d+\.\s+)', r'\n\1', content)   # Numbered lists
        
        # Ensure code blocks have proper spacing
        content = re.sub(r'\n(```[^\n]*\n)', r'\n\n\1', content)
        content = re.sub(r'(\n```\s*)\n', r'\1\n\n', content)
        
        return content
    
    def _generate_table_of_contents(self, content: str) -> str:
        """Generate table of contents from headers."""
        headers = []
        lines = content.split('\n')
        
        for line in lines:
            # Match markdown headers
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line.strip())
            if header_match:
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                
                # Create anchor link
                anchor = re.sub(r'[^\w\s-]', '', title).strip()
                anchor = re.sub(r'[-\s]+', '-', anchor).lower()
                
                # Add to TOC
                indent = '  ' * (level - 1)
                headers.append(f"{indent}- [{title}](#{anchor})")
        
        return '\n'.join(headers) if headers else ""
    
    def _generate_metadata_header(self, template_metadata: TemplateMetadata) -> str:
        """Generate YAML frontmatter metadata header."""
        metadata_lines = ['---']
        
        # Add basic metadata
        if template_metadata.title:
            metadata_lines.append(f'title: "{template_metadata.title}"')
        
        metadata_lines.append(f'template: "{template_metadata.name}"')
        metadata_lines.append(f'type: "{template_metadata.type}"')
        metadata_lines.append(f'category: "{template_metadata.category}"')
        metadata_lines.append(f'version: "{template_metadata.version}"')
        
        if template_metadata.author:
            metadata_lines.append(f'author: "{template_metadata.author}"')
        
        from datetime import datetime
        metadata_lines.append(f'generated_date: "{datetime.now().isoformat()}"')
        
        if template_metadata.tags:
            tags_str = ', '.join(f'"{tag}"' for tag in template_metadata.tags)
            metadata_lines.append(f'tags: [{tags_str}]')
        
        metadata_lines.append('---\n')
        
        return '\n'.join(metadata_lines)
    
    def _cleanup_markdown(self, content: str) -> str:
        """Final cleanup of markdown content."""
        # Remove excessive blank lines (more than 2 consecutive)
        content = re.sub(r'\n\s*\n\s*\n+', '\n\n', content)
        
        # Ensure file ends with single newline
        content = content.rstrip() + '\n'
        
        # Fix spacing around horizontal rules
        content = re.sub(r'\n(---+)\n', r'\n\n\1\n\n', content)
        
        return content
    
    def _validate_line(self, line: str, line_num: int, results: Dict[str, Any]) -> None:
        """Validate individual line of markdown."""
        # Count headers
        if re.match(r'^#{1,6}\s+', line):
            results['stats']['headers'] += 1
            
            # Check for proper header spacing
            if not re.match(r'^#{1,6}\s+.+', line):
                results['warnings'].append(f"Line {line_num}: Header missing space after #")
        
        # Count links
        links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', line)
        results['stats']['links'] += len(links)
        
        # Validate links
        for text, url in links:
            if not url.strip():
                results['errors'].append(f"Line {line_num}: Empty link URL for text '{text}'")
        
        # Count code blocks
        if line.strip().startswith('```'):
            results['stats']['code_blocks'] += 1
        
        # Count tables
        if '|' in line and not line.strip().startswith('```'):
            if re.match(r'^(\s*\|.*\|\s*)$', line):
                results['stats']['tables'] += 1
    
    def _validate_structure(self, content: str, results: Dict[str, Any]) -> None:
        """Validate overall markdown structure."""
        lines = content.split('\n')
        
        # Check for balanced code blocks
        code_block_starts = len([line for line in lines if re.match(r'^\s*```', line)])
        if code_block_starts % 2 != 0:
            results['errors'].append("Unbalanced code blocks (missing closing ```)")
            results['valid'] = False
        
        # Check header hierarchy
        header_levels = []
        for line in lines:
            header_match = re.match(r'^(#{1,6})\s+', line)
            if header_match:
                level = len(header_match.group(1))
                header_levels.append(level)
        
        # Validate header sequence (should not jump more than one level)
        for i in range(1, len(header_levels)):
            if header_levels[i] > header_levels[i-1] + 1:
                results['warnings'].append(f"Header hierarchy jump detected (#{header_levels[i-1]} to #{header_levels[i]})")