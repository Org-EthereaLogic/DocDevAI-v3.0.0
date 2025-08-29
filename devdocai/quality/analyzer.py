"""
Main quality analyzer for M005 Quality Engine.

Coordinates quality analysis across dimensions and integrates with other modules.
"""

import time
import logging
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
from functools import lru_cache
from pathlib import Path

from .models import (
    QualityConfig, QualityReport, DimensionScore, QualityDimension,
    AnalysisRequest, QualityIssue, SeverityLevel
)
from .scoring import QualityScorer, ScoringMetrics
from .dimensions import (
    CompletenessAnalyzer, ClarityAnalyzer, StructureAnalyzer,
    AccuracyAnalyzer, FormattingAnalyzer
)
from .validators import DocumentValidator, MarkdownValidator, CodeDocumentValidator
from .exceptions import (
    QualityEngineError, QualityGateFailure, IntegrationError,
    DimensionAnalysisError
)

# Import integration modules
try:
    from devdocai.core.config import ConfigurationManager
    CONFIG_AVAILABLE = True
except ImportError:
    CONFIG_AVAILABLE = False
    
try:
    from devdocai.storage.local_storage import LocalStorageSystem
    STORAGE_AVAILABLE = True
except ImportError:
    STORAGE_AVAILABLE = False
    
try:
    from devdocai.miair.engine_unified import UnifiedMIAIREngine, EngineMode
    MIAIR_AVAILABLE = True
except ImportError:
    MIAIR_AVAILABLE = False

logger = logging.getLogger(__name__)


