"""
M011 Batch Operations Manager - Processor Factory Implementation
DevDocAI v3.0.0 - Pass 4: Refactoring & Integration

Purpose: Extract document processors with Factory pattern
Dependencies: M009 (Enhancement), M004 (Generator), M007 (Review)
Performance: Maintains all Pass 2/3 achievements

Factory Pattern for different document processors:
- EnhanceProcessor: AI-powered document enhancement
- GenerateProcessor: Document generation
- ReviewProcessor: Quality review
- ValidateProcessor: Structure validation
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ============================================================================
# Processor Interface
# ============================================================================


class DocumentProcessor(ABC):
    """Abstract base class for document processors."""

    @abstractmethod
    async def process(
        self,
        document: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Process a single document."""
        pass

    @abstractmethod
    def validate_input(self, document: Dict[str, Any]) -> bool:
        """Validate document before processing."""
        pass

    @abstractmethod
    def get_required_fields(self) -> List[str]:
        """Get list of required document fields."""
        pass

    @property
    @abstractmethod
    def processor_type(self) -> str:
        """Get processor type identifier."""
        pass


# ============================================================================
# Enhancement Processor
# ============================================================================


class EnhanceProcessor(DocumentProcessor):
    """AI-powered document enhancement processor."""

    def __init__(self):
        self._pipeline = None  # Lazy loading

    async def process(
        self,
        document: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Enhance document using AI pipeline."""
        # Lazy load enhancement pipeline
        if self._pipeline is None:
            from ..intelligence.enhance import EnhancementPipeline
            self._pipeline = EnhancementPipeline()

        content = document.get("content", "")
        doc_type = document.get("type", "general")
        
        try:
            result = await self._pipeline.enhance_document(
                content=content,
                document_type=doc_type,
                **kwargs
            )
            
            return {
                "success": True,
                "document_id": document.get("id", "unknown"),
                "enhanced_content": result.enhanced_content,
                "quality_improvement": result.quality_improvement,
                "metrics": {
                    "original_length": len(content),
                    "enhanced_length": len(result.enhanced_content),
                    "improvement_percentage": result.quality_improvement,
                }
            }
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return {
                "success": False,
                "document_id": document.get("id", "unknown"),
                "error": str(e)
            }

    def validate_input(self, document: Dict[str, Any]) -> bool:
        """Validate document has required fields."""
        return all(
            field in document
            for field in self.get_required_fields()
        )

    def get_required_fields(self) -> List[str]:
        """Enhancement requires content field."""
        return ["content"]

    @property
    def processor_type(self) -> str:
        return "enhance"


# ============================================================================
# Generate Processor
# ============================================================================


class GenerateProcessor(DocumentProcessor):
    """Document generation processor."""

    def __init__(self):
        self._generator = None  # Lazy loading

    async def process(
        self,
        document: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Generate document content."""
        # Lazy load generator
        if self._generator is None:
            from ..core.generator import DocumentGenerator
            self._generator = DocumentGenerator()

        template_type = document.get("template", "readme")
        context = document.get("context", {})
        
        try:
            generated = await self._generator.generate(
                template_type=template_type,
                context=context,
                **kwargs
            )
            
            return {
                "success": True,
                "document_id": document.get("id", "unknown"),
                "generated_content": generated,
                "template_used": template_type,
            }
        except Exception as e:
            logger.error(f"Generation failed: {e}")
            return {
                "success": False,
                "document_id": document.get("id", "unknown"),
                "error": str(e)
            }

    def validate_input(self, document: Dict[str, Any]) -> bool:
        """Validate document has template or context."""
        return "template" in document or "context" in document

    def get_required_fields(self) -> List[str]:
        """Generation requires template or context."""
        return []  # No strictly required fields

    @property
    def processor_type(self) -> str:
        return "generate"


# ============================================================================
# Review Processor
# ============================================================================


class ReviewProcessor(DocumentProcessor):
    """Document quality review processor."""

    def __init__(self):
        self._reviewer = None  # Lazy loading

    async def process(
        self,
        document: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Review document for quality."""
        # Lazy load reviewer
        if self._reviewer is None:
            from ..core.review import ReviewEngine
            self._reviewer = ReviewEngine()

        content = document.get("content", "")
        doc_type = document.get("type", "general")
        
        try:
            review_result = await self._reviewer.review_document(
                content=content,
                document_type=doc_type,
                **kwargs
            )
            
            return {
                "success": True,
                "document_id": document.get("id", "unknown"),
                "quality_score": review_result.overall_score,
                "passed": review_result.passed,
                "issues": review_result.issues,
                "suggestions": review_result.suggestions,
            }
        except Exception as e:
            logger.error(f"Review failed: {e}")
            return {
                "success": False,
                "document_id": document.get("id", "unknown"),
                "error": str(e)
            }

    def validate_input(self, document: Dict[str, Any]) -> bool:
        """Validate document has content to review."""
        return "content" in document

    def get_required_fields(self) -> List[str]:
        """Review requires content field."""
        return ["content"]

    @property
    def processor_type(self) -> str:
        return "review"


# ============================================================================
# Validate Processor
# ============================================================================


class ValidateProcessor(DocumentProcessor):
    """Document structure validation processor."""

    REQUIRED_STRUCTURE = {
        "readme": ["title", "description", "installation", "usage"],
        "api_doc": ["endpoints", "authentication", "responses"],
        "changelog": ["version", "date", "changes"],
    }

    async def process(
        self,
        document: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Validate document structure and content."""
        doc_id = document.get("id", "unknown")
        doc_type = document.get("type", "general")
        content = document.get("content", "")
        
        validation_results = {
            "success": True,
            "document_id": doc_id,
            "valid": True,
            "errors": [],
            "warnings": [],
        }
        
        # Check required fields
        if not content:
            validation_results["valid"] = False
            validation_results["errors"].append("Missing content field")
        
        # Check document structure
        if doc_type in self.REQUIRED_STRUCTURE:
            required_sections = self.REQUIRED_STRUCTURE[doc_type]
            missing_sections = []
            
            for section in required_sections:
                if section.lower() not in content.lower():
                    missing_sections.append(section)
            
            if missing_sections:
                validation_results["warnings"].append(
                    f"Missing sections: {', '.join(missing_sections)}"
                )
        
        # Check content length
        if len(content) < 100:
            validation_results["warnings"].append(
                "Content is very short (< 100 characters)"
            )
        elif len(content) > 1_000_000:
            validation_results["warnings"].append(
                "Content is very large (> 1MB)"
            )
        
        # Overall validation status
        validation_results["valid"] = len(validation_results["errors"]) == 0
        validation_results["success"] = validation_results["valid"]
        
        return validation_results

    def validate_input(self, document: Dict[str, Any]) -> bool:
        """Basic input validation."""
        return isinstance(document, dict)

    def get_required_fields(self) -> List[str]:
        """Validation can work with any document."""
        return []

    @property
    def processor_type(self) -> str:
        return "validate"


# ============================================================================
# Custom Processor
# ============================================================================


class CustomProcessor(DocumentProcessor):
    """Custom processor for user-defined operations."""

    def __init__(self, process_func: callable):
        """
        Initialize with custom processing function.
        
        Args:
            process_func: Async function to process documents
        """
        if not callable(process_func):
            raise TypeError("process_func must be callable")
        self._process_func = process_func

    async def process(
        self,
        document: Dict[str, Any],
        **kwargs
    ) -> Dict[str, Any]:
        """Process document with custom function."""
        try:
            if asyncio.iscoroutinefunction(self._process_func):
                result = await self._process_func(document, **kwargs)
            else:
                # Run sync function in executor
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(
                    None,
                    self._process_func,
                    document,
                    kwargs
                )
            
            # Ensure result is a dict
            if not isinstance(result, dict):
                result = {"result": result}
            
            result["success"] = True
            result["document_id"] = document.get("id", "unknown")
            return result
            
        except Exception as e:
            logger.error(f"Custom processor failed: {e}")
            return {
                "success": False,
                "document_id": document.get("id", "unknown"),
                "error": str(e)
            }

    def validate_input(self, document: Dict[str, Any]) -> bool:
        """Custom processor accepts any dict."""
        return isinstance(document, dict)

    def get_required_fields(self) -> List[str]:
        """No specific requirements for custom processor."""
        return []

    @property
    def processor_type(self) -> str:
        return "custom"


# ============================================================================
# Processor Factory
# ============================================================================


class DocumentProcessorFactory:
    """Factory for creating document processors."""

    _processors = {
        "enhance": EnhanceProcessor,
        "generate": GenerateProcessor,
        "review": ReviewProcessor,
        "validate": ValidateProcessor,
    }

    @classmethod
    def create(
        cls,
        processor_type: str,
        **kwargs
    ) -> DocumentProcessor:
        """
        Create a document processor.
        
        Args:
            processor_type: Type of processor to create
            **kwargs: Processor-specific configuration
            
        Returns:
            DocumentProcessor instance
        """
        if processor_type == "custom":
            if "process_func" not in kwargs:
                raise ValueError("Custom processor requires process_func")
            return CustomProcessor(kwargs["process_func"])
        
        if processor_type not in cls._processors:
            raise ValueError(f"Unknown processor type: {processor_type}")
        
        processor_class = cls._processors[processor_type]
        return processor_class(**kwargs)

    @classmethod
    def register(cls, name: str, processor_class: type):
        """Register a new processor type."""
        if not issubclass(processor_class, DocumentProcessor):
            raise TypeError("Processor must inherit from DocumentProcessor")
        cls._processors[name] = processor_class

    @classmethod
    def list_processors(cls) -> List[str]:
        """List available processor types."""
        return list(cls._processors.keys()) + ["custom"]
