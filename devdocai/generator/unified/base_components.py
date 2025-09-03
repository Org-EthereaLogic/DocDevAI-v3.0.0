"""
Base components for unified document generator.

This module provides abstract base classes and interfaces that are used
across all generation modes, eliminating duplication from the three implementations.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any, AsyncGenerator, Callable
from pathlib import Path
from datetime import datetime
from enum import Enum
import asyncio
import logging


logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Standard document types supported by the generator."""
    README = "readme"
    API = "api"
    USER_GUIDE = "user_guide"
    ARCHITECTURE = "architecture"
    DEPLOYMENT = "deployment"
    CONTRIBUTING = "contributing"
    SECURITY = "security"
    TESTING = "testing"
    MIGRATION = "migration"
    CHANGELOG = "changelog"
    CUSTOM = "custom"


@dataclass
class GenerationRequest:
    """
    Unified request object for document generation.
    
    Replaces the multiple request formats from the three implementations.
    """
    document_type: DocumentType
    context: Dict[str, Any]
    template_name: Optional[str] = None
    output_format: str = "markdown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    options: Dict[str, Any] = field(default_factory=dict)
    
    # Security context
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    permissions: List[str] = field(default_factory=list)
    
    # Performance hints
    priority: int = 5  # 1-10, higher is more important
    cache_enabled: bool = True
    streaming_enabled: bool = False
    
    # Quality requirements
    quality_threshold: float = 0.8
    require_review: bool = False
    max_iterations: int = 3


@dataclass
class GenerationResult:
    """
    Unified result object for document generation.
    
    Consolidates the various result formats from the three implementations.
    """
    success: bool
    document_type: DocumentType
    content: Optional[str] = None
    error: Optional[str] = None
    
    # Metadata
    generation_time_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0
    quality_score: float = 0.0
    
    # Security audit
    security_checks_passed: bool = True
    pii_detected: bool = False
    injection_attempts: int = 0
    
    # Performance metrics
    cache_hit: bool = False
    cache_key: Optional[str] = None
    parallel_tasks: int = 1
    
    # Additional data
    metadata: Dict[str, Any] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class GenerationStrategy(ABC):
    """
    Abstract base class for generation strategies.
    
    This implements the Strategy pattern, allowing different generation
    approaches to be used based on the mode.
    """
    
    @abstractmethod
    async def generate(
        self, 
        request: GenerationRequest,
        components: Dict[str, Any]
    ) -> GenerationResult:
        """Generate a document based on the request."""
        pass
    
    @abstractmethod
    def validate_request(self, request: GenerationRequest) -> bool:
        """Validate that the request can be processed."""
        pass
    
    def preprocess_request(self, request: GenerationRequest) -> GenerationRequest:
        """Preprocess the request before generation."""
        return request
    
    def postprocess_result(self, result: GenerationResult) -> GenerationResult:
        """Postprocess the result after generation."""
        return result


class ComponentFactory(ABC):
    """
    Abstract factory for creating generation components.
    
    This implements the Factory pattern, allowing different component
    implementations to be created based on the mode.
    """
    
    @abstractmethod
    def create_cache_manager(self, config: Any) -> Optional[Any]:
        """Create a cache manager based on configuration."""
        pass
    
    @abstractmethod
    def create_security_manager(self, config: Any) -> Optional[Any]:
        """Create a security manager based on configuration."""
        pass
    
    @abstractmethod
    def create_optimizer(self, config: Any) -> Optional[Any]:
        """Create a token optimizer based on configuration."""
        pass
    
    @abstractmethod
    def create_llm_adapter(self, config: Any) -> Any:
        """Create an LLM adapter based on configuration."""
        pass


class SecurityHandler(ABC):
    """
    Abstract base class for security handlers.
    
    Implements the Chain of Responsibility pattern for security pipeline.
    """
    
    def __init__(self, next_handler: Optional["SecurityHandler"] = None):
        """Initialize with optional next handler in chain."""
        self.next_handler = next_handler
    
    @abstractmethod
    async def handle(self, request: GenerationRequest, content: str) -> tuple[bool, str]:
        """
        Handle security check for the content.
        
        Returns:
            Tuple of (is_safe, processed_content)
        """
        pass
    
    async def process_chain(self, request: GenerationRequest, content: str) -> tuple[bool, str]:
        """Process this handler and continue the chain."""
        is_safe, processed_content = await self.handle(request, content)
        
        if not is_safe:
            return False, processed_content
        
        if self.next_handler:
            return await self.next_handler.process_chain(request, processed_content)
        
        return is_safe, processed_content