class QualityAnalyzer:
    """
    Main quality analysis engine for DevDocAI.
    
    Coordinates quality assessment across multiple dimensions and
    integrates with other DevDocAI modules.
    """
    
    def __init__(
        self,
        config: Optional[QualityConfig] = None,
        config_manager: Optional[Any] = None,
        storage_system: Optional[Any] = None,
        miair_engine: Optional[Any] = None
    ):
        """
        Initialize quality analyzer.
        
        Args:
            config: Quality configuration
            config_manager: M001 Configuration Manager instance
            storage_system: M002 Storage System instance
            miair_engine: M003 MIAIR Engine instance
        """
        self.config = config or QualityConfig()
        self.scorer = QualityScorer(self.config)
        
        # Initialize dimension analyzers
        self.analyzers = {
            QualityDimension.COMPLETENESS: CompletenessAnalyzer(),
            QualityDimension.CLARITY: ClarityAnalyzer(),
            QualityDimension.STRUCTURE: StructureAnalyzer(),
            QualityDimension.ACCURACY: AccuracyAnalyzer(),
            QualityDimension.FORMATTING: FormattingAnalyzer()
        }
        
        # Initialize validators
        self.validators = {
            'markdown': MarkdownValidator(),
            'code': CodeDocumentValidator(),
            'default': DocumentValidator()
        }
        
        # Integration with other modules
        self.config_manager = config_manager
        self.storage_system = storage_system
        self.miair_engine = miair_engine
        
        # Cache for performance
        self._cache = {}
        self._cache_ttl = self.config.cache_ttl_seconds
        
        # Thread pool for parallel analysis
        self.executor = ThreadPoolExecutor(max_workers=self.config.max_workers)
        
        logger.info(f"QualityAnalyzer initialized with threshold: {self.config.quality_gate_threshold}%")
    
    def analyze(
        self,
        content: str,
        document_id: Optional[str] = None,
        document_type: str = "markdown",
        metadata: Optional[Dict] = None
    ) -> QualityReport:
        """
        Perform comprehensive quality analysis on document.
        
        Args:
            content: Document content to analyze
            document_id: Optional document identifier
            document_type: Type of document (markdown, code, etc.)
            metadata: Optional metadata about the document
            
        Returns:
            QualityReport with analysis results
            
        Raises:
            QualityGateFailure: If document fails quality gate
            QualityEngineError: For other analysis errors
        """
        start_time = time.time()
        document_id = document_id or self._generate_document_id(content)
        
        try:
            # Check cache
            if self.config.enable_caching:
                cached = self._get_cached_report(document_id)
                if cached:
                    logger.info(f"Using cached report for {document_id}")
                    return cached
            
            # Validate document first
            validation_results = self._validate_document(content, document_type)
            
            # Analyze each dimension
            dimension_scores = []
            
            if self.config.parallel_analysis:
                # Parallel analysis
                futures = []
                for dimension, analyzer in self.analyzers.items():
                    if dimension not in self.config.dimension_weights:
                        continue
                    if dimension in metadata.get('skip_dimensions', []) if metadata else False:
                        continue
                    
                    future = self.executor.submit(
                        self._analyze_dimension,
                        analyzer,
                        content,
                        metadata
                    )
                    futures.append((dimension, future))
                
                # Collect results
                for dimension, future in futures:
                    try:
                        score = future.result(timeout=30)
                        dimension_scores.append(score)
                    except Exception as e:
                        logger.error(f"Failed to analyze {dimension}: {e}")
                        # Add failed dimension with zero score
                        dimension_scores.append(DimensionScore(
                            dimension=dimension,
                            score=0.0,
                            issues=[QualityIssue(
                                dimension=dimension,
                                severity=SeverityLevel.CRITICAL,
                                description=f"Analysis failed: {str(e)}",
                                impact_score=10.0
                            )]
                        ))
            else:
                # Sequential analysis
                for dimension, analyzer in self.analyzers.items():
                    if dimension not in self.config.dimension_weights:
                        continue
                    if dimension in metadata.get('skip_dimensions', []) if metadata else False:
                        continue
                    
                    try:
                        score = self._analyze_dimension(analyzer, content, metadata)
                        dimension_scores.append(score)
                    except Exception as e:
                        logger.error(f"Failed to analyze {dimension}: {e}")
                        dimension_scores.append(DimensionScore(
                            dimension=dimension,
                            score=0.0,
                            issues=[QualityIssue(
                                dimension=dimension,
                                severity=SeverityLevel.CRITICAL,
                                description=f"Analysis failed: {str(e)}",
                                impact_score=10.0
                            )]
                        ))
            
            # Calculate overall score
            overall_score = self.scorer.calculate_overall_score(dimension_scores)
            
            # Add validation issues to formatting dimension
            if validation_results:
                formatting_score = next(
                    (ds for ds in dimension_scores if ds.dimension == QualityDimension.FORMATTING),
                    None
                )
                if formatting_score:
                    for result in validation_results:
                        if not result.get('passed', True):
                            for error in result.get('errors', []):
                                formatting_score.issues.append(QualityIssue(
                                    dimension=QualityDimension.FORMATTING,
                                    severity=SeverityLevel(result.get('severity', 'low')),
                                    description=error,
                                    impact_score=2.0
                                ))
            
            # Generate recommendations
            recommendations = self._generate_recommendations(dimension_scores)
            
            # Check quality gate
            gate_passed = overall_score >= self.config.quality_gate_threshold
            
            # Check for critical issues in strict mode
            if self.config.strict_mode:
                has_critical = any(
                    issue.severity == SeverityLevel.CRITICAL
                    for ds in dimension_scores
                    for issue in ds.issues
                )
                if has_critical:
                    gate_passed = False
            
            # Create report
            analysis_time = (time.time() - start_time) * 1000  # Convert to ms
            
            report = QualityReport(
                document_id=document_id,
                overall_score=overall_score,
                gate_passed=gate_passed,
                dimension_scores=dimension_scores,
                recommendations=recommendations,
                metadata={
                    'document_type': document_type,
                    'validation_results': validation_results,
                    'config': self.config.dict()
                },
                analysis_time_ms=analysis_time
            )
            
            # Cache report
            if self.config.enable_caching:
                self._cache_report(document_id, report)
            
            # Store in M002 if available
            if self.storage_system and STORAGE_AVAILABLE:
                self._store_report(report)
            
            # Raise exception if gate failed
            if not gate_passed:
                raise QualityGateFailure(
                    score=overall_score,
                    threshold=self.config.quality_gate_threshold,
                    dimensions={ds.dimension.value: ds.score for ds in dimension_scores}
                )
            
            logger.info(
                f"Analysis complete for {document_id}: "
                f"Score={overall_score:.1f}%, Gate={'PASSED' if gate_passed else 'FAILED'}, "
                f"Time={analysis_time:.1f}ms"
            )
            
            return report
            
        except QualityGateFailure:
            raise
        except Exception as e:
            logger.error(f"Quality analysis failed: {e}")
            raise QualityEngineError(f"Analysis failed: {str(e)}")
    
    async def analyze_async(
        self,
        content: str,
        document_id: Optional[str] = None,
        document_type: str = "markdown",
        metadata: Optional[Dict] = None
    ) -> QualityReport:
        """
        Async version of analyze method.
        
        Args:
            content: Document content to analyze
            document_id: Optional document identifier
            document_type: Type of document
            metadata: Optional metadata
            
        Returns:
            QualityReport with analysis results
        """
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.analyze,
            content,
            document_id,
            document_type,
            metadata
        )
    
    def analyze_with_miair(
        self,
        content: str,
        document_id: Optional[str] = None,
        use_optimization: bool = True
    ) -> QualityReport:
        """
        Analyze document using MIAIR engine integration.
        
        Args:
            content: Document content
            document_id: Document identifier
            use_optimization: Whether to use MIAIR optimization
            
        Returns:
            QualityReport with MIAIR-enhanced analysis
        """
        if not MIAIR_AVAILABLE or not self.miair_engine:
            logger.warning("MIAIR engine not available, using standard analysis")
            return self.analyze(content, document_id)
        
        try:
            # Get MIAIR analysis
            miair_mode = EngineMode.OPTIMIZED if use_optimization else EngineMode.BASE
            self.miair_engine.set_mode(miair_mode)
            
            miair_result = self.miair_engine.analyze_document(content)
            
            # Enhance metadata with MIAIR insights
            metadata = {
                'entropy_score': miair_result.get('entropy', 0),
                'pattern_score': miair_result.get('pattern_score', 0),
                'quality_metrics': miair_result.get('quality_metrics', {}),
                'miair_optimization': use_optimization
            }
            
            # Perform standard analysis with MIAIR metadata
            report = self.analyze(content, document_id, metadata=metadata)
            
            # Add MIAIR recommendations
            if 'recommendations' in miair_result:
                report.recommendations.extend(miair_result['recommendations'])
            
            return report
            
        except Exception as e:
            logger.error(f"MIAIR integration failed: {e}")
            raise IntegrationError("MIAIR", str(e))
    
    def batch_analyze(
        self,
        documents: List[Dict[str, Any]],
        parallel: bool = True
    ) -> List[QualityReport]:
        """
        Analyze multiple documents in batch.
        
        Args:
            documents: List of document dicts with 'content' and optional 'id', 'type'
            parallel: Whether to analyze in parallel
            
        Returns:
            List of QualityReports
        """
        reports = []
        
        if parallel and self.config.parallel_analysis:
            futures = []
            for doc in documents:
                future = self.executor.submit(
                    self.analyze,
                    doc['content'],
                    doc.get('id'),
                    doc.get('type', 'markdown'),
                    doc.get('metadata')
                )
                futures.append(future)
            
            for future in futures:
                try:
                    report = future.result(timeout=60)
                    reports.append(report)
                except Exception as e:
                    logger.error(f"Batch analysis failed for document: {e}")
        else:
            for doc in documents:
                try:
                    report = self.analyze(
                        doc['content'],
                        doc.get('id'),
                        doc.get('type', 'markdown'),
                        doc.get('metadata')
                    )
                    reports.append(report)
                except Exception as e:
                    logger.error(f"Batch analysis failed for document: {e}")
        
        return reports
    
    def _analyze_dimension(
        self,
        analyzer: Any,
        content: str,
        metadata: Optional[Dict]
    ) -> DimensionScore:
        """Analyze a single quality dimension."""
        return analyzer.analyze(content, metadata)
    
    def _validate_document(
        self,
        content: str,
        document_type: str
    ) -> List[Dict]:
        """Validate document using appropriate validator."""
        validator = self.validators.get(document_type, self.validators['default'])
        return validator.validate(content, document_type)
    
    def _generate_recommendations(
        self,
        dimension_scores: List[DimensionScore]
    ) -> List[str]:
        """Generate improvement recommendations based on analysis."""
        recommendations = []
        
        # Sort dimensions by score (lowest first)
        sorted_dims = sorted(dimension_scores, key=lambda x: x.score)
        
        for dim_score in sorted_dims[:3]:  # Focus on worst 3 dimensions
            if dim_score.score < 70:
                # Count issues by severity
                critical = sum(1 for i in dim_score.issues if i.severity == SeverityLevel.CRITICAL)
                high = sum(1 for i in dim_score.issues if i.severity == SeverityLevel.HIGH)
                
                if critical > 0:
                    recommendations.append(
                        f"CRITICAL: Fix {critical} critical {dim_score.dimension.value} issues immediately"
                    )
                if high > 0:
                    recommendations.append(
                        f"HIGH: Address {high} high-priority {dim_score.dimension.value} issues"
                    )
                
                # Add specific suggestions from issues
                for issue in dim_score.issues[:2]:  # Top 2 issues
                    if issue.suggestion:
                        recommendations.append(f"{dim_score.dimension.value.title()}: {issue.suggestion}")
        
        # Add general recommendations
        if not recommendations:
            recommendations.append("Document meets quality standards. Consider minor improvements.")
        
        return list(dict.fromkeys(recommendations))  # Remove duplicates
    
    def _generate_document_id(self, content: str) -> str:
        """Generate unique document ID from content."""
        import hashlib
        return hashlib.md5(content.encode()).hexdigest()[:12]
    
    def _get_cached_report(self, document_id: str) -> Optional[QualityReport]:
        """Get cached report if available and not expired."""
        if document_id in self._cache:
            cached_time, report = self._cache[document_id]
            if time.time() - cached_time < self._cache_ttl:
                return report
            else:
                del self._cache[document_id]
        return None
    
    def _cache_report(self, document_id: str, report: QualityReport):
        """Cache analysis report."""
        self._cache[document_id] = (time.time(), report)
        
        # Limit cache size
        if len(self._cache) > 100:
            # Remove oldest entries
            sorted_cache = sorted(self._cache.items(), key=lambda x: x[1][0])
            for key, _ in sorted_cache[:20]:
                del self._cache[key]
    
    def _store_report(self, report: QualityReport):
        """Store report in M002 storage system."""
        try:
            if self.storage_system:
                self.storage_system.create_document({
                    'id': f"quality_report_{report.document_id}",
                    'type': 'quality_report',
                    'content': report.dict(),
                    'timestamp': report.timestamp.isoformat()
                })
        except Exception as e:
            logger.warning(f"Failed to store report in M002: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get analyzer statistics."""
        return {
            'cache_size': len(self._cache),
            'quality_threshold': self.config.quality_gate_threshold,
            'parallel_analysis': self.config.parallel_analysis,
            'max_workers': self.config.max_workers,
            'dimensions': list(self.config.dimension_weights.keys()),
            'integrations': {
                'config_manager': CONFIG_AVAILABLE and self.config_manager is not None,
                'storage_system': STORAGE_AVAILABLE and self.storage_system is not None,
                'miair_engine': MIAIR_AVAILABLE and self.miair_engine is not None
            }
        }
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit - cleanup resources."""
        self.executor.shutdown(wait=False)
        self._cache.clear()