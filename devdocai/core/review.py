"""
M007 Review Engine - Main Orchestrator (Pass 4: Refactored)
DevDocAI v3.0.0

Lean orchestrator for multi-dimensional document analysis.
Delegates to specialized modules for clean separation of concerns.
"""

import asyncio
import logging
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# Integration imports
from ..core.config import ConfigurationManager
from ..core.storage import Document, DocumentMetadata, StorageManager
from .review_performance import (
    CacheManager,
    ParallelProcessor,
    PerformanceMonitor,
    performance_timer,
)
from .review_security import RateLimitError, SecurityManager, ValidationError
from .review_strategies import IssueCollector, QualityScore, ReviewStrategyFactory

# Local imports - Review components
from .review_types import PIIMatch, ReviewResult, ReviewType
from .reviewers import (
    ComplianceReviewer,
    ConsistencyReviewer,
    CoverageReviewer,
    DesignReviewer,
    PerformanceReviewer,
    PIIDetector,
    RequirementsReviewer,
    SecurityReviewer,
    UsabilityReviewer,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class ReviewError(Exception):
    """Base exception for review engine errors."""

    pass


# ============================================================================
# Data Classes
# ============================================================================


@dataclass
class PIIDetectionResult:
    """Result of PII detection."""

    pii_found: List[PIIMatch] = field(default_factory=list)
    accuracy: float = 0.0
    total_found: int = 0
    detection_time: float = 0.0


@dataclass
class AnalysisReport:
    """Comprehensive analysis report for a document."""

    document_id: str
    document_type: str
    overall_score: float
    quality_gate_status: str
    quality_score: QualityScore
    reviews: Dict[ReviewType, ReviewResult] = field(default_factory=dict)
    pii_detection: Optional[PIIDetectionResult] = None
    quality_issues: List[str] = field(default_factory=list)
    all_issues: List[Any] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    execution_time: float = 0.0
    from_cache: bool = False
    llm_enhanced: bool = False
    security_signature: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert report to dictionary."""
        data = asdict(self)
        data["timestamp"] = self.timestamp.isoformat()
        # Convert enums to strings
        data["reviews"] = {k.value: v for k, v in self.reviews.items()}
        return data

    def to_json(self) -> str:
        """Convert report to JSON string."""
        import json

        return json.dumps(self.to_dict(), indent=2, default=str)


class QualityGateError(Exception):
    """Raised when document fails quality gate."""

    def __init__(self, score: float, threshold: float):
        self.score = score
        self.threshold = threshold
        super().__init__(f"Quality gate failed: score {score:.2f} < threshold {threshold:.2f}")


# ============================================================================
# Factory
# ============================================================================


class ReviewEngineFactory:
    """Factory for creating ReviewEngine instances."""

    @classmethod
    def create(cls, **kwargs) -> "ReviewEngine":
        """Create ReviewEngine with appropriate configuration."""
        config = kwargs.get("config")
        storage = kwargs.get("storage")
        generator = kwargs.get("generator")
        tracking = kwargs.get("tracking")
        strategy = kwargs.get("review_strategy", "standard")

        return ReviewEngine(
            config=config,
            storage=storage,
            generator=generator,
            tracking=tracking,
            review_strategy=strategy,
        )


# ============================================================================
# Review Engine
# ============================================================================


class ReviewEngine:
    """
    Main orchestrator for multi-dimensional document analysis.

    Pass 4 Refactoring:
    - Extracted strategy pattern to review_strategies.py
    - Extracted security to review_security.py
    - Extracted performance to review_performance.py
    - Lean orchestrator focusing on coordination
    """

    def __init__(
        self,
        config=None,
        storage=None,
        generator=None,
        tracking=None,
        review_strategy="standard",
    ):
        """Initialize review engine with dependencies."""
        # Core dependencies
        self.config = config if config is not None else ConfigurationManager()
        self.storage = (
            storage
            if storage is not None
            else (StorageManager(self.config) if self.config else None)
        )
        self.generator = generator
        self.tracking = tracking
        self.llm_adapter = None  # Optional M008 integration

        # Strategy components
        self.review_strategy = ReviewStrategyFactory.create(review_strategy)
        self.issue_collector = IssueCollector()

        # Security components
        self.security_manager = SecurityManager()

        # Performance components
        self.cache_manager = CacheManager()
        self.parallel_processor = ParallelProcessor()
        self.performance_monitor = PerformanceMonitor()

        # Initialize reviewers
        self.reviewers = self._initialize_reviewers()
        self.pii_detector = PIIDetector()

        # Configuration
        self.quality_threshold = 0.85
        self._load_configuration()

    def _initialize_reviewers(self) -> Dict[ReviewType, Any]:
        """Initialize all specialized reviewers."""
        return {
            ReviewType.REQUIREMENTS: RequirementsReviewer(),
            ReviewType.DESIGN: DesignReviewer(),
            ReviewType.SECURITY: SecurityReviewer(),
            ReviewType.PERFORMANCE: PerformanceReviewer(),
            ReviewType.USABILITY: UsabilityReviewer(),
            ReviewType.TEST_COVERAGE: CoverageReviewer(),
            ReviewType.COMPLIANCE: ComplianceReviewer(),
            ReviewType.CONSISTENCY: ConsistencyReviewer(self.tracking),
        }

    def _load_configuration(self):
        """Load configuration from M001."""
        if self.config:
            try:
                review_config = self.config.get("review", {})
                self.quality_threshold = review_config.get("quality_threshold", 0.85)

                # Load custom PII patterns if configured
                pii_patterns = review_config.get("pii_patterns", {})
                for pii_type, pattern in pii_patterns.items():
                    if pattern and pii_type != "email":
                        from .review_types import PIIType

                        self.pii_detector.add_pattern(
                            PIIType.CUSTOM, pattern, f"Custom {pii_type} pattern"
                        )
            except Exception as e:
                logger.warning(f"Failed to load review configuration: {e}")

    @performance_timer
    async def analyze(
        self,
        document: Document,
        review_types: Optional[List[ReviewType]] = None,
        use_llm_enhancement: bool = False,
        save_results: bool = False,
        client_id: Optional[str] = None,
    ) -> AnalysisReport:
        """
        Perform comprehensive document analysis.

        Args:
            document: Document to analyze
            review_types: Specific review types to run (None = all)
            use_llm_enhancement: Use LLM for enhanced analysis
            save_results: Save results to storage
            client_id: Client identifier for rate limiting

        Returns:
            AnalysisReport with comprehensive analysis results
        """
        start_time = time.time()
        client_id = client_id or "anonymous"

        # Security validation
        try:
            self.security_manager.validate_document(document)
            self._validate_review_types(review_types)
        except ValidationError as e:
            self.security_manager.log_security_event(
                "validation_failed", {"error": str(e), "document_id": document.id}
            )
            raise

        # Rate limiting
        if not self.security_manager.check_rate_limit(client_id):
            self.security_manager.log_security_event(
                "rate_limit_exceeded", {"client_id": client_id}
            )
            raise RateLimitError(f"Rate limit exceeded for client {client_id}")

        # Resource limiting
        if not self.security_manager.acquire_request_slot():
            self.security_manager.log_security_event(
                "resource_limit_exceeded",
                {"active_requests": self.security_manager.get_active_requests()},
            )
            raise Exception("Too many concurrent requests")

        try:
            # Check cache
            cache_key = self.cache_manager.get_cache_key(document)
            cached_result = await self.cache_manager.get(cache_key)
            if cached_result:
                self.performance_monitor.update_metrics(
                    time.time() - start_time,
                    from_cache=True,
                    cache_stats=self.cache_manager.get_stats(),
                )
                return cached_result

            # Perform analysis
            report = await self._perform_analysis(document, review_types, use_llm_enhancement)

            # Store in cache
            self.cache_manager.store(cache_key, report)

            # Update metrics
            self.performance_monitor.update_metrics(
                report.execution_time,
                from_cache=False,
                cache_stats=self.cache_manager.get_stats(),
            )

            # Save results if requested
            if save_results and self.storage:
                await self._save_results(report)

            # Sign report for integrity
            report.security_signature = self.security_manager.sign_data(report.to_json())

            return report

        finally:
            # Always release resources
            self.security_manager.release_request_slot()

            # Log audit trail
            self.security_manager.log_audit_event(
                "document_analyzed",
                {
                    "document_id": document.id,
                    "client_id": client_id,
                    "execution_time": time.time() - start_time,
                    "quality_gate": (report.quality_gate_status if "report" in locals() else "N/A"),
                },
            )

    async def _perform_analysis(
        self,
        document: Document,
        review_types: Optional[List[ReviewType]],
        use_llm_enhancement: bool,
    ) -> AnalysisReport:
        """Perform the actual document analysis."""
        start_time = time.time()

        # Determine review types
        if review_types is None:
            review_types = list(ReviewType)

        # Prepare review tasks
        review_tasks = []
        content_chunks = (
            self.parallel_processor.chunk_document(document.content)
            if len(document.content) > 50000
            else None
        )

        for review_type in review_types:
            if review_type in self.reviewers:
                reviewer = self.reviewers[review_type]
                metadata = {
                    "document_id": document.id,
                    "document_type": document.type,
                    "metadata": document.metadata,
                    "content_chunks": content_chunks,
                }
                task = reviewer.review(document.content, metadata)
                review_tasks.append((review_type, task))

        # Execute reviews in parallel
        review_results = await self.parallel_processor.process_parallel(
            review_tasks, max_concurrent=6
        )

        # Process results
        reviews = {}
        for review_type, result in review_results:
            if result is not None:
                reviews[review_type] = result

        # Run additional analyses in parallel
        pii_task = asyncio.create_task(self._detect_pii(document.content))

        # Calculate quality score
        quality_score = self.review_strategy.calculate_quality_score(reviews)
        overall_score = quality_score.calculate_overall()

        # Evaluate quality gate
        quality_gate_status, quality_issues = self.review_strategy.evaluate_quality_gate(
            overall_score, self.quality_threshold
        )

        # Collect all issues
        all_issues = self.issue_collector.collect_all_issues(reviews)

        # Wait for PII detection
        pii_result = await pii_task

        # LLM enhancement if requested
        llm_enhanced = False
        if use_llm_enhancement and self.llm_adapter:
            try:
                await self._enhance_with_llm(document, reviews)
                llm_enhanced = True
            except Exception as e:
                logger.warning(f"LLM enhancement failed: {e}")

        # Create report
        return AnalysisReport(
            document_id=document.id,
            document_type=document.type,
            overall_score=overall_score,
            quality_gate_status=quality_gate_status,
            quality_score=quality_score,
            reviews=reviews,
            pii_detection=pii_result,
            quality_issues=quality_issues,
            all_issues=all_issues,
            execution_time=time.time() - start_time,
            llm_enhanced=llm_enhanced,
        )

    async def analyze_batch(
        self, documents: List[Document], max_concurrent: int = 5
    ) -> List[AnalysisReport]:
        """Analyze multiple documents in batch."""

        async def analyze_with_limit(doc, semaphore):
            async with semaphore:
                try:
                    return await self.analyze(doc)
                except Exception as e:
                    logger.error(f"Batch analysis failed for document {doc.id}: {e}")
                    return None

        semaphore = asyncio.Semaphore(max_concurrent)
        tasks = [analyze_with_limit(doc, semaphore) for doc in documents]
        results = await asyncio.gather(*tasks, return_exceptions=False)

        # Filter out None results
        reports = [r for r in results if r is not None]
        logger.info(f"Batch analysis completed: {len(reports)}/{len(documents)} successful")

        return reports

    async def _detect_pii(self, content: str) -> PIIDetectionResult:
        """Detect PII in document content."""
        start_time = time.time()

        try:
            detection_result = await self.pii_detector.detect(content)

            return PIIDetectionResult(
                pii_found=detection_result.get("pii_found", []),
                accuracy=detection_result.get("accuracy", 0.0),
                total_found=detection_result.get("total_found", 0),
                detection_time=time.time() - start_time,
            )
        except Exception as e:
            logger.error(f"PII detection failed: {e}")
            return PIIDetectionResult(detection_time=time.time() - start_time)

    def _validate_review_types(self, review_types: Optional[List[ReviewType]]) -> None:
        """Validate review types."""
        if review_types:
            for rt in review_types:
                if not isinstance(rt, ReviewType):
                    raise ValidationError(f"Invalid review type: {rt}")

    async def _enhance_with_llm(self, document: Document, reviews: Dict[ReviewType, ReviewResult]):
        """Enhance analysis with LLM insights."""
        if not self.llm_adapter:
            return

        try:
            prompt = f"""
            Analyze this document and provide insights:

            Document Type: {document.type}
            Current Reviews: {len(reviews)} completed

            Content Preview:
            {document.content[:500]}

            Provide additional insights not covered by automated analysis.
            """

            await self.llm_adapter.generate(prompt=prompt, max_tokens=500)

            logger.info("LLM enhancement completed")
        except Exception as e:
            logger.error(f"LLM enhancement failed: {e}")

    async def _save_results(self, report: AnalysisReport):
        """Save analysis results to storage."""
        if not self.storage:
            return

        try:
            analysis_doc = Document(
                id=f"analysis_{report.document_id}_{int(time.time())}",
                type="analysis_report",
                content=report.to_json(),
                metadata=DocumentMetadata(
                    tags=["analysis", "review", report.document_type],
                    version="1.0",
                    custom={
                        "created_at": report.timestamp.isoformat(),
                        "document_id": report.document_id,
                        "overall_score": report.overall_score,
                        "quality_gate": report.quality_gate_status,
                    },
                ),
            )

            if asyncio.iscoroutinefunction(self.storage.save_document):
                await self.storage.save_document(analysis_doc)
            else:
                self.storage.save_document(analysis_doc)

            logger.info(f"Analysis report saved for document {report.document_id}")
        except Exception as e:
            logger.error(f"Failed to save analysis report: {e}")

    def verify_report_signature(self, report: AnalysisReport) -> bool:
        """Verify report signature."""
        if not report.security_signature:
            return False
        return self.security_manager.verify_signature(report.to_json(), report.security_signature)

    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get current performance metrics."""
        metrics = self.performance_monitor.get_metrics()
        metrics["cache_info"] = self.cache_manager.get_stats()
        return metrics

    def clear_cache(self):
        """Clear all caches and reset statistics."""
        self.cache_manager.clear()
        logger.info("Cache cleared")

    def shutdown(self):
        """Clean shutdown of the review engine."""
        self.parallel_processor.shutdown()
        self.clear_cache()
        self.security_manager.save_audit_log()
        logger.info("Review engine shutdown complete")
