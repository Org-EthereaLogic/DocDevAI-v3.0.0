"""
M004 Document Generator - AI-Powered Documentation Generation
DevDocAI v3.0.0 - Pass 1: Core Implementation

This module provides AI-powered document generation using LLM integration.
Templates guide AI prompts, not content substitution.
"""

import os
import json
import yaml
import asyncio
import logging
import hashlib
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor
import re
import ast

# Local imports
from ..core.config import ConfigurationManager
from ..core.storage import StorageManager, Document, DocumentMetadata
from ..intelligence.llm_adapter import LLMAdapter, LLMResponse

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================

class DocumentGenerationError(Exception):
    """Base exception for document generation errors."""
    pass


class TemplateNotFoundError(DocumentGenerationError):
    """Raised when a template cannot be found."""
    pass


class ContextExtractionError(DocumentGenerationError):
    """Raised when context extraction fails."""
    pass


class QualityValidationError(DocumentGenerationError):
    """Raised when document quality validation fails."""
    pass


class PromptConstructionError(DocumentGenerationError):
    """Raised when prompt construction fails."""
    pass


# ============================================================================
# Data Classes
# ============================================================================

@dataclass
class ValidationResult:
    """Result of document validation."""
    is_valid: bool
    score: float
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


@dataclass
class GenerationResult:
    """Result of document generation."""
    document_id: str
    type: str
    content: str
    quality_score: float
    metadata: Dict[str, Any] = field(default_factory=dict)
    generation_time: float = 0.0
    tokens_used: int = 0
    cost: float = 0.0


# ============================================================================
# TemplateManager Class
# ============================================================================

