"""
AI-Powered Document Generator for M004.

Integrates the prompt template engine and document workflow with M008 LLM Adapter
to enable AI-powered document generation instead of simple template substitution.
"""

import asyncio
import logging
import json
from typing import Dict, List, Optional, Any, Union
from pathlib import Path
from datetime import datetime
from enum import Enum

from devdocai.generator.document_workflow import (
    DocumentWorkflow, DocumentType, ReviewPhase
)
from devdocai.generator.prompt_template_engine import (
    PromptTemplateEngine, PromptTemplate, RenderedPrompt
)
from devdocai.llm_adapter.adapter_unified import UnifiedLLMAdapter, OperationMode
from devdocai.llm_adapter.config import LLMConfig, ProviderConfig, ProviderType
from devdocai.llm_adapter.providers.base import LLMRequest
from devdocai.storage import LocalStorageSystem
from devdocai.miair.engine_unified import UnifiedMIAIREngine
from devdocai.core.config import ConfigurationManager

logger = logging.getLogger(__name__)


class GenerationMode(Enum):
    """Document generation modes."""
    SINGLE = "single"  # Generate a single document
    SUITE = "suite"   # Generate a complete document suite
    REVIEW = "review"  # Generate with review passes


class AIDocumentGenerator:
    """
    AI-powered document generator that orchestrates LLM-based generation.
    
    This replaces template substitution with sophisticated AI generation
    using multi-LLM synthesis and iterative refinement.
    """
    
    def __init__(
        self,
        config_manager: Optional[ConfigurationManager] = None,
        storage: Optional[LocalStorageSystem] = None,
        template_dir: Optional[Path] = None
    ):
        """
        Initialize the AI document generator.
        
        Args:
            config_manager: M001 Configuration manager
            storage: M002 Storage system
            template_dir: Directory containing prompt templates
        """
        self.config_manager = config_manager or ConfigurationManager()
        self.storage = storage
        self.template_dir = template_dir or Path("devdocai/templates/prompt_templates/generation")
        
        # Initialize components
        self._init_llm_adapter()
        self._init_template_engine()
        self._init_miair_engine()
        self._init_workflow_engine()
        
        # Track generated documents
        self.generated_documents: Dict[str, Any] = {}
        self.generation_history: List[Dict[str, Any]] = []
        
        logger.info("Initialized AI Document Generator")
    
    def _init_llm_adapter(self):
        """Initialize M008 LLM Adapter with multi-provider support."""
        # Get LLM configuration from config manager
        # For Pass 1, we'll use a simple configuration
        llm_settings = {}
        
        # Configure multiple providers for synthesis
        providers = []
        
        # Anthropic Claude
        if llm_settings.get("anthropic_api_key"):
            providers.append(ProviderConfig(
                provider_type=ProviderType.ANTHROPIC,
                api_key=llm_settings["anthropic_api_key"],
                model="claude-3-opus-20240229",
                max_retries=3,
                timeout=60
            ))
        
        # OpenAI GPT
        if llm_settings.get("openai_api_key"):
            providers.append(ProviderConfig(
                provider_type=ProviderType.OPENAI,
                api_key=llm_settings["openai_api_key"],
                model="gpt-4-turbo-preview",
                max_retries=3,
                timeout=60
            ))
        
        # Google Gemini
        if llm_settings.get("google_api_key"):
            providers.append(ProviderConfig(
                provider_type=ProviderType.GOOGLE,
                api_key=llm_settings["google_api_key"],
                model="gemini-pro",
                max_retries=3,
                timeout=60
            ))
        
        # Create LLM configuration
        if providers:
            llm_config = LLMConfig(
                providers=providers,
                default_provider=ProviderType.ANTHROPIC,
                enable_fallback=True,
                enable_cost_tracking=True,
                daily_cost_limit=10.0,
                monthly_cost_limit=200.0
            )
            
            # Initialize adapter in BASIC mode for Pass 1 (we'll optimize in Pass 2)
            self.llm_adapter = UnifiedLLMAdapter(
                config=llm_config,
                operation_mode=OperationMode.BASIC
            )
            
            logger.info(f"Initialized LLM Adapter with {len(providers)} providers")
        else:
            # Create a mock adapter for testing without API keys
            logger.warning("No LLM providers configured - using mock adapter")
            self.llm_adapter = None  # Will be mocked in tests
    
    def _init_template_engine(self):
        """Initialize the prompt template engine."""
        self.template_engine = PromptTemplateEngine(
            template_dir=self.template_dir,
            cache_templates=True
        )
        logger.info(f"Initialized template engine with directory: {self.template_dir}")
    
    def _init_miair_engine(self):
        """Initialize M003 MIAIR Engine for quality optimization."""
        # We'll use MIAIR to optimize generated documents
        from devdocai.miair.engine_unified import UnifiedMIAIRConfig, EngineMode
        
        # Create MIAIR configuration
        miair_config = UnifiedMIAIRConfig()
        miair_config.mode = EngineMode.STANDARD  # Start with standard mode
        miair_config.enable_caching = False      # No caching for Pass 1
        miair_config.target_quality = 0.75       # Target 75% quality for Pass 1
        
        self.miair_engine = UnifiedMIAIREngine(config=miair_config)
        logger.info("Initialized MIAIR Engine for quality optimization")
    
    def _init_workflow_engine(self):
        """Initialize the document workflow engine."""
        # Only initialize workflow if we have an LLM adapter
        if self.llm_adapter:
            self.workflow = DocumentWorkflow(
                llm_adapter=self.llm_adapter,
                template_engine=self.template_engine,
                storage=self.storage
            )
            logger.info("Initialized Document Workflow Engine")
        else:
            self.workflow = None
            logger.info("Workflow Engine not initialized (no LLM adapter)")
    
    async def generate_document(
        self,
        document_type: str,
        context: Dict[str, Any],
        mode: GenerationMode = GenerationMode.SINGLE
    ) -> Dict[str, Any]:
        """
        Generate a single document using AI.
        
        Args:
            document_type: Type of document to generate
            context: Context/inputs for generation
            mode: Generation mode
            
        Returns:
            Generated document with metadata
        """
        logger.info(f"Generating {document_type} document in {mode.value} mode")
        
        # Load the appropriate template
        template_name = f"{document_type}_generation"
        
        try:
            # Render the prompt
            rendered_prompt = self.template_engine.render(
                template=template_name,
                context=context
            )
            
            # Prepare LLM request
            request = LLMRequest(
                prompt=rendered_prompt.user_prompt,
                system_prompt=rendered_prompt.system_prompt,
                temperature=rendered_prompt.llm_config.get("temperature", 0.7),
                max_tokens=rendered_prompt.llm_config.get("max_tokens", 4000)
            )
            
            # Generate using multi-LLM synthesis
            response = await self._generate_with_synthesis(
                request=request,
                providers_weights=self._get_provider_weights(rendered_prompt.llm_config)
            )
            
            # Extract structured output
            structured_output = self.template_engine.extract_output_sections(
                llm_response=response.content,
                output_config=rendered_prompt.output_config
            )
            
            # Optimize with MIAIR if configured
            if rendered_prompt.miair_config and rendered_prompt.miair_config.get("enabled"):
                structured_output = await self._optimize_with_miair(
                    content=structured_output,
                    config=rendered_prompt.miair_config
                )
            
            # Store in M002 if storage is available
            if self.storage:
                document_id = await self._store_document(
                    document_type=document_type,
                    content=structured_output,
                    metadata={
                        "generation_mode": mode.value,
                        "timestamp": datetime.now().isoformat(),
                        "llm_providers": list(self._get_provider_weights(rendered_prompt.llm_config).keys())
                    }
                )
                structured_output["document_id"] = document_id
            
            # Track generated document
            self.generated_documents[document_type] = structured_output
            self.generation_history.append({
                "type": document_type,
                "timestamp": datetime.now().isoformat(),
                "mode": mode.value,
                "success": True
            })
            
            logger.info(f"Successfully generated {document_type} document")
            return structured_output
            
        except Exception as e:
            logger.error(f"Failed to generate {document_type}: {str(e)}")
            self.generation_history.append({
                "type": document_type,
                "timestamp": datetime.now().isoformat(),
                "mode": mode.value,
                "success": False,
                "error": str(e)
            })
            raise
    
    async def generate_suite(
        self,
        initial_description: str,
        include_documents: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Generate a complete document suite from initial description.
        
        Args:
            initial_description: User's project description
            include_documents: Specific documents to include (default: core documents)
            
        Returns:
            Dictionary of all generated documents
        """
        logger.info("Starting document suite generation")
        
        # Default to core documents if not specified
        if not include_documents:
            include_documents = [
                "user_stories",
                "project_plan", 
                "software_requirements",
                "architecture_blueprint"
            ]
        
        generated_suite = {}
        
        # Step 1: Generate user stories from initial description
        logger.info("Generating user stories from initial description")
        user_stories = await self.generate_document(
            document_type="user_stories",
            context={"initial_description": initial_description},
            mode=GenerationMode.SUITE
        )
        generated_suite["user_stories"] = user_stories
        
        # Step 2: Generate project plan based on user stories
        if "project_plan" in include_documents:
            logger.info("Generating project plan")
            project_plan = await self.generate_document(
                document_type="project_plan",
                context={
                    "user_stories": user_stories,
                    "initial_description": initial_description
                },
                mode=GenerationMode.SUITE
            )
            generated_suite["project_plan"] = project_plan
        
        # Step 3: Generate SRS based on user stories and project plan
        if "software_requirements" in include_documents:
            logger.info("Generating software requirements specification")
            srs = await self.generate_document(
                document_type="software_requirements",
                context={
                    "user_stories": user_stories,
                    "project_plan": generated_suite.get("project_plan", {}),
                    "initial_description": initial_description
                },
                mode=GenerationMode.SUITE
            )
            generated_suite["software_requirements"] = srs
        
        # Step 4: Generate architecture based on all previous documents
        if "architecture_blueprint" in include_documents:
            logger.info("Generating architecture blueprint")
            architecture = await self.generate_document(
                document_type="architecture_blueprint",
                context={
                    "user_stories": user_stories,
                    "project_plan": generated_suite.get("project_plan", {}),
                    "software_requirements": generated_suite.get("software_requirements", {}),
                    "initial_description": initial_description
                },
                mode=GenerationMode.SUITE
            )
            generated_suite["architecture_blueprint"] = architecture
        
        # Step 5: Apply first-draft review to all documents
        logger.info("Applying first-draft review to all documents")
        for doc_type, document in generated_suite.items():
            reviewed_doc = await self._apply_review(
                document_type=doc_type,
                document=document,
                review_phase="first_draft",
                context=generated_suite
            )
            generated_suite[doc_type] = reviewed_doc
        
        # Store the complete suite
        if self.storage:
            suite_id = await self._store_suite(generated_suite)
            generated_suite["suite_id"] = suite_id
        
        logger.info(f"Successfully generated document suite with {len(generated_suite)} documents")
        return generated_suite
    
    async def _generate_with_synthesis(
        self,
        request: LLMRequest,
        providers_weights: Dict[str, float]
    ) -> Any:
        """
        Generate response using multi-LLM synthesis.
        
        Args:
            request: LLM request
            providers_weights: Provider weights for synthesis
            
        Returns:
            Synthesized LLM response
        """
        # For Pass 1, we'll use a simplified synthesis approach
        # The adapter should handle the actual synthesis
        
        # Convert request to dict format expected by adapter
        request_dict = {
            "prompt": request.prompt,
            "system_prompt": request.system_prompt,
            "temperature": request.temperature,
            "max_tokens": request.max_tokens
        }
        
        # Query the adapter (it will handle multi-provider synthesis internally)
        response = await self.llm_adapter.query(request_dict)
        
        return response
    
    def _get_provider_weights(self, llm_config: Dict[str, Any]) -> Dict[str, float]:
        """
        Extract provider weights from LLM configuration.
        
        Args:
            llm_config: LLM configuration from template
            
        Returns:
            Dictionary of provider names to weights
        """
        weights = {}
        
        # Check if providers are specified in config
        if "providers" in llm_config:
            for provider in llm_config["providers"]:
                name = provider.get("name", "").lower()
                weight = provider.get("weight", 0.0)
                
                # Map template names to adapter provider names
                provider_map = {
                    "claude": "anthropic",
                    "openai": "openai",
                    "gpt": "openai",
                    "google": "google",
                    "gemini": "google"
                }
                
                mapped_name = provider_map.get(name, name)
                weights[mapped_name] = weight
        else:
            # Default weights if not specified
            weights = {
                "anthropic": 0.4,
                "openai": 0.35,
                "google": 0.25
            }
        
        return weights
    
    async def _optimize_with_miair(
        self,
        content: Dict[str, Any],
        config: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Optimize document content using MIAIR engine.
        
        Args:
            content: Document content to optimize
            config: MIAIR configuration
            
        Returns:
            Optimized content
        """
        # Convert content to string for MIAIR processing
        content_str = json.dumps(content) if isinstance(content, dict) else str(content)
        
        # Analyze and optimize
        analysis_result = self.miair_engine.analyze_documentation(content_str)
        
        # If quality is below threshold, attempt optimization
        if analysis_result.quality_score < config.get("target_quality", 0.75):
            logger.info(f"Quality score {analysis_result.quality_score:.2f} below target, optimizing...")
            
            # Apply MIAIR optimization suggestions
            # For Pass 1, we'll just return the content with quality metadata
            content["_miair_quality"] = analysis_result.quality_score
            content["_miair_suggestions"] = analysis_result.improvement_suggestions[:3]
        else:
            content["_miair_quality"] = analysis_result.quality_score
        
        return content
    
    async def _apply_review(
        self,
        document_type: str,
        document: Dict[str, Any],
        review_phase: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Apply a review pass to a document.
        
        Args:
            document_type: Type of document
            document: Document content
            review_phase: Review phase to apply
            context: Additional context for review
            
        Returns:
            Reviewed and improved document
        """
        logger.info(f"Applying {review_phase} review to {document_type}")
        
        try:
            # Load review template
            template_name = f"{review_phase}_review"
            
            # Prepare review context
            review_context = {
                "document": document,
                "document_type": document_type,
                **context
            }
            
            # Render review prompt
            rendered_prompt = self.template_engine.render(
                template=template_name,
                context=review_context
            )
            
            # Generate review
            request = LLMRequest(
                prompt=rendered_prompt.user_prompt,
                system_prompt=rendered_prompt.system_prompt,
                temperature=0.6,  # Lower temperature for reviews
                max_tokens=3000
            )
            
            response = await self._generate_with_synthesis(
                request=request,
                providers_weights=self._get_provider_weights(rendered_prompt.llm_config)
            )
            
            # Extract review feedback
            review_feedback = self.template_engine.extract_output_sections(
                llm_response=response.content,
                output_config=rendered_prompt.output_config
            )
            
            # Apply review suggestions (for Pass 1, just add metadata)
            document["_review"] = {
                "phase": review_phase,
                "timestamp": datetime.now().isoformat(),
                "feedback": review_feedback
            }
            
            return document
            
        except Exception as e:
            logger.warning(f"Review {review_phase} failed: {str(e)}, returning original document")
            return document
    
    async def _store_document(
        self,
        document_type: str,
        content: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> str:
        """
        Store document in M002 storage.
        
        Args:
            document_type: Type of document
            content: Document content
            metadata: Document metadata
            
        Returns:
            Document ID
        """
        if not self.storage:
            return f"doc_{document_type}_{datetime.now().timestamp()}"
        
        # Create document record
        document = {
            "type": document_type,
            "content": json.dumps(content),
            "metadata": metadata,
            "created_at": datetime.now().isoformat()
        }
        
        # Store in M002
        document_id = self.storage.create_document(
            content=document["content"],
            metadata=document["metadata"]
        )
        
        logger.debug(f"Stored document {document_id} of type {document_type}")
        return document_id
    
    async def _store_suite(self, suite: Dict[str, Any]) -> str:
        """
        Store complete document suite.
        
        Args:
            suite: Complete document suite
            
        Returns:
            Suite ID
        """
        suite_id = f"suite_{datetime.now().timestamp()}"
        
        if self.storage:
            # Store suite metadata
            suite_metadata = {
                "suite_id": suite_id,
                "documents": list(suite.keys()),
                "created_at": datetime.now().isoformat()
            }
            
            self.storage.create_document(
                content=json.dumps(suite),
                metadata=suite_metadata
            )
        
        return suite_id
    
    def get_generation_history(self) -> List[Dict[str, Any]]:
        """Get history of all generation attempts."""
        return self.generation_history
    
    def get_generated_document(self, document_type: str) -> Optional[Dict[str, Any]]:
        """Get a specific generated document."""
        return self.generated_documents.get(document_type)
    
    def clear_history(self):
        """Clear generation history and cached documents."""
        self.generated_documents.clear()
        self.generation_history.clear()
        logger.info("Cleared generation history and cache")