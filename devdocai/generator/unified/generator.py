"""
Unified AI Document Generator with mode-based behavior.

This module replaces the three separate implementations (basic, optimized, secure)
with a single, flexible generator that uses composition and strategy patterns.
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any, Union, AsyncGenerator
from pathlib import Path
from datetime import datetime
import hashlib
import json

from devdocai.generator.unified.config import (
    GenerationMode, UnifiedGenerationConfig
)
from devdocai.generator.unified.base_components import (
    DocumentType, GenerationRequest, GenerationResult, GenerationStrategy,
    ComponentFactory, GenerationMetrics, GenerationHooks, GenerationError
)
from devdocai.generator.unified.strategies import (
    BasicStrategy, PerformanceStrategy, SecureStrategy, EnterpriseStrategy
)
from devdocai.generator.unified.component_factory import UnifiedComponentFactory

# Import existing components for backward compatibility
from devdocai.generator.document_workflow import DocumentWorkflow
from devdocai.generator.prompt_template_engine import PromptTemplateEngine
from devdocai.storage import LocalStorageSystem
from devdocai.miair.engine_unified import UnifiedMIAIREngine
from devdocai.core.config import ConfigurationManager
from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter

logger = logging.getLogger(__name__)


class UnifiedAIDocumentGenerator:
    """
    Unified AI-powered document generator with mode-based behavior.
    
    This single implementation replaces:
    - AIDocumentGenerator (basic)
    - OptimizedAIDocumentGenerator (performance)
    - SecureAIDocumentGenerator (secure)
    
    Features are enabled based on the mode, using composition over inheritance
    for better flexibility and maintainability.
    """
    
    def __init__(
        self,
        config: Optional[UnifiedGenerationConfig] = None,
        mode: Optional[GenerationMode] = None,
        config_manager: Optional[ConfigurationManager] = None,
        storage: Optional[LocalStorageSystem] = None,
        template_dir: Optional[Path] = None
    ):
        """
        Initialize the unified document generator.
        
        Args:
            config: Unified configuration (takes precedence)
            mode: Generation mode (if config not provided)
            config_manager: M001 Configuration manager
            storage: M002 Storage system
            template_dir: Template directory path
        """
        # Initialize configuration
        if config:
            self.config = config
        elif mode:
            self.config = UnifiedGenerationConfig.from_mode(mode)
        else:
            self.config = UnifiedGenerationConfig.from_mode(GenerationMode.BASIC)
        
        # Core dependencies
        self.config_manager = config_manager or ConfigurationManager()
        self.storage = storage
        self.template_dir = template_dir or self.config.template_dir
        
        # Initialize strategy based on mode
        self.strategy = self._create_strategy()
        
        # Initialize components based on configuration
        self.component_factory = UnifiedComponentFactory()
        self.components = self._initialize_components()
        
        # Initialize metrics and hooks
        self.metrics = GenerationMetrics()
        self.hooks = GenerationHooks()
        
        # Track generation history
        self.generation_history: List[GenerationResult] = []
        self.active_generations: Dict[str, asyncio.Task] = {}
        
        logger.info(f"Initialized Unified Generator in {self.config.mode.value} mode")
    
    def _create_strategy(self) -> GenerationStrategy:
        """Create the appropriate generation strategy based on mode."""
        strategies = {
            GenerationMode.BASIC: BasicStrategy,
            GenerationMode.PERFORMANCE: PerformanceStrategy,
            GenerationMode.SECURE: SecureStrategy,
            GenerationMode.ENTERPRISE: EnterpriseStrategy
        }
        
        strategy_class = strategies.get(self.config.mode, BasicStrategy)
        return strategy_class()
    
    def _initialize_components(self) -> Dict[str, Any]:
        """Initialize all components based on configuration."""
        components = {}
        
        # Always initialize core components
        components["llm_adapter"] = self._init_llm_adapter()
        components["template_engine"] = self._init_template_engine()
        components["miair_engine"] = self._init_miair_engine()
        components["workflow_engine"] = self._init_workflow_engine()
        
        # Conditionally initialize based on configuration
        if self.config.cache.enabled:
            components["cache_manager"] = self.component_factory.create_cache_manager(
                self.config.cache
            )
        
        if self.config.security.enabled:
            components["security_manager"] = self.component_factory.create_security_manager(
                self.config.security
            )
        
        if self.config.performance.enabled:
            components["optimizer"] = self.component_factory.create_optimizer(
                self.config.performance
            )
        
        return components
    
    def _init_llm_adapter(self) -> UnifiedLLMAdapter:
        """Initialize the LLM adapter with configuration."""
        # Map our mode to LLM adapter operation mode
        llm_mode_map = {
            GenerationMode.BASIC: "BASIC",
            GenerationMode.PERFORMANCE: "PERFORMANCE",
            GenerationMode.SECURE: "SECURE",
            GenerationMode.ENTERPRISE: "ENTERPRISE"
        }
        
        return UnifiedLLMAdapter(
            config=self.config_manager,
            mode=llm_mode_map.get(self.config.mode, "BASIC")
        )
    
    def _init_template_engine(self) -> PromptTemplateEngine:
        """Initialize the template engine."""
        return PromptTemplateEngine(template_dir=self.template_dir)
    
    def _init_miair_engine(self) -> Optional[UnifiedMIAIREngine]:
        """Initialize the MIAIR engine if enabled."""
        if self.config.enable_miair_optimization:
            # Map our mode to MIAIR operation mode
            miair_mode_map = {
                GenerationMode.BASIC: "BASIC",
                GenerationMode.PERFORMANCE: "OPTIMIZED",
                GenerationMode.SECURE: "SECURE",
                GenerationMode.ENTERPRISE: "ENTERPRISE"
            }
            
            return UnifiedMIAIREngine(
                operation_mode=miair_mode_map.get(self.config.mode, "BASIC")
            )
        return None
    
    def _init_workflow_engine(self) -> DocumentWorkflow:
        """Initialize the document workflow engine."""
        return DocumentWorkflow()
    
    async def generate_document(
        self,
        document_type: Union[str, DocumentType],
        context: Dict[str, Any],
        **kwargs
    ) -> GenerationResult:
        """
        Generate a single document.
        
        This is the main entry point that replaces the multiple generate methods
        from the three implementations.
        
        Args:
            document_type: Type of document to generate
            context: Context for generation
            **kwargs: Additional options
        
        Returns:
            GenerationResult with the generated document
        """
        # Convert string to enum if needed
        if isinstance(document_type, str):
            try:
                document_type = DocumentType(document_type)
            except ValueError:
                document_type = DocumentType.CUSTOM
        
        # Create generation request
        request = GenerationRequest(
            document_type=document_type,
            context=context,
            template_name=kwargs.get("template_name"),
            output_format=kwargs.get("output_format", "markdown"),
            metadata=kwargs.get("metadata", {}),
            options=kwargs.get("options", {}),
            user_id=kwargs.get("user_id"),
            session_id=kwargs.get("session_id"),
            permissions=kwargs.get("permissions", []),
            priority=kwargs.get("priority", 5),
            cache_enabled=kwargs.get("cache_enabled", self.config.cache.enabled),
            streaming_enabled=kwargs.get("streaming_enabled", self.config.performance.streaming_enabled),
            quality_threshold=kwargs.get("quality_threshold", 0.8),
            require_review=kwargs.get("require_review", False),
            max_iterations=kwargs.get("max_iterations", 3)
        )
        
        # Start metrics tracking
        self.metrics.start_time = datetime.now()
        
        try:
            # Pre-generation hooks
            await self.hooks.trigger("pre_generation", request)
            
            # Validate request
            if not self.strategy.validate_request(request):
                raise GenerationError(f"Invalid request for {document_type.value}")
            
            # Preprocess request
            request = self.strategy.preprocess_request(request)
            
            # Check cache if enabled
            if request.cache_enabled and "cache_manager" in self.components:
                cache_key = self._generate_cache_key(request)
                cached_content = await self.components["cache_manager"].get(cache_key)
                
                if cached_content:
                    logger.info(f"Cache hit for {document_type.value}")
                    self.metrics.cache_hits += 1
                    
                    result = GenerationResult(
                        success=True,
                        document_type=document_type,
                        content=cached_content,
                        cache_hit=True,
                        cache_key=cache_key,
                        generation_time_ms=0,
                        quality_score=1.0
                    )
                    
                    # Post-generation hooks
                    await self.hooks.trigger("post_generation", result)
                    
                    return result
                else:
                    self.metrics.cache_misses += 1
            
            # Generate using strategy
            result = await self.strategy.generate(request, self.components)
            
            # Postprocess result
            result = self.strategy.postprocess_result(result)
            
            # Apply MIAIR optimization if enabled
            if self.config.enable_miair_optimization and self.components.get("miair_engine"):
                miair_result = await self.components["miair_engine"].analyze(result.content)
                result.quality_score = miair_result.get("quality_score", 0.0)
                
                # Enhance if below threshold
                if result.quality_score < request.quality_threshold:
                    enhanced = await self._enhance_with_miair(
                        result.content, 
                        request.quality_threshold
                    )
                    if enhanced:
                        result.content = enhanced
                        result.quality_score = request.quality_threshold
            
            # Store in cache if successful
            if result.success and request.cache_enabled and "cache_manager" in self.components:
                cache_key = self._generate_cache_key(request)
                await self.components["cache_manager"].set(
                    cache_key,
                    result.content,
                    ttl=self.config.cache.ttl_seconds
                )
                result.cache_key = cache_key
            
            # Store in history
            self.generation_history.append(result)
            
            # Calculate final metrics
            self.metrics.end_time = datetime.now()
            self.metrics.calculate_final_metrics()
            result.generation_time_ms = self.metrics.generation_time_ms
            
            # Post-generation hooks
            await self.hooks.trigger("post_generation", result)
            
            return result
            
        except Exception as e:
            logger.error(f"Generation failed for {document_type.value}: {e}")
            
            # Error hooks
            await self.hooks.trigger("on_generation_error", e)
            
            return GenerationResult(
                success=False,
                document_type=document_type,
                error=str(e),
                generation_time_ms=self.metrics.generation_time_ms
            )
    
    async def generate_document_suite(
        self,
        project_context: Dict[str, Any],
        document_types: Optional[List[DocumentType]] = None,
        **kwargs
    ) -> Dict[str, GenerationResult]:
        """
        Generate a complete suite of documents.
        
        Replaces the multiple suite generation methods from the implementations.
        """
        if document_types is None:
            # Default suite
            document_types = [
                DocumentType.README,
                DocumentType.API,
                DocumentType.USER_GUIDE,
                DocumentType.ARCHITECTURE,
                DocumentType.CONTRIBUTING
            ]
        
        results = {}
        
        # Determine if parallel generation is enabled
        if self.config.performance.parallel_generation and len(document_types) > 1:
            # Generate in parallel
            tasks = []
            for doc_type in document_types:
                task = asyncio.create_task(
                    self.generate_document(doc_type, project_context, **kwargs)
                )
                tasks.append((doc_type, task))
            
            # Wait for all to complete
            for doc_type, task in tasks:
                try:
                    result = await task
                    results[doc_type.value] = result
                except Exception as e:
                    logger.error(f"Failed to generate {doc_type.value}: {e}")
                    results[doc_type.value] = GenerationResult(
                        success=False,
                        document_type=doc_type,
                        error=str(e)
                    )
        else:
            # Generate sequentially
            for doc_type in document_types:
                try:
                    result = await self.generate_document(
                        doc_type, 
                        project_context, 
                        **kwargs
                    )
                    results[doc_type.value] = result
                    
                    # Check dependencies and update context
                    deps = self.components["workflow_engine"].get_dependencies(doc_type)
                    if deps and result.success:
                        project_context[f"{doc_type.value}_content"] = result.content
                        
                except Exception as e:
                    logger.error(f"Failed to generate {doc_type.value}: {e}")
                    results[doc_type.value] = GenerationResult(
                        success=False,
                        document_type=doc_type,
                        error=str(e)
                    )
        
        return results
    
    async def stream_generation(
        self,
        document_type: Union[str, DocumentType],
        context: Dict[str, Any],
        **kwargs
    ) -> AsyncGenerator[str, None]:
        """
        Stream document generation for real-time output.
        
        Only available in PERFORMANCE or ENTERPRISE modes.
        """
        if not self.config.performance.streaming_enabled:
            raise GenerationError("Streaming not enabled in current mode")
        
        # Convert string to enum if needed
        if isinstance(document_type, str):
            document_type = DocumentType(document_type)
        
        # Create request with streaming enabled
        kwargs["streaming_enabled"] = True
        request = GenerationRequest(
            document_type=document_type,
            context=context,
            **kwargs
        )
        
        # Stream through strategy
        if hasattr(self.strategy, "stream_generate"):
            async for chunk in self.strategy.stream_generate(request, self.components):
                yield chunk
        else:
            # Fallback to non-streaming
            result = await self.generate_document(document_type, context, **kwargs)
            if result.success and result.content:
                yield result.content
    
    def _generate_cache_key(self, request: GenerationRequest) -> str:
        """Generate a cache key for the request."""
        key_data = {
            "type": request.document_type.value,
            "template": request.template_name,
            "format": request.output_format,
            "context_keys": sorted(request.context.keys()),
            "options": request.options
        }
        
        key_str = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(key_str.encode()).hexdigest()
    
    async def _enhance_with_miair(
        self, 
        content: str, 
        target_quality: float
    ) -> Optional[str]:
        """Enhance content using MIAIR engine."""
        if not self.components.get("miair_engine"):
            return None
        
        try:
            enhanced = await self.components["miair_engine"].optimize(
                content,
                target_score=target_quality
            )
            return enhanced
        except Exception as e:
            logger.warning(f"MIAIR enhancement failed: {e}")
            return None
    
    def set_mode(self, mode: GenerationMode):
        """
        Dynamically change the generation mode.
        
        This allows switching modes without recreating the generator.
        """
        if mode != self.config.mode:
            logger.info(f"Switching from {self.config.mode.value} to {mode.value} mode")
            
            # Update configuration
            self.config = UnifiedGenerationConfig.from_mode(mode)
            
            # Recreate strategy
            self.strategy = self._create_strategy()
            
            # Reinitialize components
            self.components = self._initialize_components()
    
    def register_hook(self, event: str, handler):
        """Register a hook for extending behavior."""
        self.hooks.register(event, handler)
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics."""
        return {
            "generation_time_ms": self.metrics.generation_time_ms,
            "tokens_used": self.metrics.tokens_used,
            "cache_hit_rate": self.metrics.cache_hit_rate,
            "security_violations": self.metrics.security_violations,
            "quality_score": self.metrics.quality_score,
            "total_cost_usd": self.metrics.total_cost_usd
        }
    
    def get_history(self) -> List[GenerationResult]:
        """Get generation history."""
        return self.generation_history
    
    def clear_history(self):
        """Clear generation history."""
        self.generation_history.clear()
    
    async def cleanup(self):
        """Clean up resources."""
        # Cancel any active generations
        for task in self.active_generations.values():
            task.cancel()
        
        # Clear cache if available
        if "cache_manager" in self.components:
            await self.components["cache_manager"].clear()
        
        # Clear history
        self.clear_history()
        
        logger.info("Unified generator cleaned up")


# Backward compatibility aliases
AIDocumentGenerator = UnifiedAIDocumentGenerator
OptimizedAIDocumentGenerator = UnifiedAIDocumentGenerator
SecureAIDocumentGenerator = UnifiedAIDocumentGenerator