class TemplateManager:
    """Manages document templates for AI-guided generation."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize template manager."""
        self.config = config
        self.template_dir = Path(config.get('templates.dir', '/tmp/templates'))
        self._cache: Dict[str, Dict[str, Any]] = {}
        
        # Create template directory if it doesn't exist
        self.template_dir.mkdir(parents=True, exist_ok=True)
        
        # Load built-in templates if directory is empty
        if not list(self.template_dir.glob('*.yaml')) and not list(self.template_dir.glob('*.yml')):
            self._create_default_templates()
    
    def _create_default_templates(self):
        """Create default document templates."""
        default_templates = {
            'readme': {
                'document_type': 'readme',
                'name': 'README Documentation',
                'sections': [
                    {
                        'name': 'header',
                        'prompt_template': 'Generate a professional README header for {project_name}. Include appropriate badges for build status, test coverage, and license.',
                        'required': True
                    },
                    {
                        'name': 'description',
                        'prompt_template': 'Write a clear and compelling description for {project_name}. The project is: {project_description}. Highlight key features and benefits.',
                        'required': True
                    },
                    {
                        'name': 'installation',
                        'prompt_template': 'Create detailed installation instructions for {project_name}, a Python {python_version} project. Include pip installation, development setup, and any system requirements.',
                        'required': True
                    },
                    {
                        'name': 'usage',
                        'prompt_template': 'Write comprehensive usage examples for {project_name}. Include basic usage, advanced features, and common use cases with code examples.',
                        'required': True
                    },
                    {
                        'name': 'api',
                        'prompt_template': 'Generate API documentation for the main classes and functions in {project_name}. Focus on: {main_modules}',
                        'required': False
                    },
                    {
                        'name': 'contributing',
                        'prompt_template': 'Create contributing guidelines for {project_name}. Include development setup, coding standards, and pull request process.',
                        'required': False
                    }
                ],
                'context_requirements': [
                    'project_name',
                    'project_description',
                    'python_version'
                ],
                'quality_criteria': {
                    'min_length': 500,
                    'max_length': 10000,
                    'required_sections': ['header', 'description', 'installation', 'usage']
                }
            },
            'api_doc': {
                'document_type': 'api_doc',
                'name': 'API Documentation',
                'sections': [
                    {
                        'name': 'overview',
                        'prompt_template': 'Create an API overview for {project_name}. Describe the main modules, classes, and their purposes.',
                        'required': True
                    },
                    {
                        'name': 'classes',
                        'prompt_template': 'Document all classes in {project_name}. For each class, include description, methods, attributes, and usage examples. Classes found: {classes}',
                        'required': True
                    },
                    {
                        'name': 'functions',
                        'prompt_template': 'Document all functions in {project_name}. Include parameters, return values, exceptions, and examples. Functions found: {functions}',
                        'required': True
                    }
                ],
                'context_requirements': [
                    'project_name',
                    'classes',
                    'functions'
                ],
                'quality_criteria': {
                    'min_length': 1000,
                    'required_sections': ['overview', 'classes', 'functions']
                }
            },
            'changelog': {
                'document_type': 'changelog',
                'name': 'Changelog',
                'sections': [
                    {
                        'name': 'header',
                        'prompt_template': 'Create a changelog header for {project_name} following Keep a Changelog format.',
                        'required': True
                    },
                    {
                        'name': 'version',
                        'prompt_template': 'Document version {version} changes. Include Added, Changed, Fixed, and Removed sections based on: {recent_changes}',
                        'required': True
                    }
                ],
                'context_requirements': [
                    'project_name',
                    'version'
                ],
                'quality_criteria': {
                    'min_length': 200,
                    'required_sections': ['header', 'version']
                }
            }
        }
        
        # Save default templates
        for template_name, template_data in default_templates.items():
            template_file = self.template_dir / f"{template_name}.yaml"
            with open(template_file, 'w') as f:
                yaml.dump(template_data, f, default_flow_style=False)
        
        logger.info(f"Created {len(default_templates)} default templates in {self.template_dir}")
    
    def load_template(self, template_name: str) -> Dict[str, Any]:
        """Load a template by name."""
        # Check cache first
        if template_name in self._cache:
            return self._cache[template_name]
        
        # Try loading from file
        template_file = None
        for ext in ['.yaml', '.yml']:
            candidate = self.template_dir / f"{template_name}{ext}"
            if candidate.exists():
                template_file = candidate
                break
        
        if not template_file:
            available = self.list_templates()
            raise TemplateNotFoundError(
                f"Template not found: {template_name}. "
                f"Available templates: {', '.join(available)}"
            )
        
        # Load and validate template
        with open(template_file, 'r') as f:
            template = yaml.safe_load(f)
        
        self.validate_template(template)
        
        # Cache for future use
        self._cache[template_name] = template
        
        return template
    
    def validate_template(self, template: Dict[str, Any]) -> bool:
        """Validate template structure."""
        required_fields = ['document_type', 'sections']
        
        for field in required_fields:
            if field not in template:
                raise ValueError(f"Missing required field: {field}")
        
        if not isinstance(template['sections'], list):
            raise ValueError("'sections' must be a list")
        
        for section in template['sections']:
            if 'name' not in section:
                raise ValueError("Each section must have a 'name' field")
            if 'prompt_template' not in section:
                raise ValueError(f"Section '{section['name']}' missing 'prompt_template'")
        
        return True
    
    def list_templates(self) -> List[str]:
        """List available templates."""
        templates = []
        
        for file in self.template_dir.glob('*.yaml'):
            templates.append(file.stem)
        for file in self.template_dir.glob('*.yml'):
            templates.append(file.stem)
        
        return sorted(set(templates))


# ============================================================================
# ContextBuilder Class
# ============================================================================