class GenerationObserver(ABC):
    """
    Abstract observer for generation events.
    
    Implements the Observer pattern for progress tracking and monitoring.
    """
    
    @abstractmethod
    async def on_generation_start(self, request: GenerationRequest):
        """Called when generation starts."""
        pass
    
    @abstractmethod
    async def on_progress_update(self, percent: float, message: str):
        """Called when progress is updated."""
        pass
    
    @abstractmethod
    async def on_generation_complete(self, result: GenerationResult):
        """Called when generation completes."""
        pass
    
    @abstractmethod
    async def on_generation_error(self, error: Exception):
        """Called when an error occurs."""
        pass


class CacheInterface(ABC):
    """
    Abstract interface for caching implementations.
    
    Unifies the different caching approaches from optimized implementation.
    """
    
    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """Get cached content by key."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None):
        """Set cached content with optional TTL."""
        pass
    
    @abstractmethod
    async def invalidate(self, key: str):
        """Invalidate cached content."""
        pass
    
    @abstractmethod
    async def clear(self):
        """Clear all cached content."""
        pass
    
    @abstractmethod
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        pass


class LLMInterface(ABC):
    """
    Abstract interface for LLM interactions.
    
    Unifies the different LLM interaction patterns from the implementations.
    """
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        context: Dict[str, Any],
        streaming: bool = False
    ) -> str | AsyncGenerator[str, None]:
        """Generate content from prompt."""
        pass
    
    @abstractmethod
    async def synthesize(
        self,
        prompts: List[str],
        strategy: str = "weighted_average"
    ) -> str:
        """Synthesize responses from multiple prompts/models."""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        pass
    
    @abstractmethod
    def estimate_cost(self, tokens: int, model: str) -> float:
        """Estimate cost for token usage."""
        pass


class TemplateInterface(ABC):
    """
    Abstract interface for template management.
    
    Unifies the template handling from the implementations.
    """
    
    @abstractmethod
    async def load_template(self, name: str) -> str:
        """Load template by name."""
        pass
    
    @abstractmethod
    async def render_template(
        self,
        template: str,
        context: Dict[str, Any]
    ) -> str:
        """Render template with context."""
        pass
    
    @abstractmethod
    def validate_template(self, template: str) -> bool:
        """Validate template syntax."""
        pass
    
    @abstractmethod
    def list_templates(self) -> List[str]:
        """List available templates."""
        pass


@dataclass
class GenerationMetrics:
    """
    Unified metrics collection for generation process.
    
    Consolidates the various metrics from the implementations.
    """
    # Performance metrics
    start_time: datetime = field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    generation_time_ms: float = 0.0
    
    # Resource metrics
    tokens_used: int = 0
    memory_used_mb: float = 0.0
    cpu_percent: float = 0.0
    
    # Cache metrics
    cache_hits: int = 0
    cache_misses: int = 0
    cache_hit_rate: float = 0.0
    
    # Security metrics
    security_checks_performed: int = 0
    security_violations: int = 0
    pii_detections: int = 0
    injection_attempts: int = 0
    
    # Quality metrics
    quality_score: float = 0.0
    readability_score: float = 0.0
    completeness_score: float = 0.0
    
    # Cost metrics
    total_cost_usd: float = 0.0
    provider_costs: Dict[str, float] = field(default_factory=dict)
    
    def calculate_final_metrics(self):
        """Calculate final metrics after generation."""
        if self.end_time and self.start_time:
            delta = self.end_time - self.start_time
            self.generation_time_ms = delta.total_seconds() * 1000
        
        if self.cache_hits + self.cache_misses > 0:
            self.cache_hit_rate = self.cache_hits / (self.cache_hits + self.cache_misses)


class GenerationHooks:
    """
    Hook system for extending generation behavior.
    
    Allows plugins and extensions without modifying core logic.
    """
    
    def __init__(self):
        """Initialize hook registry."""
        self.hooks: Dict[str, List[Callable]] = {
            "pre_generation": [],
            "post_generation": [],
            "pre_llm_call": [],
            "post_llm_call": [],
            "pre_cache_check": [],
            "post_cache_check": [],
            "pre_security_check": [],
            "post_security_check": [],
            "pre_template_render": [],
            "post_template_render": []
        }
    
    def register(self, event: str, handler: Callable):
        """Register a hook handler for an event."""
        if event in self.hooks:
            self.hooks[event].append(handler)
    
    async def trigger(self, event: str, *args, **kwargs):
        """Trigger all handlers for an event."""
        if event in self.hooks:
            for handler in self.hooks[event]:
                if asyncio.iscoroutinefunction(handler):
                    await handler(*args, **kwargs)
                else:
                    handler(*args, **kwargs)


class GenerationError(Exception):
    """Base exception for generation errors."""
    pass


class SecurityError(GenerationError):
    """Security-related generation error."""
    pass


class RateLimitError(GenerationError):
    """Rate limit exceeded error."""
    pass


class ValidationError(GenerationError):
    """Validation error during generation."""
    pass