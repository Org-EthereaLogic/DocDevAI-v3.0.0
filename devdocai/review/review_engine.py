"""
M007 Review Engine - Main implementation.

Provides multi-dimensional document review with integration to M001-M006 modules.
Orchestrates review dimensions, manages caching, and generates comprehensive reports.
"""

import asyncio
import hashlib
import json
import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set, Tuple
from functools import lru_cache
from pathlib import Path

from ..core.config import ConfigurationManager  # M001
from ..storage.local_storage import LocalStorageSystem  # M002
from ..storage.pii_detector import PIIDetector  # M002
from ..miair.engine_unified import UnifiedMIAIREngine  # M003
from ..quality.analyzer_unified import UnifiedQualityAnalyzer  # M005
from ..templates.registry_unified import UnifiedTemplateRegistry  # M006

from .models import (
    ReviewResult,
    ReviewStatus,
    ReviewEngineConfig,
    ReviewDimension,
    ReviewSeverity,
    ReviewIssue,
    DimensionResult,
    ReviewMetrics
)
from .dimensions import (
    BaseDimension,
    TechnicalAccuracyDimension,
    CompletenessDimension,
    ConsistencyDimension,
    StyleFormattingDimension,
    SecurityPIIDimension,
    get_default_dimensions
)

logger = logging.getLogger(__name__)


class ReviewCache:
    """Simple in-memory cache for review results."""
    
    def __init__(self, ttl_seconds: int = 3600):
        """Initialize cache with TTL."""
        self.cache: Dict[str, Tuple[ReviewResult, datetime]] = {}
        self.ttl_seconds = ttl_seconds
    
    def get(self, key: str) -> Optional[ReviewResult]:
        """Get cached result if not expired."""
        if key in self.cache:
            result, timestamp = self.cache[key]
            if datetime.now() - timestamp < timedelta(seconds=self.ttl_seconds):
                return result
            else:
                del self.cache[key]
        return None
    
    def set(self, key: str, result: ReviewResult) -> None:
        """Cache a review result."""
        self.cache[key] = (result, datetime.now())
    
    def clear(self) -> None:
        """Clear all cached results."""
        self.cache.clear()
    
    def remove_expired(self) -> None:
        """Remove expired entries."""
        now = datetime.now()
        expired = [
            key for key, (_, timestamp) in self.cache.items()
            if now - timestamp >= timedelta(seconds=self.ttl_seconds)
        ]
        for key in expired:
            del self.cache[key]