class ContextBuilder:
    """Extracts context from project for document generation."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize context builder."""
        self.config = config
        self._extractors = {
            'python': self._extract_python_context,
            'package': self._extract_package_context,
            'git': self._extract_git_context,
            'files': self._extract_file_context
        }
    
    def extract_from_project(self, project_path: str) -> Dict[str, Any]:
        """Extract comprehensive context from project."""
        project_dir = Path(project_path)
        
        if not project_dir.exists():
            raise ContextExtractionError(f"Project path does not exist: {project_path}")
        
        context = {
            'project_path': str(project_dir.absolute()),
            'project_name': project_dir.name,
            'extracted_at': datetime.now().isoformat()
        }
        
        # Run all extractors
        for name, extractor in self._extractors.items():
            try:
                extractor_context = extractor(project_dir)
                context.update(extractor_context)
            except Exception as e:
                logger.warning(f"Extractor '{name}' failed: {e}")
        
        return context
    
    def _extract_python_context(self, project_dir: Path) -> Dict[str, Any]:
        """Extract Python-specific context."""
        context = {
            'modules': [],
            'classes': [],
            'functions': [],
            'main_modules': []
        }
        
        # Find Python files
        py_files = list(project_dir.rglob('*.py'))
        
        for py_file in py_files[:20]:  # Limit to prevent too much processing
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Basic AST parsing for structure
                tree = ast.parse(content)
                
                module_name = py_file.stem
                context['modules'].append(module_name)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.ClassDef):
                        context['classes'].append(node.name)
                    elif isinstance(node, ast.FunctionDef):
                        if not node.name.startswith('_'):
                            context['functions'].append(node.name)
                
                # Check if it's a main module
                if py_file.name in ['__init__.py', 'main.py', f'{project_dir.name}.py']:
                    context['main_modules'].append(module_name)
                    
            except Exception as e:
                logger.debug(f"Failed to parse {py_file}: {e}")
        
        # Remove duplicates
        context['classes'] = list(set(context['classes']))[:20]
        context['functions'] = list(set(context['functions']))[:30]
        
        return context
    
    def _extract_package_context(self, project_dir: Path) -> Dict[str, Any]:
        """Extract package/project metadata."""
        context = {}
        
        # Check for pyproject.toml
        pyproject_file = project_dir / 'pyproject.toml'
        if pyproject_file.exists():
            try:
                import tomli
                with open(pyproject_file, 'rb') as f:
                    pyproject = tomli.load(f)
                
                project = pyproject.get('project', {})
                context['project_name'] = project.get('name', project_dir.name)
                context['project_description'] = project.get('description', '')
                context['version'] = project.get('version', '0.1.0')
                context['python_version'] = project.get('requires-python', '>=3.8')
                context['dependencies'] = project.get('dependencies', [])
                
            except Exception as e:
                logger.debug(f"Failed to parse pyproject.toml: {e}")
        
        # Check for setup.py
        setup_file = project_dir / 'setup.py'
        if setup_file.exists() and 'project_name' not in context:
            try:
                with open(setup_file, 'r') as f:
                    content = f.read()
                
                # Basic regex extraction (not executing setup.py)
                name_match = re.search(r"name\s*=\s*['\"]([^'\"]+)['\"]", content)
                if name_match:
                    context['project_name'] = name_match.group(1)
                
                desc_match = re.search(r"description\s*=\s*['\"]([^'\"]+)['\"]", content)
                if desc_match:
                    context['project_description'] = desc_match.group(1)
                    
            except Exception as e:
                logger.debug(f"Failed to parse setup.py: {e}")
        
        # Check for requirements.txt
        requirements_file = project_dir / 'requirements.txt'
        if requirements_file.exists() and 'dependencies' not in context:
            try:
                with open(requirements_file, 'r') as f:
                    deps = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                    context['dependencies'] = deps[:20]  # Limit number
            except Exception as e:
                logger.debug(f"Failed to parse requirements.txt: {e}")
        
        # Check for README
        for readme_name in ['README.md', 'README.rst', 'README.txt', 'README']:
            readme_file = project_dir / readme_name
            if readme_file.exists():
                try:
                    with open(readme_file, 'r', encoding='utf-8') as f:
                        content = f.read(1000)  # First 1000 chars
                        context['readme_content'] = content
                        
                        # Extract description if not found
                        if 'project_description' not in context:
                            lines = content.split('\n')
                            for line in lines[1:5]:  # Check first few lines after title
                                if line.strip() and not line.startswith('#'):
                                    context['project_description'] = line.strip()
                                    break
                except Exception as e:
                    logger.debug(f"Failed to read README: {e}")
                break
        
        return context
    
    def _extract_git_context(self, project_dir: Path) -> Dict[str, Any]:
        """Extract git repository context."""
        context = {}
        
        git_dir = project_dir / '.git'
        if not git_dir.exists():
            return context
        
        try:
            # Get recent commits (simplified, no git command execution)
            context['has_git'] = True
            
            # Check for .gitignore
            gitignore = project_dir / '.gitignore'
            if gitignore.exists():
                context['has_gitignore'] = True
        except Exception as e:
            logger.debug(f"Failed to extract git context: {e}")
        
        return context
    
    def _extract_file_context(self, project_dir: Path) -> Dict[str, Any]:
        """Extract general file structure context."""
        context = {
            'file_count': 0,
            'total_size': 0,
            'file_types': {}
        }
        
        try:
            for file in project_dir.rglob('*'):
                if file.is_file():
                    context['file_count'] += 1
                    context['total_size'] += file.stat().st_size
                    
                    ext = file.suffix.lower()
                    if ext:
                        context['file_types'][ext] = context['file_types'].get(ext, 0) + 1
            
            # Sort file types by count
            context['file_types'] = dict(
                sorted(context['file_types'].items(), key=lambda x: x[1], reverse=True)[:10]
            )
            
        except Exception as e:
            logger.debug(f"Failed to extract file context: {e}")
        
        return context
    
    def merge_contexts(self, *contexts: Dict[str, Any]) -> Dict[str, Any]:
        """Merge multiple contexts, later ones override earlier ones."""
        merged = {}
        
        for context in contexts:
            merged.update(context)
        
        return merged


