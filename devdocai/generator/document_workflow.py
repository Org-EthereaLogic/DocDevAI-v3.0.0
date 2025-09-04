"""
Document Suite Generation Workflow Engine.

Implements the methodology for building comprehensive documentation suites
where each document builds on others, with multi-phase reviews using
different LLMs for specialized analysis.
"""

from enum import Enum
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


class DocumentType(Enum):
    """Types of documents in the suite."""
    USER_STORIES = "user_stories"
    PROJECT_PLAN = "project_plan"
    SRS = "software_requirements"
    ARCHITECTURE = "architecture_blueprint"
    SDD = "software_design_document"
    SOURCE_CODE = "source_code"
    MOCKUPS = "mockups"
    TEST_PLAN = "test_plan"
    TRACEABILITY = "traceability_matrix"
    SCMP = "configuration_management"
    API_DOCS = "api_documentation"
    BUILD_INSTRUCTIONS = "build_instructions"
    RELEASE_NOTES = "release_notes"
    MAINTENANCE_PLAN = "maintenance_plan"
    DEPLOYMENT = "deployment_instructions"
    USER_DOCS = "user_documentation"
    USER_MANUAL = "user_manual"
    CONTRIBUTING = "contributing_guide"


class ReviewPhase(Enum):
    """Review phases with specialized LLM assignments."""
    FIRST_DRAFT = "first_draft"  # Initial generation
    REQUIREMENTS = "requirements_review"  # ChatGPT-5: clarity, completeness
    DESIGN = "design_review"  # Claude Sonnet 4: technical suitability
    SECURITY = "security_review"  # Gemini 2.5 Pro: vulnerabilities
    PERFORMANCE = "performance_review"  # Gemini 2.5 Pro: efficiency
    TEST = "test_review"  # Claude Opus 4: test coverage
    USABILITY = "usability_review"  # ChatGPT-5: UX, accessibility
    COMPLIANCE = "compliance_review"  # ChatGPT-5 PRO: suite alignment


@dataclass
class DocumentDependency:
    """Defines document dependencies and generation order."""
    document_type: DocumentType
    depends_on: Set[DocumentType] = field(default_factory=set)
    review_phases: List[ReviewPhase] = field(default_factory=list)
    is_core: bool = False  # Core documents go through all review phases


@dataclass
class ReviewConfiguration:
    """Configuration for a specific review phase."""
    phase: ReviewPhase
    llm_provider: str
    llm_model: str
    temperature: float = 0.7
    focus_areas: List[str] = field(default_factory=list)
    prompt_template: Optional[str] = None


