"""
Document validators for M005 Quality Engine.

Provides validation rules and checks for document quality.
"""

import re
import json
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path

from .models import ValidationRule, QualityDimension, SeverityLevel
from .exceptions import ValidationError

logger = logging.getLogger(__name__)


class DocumentValidator:
    """Base validator for document quality checks."""
    
    def __init__(self, rules: Optional[List[ValidationRule]] = None):
        """Initialize validator with rules."""
        self.rules = rules or self._get_default_rules()
        self.enabled_rules = [r for r in self.rules if r.enabled]
    
    def validate(self, content: str, document_type: str = "markdown") -> List[Dict]:
        """
        Validate document content against rules.
        
        Args:
            content: Document content to validate
            document_type: Type of document (markdown, rst, etc.)
            
        Returns:
            List of validation results
        """
        results = []
        
        for rule in self.enabled_rules:
            try:
                result = self._apply_rule(rule, content, document_type)
                if result:
                    results.append(result)
            except Exception as e:
                logger.warning(f"Failed to apply rule {rule.name}: {e}")
        
        return results
    
    def _apply_rule(
        self, 
        rule: ValidationRule, 
        content: str, 
        document_type: str
    ) -> Optional[Dict]:
        """Apply a single validation rule."""
        validator_method = getattr(self, f"_validate_{rule.name}", None)
        if validator_method:
            return validator_method(content, rule.parameters, document_type)
        return None
    
    def _get_default_rules(self) -> List[ValidationRule]:
        """Get default validation rules."""
        return [
            ValidationRule(
                name="required_sections",
                description="Check for required document sections",
                dimension=QualityDimension.COMPLETENESS,
                severity=SeverityLevel.HIGH,
                parameters={"sections": ["description", "usage"]}
            ),
            ValidationRule(
                name="minimum_length",
                description="Check minimum document length",
                dimension=QualityDimension.COMPLETENESS,
                severity=SeverityLevel.MEDIUM,
                parameters={"min_words": 100}
            ),
            ValidationRule(
                name="heading_structure",
                description="Validate heading hierarchy",
                dimension=QualityDimension.STRUCTURE,
                severity=SeverityLevel.MEDIUM
            ),
            ValidationRule(
                name="code_block_syntax",
                description="Check code block syntax",
                dimension=QualityDimension.ACCURACY,
                severity=SeverityLevel.HIGH
            ),
            ValidationRule(
                name="link_format",
                description="Validate link formatting",
                dimension=QualityDimension.FORMATTING,
                severity=SeverityLevel.LOW
            ),
        ]
    
    def _validate_required_sections(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate required sections are present."""
        required = params.get("sections", [])
        headings = re.findall(r'^#+\s+(.+)$', content, re.MULTILINE)
        headings_lower = [h.lower().strip() for h in headings]
        
        missing = []
        for section in required:
            if section.lower() not in headings_lower:
                missing.append(section)
        
        if missing:
            return {
                "rule": "required_sections",
                "passed": False,
                "errors": [f"Missing section: {s}" for s in missing],
                "severity": SeverityLevel.HIGH.value
            }
        
        return {"rule": "required_sections", "passed": True}
    
    def _validate_minimum_length(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate minimum document length."""
        min_words = params.get("min_words", 100)
        word_count = len(content.split())
        
        if word_count < min_words:
            return {
                "rule": "minimum_length",
                "passed": False,
                "errors": [f"Document has {word_count} words, minimum is {min_words}"],
                "severity": SeverityLevel.MEDIUM.value
            }
        
        return {"rule": "minimum_length", "passed": True}
    
    def _validate_heading_structure(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate heading hierarchy."""
        errors = []
        headings = []
        
        for match in re.finditer(r'^(#+)\s+(.+)$', content, re.MULTILINE):
            level = len(match.group(1))
            title = match.group(2).strip()
            headings.append((level, title))
        
        if not headings:
            return {
                "rule": "heading_structure",
                "passed": False,
                "errors": ["No headings found"],
                "severity": SeverityLevel.MEDIUM.value
            }
        
        # Check for skipped levels
        prev_level = 0
        for level, title in headings:
            if prev_level > 0 and level > prev_level + 1:
                errors.append(f"Skipped heading level at '{title}'")
            prev_level = level
        
        # Check for multiple H1s
        h1_count = sum(1 for level, _ in headings if level == 1)
        if h1_count > 1:
            errors.append(f"Multiple H1 headings ({h1_count} found)")
        elif h1_count == 0:
            errors.append("No H1 heading found")
        
        if errors:
            return {
                "rule": "heading_structure",
                "passed": False,
                "errors": errors,
                "severity": SeverityLevel.MEDIUM.value
            }
        
        return {"rule": "heading_structure", "passed": True}
    
    def _validate_code_block_syntax(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate code block syntax."""
        errors = []
        code_blocks = re.findall(r'```(\w*)\n(.*?)\n```', content, re.DOTALL)
        
        for i, (lang, code) in enumerate(code_blocks, 1):
            if not lang:
                errors.append(f"Code block {i} missing language identifier")
            
            # Basic syntax checks
            if lang.lower() in ['python', 'py']:
                syntax_errors = self._check_python_syntax(code)
                errors.extend([f"Block {i}: {e}" for e in syntax_errors])
        
        if errors:
            return {
                "rule": "code_block_syntax",
                "passed": False,
                "errors": errors,
                "severity": SeverityLevel.HIGH.value
            }
        
        return {"rule": "code_block_syntax", "passed": True}
    
    def _validate_link_format(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate link formatting."""
        errors = []
        
        # Check for bare URLs
        bare_urls = re.findall(r'(?<!\[)https?://[^\s\)]+', content)
        if bare_urls:
            errors.append(f"Found {len(bare_urls)} bare URLs without markdown formatting")
        
        # Check for empty link text
        empty_links = re.findall(r'\[\s*\]\([^\)]+\)', content)
        if empty_links:
            errors.append(f"Found {len(empty_links)} links with empty text")
        
        if errors:
            return {
                "rule": "link_format",
                "passed": False,
                "errors": errors,
                "severity": SeverityLevel.LOW.value
            }
        
        return {"rule": "link_format", "passed": True}
    
    def _check_python_syntax(self, code: str) -> List[str]:
        """Basic Python syntax validation."""
        errors = []
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            if not stripped or stripped.startswith('#'):
                continue
            
            # Check for missing colons
            for keyword in ['if ', 'elif ', 'else', 'for ', 'while ', 'def ', 'class ', 'try', 'except', 'finally']:
                if stripped.startswith(keyword) and not line.rstrip().endswith(':'):
                    errors.append(f"Line {i}: Missing colon after {keyword.strip()}")
            
            # Check for unbalanced parentheses/brackets
            if line.count('(') != line.count(')'):
                errors.append(f"Line {i}: Unbalanced parentheses")
            if line.count('[') != line.count(']'):
                errors.append(f"Line {i}: Unbalanced brackets")
            if line.count('{') != line.count('}'):
                errors.append(f"Line {i}: Unbalanced braces")
        
        return errors


class MarkdownValidator(DocumentValidator):
    """Validator specifically for Markdown documents."""
    
    def _get_default_rules(self) -> List[ValidationRule]:
        """Get Markdown-specific validation rules."""
        rules = super()._get_default_rules()
        rules.extend([
            ValidationRule(
                name="markdown_tables",
                description="Validate markdown table formatting",
                dimension=QualityDimension.FORMATTING,
                severity=SeverityLevel.LOW
            ),
            ValidationRule(
                name="markdown_lists",
                description="Validate markdown list formatting",
                dimension=QualityDimension.FORMATTING,
                severity=SeverityLevel.LOW
            ),
            ValidationRule(
                name="front_matter",
                description="Check for valid front matter",
                dimension=QualityDimension.STRUCTURE,
                severity=SeverityLevel.INFO
            ),
        ])
        return rules
    
    def _validate_markdown_tables(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate markdown table formatting."""
        errors = []
        table_lines = [line for line in content.split('\n') if '|' in line]
        
        if table_lines:
            # Check for header separator
            for i, line in enumerate(table_lines):
                if re.match(r'^\|?\s*:?-+:?\s*\|', line):
                    # This is a separator line
                    if i == 0:
                        errors.append("Table separator appears before header")
                    elif i > 0 and '|' not in table_lines[i-1]:
                        errors.append("Table separator without header")
        
        if errors:
            return {
                "rule": "markdown_tables",
                "passed": False,
                "errors": errors,
                "severity": SeverityLevel.LOW.value
            }
        
        return {"rule": "markdown_tables", "passed": True}
    
    def _validate_markdown_lists(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate markdown list formatting."""
        errors = []
        lines = content.split('\n')
        
        # Check for mixed list styles
        bullet_styles = set()
        for line in lines:
            if re.match(r'^\s*[-*+]\s', line):
                bullet_styles.add(line.lstrip()[0])
        
        if len(bullet_styles) > 1:
            errors.append(f"Mixed bullet styles: {', '.join(bullet_styles)}")
        
        # Check for broken numbered lists
        prev_num = 0
        for line in lines:
            match = re.match(r'^\s*(\d+)\.\s', line)
            if match:
                num = int(match.group(1))
                if prev_num > 0 and num != prev_num + 1 and num != 1:
                    errors.append(f"Broken numbered list sequence: {prev_num} -> {num}")
                prev_num = num
            else:
                prev_num = 0
        
        if errors:
            return {
                "rule": "markdown_lists",
                "passed": False,
                "errors": errors,
                "severity": SeverityLevel.LOW.value
            }
        
        return {"rule": "markdown_lists", "passed": True}
    
    def _validate_front_matter(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate YAML front matter if present."""
        if not content.startswith('---'):
            return {"rule": "front_matter", "passed": True}
        
        errors = []
        lines = content.split('\n')
        
        # Find front matter boundaries
        end_index = -1
        for i, line in enumerate(lines[1:], 1):
            if line.strip() == '---':
                end_index = i
                break
        
        if end_index == -1:
            errors.append("Unclosed front matter section")
        else:
            # Basic YAML validation
            front_matter = '\n'.join(lines[1:end_index])
            try:
                # Simple check for YAML structure
                for line in front_matter.split('\n'):
                    if line.strip() and not re.match(r'^[a-zA-Z_][\w]*:\s*', line):
                        if not line.startswith((' ', '\t', '-')):
                            errors.append(f"Invalid YAML syntax: {line[:30]}")
            except Exception as e:
                errors.append(f"Front matter parsing error: {str(e)}")
        
        if errors:
            return {
                "rule": "front_matter",
                "passed": False,
                "errors": errors,
                "severity": SeverityLevel.INFO.value
            }
        
        return {"rule": "front_matter", "passed": True}


class CodeDocumentValidator(DocumentValidator):
    """Validator for code documentation (docstrings, comments)."""
    
    def _get_default_rules(self) -> List[ValidationRule]:
        """Get code documentation validation rules."""
        return [
            ValidationRule(
                name="docstring_presence",
                description="Check for docstrings in code",
                dimension=QualityDimension.COMPLETENESS,
                severity=SeverityLevel.MEDIUM,
                parameters={"min_coverage": 0.8}
            ),
            ValidationRule(
                name="comment_quality",
                description="Check comment quality and coverage",
                dimension=QualityDimension.CLARITY,
                severity=SeverityLevel.LOW,
                parameters={"min_ratio": 0.1}
            ),
        ]
    
    def _validate_docstring_presence(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate docstring presence in code."""
        min_coverage = params.get("min_coverage", 0.8)
        
        # Count functions/classes and docstrings
        function_count = len(re.findall(r'^\s*def\s+\w+', content, re.MULTILINE))
        class_count = len(re.findall(r'^\s*class\s+\w+', content, re.MULTILINE))
        docstring_count = len(re.findall(r'""".*?"""', content, re.DOTALL))
        
        total_items = function_count + class_count
        if total_items == 0:
            return {"rule": "docstring_presence", "passed": True}
        
        coverage = docstring_count / total_items
        
        if coverage < min_coverage:
            return {
                "rule": "docstring_presence",
                "passed": False,
                "errors": [f"Docstring coverage {coverage:.1%} below minimum {min_coverage:.1%}"],
                "severity": SeverityLevel.MEDIUM.value
            }
        
        return {"rule": "docstring_presence", "passed": True}
    
    def _validate_comment_quality(
        self, 
        content: str, 
        params: Dict, 
        doc_type: str
    ) -> Optional[Dict]:
        """Validate comment quality and coverage."""
        min_ratio = params.get("min_ratio", 0.1)
        
        lines = content.split('\n')
        code_lines = [l for l in lines if l.strip() and not l.strip().startswith('#')]
        comment_lines = [l for l in lines if l.strip().startswith('#')]
        
        if not code_lines:
            return {"rule": "comment_quality", "passed": True}
        
        comment_ratio = len(comment_lines) / len(code_lines)
        
        if comment_ratio < min_ratio:
            return {
                "rule": "comment_quality",
                "passed": False,
                "errors": [f"Comment ratio {comment_ratio:.1%} below minimum {min_ratio:.1%}"],
                "severity": SeverityLevel.LOW.value
            }
        
        return {"rule": "comment_quality", "passed": True}