# ============================================================================
# PromptEngine Class
# ============================================================================

class PromptEngine:
    """Constructs prompts for LLM from templates and context."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize prompt engine."""
        self.config = config
        self.max_prompt_length = config.get('ai.max_prompt_length', 8000)
        self.model = config.get('ai.model', 'gpt-4')
    
    def construct_prompt(self, template: str, context: Dict[str, Any]) -> str:
        """Construct a prompt from template and context."""
        # Format template with context
        prompt = self.format_template(template, context)
        
        # Optimize length if needed
        if len(prompt) > self.max_prompt_length:
            prompt = self.optimize_prompt(prompt)
        
        return prompt
    
    def construct_system_prompt(self, document_type: str) -> str:
        """Construct system prompt for specific document type."""
        system_prompts = {
            'readme': (
                "You are a technical documentation expert specializing in creating "
                "comprehensive, clear, and professional README files. Focus on clarity, "
                "completeness, and following best practices. Use Markdown formatting."
            ),
            'api_doc': (
                "You are an API documentation specialist. Create detailed, accurate, "
                "and developer-friendly API documentation. Include clear descriptions, "
                "parameter details, return values, and practical examples."
            ),
            'changelog': (
                "You are a changelog writer following the Keep a Changelog format. "
                "Organize changes into Added, Changed, Deprecated, Removed, Fixed, "
                "and Security categories. Be concise but informative."
            ),
            'default': (
                "You are a professional technical writer creating high-quality "
                "documentation. Focus on clarity, accuracy, and completeness."
            )
        }
        
        return system_prompts.get(document_type, system_prompts['default'])
    
    def format_template(self, template: str, context: Dict[str, Any], use_defaults: bool = True) -> str:
        """Format template with context values."""
        # Create a copy to avoid modifying original
        formatted = template
        
        # Find all placeholders
        placeholders = re.findall(r'\{(\w+)\}', template)
        
        for placeholder in placeholders:
            if placeholder in context:
                value = context[placeholder]
                
                # Handle different value types
                if isinstance(value, list):
                    value = ', '.join(str(v) for v in value[:10])  # Limit list size
                elif isinstance(value, dict):
                    value = json.dumps(value, indent=2)[:500]  # Limit dict size
                else:
                    value = str(value)
                
                formatted = formatted.replace(f'{{{placeholder}}}', value)
                
            elif use_defaults:
                # Use sensible defaults for missing values
                defaults = {
                    'project_name': 'MyProject',
                    'project_description': 'A Python project',
                    'version': '0.1.0',
                    'author': 'Developer',
                    'python_version': '3.8+',
                    'license': 'MIT'
                }
                
                if placeholder in defaults:
                    formatted = formatted.replace(f'{{{placeholder}}}', defaults[placeholder])
                else:
                    # Remove unfilled placeholders
                    formatted = formatted.replace(f'{{{placeholder}}}', f'[{placeholder}]')
        
        return formatted
    
    def optimize_prompt(self, prompt: str) -> str:
        """Optimize prompt length while preserving information."""
        if len(prompt) <= self.max_prompt_length:
            return prompt
        
        # Truncate with ellipsis
        truncated = prompt[:self.max_prompt_length - 100]
        
        # Try to end at a sentence boundary
        last_period = truncated.rfind('.')
        if last_period > self.max_prompt_length - 500:
            truncated = truncated[:last_period + 1]
        
        truncated += "\n\n[Content truncated for length...]"
        
        return truncated
    
    def add_examples(self, base_prompt: str, examples: List[str]) -> str:
        """Add examples to prompt for better generation."""
        if not examples:
            return base_prompt
        
        prompt_with_examples = base_prompt + "\n\nExamples:\n"
        
        for i, example in enumerate(examples[:3], 1):  # Limit to 3 examples
            prompt_with_examples += f"\nExample {i}:\n{example}\n"
        
        return prompt_with_examples
    
    def create_section_prompt(self, section: Dict[str, Any], context: Dict[str, Any], 
                            previous_sections: Optional[str] = None) -> str:
        """Create prompt for a specific section."""
        prompt_template = section.get('prompt_template', '')
        
        # Add context about previous sections if available
        if previous_sections:
            prompt = f"Previous sections of the document:\n\n{previous_sections}\n\n"
            prompt += "Now generate the next section:\n\n"
        else:
            prompt = ""
        
        # Add the section-specific prompt
        prompt += self.construct_prompt(prompt_template, context)
        
        # Add any section-specific examples
        if 'examples' in section:
            prompt = self.add_examples(prompt, section['examples'])
        
        return prompt