class ReviewEngine:
    """
    Main review engine for M007.
    
    Orchestrates multi-dimensional document review with integration
    to all existing modules (M001-M006) and provides comprehensive
    analysis and reporting capabilities.
    """
    
    def __init__(self, config: Optional[ReviewEngineConfig] = None):
        """
        Initialize review engine with configuration.
        
        Args:
            config: Optional review engine configuration
        """
        self.config = config or ReviewEngineConfig()
        
        # Initialize module integrations
        self._init_integrations()
        
        # Initialize dimensions
        self.dimensions = self._init_dimensions()
        
        # Initialize cache if enabled
        self.cache = ReviewCache(self.config.cache_ttl_seconds) if self.config.enable_caching else None
        
        # Thread pool for parallel analysis
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers) if self.config.parallel_analysis else None
        
        # Statistics
        self.reviews_performed = 0
        self.total_issues_found = 0
        self.cache_hits = 0
        self.cache_misses = 0
    
    def _init_integrations(self) -> None:
        """Initialize integrations with M001-M006 modules."""
        try:
            # M001 - Configuration Manager
            self.config_manager = ConfigurationManager()
            logger.info("Initialized M001 Configuration Manager integration")
        except Exception as e:
            logger.warning(f"M001 Configuration Manager not available: {e}")
            self.config_manager = None
        
        try:
            # M002 - Local Storage System
            self.storage = LocalStorageSystem()
            logger.info("Initialized M002 Local Storage integration")
        except Exception as e:
            logger.warning(f"M002 Local Storage not available: {e}")
            self.storage = None
        
        try:
            # M003 - MIAIR Engine
            if self.config.use_miair_optimization:
                self.miair_engine = UnifiedMIAIREngine()
                logger.info("Initialized M003 MIAIR Engine integration")
            else:
                self.miair_engine = None
        except Exception as e:
            logger.warning(f"M003 MIAIR Engine not available: {e}")
            self.miair_engine = None
        
        try:
            # M005 - Quality Engine
            if self.config.use_quality_engine:
                self.quality_analyzer = UnifiedQualityAnalyzer()
                logger.info("Initialized M005 Quality Analyzer integration")
            else:
                self.quality_analyzer = None
        except Exception as e:
            logger.warning(f"M005 Quality Analyzer not available: {e}")
            self.quality_analyzer = None
        
        try:
            # M006 - Template Registry
            self.template_registry = UnifiedTemplateRegistry()
            logger.info("Initialized M006 Template Registry integration")
        except Exception as e:
            logger.warning(f"M006 Template Registry not available: {e}")
            self.template_registry = None
    
    def _init_dimensions(self) -> List[BaseDimension]:
        """Initialize review dimensions based on configuration."""
        # Filter enabled dimensions
        enabled = self.config.enabled_dimensions
        weights = self.config.dimension_weights
        
        dimensions = []
        
        if ReviewDimension.TECHNICAL_ACCURACY in enabled:
            dimensions.append(TechnicalAccuracyDimension(
                weight=weights.get(ReviewDimension.TECHNICAL_ACCURACY, 0.25)
            ))
        
        if ReviewDimension.COMPLETENESS in enabled:
            dimensions.append(CompletenessDimension(
                weight=weights.get(ReviewDimension.COMPLETENESS, 0.20)
            ))
        
        if ReviewDimension.CONSISTENCY in enabled:
            dimensions.append(ConsistencyDimension(
                weight=weights.get(ReviewDimension.CONSISTENCY, 0.20)
            ))
        
        if ReviewDimension.STYLE_FORMATTING in enabled:
            dimensions.append(StyleFormattingDimension(
                weight=weights.get(ReviewDimension.STYLE_FORMATTING, 0.15)
            ))
        
        if ReviewDimension.SECURITY_PII in enabled:
            dimensions.append(SecurityPIIDimension(
                weight=weights.get(ReviewDimension.SECURITY_PII, 0.20)
            ))
        
        return dimensions
    
    async def review_document(
        self,
        content: str,
        document_id: Optional[str] = None,
        document_type: str = "generic",
        metadata: Optional[Dict[str, Any]] = None
    ) -> ReviewResult:
        """
        Perform comprehensive review of a document.
        
        Args:
            content: Document content to review
            document_id: Optional document identifier
            document_type: Type of document (readme, api, guide, etc.)
            metadata: Additional metadata for review context
            
        Returns:
            ReviewResult with comprehensive analysis
        """
        start_time = time.time()
        
        # Generate document ID if not provided
        if not document_id:
            document_id = self._generate_document_id(content)
        
        # Check cache if enabled
        cache_key = f"{document_id}:{document_type}:{hashlib.md5(content.encode()).hexdigest()}"
        if self.cache:
            cached = self.cache.get(cache_key)
            if cached:
                self.cache_hits += 1
                logger.info(f"Cache hit for document {document_id}")
                return cached
            self.cache_misses += 1
        
        # Prepare metadata
        if metadata is None:
            metadata = {}
        metadata['document_type'] = document_type
        metadata['document_id'] = document_id
        metadata['review_timestamp'] = datetime.now().isoformat()
        
        # Run dimension analyses
        dimension_results = await self._analyze_dimensions(content, metadata)
        
        # Aggregate results
        all_issues = []
        for dim_result in dimension_results:
            all_issues.extend(dim_result.issues)
        
        # Calculate overall score
        overall_score = self._calculate_overall_score(dimension_results)
        
        # Determine status
        status = self._determine_status(overall_score, all_issues)
        
        # Get recommendations
        recommended_actions = self._generate_recommendations(all_issues, dimension_results)
        approval_conditions = self._generate_approval_conditions(status, all_issues)
        
        # Run quality analysis if enabled
        quality_insights = None
        if self.quality_analyzer and self.config.use_quality_engine:
            try:
                quality_result = await self.quality_analyzer.analyze(content)
                quality_insights = {
                    'quality_score': quality_result.overall_score,
                    'quality_issues': len(quality_result.issues)
                }
            except Exception as e:
                logger.warning(f"Quality analysis failed: {e}")
        
        # Run MIAIR optimization if enabled
        optimization_suggestions = None
        if self.miair_engine and self.config.use_miair_optimization:
            try:
                miair_result = self.miair_engine.analyze(content)
                optimization_suggestions = {
                    'entropy_score': miair_result['entropy'],
                    'quality_score': miair_result['quality_score'],
                    'optimizations': miair_result.get('patterns', [])[:3]  # Top 3 suggestions
                }
            except Exception as e:
                logger.warning(f"MIAIR optimization failed: {e}")
        
        # Create review result
        execution_time = (time.time() - start_time) * 1000  # Convert to ms
        
        result = ReviewResult(
            document_id=document_id,
            document_type=document_type,
            review_id=str(uuid.uuid4()),
            timestamp=datetime.now(),
            overall_score=overall_score,
            status=status,
            dimension_results=dimension_results,
            all_issues=all_issues,
            metrics=ReviewMetrics(
                execution_time_ms=execution_time
            ),
            reviewer_notes=self._generate_reviewer_notes(all_issues, overall_score),
            recommended_actions=recommended_actions,
            approval_conditions=approval_conditions,
            configuration=self.config.to_dict(),
            metadata={
                **metadata,
                'quality_insights': quality_insights,
                'optimization_suggestions': optimization_suggestions,
                'execution_time_ms': execution_time
            }
        )
        
        # Cache result if enabled
        if self.cache:
            self.cache.set(cache_key, result)
        
        # Store in local storage if available
        if self.storage:
            await self._store_review_result(result)
        
        # Update statistics
        self.reviews_performed += 1
        self.total_issues_found += len(all_issues)
        
        logger.info(f"Review completed for {document_id}: Score={overall_score:.1f}, Status={status.value}, Issues={len(all_issues)}")
        
        return result
    
    async def _analyze_dimensions(
        self,
        content: str,
        metadata: Dict[str, Any]
    ) -> List[DimensionResult]:
        """
        Analyze document across all enabled dimensions.
        
        Args:
            content: Document content
            metadata: Document metadata
            
        Returns:
            List of dimension results
        """
        if self.config.parallel_analysis and self.executor:
            # Parallel execution
            futures = []
            for dimension in self.dimensions:
                future = self.executor.submit(
                    asyncio.run,
                    dimension.analyze(content, metadata)
                )
                futures.append((dimension, future))
            
            results = []
            for dimension, future in futures:
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Dimension {dimension.__class__.__name__} failed: {e}")
                    # Create error result
                    results.append(DimensionResult(
                        dimension=dimension.dimension,
                        score=0.0,
                        weight=dimension.weight,
                        issues=[self._create_error_issue(dimension.dimension, str(e))],
                        passed_checks=0,
                        total_checks=1
                    ))
        else:
            # Sequential execution
            results = []
            for dimension in self.dimensions:
                try:
                    result = await dimension.analyze(content, metadata)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Dimension {dimension.__class__.__name__} failed: {e}")
                    # Create error result
                    results.append(DimensionResult(
                        dimension=dimension.dimension,
                        score=0.0,
                        weight=dimension.weight,
                        issues=[self._create_error_issue(dimension.dimension, str(e))],
                        passed_checks=0,
                        total_checks=1
                    ))
        
        return results
    
    def _calculate_overall_score(self, dimension_results: List[DimensionResult]) -> float:
        """
        Calculate weighted overall score from dimension results.
        
        Args:
            dimension_results: List of dimension results
            
        Returns:
            Overall score between 0 and 100
        """
        if not dimension_results:
            return 0.0
        
        total_weighted_score = 0.0
        total_weight = 0.0
        
        for result in dimension_results:
            total_weighted_score += result.weighted_score
            total_weight += result.weight
        
        if total_weight == 0:
            return 0.0
        
        # Normalize if weights don't sum to 1.0
        return (total_weighted_score / total_weight) * 100.0 if total_weight != 1.0 else total_weighted_score
    
    def _determine_status(self, overall_score: float, issues: List[ReviewIssue]) -> ReviewStatus:
        """
        Determine review status based on score and issues.
        
        Args:
            overall_score: Overall review score
            issues: List of all issues found
            
        Returns:
            Review status
        """
        # Check for blockers in strict mode
        has_blockers = any(issue.severity == ReviewSeverity.BLOCKER for issue in issues)
        
        if self.config.strict_mode and has_blockers:
            return ReviewStatus.REJECTED
        
        # Check for critical issues
        critical_count = sum(1 for issue in issues 
                           if issue.severity in [ReviewSeverity.BLOCKER, ReviewSeverity.CRITICAL])
        
        # Determine status based on score and issues
        if overall_score >= self.config.approval_threshold:
            if critical_count == 0:
                return ReviewStatus.APPROVED
            else:
                return ReviewStatus.APPROVED_WITH_CONDITIONS
        elif overall_score >= self.config.conditional_approval_threshold:
            if critical_count <= 2:  # Allow up to 2 critical issues for conditional approval
                return ReviewStatus.APPROVED_WITH_CONDITIONS
            else:
                return ReviewStatus.NEEDS_REVISION
        else:
            if has_blockers or critical_count > 5:
                return ReviewStatus.REJECTED
            else:
                return ReviewStatus.NEEDS_REVISION
    
    def _generate_recommendations(
        self,
        issues: List[ReviewIssue],
        dimension_results: List[DimensionResult]
    ) -> List[str]:
        """
        Generate actionable recommendations based on review results.
        
        Args:
            issues: All issues found
            dimension_results: Results from each dimension
            
        Returns:
            List of recommended actions
        """
        recommendations = []
        
        # Priority 1: Address blockers
        blockers = [issue for issue in issues if issue.severity == ReviewSeverity.BLOCKER]
        if blockers:
            recommendations.append(f"URGENT: Fix {len(blockers)} blocker issues before proceeding")
        
        # Priority 2: Address critical issues
        criticals = [issue for issue in issues if issue.severity == ReviewSeverity.CRITICAL]
        if criticals:
            recommendations.append(f"Address {len(criticals)} critical issues for approval")
        
        # Priority 3: Improve low-scoring dimensions
        for result in dimension_results:
            if result.score < 60:
                recommendations.append(
                    f"Improve {result.dimension.value} (current score: {result.score:.1f}/100)"
                )
        
        # Priority 4: Auto-fixable issues
        auto_fixable = [issue for issue in issues if issue.auto_fixable]
        if auto_fixable and self.config.auto_fix_enabled:
            recommendations.append(f"Auto-fix available for {len(auto_fixable)} issues")
        
        # Priority 5: Dimension-specific recommendations
        for result in dimension_results:
            if result.dimension == ReviewDimension.SECURITY_PII and result.metrics.get('pii_found', 0) > 0:
                recommendations.append("Remove or mask all PII before publishing")
            elif result.dimension == ReviewDimension.COMPLETENESS and result.metrics.get('todo_count', 0) > 0:
                recommendations.append("Complete all TODO items and placeholders")
            elif result.dimension == ReviewDimension.TECHNICAL_ACCURACY and result.metrics.get('syntax_errors', 0) > 0:
                recommendations.append("Fix syntax errors in code examples")
        
        # Limit to top 10 recommendations
        return recommendations[:10] if recommendations else ["Document meets review standards"]
    
    def _generate_approval_conditions(
        self,
        status: ReviewStatus,
        issues: List[ReviewIssue]
    ) -> List[str]:
        """
        Generate conditions for approval if status is conditional.
        
        Args:
            status: Current review status
            issues: All issues found
            
        Returns:
            List of approval conditions
        """
        if status == ReviewStatus.APPROVED:
            return []
        
        conditions = []
        
        if status == ReviewStatus.APPROVED_WITH_CONDITIONS:
            # Must fix critical issues
            criticals = [issue for issue in issues if issue.severity == ReviewSeverity.CRITICAL]
            if criticals:
                conditions.append(f"Fix {len(criticals)} critical issues")
            
            # Must address high-priority issues
            high_priority = [issue for issue in issues if issue.severity == ReviewSeverity.HIGH]
            if len(high_priority) > 5:
                conditions.append(f"Address at least {len(high_priority) - 5} high-priority issues")
        
        elif status in [ReviewStatus.NEEDS_REVISION, ReviewStatus.REJECTED]:
            # Must fix all blockers
            blockers = [issue for issue in issues if issue.severity == ReviewSeverity.BLOCKER]
            if blockers:
                conditions.append(f"Fix all {len(blockers)} blocker issues")
            
            # Must fix all critical issues
            criticals = [issue for issue in issues if issue.severity == ReviewSeverity.CRITICAL]
            if criticals:
                conditions.append(f"Fix all {len(criticals)} critical issues")
            
            # Must improve overall score
            conditions.append(f"Improve overall score to at least {self.config.conditional_approval_threshold:.0f}")
        
        return conditions
    
    def _generate_reviewer_notes(self, issues: List[ReviewIssue], overall_score: float) -> str:
        """
        Generate human-readable reviewer notes.
        
        Args:
            issues: All issues found
            overall_score: Overall review score
            
        Returns:
            Reviewer notes string
        """
        notes = []
        
        # Overall assessment
        if overall_score >= 90:
            notes.append("Excellent document quality with minor improvements needed.")
        elif overall_score >= 80:
            notes.append("Good document quality with some areas for improvement.")
        elif overall_score >= 70:
            notes.append("Acceptable document quality but significant improvements recommended.")
        else:
            notes.append("Document requires substantial revision before approval.")
        
        # Issue summary
        issue_summary = {}
        for issue in issues:
            dim = issue.dimension.value
            if dim not in issue_summary:
                issue_summary[dim] = 0
            issue_summary[dim] += 1
        
        if issue_summary:
            notes.append("Main areas of concern: " + 
                        ", ".join(f"{dim} ({count} issues)" 
                                for dim, count in sorted(issue_summary.items(), 
                                                        key=lambda x: x[1], 
                                                        reverse=True)[:3]))
        
        # Auto-fix availability
        auto_fixable = sum(1 for issue in issues if issue.auto_fixable)
        if auto_fixable > 0:
            notes.append(f"{auto_fixable} issues can be automatically fixed.")
        
        return " ".join(notes)
    
    def _create_error_issue(self, dimension: ReviewDimension, error_message: str) -> ReviewIssue:
        """Create an error issue for dimension analysis failure."""
        return ReviewIssue(
            dimension=dimension,
            severity=ReviewSeverity.HIGH,
            title="Dimension analysis failed",
            description=f"Failed to analyze {dimension.value}: {error_message}",
            impact_score=8.0,
            confidence=1.0,
            auto_fixable=False
        )
    
    def _generate_document_id(self, content: str) -> str:
        """Generate a unique document ID based on content."""
        content_hash = hashlib.md5(content.encode()).hexdigest()[:8]
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"doc_{timestamp}_{content_hash}"
    
    async def _store_review_result(self, result: ReviewResult) -> None:
        """
        Store review result in local storage.
        
        Args:
            result: Review result to store
        """
        if not self.storage:
            return
        
        try:
            # Store as JSON document
            document = {
                'id': result.review_id,
                'type': 'review_result',
                'document_id': result.document_id,
                'timestamp': result.timestamp.isoformat(),
                'data': result.to_dict()
            }
            
            await self.storage.create(
                collection='review_results',
                document=document
            )
            
            logger.info(f"Stored review result {result.review_id} in local storage")
        except Exception as e:
            logger.error(f"Failed to store review result: {e}")
    
    async def batch_review(
        self,
        documents: List[Dict[str, Any]],
        parallel: bool = True
    ) -> List[ReviewResult]:
        """
        Review multiple documents in batch.
        
        Args:
            documents: List of document dictionaries with 'content', 'id', 'type'
            parallel: Whether to process in parallel
            
        Returns:
            List of review results
        """
        if parallel and self.executor:
            futures = []
            for doc in documents:
                future = self.executor.submit(
                    asyncio.run,
                    self.review_document(
                        content=doc['content'],
                        document_id=doc.get('id'),
                        document_type=doc.get('type', 'generic'),
                        metadata=doc.get('metadata')
                    )
                )
                futures.append(future)
            
            results = []
            for future in as_completed(futures):
                try:
                    result = future.result(timeout=self.config.timeout_seconds)
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch review failed for document: {e}")
            
            return results
        else:
            results = []
            for doc in documents:
                try:
                    result = await self.review_document(
                        content=doc['content'],
                        document_id=doc.get('id'),
                        document_type=doc.get('type', 'generic'),
                        metadata=doc.get('metadata')
                    )
                    results.append(result)
                except Exception as e:
                    logger.error(f"Batch review failed for document: {e}")
            
            return results
    
    async def auto_fix_issues(
        self,
        content: str,
        issues: List[ReviewIssue]
    ) -> Tuple[str, List[ReviewIssue]]:
        """
        Attempt to automatically fix issues in content.
        
        Args:
            content: Original content
            issues: Issues to fix
            
        Returns:
            Tuple of (fixed_content, fixed_issues)
        """
        if not self.config.auto_fix_enabled:
            return content, []
        
        fixed_content = content
        fixed_issues = []
        
        # Sort issues by location to apply fixes in order
        auto_fixable = [issue for issue in issues if issue.auto_fixable]
        
        for issue in auto_fixable:
            try:
                # Apply fixes based on issue type and dimension
                if issue.dimension == ReviewDimension.STYLE_FORMATTING:
                    # Fix formatting issues
                    if "trailing whitespace" in issue.title.lower():
                        lines = fixed_content.split('\n')
                        fixed_content = '\n'.join(line.rstrip() for line in lines)
                        fixed_issues.append(issue)
                    elif "excessive blank lines" in issue.title.lower():
                        import re
                        fixed_content = re.sub(r'\n{3,}', '\n\n', fixed_content)
                        fixed_issues.append(issue)
                
                elif issue.dimension == ReviewDimension.CONSISTENCY:
                    # Fix terminology consistency
                    if "terminology" in issue.title.lower():
                        # Example: standardize common terms
                        replacements = {
                            r'\bapi\b': 'API',
                            r'\burl\b': 'URL',
                            r'\bjson\b': 'JSON',
                        }
                        import re
                        for pattern, replacement in replacements.items():
                            fixed_content = re.sub(pattern, replacement, fixed_content, flags=re.IGNORECASE)
                        fixed_issues.append(issue)
                
                elif issue.dimension == ReviewDimension.SECURITY_PII:
                    # Mask PII
                    if "pii" in issue.title.lower() and self.config.mask_pii_in_reports:
                        # Use PIIDetector to mask
                        detector = PIIDetector()
                        fixed_content = detector.mask(fixed_content)
                        fixed_issues.append(issue)
                
            except Exception as e:
                logger.warning(f"Failed to auto-fix issue: {e}")
        
        logger.info(f"Auto-fixed {len(fixed_issues)} out of {len(auto_fixable)} fixable issues")
        
        return fixed_content, fixed_issues
    
    def generate_report(
        self,
        result: ReviewResult,
        format: str = "markdown"
    ) -> str:
        """
        Generate a formatted review report.
        
        Args:
            result: Review result
            format: Output format (markdown, html, json)
            
        Returns:
            Formatted report string
        """
        if format == "json":
            return json.dumps(result.to_dict(), indent=2)
        elif format == "markdown":
            return self._generate_markdown_report(result)
        elif format == "html":
            return self._generate_html_report(result)
        else:
            return result.to_summary()
    
    def _generate_markdown_report(self, result: ReviewResult) -> str:
        """Generate markdown format review report."""
        lines = [
            f"# Document Review Report",
            f"",
            f"**Document ID:** {result.document_id}",
            f"**Document Type:** {result.document_type}",
            f"**Review ID:** {result.review_id}",
            f"**Timestamp:** {result.timestamp.isoformat()}",
            f"",
            f"## Overall Assessment",
            f"",
            f"- **Status:** {result.status.value.upper()}",
            f"- **Overall Score:** {result.overall_score:.1f}/100",
            f"- **Total Issues:** {result.metrics.total_issues}",
            f"- **Execution Time:** {result.metrics.execution_time_ms:.1f}ms",
            f"",
            f"## Dimension Scores",
            f""
        ]
        
        for dim_result in result.dimension_results:
            lines.append(f"### {dim_result.dimension.value.replace('_', ' ').title()}")
            lines.append(f"- Score: {dim_result.score:.1f}/100 (Weight: {dim_result.weight:.2f})")
            lines.append(f"- Checks: {dim_result.passed_checks}/{dim_result.total_checks} passed")
            lines.append(f"- Issues: {len(dim_result.issues)}")
            
            if dim_result.issues:
                lines.append(f"")
                lines.append(f"#### Issues:")
                for issue in dim_result.issues[:5]:  # Show top 5 issues
                    lines.append(f"- **[{issue.severity.value.upper()}]** {issue.title}")
                    if issue.suggestion:
                        lines.append(f"  - Suggestion: {issue.suggestion}")
            lines.append("")
        
        if result.recommended_actions:
            lines.append(f"## Recommended Actions")
            lines.append("")
            for i, action in enumerate(result.recommended_actions, 1):
                lines.append(f"{i}. {action}")
            lines.append("")
        
        if result.approval_conditions:
            lines.append(f"## Approval Conditions")
            lines.append("")
            for i, condition in enumerate(result.approval_conditions, 1):
                lines.append(f"{i}. {condition}")
            lines.append("")
        
        if result.reviewer_notes:
            lines.append(f"## Reviewer Notes")
            lines.append("")
            lines.append(result.reviewer_notes)
            lines.append("")
        
        lines.append(f"## Issue Summary by Severity")
        lines.append("")
        for severity, count in result.metrics.issues_by_severity.items():
            if count > 0:
                lines.append(f"- {severity.upper()}: {count}")
        
        return "\n".join(lines)
    
    def _generate_html_report(self, result: ReviewResult) -> str:
        """Generate HTML format review report."""
        # Use template if available
        if self.template_registry:
            try:
                template = self.template_registry.get_template('review_report')
                return template.render(result=result)
            except Exception as e:
                logger.warning(f"Failed to use template for HTML report: {e}")
        
        # Fallback to basic HTML
        html = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Review Report - {result.document_id}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                h1 {{ color: #333; }}
                h2 {{ color: #666; border-bottom: 1px solid #ccc; }}
                .status {{ padding: 5px 10px; border-radius: 3px; font-weight: bold; }}
                .approved {{ background: #d4edda; color: #155724; }}
                .needs-revision {{ background: #fff3cd; color: #856404; }}
                .rejected {{ background: #f8d7da; color: #721c24; }}
                .score {{ font-size: 24px; font-weight: bold; }}
                .issue {{ margin: 10px 0; padding: 10px; border-left: 3px solid; }}
                .blocker {{ border-color: #dc3545; background: #f8d7da; }}
                .critical {{ border-color: #fd7e14; background: #fff3cd; }}
                .high {{ border-color: #ffc107; background: #fff3cd; }}
                .medium {{ border-color: #28a745; background: #d4edda; }}
                .low {{ border-color: #17a2b8; background: #d1ecf1; }}
                .info {{ border-color: #6c757d; background: #e2e3e5; }}
            </style>
        </head>
        <body>
            <h1>Document Review Report</h1>
            
            <div>
                <strong>Document ID:</strong> {result.document_id}<br>
                <strong>Review ID:</strong> {result.review_id}<br>
                <strong>Timestamp:</strong> {result.timestamp.isoformat()}<br>
            </div>
            
            <h2>Overall Assessment</h2>
            <div class="status {result.status.value}">{result.status.value.upper()}</div>
            <div class="score">{result.overall_score:.1f}/100</div>
            
            <h2>Issues by Severity</h2>
            <ul>
        """
        
        for severity, count in result.metrics.issues_by_severity.items():
            if count > 0:
                html += f"<li>{severity.upper()}: {count}</li>"
        
        html += """
            </ul>
            
            <h2>Top Issues</h2>
        """
        
        for issue in result.all_issues[:10]:
            html += f"""
            <div class="issue {issue.severity.value}">
                <strong>[{issue.severity.value.upper()}]</strong> {issue.title}<br>
                {issue.description}<br>
                {f'<em>Suggestion: {issue.suggestion}</em>' if issue.suggestion else ''}
            </div>
            """
        
        html += """
        </body>
        </html>
        """
        
        return html
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get review engine statistics."""
        return {
            'reviews_performed': self.reviews_performed,
            'total_issues_found': self.total_issues_found,
            'average_issues_per_review': (
                self.total_issues_found / self.reviews_performed 
                if self.reviews_performed > 0 else 0
            ),
            'cache_hits': self.cache_hits,
            'cache_misses': self.cache_misses,
            'cache_hit_rate': (
                self.cache_hits / (self.cache_hits + self.cache_misses) * 100
                if (self.cache_hits + self.cache_misses) > 0 else 0
            ),
            'enabled_dimensions': [dim.value for dim in self.config.enabled_dimensions],
            'configuration': self.config.to_dict()
        }
    
    def clear_cache(self) -> None:
        """Clear the review cache."""
        if self.cache:
            self.cache.clear()
            logger.info("Review cache cleared")
    
    def shutdown(self) -> None:
        """Shutdown the review engine and cleanup resources."""
        if self.executor:
            self.executor.shutdown(wait=True)
        
        if self.cache:
            self.cache.clear()
        
        logger.info("Review engine shutdown complete")