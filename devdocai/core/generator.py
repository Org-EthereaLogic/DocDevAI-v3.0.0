"""
M004 Document Generator - Pass 1: Core Implementation

UnifiedDocumentGenerator with 4 operation modes for AI-powered document generation.
Integrates with M001 (Config), M002 (Storage), and M003 (MIAIR) for comprehensive
document creation with quality gate enforcement.

Design Specifications:
- 4 Operation Modes: BASIC, PERFORMANCE, SECURE, ENTERPRISE
- 5+ Document Types: README, API, PRD, SRS, SDD
- 4 Output Formats: Markdown, HTML, PDF, DOCX
- Performance Target: 10 docs/second baseline
- Quality Gate: 85% minimum score enforcement
"""

import asyncio
import hashlib
import json
import logging
import re
import time
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Dict, Any, List, Optional, Union, Set
from dataclasses import dataclass, field
import warnings

# Jinja2 for templating
from jinja2 import (
    Environment, FileSystemLoader, select_autoescape,
    Template, TemplateError, UndefinedError,
    StrictUndefined
)
from jinja2.sandbox import SandboxedEnvironment

# Format converters
import markdown
from markdown.extensions import codehilite, fenced_code, tables, toc

# PDF generation
try:
    from weasyprint import HTML as WeasyHTML
    HAS_WEASYPRINT = True
except ImportError:
    HAS_WEASYPRINT = False
    warnings.warn("WeasyPrint not installed. PDF generation will be limited.")

# DOCX generation
try:
    from python_docx import Document as DocxDocument
    from python_docx.shared import Inches, Pt
    from python_docx.enum.text import WD_ALIGN_PARAGRAPH
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False
    warnings.warn("python-docx not installed. DOCX generation will be limited.")

# HTML sanitization for security
try:
    import bleach
    HAS_BLEACH = True
except ImportError:
    HAS_BLEACH = False
    warnings.warn("Bleach not installed. HTML sanitization will be limited.")

# Import M001, M002, M003 integrations
from devdocai.core.config import ConfigurationManager, MemoryMode
from devdocai.storage.storage_manager_unified import (
    UnifiedStorageManager, OperationMode
)
from devdocai.miair.engine_unified_final import MIAIREngineUnified
from devdocai.miair.models import Document as MIAIRDocument, AnalysisResult


logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Supported document types."""
    README = "readme"
    API = "api"
    PRD = "prd"
    SRS = "srs"
    SDD = "sdd"
    CHANGELOG = "changelog"
    CONTRIBUTING = "contributing"
    LICENSE = "license"
    SECURITY = "security"
    CUSTOM = "custom"


class OutputFormat(Enum):
    """Supported output formats."""
    MARKDOWN = "markdown"
    HTML = "html"
    PDF = "pdf"
    DOCX = "docx"
    JSON = "json"
    RST = "rst"  # reStructuredText
    ASCIIDOC = "asciidoc"


class GenerationMode(Enum):
    """Generator operation modes aligned with M002/M003."""
    BASIC = "basic"
    PERFORMANCE = "performance"
    SECURE = "secure"
    ENTERPRISE = "enterprise"


class GeneratorError(Exception):
    """Document generation errors."""
    pass


@dataclass
class TemplateVariable:
    """Template variable definition."""
    name: str
    type: str = "string"
    required: bool = True
    default: Any = None
    description: str = ""
    validation: Optional[str] = None  # Regex pattern for validation


@dataclass
class DocumentMetadata:
    """Document metadata."""
    document_type: str
    format: str
    created_at: str
    version: str = "1.0.0"
    quality_score: float = 0.0
    template_id: str = ""
    generation_time_ms: float = 0.0
    word_count: int = 0
    character_count: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            'document_type': self.document_type,
            'format': self.format,
            'created_at': self.created_at,
            'version': self.version,
            'quality_score': self.quality_score,
            'template_id': self.template_id,
            'generation_time_ms': self.generation_time_ms,
            'word_count': self.word_count,
            'character_count': self.character_count
        }


@dataclass
class GenerationResult:
    """Document generation result."""
    success: bool
    document_id: Optional[str] = None
    content: Optional[Union[str, bytes]] = None
    format: Optional[OutputFormat] = None
    quality_score: float = 0.0
    metadata: Optional[Dict[str, Any]] = None
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    generation_time_ms: float = 0.0


class DocumentCache:
    """Simple LRU cache for performance mode."""
    
    def __init__(self, max_size: int = 100, ttl_seconds: int = 3600):
        """Initialize cache."""
        self.max_size = max_size
        self.ttl_seconds = ttl_seconds
        self._cache: Dict[str, Any] = {}
        self._timestamps: Dict[str, float] = {}
        self._access_order: List[str] = []
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache."""
        if key not in self._cache:
            return None
        
        # Check TTL
        if time.time() - self._timestamps[key] > self.ttl_seconds:
            self._remove(key)
            return None
        
        # Update access order
        self._access_order.remove(key)
        self._access_order.append(key)
        
        return self._cache[key]
    
    def set(self, key: str, value: Any) -> None:
        """Set item in cache."""
        # Evict if at capacity
        if key not in self._cache and len(self._cache) >= self.max_size:
            oldest = self._access_order.pop(0)
            self._remove(oldest)
        
        self._cache[key] = value
        self._timestamps[key] = time.time()
        
        if key in self._access_order:
            self._access_order.remove(key)
        self._access_order.append(key)
    
    def _remove(self, key: str) -> None:
        """Remove item from cache."""
        if key in self._cache:
            del self._cache[key]
            del self._timestamps[key]
            if key in self._access_order:
                self._access_order.remove(key)