# ============================================================================
# DocumentValidator Class
# ============================================================================

class DocumentValidator:
    """Validates generated documents against quality criteria."""
    
    def __init__(self, config: ConfigurationManager):
        """Initialize document validator."""
        self.config = config
        self.min_quality_score = config.get('quality.min_score', 85)
        self.grammar_check_enabled = config.get('quality.check_grammar', True)
        self.check_completeness = config.get('quality.check_completeness', True)
    
    def validate(self, document: str, template: Dict[str, Any]) -> ValidationResult:
        """Validate document against template criteria."""
        errors = []
        warnings = []
        suggestions = []
        
        # Get quality criteria from template
        criteria = template.get('quality_criteria', {})
        
        # Check length requirements
        doc_length = len(document)
        min_length = criteria.get('min_length', 100)
        max_length = criteria.get('max_length', 100000)
        
        if doc_length < min_length:
            errors.append(f"Document too short: {doc_length} chars (minimum: {min_length})")
        elif doc_length > max_length:
            warnings.append(f"Document too long: {doc_length} chars (maximum: {max_length})")
        
        # Check required sections
        required_sections = criteria.get('required_sections', [])
        for section_name in required_sections:
            # Simple check - look for section headers
            if section_name.lower() not in document.lower():
                errors.append(f"Missing required section: {section_name}")
        
        # Calculate quality score
        score = self.calculate_score(document)
        
        # Check grammar if enabled
        if self.grammar_check_enabled:
            grammar_ok = self.check_grammar_simple(document)
            if not grammar_ok:
                warnings.append("Grammar issues detected")
                score *= 0.9  # Reduce score for grammar issues
        
        # Determine validity
        is_valid = len(errors) == 0 and score >= self.min_quality_score
        
        # Add suggestions
        if score < 90:
            suggestions.append("Consider adding more detailed content")
        if len(warnings) > 0:
            suggestions.append("Review and address warnings for better quality")
        
        return ValidationResult(
            is_valid=is_valid,
            score=score,
            errors=errors,
            warnings=warnings,
            suggestions=suggestions
        )
    
    def calculate_score(self, document: str) -> float:
        """Calculate quality score for document."""
        score = 100.0
        
        # Length score
        doc_length = len(document)
        if doc_length < 200:
            score -= 20
        elif doc_length < 500:
            score -= 10
        
        # Structure score - check for headers
        header_count = document.count('#')
        if header_count < 2:
            score -= 15
        elif header_count < 4:
            score -= 5
        
        # Content quality indicators
        # Check for code blocks
        if '```' in document:
            score += 5  # Bonus for including code examples
        
        # Check for lists
        if '- ' in document or '* ' in document or '1. ' in document:
            score += 3  # Bonus for structured content
        
        # Check for links
        if '[' in document and '](' in document:
            score += 2  # Bonus for references
        
        # Ensure score stays in valid range
        score = max(0, min(100, score))
        
        return score
    
    def check_grammar(self, text: str) -> bool:
        """Perform grammar check (placeholder for advanced implementation)."""
        return self.check_grammar_simple(text)
    
    def check_grammar_simple(self, text: str) -> bool:
        """Simple grammar check based on basic rules."""
        # Very basic checks - in production, use language tool
        issues = 0
        
        # Check for double spaces
        if '  ' in text:
            issues += 1
        
        # Check for missing capitalization after periods
        sentences = text.split('. ')
        for sentence in sentences[:-1]:
            next_idx = sentences.index(sentence) + 1
            if next_idx < len(sentences) and sentences[next_idx]:
                if sentences[next_idx][0].islower():
                    issues += 1
        
        # Return True if minimal issues
        return issues < 3
    
    def validate_sections(self, document: str, required_sections: List[str]) -> List[str]:
        """Validate that all required sections are present."""
        missing_sections = []
        
        for section in required_sections:
            # Look for section as a header (case-insensitive)
            section_pattern = rf'#+\s*{re.escape(section)}'
            if not re.search(section_pattern, document, re.IGNORECASE):
                missing_sections.append(section)
        
        return missing_sections


