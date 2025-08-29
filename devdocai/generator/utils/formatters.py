"""
M004 Document Generator - Content formatting utilities.

Provides utilities for content formatting, text processing, and document structure.
"""

import re
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pathlib import Path

from ...common.logging import get_logger

logger = get_logger(__name__)


class ContentFormatter:
    """
    Provides content formatting utilities for document generation.
    
    Features:
    - Text formatting and cleanup
    - Structure formatting (tables, lists, headers)
    - Content transformation utilities
    - Document organization helpers
    """
    
    def __init__(self):
        """Initialize the content formatter."""
        logger.debug("ContentFormatter initialized")
    
    def format_text(self, text: str, style: str = "default") -> str:
        """
        Format text according to specified style.
        
        Args:
            text: Text to format
            style: Formatting style (default, title, sentence, etc.)
            
        Returns:
            Formatted text
        """
        if not text:
            return ""
        
        text = str(text).strip()
        
        if style == "title":
            return self._format_title(text)
        elif style == "sentence":
            return self._format_sentence(text)
        elif style == "paragraph":
            return self._format_paragraph(text)
        elif style == "code":
            return self._format_code(text)
        else:
            return self._format_default(text)
    
    def create_table(
        self, 
        data: List[Dict[str, Any]], 
        headers: Optional[List[str]] = None,
        format_type: str = "markdown"
    ) -> str:
        """
        Create formatted table from data.
        
        Args:
            data: List of dictionaries representing table rows
            headers: Column headers (if None, uses keys from first row)
            format_type: Output format (markdown, html, plain)
            
        Returns:
            Formatted table string
        """
        if not data:
            return ""
        
        if not headers:
            headers = list(data[0].keys())
        
        if format_type == "markdown":
            return self._create_markdown_table(data, headers)
        elif format_type == "html":
            return self._create_html_table(data, headers)
        else:
            return self._create_plain_table(data, headers)
    
    def create_list(
        self, 
        items: List[Any], 
        list_type: str = "bullet",
        nested: bool = False
    ) -> str:
        """
        Create formatted list from items.
        
        Args:
            items: List items
            list_type: Type of list (bullet, numbered, checklist)
            nested: Whether to handle nested lists
            
        Returns:
            Formatted list string
        """
        if not items:
            return ""
        
        if list_type == "numbered":
            return self._create_numbered_list(items, nested)
        elif list_type == "checklist":
            return self._create_checklist(items, nested)
        else:
            return self._create_bullet_list(items, nested)
    
    def format_headers(self, text: str, base_level: int = 1) -> str:
        """
        Format and adjust header levels in text.
        
        Args:
            text: Text containing markdown headers
            base_level: Base header level to start from
            
        Returns:
            Text with adjusted header levels
        """
        lines = text.split('\n')
        formatted_lines = []
        
        for line in lines:
            if line.strip().startswith('#'):
                # Count current header level
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                
                # Adjust level
                new_level = base_level + level - 1
                if new_level > 6:
                    new_level = 6
                
                # Reconstruct header
                header_text = line.strip()[level:].strip()
                new_line = '#' * new_level + ' ' + header_text
                formatted_lines.append(new_line)
            else:
                formatted_lines.append(line)
        
        return '\n'.join(formatted_lines)
    
    def clean_whitespace(self, text: str) -> str:
        """
        Clean up whitespace in text content.
        
        Args:
            text: Text to clean
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Normalize line endings
        text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        # Remove trailing whitespace from lines
        lines = text.split('\n')
        cleaned_lines = [line.rstrip() for line in lines]
        
        # Remove excessive blank lines (more than 2 consecutive)
        result_lines = []
        blank_count = 0
        
        for line in cleaned_lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)
        
        return '\n'.join(result_lines)
    
    def wrap_text(self, text: str, width: int = 80, preserve_paragraphs: bool = True) -> str:
        """
        Wrap text to specified width.
        
        Args:
            text: Text to wrap
            width: Maximum line width
            preserve_paragraphs: Whether to preserve paragraph breaks
            
        Returns:
            Wrapped text
        """
        if not text:
            return ""
        
        if preserve_paragraphs:
            paragraphs = text.split('\n\n')
            wrapped_paragraphs = []
            
            for paragraph in paragraphs:
                if paragraph.strip():
                    wrapped = self._wrap_paragraph(paragraph.strip(), width)
                    wrapped_paragraphs.append(wrapped)
                else:
                    wrapped_paragraphs.append("")
            
            return '\n\n'.join(wrapped_paragraphs)
        else:
            return self._wrap_paragraph(text, width)
    
    def extract_structure(self, text: str) -> Dict[str, Any]:
        """
        Extract document structure from text.
        
        Args:
            text: Text to analyze
            
        Returns:
            Dictionary containing structure information
        """
        structure = {
            'headers': [],
            'sections': {},
            'word_count': 0,
            'line_count': 0,
            'paragraph_count': 0
        }
        
        lines = text.split('\n')
        structure['line_count'] = len(lines)
        
        current_section = None
        section_content = []
        
        for line in lines:
            line = line.strip()
            
            # Detect headers
            if line.startswith('#'):
                # Save previous section
                if current_section:
                    structure['sections'][current_section] = '\n'.join(section_content)
                
                # Extract header info
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                
                title = line[level:].strip()
                header_info = {
                    'level': level,
                    'title': title,
                    'line_number': lines.index(line) + 1
                }
                structure['headers'].append(header_info)
                
                # Start new section
                current_section = title
                section_content = []
            else:
                if line:  # Non-empty line
                    section_content.append(line)
        
        # Save final section
        if current_section:
            structure['sections'][current_section] = '\n'.join(section_content)
        
        # Count words and paragraphs
        structure['word_count'] = len(text.split())
        structure['paragraph_count'] = len([p for p in text.split('\n\n') if p.strip()])
        
        return structure
    
    def _format_title(self, text: str) -> str:
        """Format text as title (title case)."""
        # Simple title case - capitalize each word
        words = text.split()
        # Don't capitalize articles, prepositions, and conjunctions (unless first/last word)
        small_words = {'a', 'an', 'and', 'as', 'at', 'but', 'by', 'for', 'if', 'in', 'of', 'on', 'or', 'the', 'to', 'up', 'via'}
        
        titled_words = []
        for i, word in enumerate(words):
            if i == 0 or i == len(words) - 1 or word.lower() not in small_words:
                titled_words.append(word.capitalize())
            else:
                titled_words.append(word.lower())
        
        return ' '.join(titled_words)
    
    def _format_sentence(self, text: str) -> str:
        """Format text as proper sentence."""
        if not text:
            return ""
        
        # Capitalize first letter
        text = text[0].upper() + text[1:] if len(text) > 1 else text.upper()
        
        # Ensure ends with proper punctuation
        if not text.endswith(('.', '!', '?', ':')):
            text += '.'
        
        return text
    
    def _format_paragraph(self, text: str) -> str:
        """Format text as paragraph."""
        # Clean up spacing and ensure proper sentence structure
        sentences = re.split(r'[.!?]+', text)
        formatted_sentences = []
        
        for sentence in sentences:
            sentence = sentence.strip()
            if sentence:
                # Capitalize first letter
                sentence = sentence[0].upper() + sentence[1:] if len(sentence) > 1 else sentence.upper()
                formatted_sentences.append(sentence)
        
        if formatted_sentences:
            return '. '.join(formatted_sentences) + '.'
        return text
    
    def _format_code(self, text: str) -> str:
        """Format text as code block."""
        return f"```\n{text}\n```"
    
    def _format_default(self, text: str) -> str:
        """Default text formatting (cleanup only)."""
        # Just clean up extra whitespace
        return ' '.join(text.split())
    
    def _create_markdown_table(self, data: List[Dict[str, Any]], headers: List[str]) -> str:
        """Create markdown table."""
        if not data:
            return ""
        
        # Create header row
        header_row = "| " + " | ".join(str(h) for h in headers) + " |"
        separator_row = "|" + "|".join([" --- " for _ in headers]) + "|"
        
        # Create data rows
        data_rows = []
        for row in data:
            row_values = [str(row.get(header, "")) for header in headers]
            data_rows.append("| " + " | ".join(row_values) + " |")
        
        return "\n".join([header_row, separator_row] + data_rows)
    
    def _create_html_table(self, data: List[Dict[str, Any]], headers: List[str]) -> str:
        """Create HTML table."""
        if not data:
            return ""
        
        html = ["<table>"]
        
        # Header
        html.append("  <thead>")
        html.append("    <tr>")
        for header in headers:
            html.append(f"      <th>{header}</th>")
        html.append("    </tr>")
        html.append("  </thead>")
        
        # Body
        html.append("  <tbody>")
        for row in data:
            html.append("    <tr>")
            for header in headers:
                value = row.get(header, "")
                html.append(f"      <td>{value}</td>")
            html.append("    </tr>")
        html.append("  </tbody>")
        
        html.append("</table>")
        
        return "\n".join(html)
    
    def _create_plain_table(self, data: List[Dict[str, Any]], headers: List[str]) -> str:
        """Create plain text table."""
        if not data:
            return ""
        
        # Calculate column widths
        col_widths = {}
        for header in headers:
            col_widths[header] = len(str(header))
        
        for row in data:
            for header in headers:
                value = str(row.get(header, ""))
                col_widths[header] = max(col_widths[header], len(value))
        
        # Create table
        lines = []
        
        # Header
        header_line = "  ".join(str(h).ljust(col_widths[h]) for h in headers)
        lines.append(header_line)
        lines.append("-" * len(header_line))
        
        # Data rows
        for row in data:
            row_values = [str(row.get(header, "")).ljust(col_widths[header]) for header in headers]
            lines.append("  ".join(row_values))
        
        return "\n".join(lines)
    
    def _create_bullet_list(self, items: List[Any], nested: bool) -> str:
        """Create bullet list."""
        lines = []
        for item in items:
            if isinstance(item, (list, tuple)) and nested:
                lines.append(f"- {item[0]}")
                if len(item) > 1:
                    sub_lines = self._create_bullet_list(item[1:], nested)
                    for sub_line in sub_lines.split('\n'):
                        if sub_line.strip():
                            lines.append(f"  {sub_line}")
            else:
                lines.append(f"- {item}")
        return "\n".join(lines)
    
    def _create_numbered_list(self, items: List[Any], nested: bool) -> str:
        """Create numbered list."""
        lines = []
        for i, item in enumerate(items, 1):
            if isinstance(item, (list, tuple)) and nested:
                lines.append(f"{i}. {item[0]}")
                if len(item) > 1:
                    sub_lines = self._create_numbered_list(item[1:], nested)
                    for sub_line in sub_lines.split('\n'):
                        if sub_line.strip():
                            lines.append(f"   {sub_line}")
            else:
                lines.append(f"{i}. {item}")
        return "\n".join(lines)
    
    def _create_checklist(self, items: List[Any], nested: bool) -> str:
        """Create checklist."""
        lines = []
        for item in items:
            if isinstance(item, (list, tuple)) and nested:
                lines.append(f"- [ ] {item[0]}")
                if len(item) > 1:
                    sub_lines = self._create_checklist(item[1:], nested)
                    for sub_line in sub_lines.split('\n'):
                        if sub_line.strip():
                            lines.append(f"  {sub_line}")
            else:
                lines.append(f"- [ ] {item}")
        return "\n".join(lines)
    
    def _wrap_paragraph(self, text: str, width: int) -> str:
        """Wrap a single paragraph."""
        words = text.split()
        lines = []
        current_line = []
        current_length = 0
        
        for word in words:
            if current_length + len(word) + len(current_line) > width:
                if current_line:
                    lines.append(' '.join(current_line))
                    current_line = [word]
                    current_length = len(word)
                else:
                    lines.append(word)  # Word is longer than width
                    current_length = 0
            else:
                current_line.append(word)
                current_length += len(word)
        
        if current_line:
            lines.append(' '.join(current_line))
        
        return '\n'.join(lines)