class UnifiedDocumentGenerator:
    """
    Unified Document Generator with 4 operation modes.
    
    Integrates with M001 (Config), M002 (Storage), and M003 (MIAIR)
    to provide comprehensive document generation with quality enforcement.
    """
    
    # Security: Allowed HTML tags for sanitization
    ALLOWED_HTML_TAGS = [
        'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i',
        'li', 'ol', 'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'p', 'pre', 'span', 'div', 'table', 'thead', 'tbody', 'tr', 'th', 'td'
    ]
    
    ALLOWED_HTML_ATTRS = {
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title'],
    }
    
    def __init__(
        self,
        config_manager: ConfigurationManager,
        storage_manager: UnifiedStorageManager,
        miair_engine: MIAIREngineUnified
    ):
        """Initialize document generator with dependencies."""
        self.config_manager = config_manager
        self.storage_manager = storage_manager
        self.miair_engine = miair_engine
        
        # Determine operation mode from config
        operation_mode_str = config_manager.get('operation_mode', 'basic')
        # Map string to OperationMode enum
        operation_mode = OperationMode(operation_mode_str.lower()) if isinstance(operation_mode_str, str) else operation_mode_str
        self.mode = self._map_operation_mode(operation_mode)
        
        # Get configuration
        self.quality_gate_threshold = config_manager.get('quality_gate_threshold', 85.0)
        self.max_document_size_mb = config_manager.get('max_document_size_mb', 10)
        
        # Mode-specific initialization
        self._initialize_for_mode(config_manager)
        
        # Initialize Jinja2 environment
        self._initialize_jinja_env()
        
        # Statistics
        self.documents_generated = 0
        self.total_generation_time = 0.0
        
        logger.info(f"Document Generator initialized in {self.mode.value} mode")
    
    def _map_operation_mode(self, operation_mode: OperationMode) -> GenerationMode:
        """Map storage operation mode to generation mode."""
        mapping = {
            OperationMode.BASIC: GenerationMode.BASIC,
            OperationMode.PERFORMANCE: GenerationMode.PERFORMANCE,
            OperationMode.SECURE: GenerationMode.SECURE,
            OperationMode.ENTERPRISE: GenerationMode.ENTERPRISE
        }
        return mapping.get(operation_mode, GenerationMode.BASIC)
    
    def _initialize_for_mode(self, config_manager: ConfigurationManager) -> None:
        """Initialize mode-specific features."""
        if self.mode == GenerationMode.BASIC:
            self.cache = None
            self.enable_parallel = False
            self.enable_security_validation = False
            self.enable_ai_enhancement = False
            
        elif self.mode == GenerationMode.PERFORMANCE:
            memory_mode = config_manager.get('memory_mode', MemoryMode.STANDARD)
            cache_size = {
                MemoryMode.BASELINE: 50,
                MemoryMode.STANDARD: 100,
                MemoryMode.ENHANCED: 200,
                MemoryMode.PERFORMANCE: 500
            }.get(memory_mode, 100)
            
            self.cache = DocumentCache(max_size=cache_size)
            self.enable_parallel = True
            self.enable_security_validation = False
            self.enable_ai_enhancement = False
            
        elif self.mode == GenerationMode.SECURE:
            self.cache = None
            self.enable_parallel = False
            self.enable_security_validation = True
            self.enable_ai_enhancement = False
            self.jinja_env = None  # Will create sandboxed environment
            
        elif self.mode == GenerationMode.ENTERPRISE:
            self.cache = DocumentCache(max_size=500)
            self.enable_parallel = True
            self.enable_security_validation = True
            self.enable_ai_enhancement = True
    
    def _initialize_jinja_env(self) -> None:
        """Initialize Jinja2 environment based on mode."""
        if self.mode == GenerationMode.SECURE or self.mode == GenerationMode.ENTERPRISE:
            # Use sandboxed environment for security
            self.jinja_env = SandboxedEnvironment(
                undefined=StrictUndefined,
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            self.jinja_env.sandboxed = True
        else:
            # Standard environment
            self.jinja_env = Environment(
                undefined=StrictUndefined,
                autoescape=select_autoescape(['html', 'xml']),
                trim_blocks=True,
                lstrip_blocks=True
            )
            self.jinja_env.autoescape = True
    
    async def generate_document(
        self,
        doc_type: DocumentType,
        template_id: str,
        variables: Dict[str, Any],
        output_format: OutputFormat = OutputFormat.MARKDOWN,
        enforce_quality_gate: bool = True,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenerationResult:
        """
        Generate a document from template with quality enforcement.
        
        Args:
            doc_type: Type of document to generate
            template_id: Template identifier
            variables: Template variables
            output_format: Desired output format
            enforce_quality_gate: Whether to enforce quality gate
            metadata: Additional metadata
        
        Returns:
            GenerationResult with document content and metadata
        """
        start_time = time.perf_counter()
        
        try:
            # Check cache if enabled
            cache_key = None
            if self.cache:
                cache_key = self._generate_cache_key(
                    doc_type, template_id, variables, output_format
                )
                cached = self.cache.get(cache_key)
                if cached:
                    logger.debug(f"Cache hit for document generation")
                    return cached
            
            # Validate inputs
            if self.enable_security_validation:
                self._validate_security(variables)
            
            # Get template from storage (templates are stored as documents)
            template_doc = self.storage_manager.get_document(template_id)
            if not template_doc:
                raise GeneratorError(f"Template not found: {template_id}")
            
            # Extract template data from document
            template_data = {
                'content': template_doc.content,
                'variables': template_doc.metadata.get('variables', []) if hasattr(template_doc, 'metadata') else []
            }
            
            # Validate template variables
            self._validate_template_variables(
                template_data.get('variables', []),
                variables
            )
            
            # Render template
            content = self._render_template(
                template_data['content'],
                variables
            )
            
            # Convert to requested format
            formatted_content = await self._convert_format(
                content,
                OutputFormat.MARKDOWN,
                output_format
            )
            
            # Quality check with M003
            quality_score = await self._check_quality(
                formatted_content,
                doc_type
            )
            
            # Enforce quality gate
            if enforce_quality_gate and quality_score < self.quality_gate_threshold:
                raise GeneratorError(
                    f"Document quality score {quality_score:.1f}% "
                    f"below threshold {self.quality_gate_threshold}%"
                )
            
            # Create document metadata
            doc_metadata = self._create_metadata(
                doc_type,
                output_format,
                template_id,
                quality_score,
                content,
                time.perf_counter() - start_time
            )
            
            # Store document in M002
            from devdocai.storage.models import Document as StorageDocument, ContentType
            
            doc_id = f"{doc_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{hashlib.md5(content.encode()).hexdigest()[:8]}"
            storage_doc = StorageDocument(
                id=doc_id,
                title=f"{doc_type.value.upper()} Document",
                content=formatted_content if isinstance(formatted_content, str) else str(formatted_content),
                content_type=ContentType.MARKDOWN,
                metadata=doc_metadata.to_dict()
            )
            
            created_doc = self.storage_manager.create_document(storage_doc)
            document_id = created_doc.id if hasattr(created_doc, 'id') else doc_id
            
            # Create result
            result = GenerationResult(
                success=True,
                document_id=document_id,
                content=formatted_content,
                format=output_format,
                quality_score=quality_score,
                metadata=doc_metadata.to_dict(),
                generation_time_ms=(time.perf_counter() - start_time) * 1000
            )
            
            # Add warning if quality is below threshold but not enforced
            if not enforce_quality_gate and quality_score < self.quality_gate_threshold:
                result.warnings.append(
                    f"Document quality score {quality_score:.1f}% "
                    f"is below recommended threshold {self.quality_gate_threshold}%"
                )
            
            # Cache result if enabled
            if cache_key and self.cache:
                self.cache.set(cache_key, result)
            
            # Update statistics
            self.documents_generated += 1
            self.total_generation_time += time.perf_counter() - start_time
            
            return result
            
        except Exception as e:
            logger.error(f"Document generation failed: {str(e)}")
            return GenerationResult(
                success=False,
                errors=[str(e)],
                generation_time_ms=(time.perf_counter() - start_time) * 1000
            )
    
    async def generate_batch(
        self,
        requests: List[Dict[str, Any]]
    ) -> List[GenerationResult]:
        """
        Generate multiple documents in batch.
        
        Utilizes parallel processing in PERFORMANCE/ENTERPRISE modes.
        """
        if self.enable_parallel:
            # Parallel generation
            tasks = [
                self.generate_document(
                    doc_type=req['doc_type'],
                    template_id=req['template_id'],
                    variables=req['variables'],
                    output_format=req.get('output_format', OutputFormat.MARKDOWN),
                    enforce_quality_gate=req.get('enforce_quality_gate', True)
                )
                for req in requests
            ]
            return await asyncio.gather(*tasks)
        else:
            # Sequential generation
            results = []
            for req in requests:
                result = await self.generate_document(
                    doc_type=req['doc_type'],
                    template_id=req['template_id'],
                    variables=req['variables'],
                    output_format=req.get('output_format', OutputFormat.MARKDOWN),
                    enforce_quality_gate=req.get('enforce_quality_gate', True)
                )
                results.append(result)
            return results
    
    async def register_template(
        self,
        name: str,
        content: str,
        category: str = "custom",
        variables: List[str] = None
    ) -> str:
        """Register a custom template."""
        from devdocai.storage.models import Document as StorageDocument, ContentType
        
        # Extract variables if not provided
        if variables is None:
            variables = self._extract_template_variables(content)
        
        # Store template in M002
        template_id = f"{category}_{name.lower().replace(' ', '_')}"
        
        template_doc = StorageDocument(
            id=f"template_{template_id}",
            title=name,
            content=content,
            content_type=ContentType.DOCUMENTATION,
            metadata={
                'type': 'template',
                'name': name,
                'category': category,
                'variables': variables,
                'created_at': datetime.now(timezone.utc).isoformat()
            }
        )
        
        self.storage_manager.create_document(template_doc)
        
        logger.info(f"Registered custom template: {template_id}")
        return template_id
    
    def _render_template(
        self,
        template_content: str,
        variables: Dict[str, Any]
    ) -> str:
        """Render template with variables."""
        try:
            template = self.jinja_env.from_string(template_content)
            return template.render(**variables)
        except (TemplateError, UndefinedError) as e:
            raise GeneratorError(f"Template rendering failed: {str(e)}")
    
    async def _convert_format(
        self,
        content: str,
        from_format: OutputFormat,
        to_format: OutputFormat
    ) -> Union[str, bytes]:
        """Convert document between formats."""
        if from_format == to_format:
            return content
        
        # Convert from Markdown to other formats
        if from_format == OutputFormat.MARKDOWN:
            if to_format == OutputFormat.HTML:
                return self._markdown_to_html(content)
            elif to_format == OutputFormat.PDF:
                return self._markdown_to_pdf(content)
            elif to_format == OutputFormat.DOCX:
                return self._markdown_to_docx(content)
            elif to_format == OutputFormat.JSON:
                return self._markdown_to_json(content)
        
        # Default: return as-is
        return content
    
    def _markdown_to_html(self, content: str) -> str:
        """Convert Markdown to HTML."""
        # Use markdown library with extensions
        html = markdown.markdown(
            content,
            extensions=[
                'markdown.extensions.fenced_code',
                'markdown.extensions.tables',
                'markdown.extensions.toc',
                'markdown.extensions.nl2br',
                'markdown.extensions.sane_lists'
            ]
        )
        
        # Sanitize HTML if security is enabled
        if self.enable_security_validation and HAS_BLEACH:
            html = bleach.clean(
                html,
                tags=self.ALLOWED_HTML_TAGS,
                attributes=self.ALLOWED_HTML_ATTRS,
                strip=True
            )
        
        # Wrap in basic HTML structure
        return f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Document</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; }}
        code {{ background: #f4f4f4; padding: 2px 4px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background: #f4f4f4; }}
    </style>
</head>
<body>
{html}
</body>
</html>"""
    
    def _markdown_to_pdf(self, content: str) -> bytes:
        """Convert Markdown to PDF."""
        if not HAS_WEASYPRINT:
            # Fallback: return PDF header with error message
            return b'%PDF-1.4\n% PDF generation not available. Install weasyprint.'
        
        # Convert to HTML first
        html = self._markdown_to_html(content)
        
        # Generate PDF using WeasyPrint
        pdf = WeasyHTML(string=html).write_pdf()
        return pdf
    
    def _markdown_to_docx(self, content: str) -> bytes:
        """Convert Markdown to DOCX."""
        if not HAS_DOCX:
            # Fallback: return DOCX header (it's a zip file)
            return b'PK\x03\x04'  # ZIP file signature
        
        # Create DOCX document
        doc = DocxDocument()
        
        # Parse markdown and add to document
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                doc.add_heading(line[2:], level=1)
            elif line.startswith('## '):
                doc.add_heading(line[3:], level=2)
            elif line.startswith('### '):
                doc.add_heading(line[4:], level=3)
            elif line.startswith('- ') or line.startswith('* '):
                doc.add_paragraph(line[2:], style='List Bullet')
            elif line.strip():
                doc.add_paragraph(line)
        
        # Save to bytes
        import io
        docx_bytes = io.BytesIO()
        doc.save(docx_bytes)
        return docx_bytes.getvalue()
    
    def _markdown_to_json(self, content: str) -> str:
        """Convert Markdown to JSON structure."""
        sections = []
        current_section = None
        
        lines = content.split('\n')
        for line in lines:
            if line.startswith('# '):
                if current_section:
                    sections.append(current_section)
                current_section = {
                    'type': 'heading1',
                    'content': line[2:],
                    'children': []
                }
            elif line.startswith('## '):
                section = {
                    'type': 'heading2',
                    'content': line[3:]
                }
                if current_section:
                    current_section['children'].append(section)
                else:
                    sections.append(section)
            elif line.strip():
                paragraph = {
                    'type': 'paragraph',
                    'content': line
                }
                if current_section:
                    current_section['children'].append(paragraph)
                else:
                    sections.append(paragraph)
        
        if current_section:
            sections.append(current_section)
        
        return json.dumps({'sections': sections}, indent=2)
    
    async def _check_quality(
        self,
        content: Union[str, bytes],
        doc_type: DocumentType
    ) -> float:
        """Check document quality using M003 MIAIR Engine."""
        # Convert bytes to string if needed
        if isinstance(content, bytes):
            content = content.decode('utf-8', errors='ignore')
        
        # Create MIAIR document
        miair_doc = MIAIRDocument(
            id=f"quality_check_{time.time()}",
            content=content,
            metadata={
                'type': doc_type.value,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }
        )
        
        # Analyze with MIAIR
        analysis_result = await self.miair_engine.analyze_document(
            miair_doc,
            include_semantic=True
        )
        
        return analysis_result.quality_score.overall
    
    def _validate_security(self, variables: Dict[str, Any]) -> None:
        """Validate variables for security threats."""
        dangerous_patterns = [
            r'__[a-zA-Z]+__',  # Dunder methods
            r'import\s+',      # Import statements
            r'exec\s*\(',      # Exec calls
            r'eval\s*\(',      # Eval calls
            r'compile\s*\(',   # Compile calls
            r'globals\s*\(',   # Globals access
            r'locals\s*\(',    # Locals access
            r'vars\s*\(',      # Vars access
            r'dir\s*\(',       # Dir access
            r'__class__',      # Class access
            r'__subclasses__', # Subclasses access
            r'__import__',     # Import function
            r'__builtins__',   # Builtins access
        ]
        
        # Check all variable values
        for key, value in variables.items():
            if isinstance(value, str):
                for pattern in dangerous_patterns:
                    if re.search(pattern, value, re.IGNORECASE):
                        raise GeneratorError(
                            f"Security validation failed: "
                            f"Potentially dangerous pattern in variable '{key}'"
                        )
    
    def _validate_template_variables(
        self,
        required_vars: List[str],
        provided_vars: Dict[str, Any]
    ) -> None:
        """Validate that all required template variables are provided."""
        missing = set(required_vars) - set(provided_vars.keys())
        if missing:
            raise GeneratorError(
                f"Missing required template variables: {', '.join(missing)}"
            )
    
    def _extract_template_variables(self, template_content: str) -> List[str]:
        """Extract variable names from template."""
        # Find all {{ variable }} patterns
        simple_vars = re.findall(r'\{\{\s*(\w+)\s*\}\}', template_content)
        
        # Find all {% for item in items %} patterns
        loop_vars = re.findall(r'\{%\s*for\s+\w+\s+in\s+(\w+)\s*%\}', template_content)
        
        # Combine and deduplicate
        all_vars = list(set(simple_vars + loop_vars))
        return all_vars
    
    def _sanitize_input(self, text: str) -> str:
        """Sanitize user input for security."""
        if HAS_BLEACH:
            # Use bleach for proper sanitization
            return bleach.clean(text, tags=[], strip=True)
        else:
            # Basic HTML escaping
            replacements = {
                '<': '&lt;',
                '>': '&gt;',
                '&': '&amp;',
                '"': '&quot;',
                "'": '&#x27;',
                '/': '&#x2F;'
            }
            for old, new in replacements.items():
                text = text.replace(old, new)
            return text
    
    def _generate_cache_key(
        self,
        doc_type: DocumentType,
        template_id: str,
        variables: Dict[str, Any],
        output_format: OutputFormat
    ) -> str:
        """Generate cache key for document."""
        # Create stable hash of inputs
        key_data = {
            'doc_type': doc_type.value,
            'template_id': template_id,
            'variables': json.dumps(variables, sort_keys=True),
            'format': output_format.value
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    def _create_metadata(
        self,
        doc_type: DocumentType,
        output_format: OutputFormat,
        template_id: str,
        quality_score: float,
        content: Union[str, bytes],
        generation_time: float
    ) -> DocumentMetadata:
        """Create document metadata."""
        # Calculate word and character counts
        text_content = content if isinstance(content, str) else str(content)
        word_count = len(text_content.split())
        char_count = len(text_content)
        
        return DocumentMetadata(
            document_type=doc_type.value,
            format=output_format.value,
            created_at=datetime.now(timezone.utc).isoformat(),
            version="1.0.0",
            quality_score=quality_score,
            template_id=template_id,
            generation_time_ms=generation_time * 1000,
            word_count=word_count,
            character_count=char_count
        )
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get generator statistics."""
        avg_time = (
            self.total_generation_time / self.documents_generated
            if self.documents_generated > 0
            else 0
        )
        
        return {
            'mode': self.mode.value,
            'documents_generated': self.documents_generated,
            'total_generation_time_sec': self.total_generation_time,
            'average_generation_time_ms': avg_time * 1000,
            'docs_per_second': (
                self.documents_generated / self.total_generation_time
                if self.total_generation_time > 0
                else 0
            ),
            'cache_enabled': self.cache is not None,
            'parallel_enabled': self.enable_parallel,
            'security_validation': self.enable_security_validation,
            'ai_enhancement': self.enable_ai_enhancement
        }