# ============================================================================
# Main DocumentGenerator Class
# ============================================================================

class DocumentGenerator:
    """Main orchestrator for AI-powered document generation."""
    
    def __init__(self, 
                 config: Optional[ConfigurationManager] = None,
                 llm_adapter: Optional[LLMAdapter] = None,
                 storage: Optional[StorageManager] = None):
        """Initialize document generator."""
        self.config = config or ConfigurationManager()
        self.llm_adapter = llm_adapter or LLMAdapter(self.config)
        self.storage = storage or StorageManager(self.config)
        
        # Initialize components
        self.template_manager = TemplateManager(self.config)
        self.context_builder = ContextBuilder(self.config)
        self.prompt_engine = PromptEngine(self.config)
        self.validator = DocumentValidator(self.config)
        
        # Thread pool for parallel section generation
        self.executor = ThreadPoolExecutor(max_workers=4)
        
        logger.info("DocumentGenerator initialized with AI-powered generation")
    
    async def generate(self,
                      document_type: str,
                      project_path: str,
                      custom_context: Optional[Dict[str, Any]] = None,
                      parallel_sections: bool = False,
                      retry_on_failure: bool = False,
                      max_retries: int = 3) -> Dict[str, Any]:
        """Generate a document using AI."""
        start_time = datetime.now()
        
        try:
            # Load template
            template = self.template_manager.load_template(document_type)
            
            # Extract context from project
            project_context = self.context_builder.extract_from_project(project_path)
            
            # Merge with custom context if provided
            if custom_context:
                context = self.context_builder.merge_contexts(project_context, custom_context)
            else:
                context = project_context
            
            # Generate document content
            if parallel_sections and len(template['sections']) > 1:
                content = await self._generate_parallel_sections(template, context)
            else:
                content = await self._generate_sequential_sections(template, context)
            
            # Validate generated document
            validation_result = self.validator.validate(content, template)
            
            # Retry if validation fails and retry is enabled
            retry_count = 0
            while not validation_result.is_valid and retry_on_failure and retry_count < max_retries:
                logger.info(f"Validation failed, retrying... (attempt {retry_count + 1}/{max_retries})")
                
                # Regenerate with adjusted parameters
                self.prompt_engine.model = 'gpt-4'  # Try with better model
                content = await self._generate_sequential_sections(template, context)
                validation_result = self.validator.validate(content, template)
                retry_count += 1
            
            # Check final validation
            if not validation_result.is_valid and not retry_on_failure:
                raise QualityValidationError(
                    f"Document failed quality standards. Score: {validation_result.score}, "
                    f"Errors: {', '.join(validation_result.errors)}"
                )
            
            # Generate document ID
            document_id = f"doc_{hashlib.md5(content.encode()).hexdigest()[:8]}"
            
            # Store document
            metadata = DocumentMetadata(
                author="AI Generator",
                tags=[document_type, "ai-generated"],
                version="1.0",
                custom={
                    'quality_score': validation_result.score,
                    'generation_time': (datetime.now() - start_time).total_seconds(),
                    'template': document_type,
                    'project': context.get('project_name', 'unknown')
                }
            )
            
            document = Document(
                id=document_id,  # Provide ID upfront
                type=document_type,
                content=content,
                metadata=metadata,
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            
            # Save document
            self.storage.save_document(document)
            
            # Prepare result
            result = {
                'document_id': document_id,
                'type': document_type,
                'content': content,
                'quality_score': validation_result.score,
                'metadata': metadata.to_dict(),
                'generation_time': (datetime.now() - start_time).total_seconds(),
                'validation': {
                    'is_valid': validation_result.is_valid,
                    'errors': validation_result.errors,
                    'warnings': validation_result.warnings,
                    'suggestions': validation_result.suggestions
                }
            }
            
            logger.info(f"Successfully generated {document_type} document with score {validation_result.score}")
            
            return result
            
        except Exception as e:
            logger.error(f"Document generation failed: {e}")
            raise DocumentGenerationError(f"Failed to generate document: {e}")
    
    async def _generate_sequential_sections(self, template: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate document sections sequentially."""
        sections_content = []
        system_prompt = self.prompt_engine.construct_system_prompt(template['document_type'])
        
        for section in template['sections']:
            # Build prompt for this section
            previous_content = '\n\n'.join(sections_content) if sections_content else None
            section_prompt = self.prompt_engine.create_section_prompt(
                section, context, previous_content
            )
            
            # Generate section content
            try:
                response = self.llm_adapter.generate(
                    prompt=section_prompt,
                    max_tokens=self.config.get('ai.max_tokens', 2000),
                    temperature=self.config.get('ai.temperature', 0.7)
                )
                
                section_content = response.content
                
                # Add section header if not present
                section_name = section['name'].replace('_', ' ').title()
                if not section_content.startswith('#'):
                    section_content = f"## {section_name}\n\n{section_content}"
                
                sections_content.append(section_content)
                
            except Exception as e:
                logger.error(f"Failed to generate section '{section['name']}': {e}")
                if section.get('required', True):
                    raise
                else:
                    # Skip optional section on failure
                    continue
        
        # Combine all sections
        document = '\n\n'.join(sections_content)
        
        return document
    
    async def _generate_parallel_sections(self, template: Dict[str, Any], context: Dict[str, Any]) -> str:
        """Generate document sections in parallel."""
        sections_content = {}
        tasks = []
        
        async def generate_section(section: Dict[str, Any], section_idx: int):
            """Generate a single section."""
            section_prompt = self.prompt_engine.create_section_prompt(section, context)
            
            try:
                # Run synchronous LLM call in thread pool
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    self.executor,
                    self.llm_adapter.generate,
                    section_prompt,
                    None,  # provider
                    self.config.get('ai.max_tokens', 2000),
                    self.config.get('ai.temperature', 0.7)
                )
                
                section_content = response.content
                
                # Add section header if not present
                section_name = section['name'].replace('_', ' ').title()
                if not section_content.startswith('#'):
                    section_content = f"## {section_name}\n\n{section_content}"
                
                sections_content[section_idx] = section_content
                
            except Exception as e:
                logger.error(f"Failed to generate section '{section['name']}': {e}")
                if section.get('required', True):
                    raise
                else:
                    sections_content[section_idx] = None
        
        # Create tasks for all sections
        for idx, section in enumerate(template['sections']):
            task = generate_section(section, idx)
            tasks.append(task)
        
        # Execute all tasks in parallel
        await asyncio.gather(*tasks)
        
        # Combine sections in order
        document_parts = []
        for idx in range(len(template['sections'])):
            if idx in sections_content and sections_content[idx]:
                document_parts.append(sections_content[idx])
        
        document = '\n\n'.join(document_parts)
        
        return document
    
    def list_templates(self) -> List[str]:
        """List available document templates."""
        return self.template_manager.list_templates()
    
    def get_template_info(self, template_name: str) -> Dict[str, Any]:
        """Get information about a specific template."""
        template = self.template_manager.load_template(template_name)
        
        return {
            'name': template.get('name', template_name),
            'type': template['document_type'],
            'sections': [s['name'] for s in template['sections']],
            'required_context': template.get('context_requirements', []),
            'quality_criteria': template.get('quality_criteria', {})
        }
    
    async def regenerate_section(self, 
                                 document_id: str,
                                 section_name: str,
                                 additional_context: Optional[Dict[str, Any]] = None) -> str:
        """Regenerate a specific section of an existing document."""
        # Retrieve existing document
        document = self.storage.get_document(document_id)
        
        if not document:
            raise DocumentGenerationError(f"Document not found: {document_id}")
        
        # Load template
        template = self.template_manager.load_template(document.type)
        
        # Find section in template
        section = None
        for s in template['sections']:
            if s['name'] == section_name:
                section = s
                break
        
        if not section:
            raise DocumentGenerationError(f"Section not found: {section_name}")
        
        # Extract context (combine stored metadata with additional context)
        context = document.metadata.custom.copy()
        if additional_context:
            context.update(additional_context)
        
        # Generate new section content
        section_prompt = self.prompt_engine.create_section_prompt(section, context)
        
        response = self.llm_adapter.generate(
            prompt=section_prompt,
            max_tokens=self.config.get('ai.max_tokens', 2000),
            temperature=self.config.get('ai.temperature', 0.7)
        )
        
        return response.content


# ============================================================================
# Convenience Functions
# ============================================================================

async def generate_document(document_type: str, 
                           project_path: str,
                           config: Optional[ConfigurationManager] = None,
                           **kwargs) -> Dict[str, Any]:
    """Convenience function to generate a document."""
    generator = DocumentGenerator(config=config)
    return await generator.generate(document_type, project_path, **kwargs)


def list_available_templates(config: Optional[ConfigurationManager] = None) -> List[str]:
    """List available document templates."""
    manager = TemplateManager(config or ConfigurationManager())
    return manager.list_templates()