class DocumentWorkflow:
    """
    Orchestrates the document suite generation workflow.
    
    Follows the methodology:
    1. Start with user stories
    2. Generate core documents (Project Plan, SRS, Architecture)
    3. Core documents go through all review phases
    4. Generate remaining documents based on core docs
    5. All documents get first-draft review
    6. Final compliance review ensures suite alignment
    """
    
    # Document dependency graph
    DOCUMENT_DEPENDENCIES = {
        DocumentType.USER_STORIES: DocumentDependency(
            document_type=DocumentType.USER_STORIES,
            depends_on=set(),  # Starting point - no dependencies
            review_phases=[ReviewPhase.FIRST_DRAFT, ReviewPhase.REQUIREMENTS],
            is_core=False  # Special case - foundational but not full review
        ),
        DocumentType.PROJECT_PLAN: DocumentDependency(
            document_type=DocumentType.PROJECT_PLAN,
            depends_on={DocumentType.USER_STORIES},
            review_phases=[
                ReviewPhase.FIRST_DRAFT,
                ReviewPhase.REQUIREMENTS,
                ReviewPhase.DESIGN,
                ReviewPhase.SECURITY,
                ReviewPhase.PERFORMANCE,
                ReviewPhase.USABILITY
            ],
            is_core=True
        ),
        DocumentType.SRS: DocumentDependency(
            document_type=DocumentType.SRS,
            depends_on={DocumentType.USER_STORIES, DocumentType.PROJECT_PLAN},
            review_phases=[
                ReviewPhase.FIRST_DRAFT,
                ReviewPhase.REQUIREMENTS,
                ReviewPhase.DESIGN,
                ReviewPhase.SECURITY,
                ReviewPhase.PERFORMANCE,
                ReviewPhase.USABILITY
            ],
            is_core=True
        ),
        DocumentType.ARCHITECTURE: DocumentDependency(
            document_type=DocumentType.ARCHITECTURE,
            depends_on={
                DocumentType.USER_STORIES,
                DocumentType.PROJECT_PLAN,
                DocumentType.SRS
            },
            review_phases=[
                ReviewPhase.FIRST_DRAFT,
                ReviewPhase.REQUIREMENTS,
                ReviewPhase.DESIGN,
                ReviewPhase.SECURITY,
                ReviewPhase.PERFORMANCE
            ],
            is_core=True
        ),
        DocumentType.SDD: DocumentDependency(
            document_type=DocumentType.SDD,
            depends_on={
                DocumentType.USER_STORIES,
                DocumentType.PROJECT_PLAN,
                DocumentType.SRS,
                DocumentType.ARCHITECTURE
            },
            review_phases=[ReviewPhase.FIRST_DRAFT],
            is_core=False
        ),
        DocumentType.SOURCE_CODE: DocumentDependency(
            document_type=DocumentType.SOURCE_CODE,
            depends_on={
                DocumentType.USER_STORIES,
                DocumentType.PROJECT_PLAN,
                DocumentType.SRS,
                DocumentType.ARCHITECTURE
            },
            review_phases=[ReviewPhase.FIRST_DRAFT],
            is_core=False
        ),
        # Add remaining documents...
        DocumentType.TEST_PLAN: DocumentDependency(
            document_type=DocumentType.TEST_PLAN,
            depends_on={
                DocumentType.USER_STORIES,
                DocumentType.SRS,
                DocumentType.ARCHITECTURE
            },
            review_phases=[ReviewPhase.FIRST_DRAFT, ReviewPhase.TEST],
            is_core=False
        ),
        DocumentType.API_DOCS: DocumentDependency(
            document_type=DocumentType.API_DOCS,
            depends_on={
                DocumentType.ARCHITECTURE,
                DocumentType.SDD
            },
            review_phases=[ReviewPhase.FIRST_DRAFT],
            is_core=False
        ),
        DocumentType.USER_MANUAL: DocumentDependency(
            document_type=DocumentType.USER_MANUAL,
            depends_on={
                DocumentType.USER_STORIES,
                DocumentType.SRS,
                DocumentType.MOCKUPS
            },
            review_phases=[ReviewPhase.FIRST_DRAFT],
            is_core=False
        ),
    }
    
    # LLM assignments for each review phase
    REVIEW_CONFIGS = {
        ReviewPhase.FIRST_DRAFT: ReviewConfiguration(
            phase=ReviewPhase.FIRST_DRAFT,
            llm_provider="multi",  # Use multi-LLM synthesis
            llm_model="best_available",
            temperature=0.8,
            focus_areas=["completeness", "structure", "clarity"]
        ),
        ReviewPhase.REQUIREMENTS: ReviewConfiguration(
            phase=ReviewPhase.REQUIREMENTS,
            llm_provider="openai",
            llm_model="gpt-4-turbo",  # Would be GPT-5 when available
            temperature=0.6,
            focus_areas=["clarity", "completeness", "consistency", "traceability"],
            prompt_template="requirements_review.yaml"
        ),
        ReviewPhase.DESIGN: ReviewConfiguration(
            phase=ReviewPhase.DESIGN,
            llm_provider="anthropic",
            llm_model="claude-3-sonnet",  # Would be Sonnet 4 when available
            temperature=0.7,
            focus_areas=["technical_suitability", "patterns", "architecture"],
            prompt_template="design_review.yaml"
        ),
        ReviewPhase.SECURITY: ReviewConfiguration(
            phase=ReviewPhase.SECURITY,
            llm_provider="google",
            llm_model="gemini-pro",  # Would be Gemini 2.5 Pro
            temperature=0.5,
            focus_areas=["vulnerabilities", "compliance", "threat_modeling"],
            prompt_template="security_review.yaml"
        ),
        ReviewPhase.PERFORMANCE: ReviewConfiguration(
            phase=ReviewPhase.PERFORMANCE,
            llm_provider="google",
            llm_model="gemini-pro",
            temperature=0.6,
            focus_areas=["efficiency", "scalability", "bottlenecks"],
            prompt_template="performance_review.yaml"
        ),
        ReviewPhase.TEST: ReviewConfiguration(
            phase=ReviewPhase.TEST,
            llm_provider="anthropic",
            llm_model="claude-3-opus",  # Would be Opus 4
            temperature=0.6,
            focus_areas=["coverage", "edge_cases", "test_strategy"],
            prompt_template="test_review.yaml"
        ),
        ReviewPhase.USABILITY: ReviewConfiguration(
            phase=ReviewPhase.USABILITY,
            llm_provider="openai",
            llm_model="gpt-4-turbo",
            temperature=0.7,
            focus_areas=["user_experience", "accessibility", "intuitiveness"],
            prompt_template="usability_review.yaml"
        ),
        ReviewPhase.COMPLIANCE: ReviewConfiguration(
            phase=ReviewPhase.COMPLIANCE,
            llm_provider="openai",
            llm_model="gpt-4-turbo",  # Would be GPT-5 PRO
            temperature=0.5,
            focus_areas=["alignment", "consistency", "completeness", "standards"],
            prompt_template="compliance_review.yaml"
        ),
    }
    
    def __init__(self, llm_adapter, template_engine, storage):
        """
        Initialize the workflow engine.
        
        Args:
            llm_adapter: M008 LLM Adapter for AI queries
            template_engine: Template processor for prompts
            storage: M002 Storage for documents
        """
        self.llm_adapter = llm_adapter
        self.template_engine = template_engine
        self.storage = storage
        self.generated_documents: Dict[DocumentType, Any] = {}
        self.review_history: Dict[DocumentType, Dict[ReviewPhase, Any]] = {}
        
    def generate_suite(self, initial_input: str) -> Dict[DocumentType, Any]:
        """
        Generate a complete document suite starting from initial input.
        
        Args:
            initial_input: User's initial project description
            
        Returns:
            Dictionary of all generated documents
        """
        logger.info("Starting document suite generation")
        
        # Step 1: Generate user stories from initial input
        user_stories = self._generate_document(
            DocumentType.USER_STORIES,
            {"initial_description": initial_input}
        )
        self.generated_documents[DocumentType.USER_STORIES] = user_stories
        
        # Step 2: Generate documents in dependency order
        generation_order = self._calculate_generation_order()
        
        for doc_type in generation_order:
            if doc_type == DocumentType.USER_STORIES:
                continue  # Already generated
                
            # Gather dependencies
            dependencies = self._gather_dependencies(doc_type)
            
            # Generate document
            document = self._generate_document(doc_type, dependencies)
            self.generated_documents[doc_type] = document
            
            # Apply review phases
            self._apply_reviews(doc_type)
        
        # Step 3: Final compliance review for suite alignment
        self._perform_compliance_review()
        
        return self.generated_documents
    
    def _calculate_generation_order(self) -> List[DocumentType]:
        """
        Calculate the order in which documents should be generated
        based on their dependencies (topological sort).
        """
        visited = set()
        order = []
        
        def visit(doc_type: DocumentType):
            if doc_type in visited:
                return
            visited.add(doc_type)
            
            dep_info = self.DOCUMENT_DEPENDENCIES.get(doc_type)
            if dep_info:
                for dependency in dep_info.depends_on:
                    visit(dependency)
            
            order.append(doc_type)
        
        for doc_type in DocumentType:
            visit(doc_type)
        
        return order
    
    def _gather_dependencies(self, doc_type: DocumentType) -> Dict[str, Any]:
        """
        Gather all required dependencies for generating a document.
        """
        dep_info = self.DOCUMENT_DEPENDENCIES.get(doc_type)
        if not dep_info:
            return {}
        
        dependencies = {}
        for dep_type in dep_info.depends_on:
            if dep_type in self.generated_documents:
                dependencies[dep_type.value] = self.generated_documents[dep_type]
        
        return dependencies
    
    def _generate_document(
        self,
        doc_type: DocumentType,
        context: Dict[str, Any]
    ) -> Any:
        """
        Generate a document using the appropriate template and LLM.
        """
        logger.info(f"Generating {doc_type.value}")
        
        # Load the generation template
        template_name = f"{doc_type.value}_generation.yaml"
        template = self.template_engine.load_template(template_name)
        
        # Prepare the prompt with context
        prompt = self.template_engine.render(template, context)
        
        # Use multi-LLM synthesis for initial generation
        config = self.REVIEW_CONFIGS[ReviewPhase.FIRST_DRAFT]
        response = self.llm_adapter.generate_multi_llm(
            prompt=prompt,
            providers_weights={
                "anthropic": 0.4,
                "openai": 0.35,
                "google": 0.25
            },
            temperature=config.temperature
        )
        
        # Parse and structure the response
        document = self._parse_llm_response(response, doc_type)
        
        # Store in review history
        if doc_type not in self.review_history:
            self.review_history[doc_type] = {}
        self.review_history[doc_type][ReviewPhase.FIRST_DRAFT] = document
        
        return document
    
    def _apply_reviews(self, doc_type: DocumentType) -> None:
        """
        Apply all required review phases to a document.
        """
        dep_info = self.DOCUMENT_DEPENDENCIES.get(doc_type)
        if not dep_info:
            return
        
        for review_phase in dep_info.review_phases:
            if review_phase == ReviewPhase.FIRST_DRAFT:
                continue  # Already done during generation
            
            logger.info(f"Applying {review_phase.value} to {doc_type.value}")
            
            # Get review configuration
            config = self.REVIEW_CONFIGS[review_phase]
            
            # Load review template
            template = self.template_engine.load_template(config.prompt_template)
            
            # Prepare review context
            review_context = {
                "document": self.generated_documents[doc_type],
                "dependencies": self._gather_dependencies(doc_type),
                "previous_reviews": self.review_history.get(doc_type, {})
            }
            
            # Render review prompt
            review_prompt = self.template_engine.render(template, review_context)
            
            # Query specific LLM for this review
            review_result = self.llm_adapter.generate(
                prompt=review_prompt,
                provider=config.llm_provider,
                model=config.llm_model,
                temperature=config.temperature
            )
            
            # Apply review recommendations
            updated_document = self._apply_review_recommendations(
                self.generated_documents[doc_type],
                review_result,
                review_phase
            )
            
            # Update document and history
            self.generated_documents[doc_type] = updated_document
            self.review_history[doc_type][review_phase] = review_result
    
    def _perform_compliance_review(self) -> None:
        """
        Perform final compliance review across all documents.
        """
        logger.info("Performing final compliance review")
        
        config = self.REVIEW_CONFIGS[ReviewPhase.COMPLIANCE]
        
        # Load compliance review template
        template = self.template_engine.load_template(config.prompt_template)
        
        # Prepare all documents for review
        compliance_context = {
            "all_documents": self.generated_documents,
            "review_history": self.review_history,
            "core_documents": {
                doc_type: self.generated_documents[doc_type]
                for doc_type in [
                    DocumentType.PROJECT_PLAN,
                    DocumentType.SRS,
                    DocumentType.ARCHITECTURE
                ]
                if doc_type in self.generated_documents
            }
        }
        
        # Render compliance prompt
        compliance_prompt = self.template_engine.render(template, compliance_context)
        
        # Query LLM for compliance review
        compliance_result = self.llm_adapter.generate(
            prompt=compliance_prompt,
            provider=config.llm_provider,
            model=config.llm_model,
            temperature=config.temperature
        )
        
        # Apply compliance adjustments to all documents
        self._apply_compliance_adjustments(compliance_result)
    
    def _parse_llm_response(self, response: str, doc_type: DocumentType) -> Any:
        """
        Parse and structure the LLM response based on document type.
        """
        # Extract structured content from XML tags or other formats
        # This would be customized per document type
        return response
    
    def _apply_review_recommendations(
        self,
        document: Any,
        review_result: Any,
        review_phase: ReviewPhase
    ) -> Any:
        """
        Apply review recommendations to improve the document.
        """
        # Apply specific improvements based on review phase
        # This would involve re-querying LLMs with refinement prompts
        return document
    
    def _apply_compliance_adjustments(self, compliance_result: Any) -> None:
        """
        Apply compliance adjustments across all documents.
        """
        # Parse compliance recommendations and update documents
        # to ensure suite-wide alignment
        pass