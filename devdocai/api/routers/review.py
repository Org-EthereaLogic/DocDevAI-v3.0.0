"""Document review and quality endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ...core.config import ConfigurationManager
from ...core.review import ReviewEngine
from ...core.storage import StorageManager
from ..models.review import DocumentQualityResponse, DocumentReviewResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["review"])

# Singleton instances
_config_manager = None
_storage_manager = None
_review_engine = None


def get_managers():
    """Get or initialize manager instances."""
    global _config_manager, _storage_manager, _review_engine

    if _config_manager is None:
        try:
            _config_manager = ConfigurationManager()
            _storage_manager = StorageManager(_config_manager)
            _review_engine = ReviewEngine(_config_manager, _storage_manager)
            logger.info("Review managers initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize review managers: {e}")
            raise

    return _config_manager, _storage_manager, _review_engine


@router.get("/{document_id}/review", response_model=DocumentReviewResponse)
async def get_document_review(
    document_id: str,
    include_details: bool = Query(True, description="Include detailed review findings"),
    reviewer_types: Optional[str] = Query(
        None, description="Comma-separated list of reviewer types to run", regex="^[a-zA-Z_,]+$"
    ),
) -> DocumentReviewResponse:
    """
    Get comprehensive review analysis for a document.

    Performs multi-dimensional analysis including:
    - Content quality and clarity
    - Structure and organization
    - Technical accuracy
    - Completeness
    - PII detection
    - Style consistency
    """
    try:
        config, storage, review_engine = get_managers()

        # Get document
        document = storage.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

        # Parse reviewer types if specified
        selected_reviewers = None
        if reviewer_types:
            selected_reviewers = [r.strip() for r in reviewer_types.split(",")]

        # Perform review
        logger.info(f"Starting review for document: {document_id}")
        review_result = review_engine.review_document(document_id, reviewers=selected_reviewers)

        if not review_result.get("success"):
            raise HTTPException(status_code=500, detail=review_result.get("error", "Review failed"))

        review_data = review_result.get("review", {})

        # Extract review findings
        findings = []
        recommendations = []

        if include_details:
            # Collect findings from all reviewers
            for reviewer_name, results in review_data.get("reviewers", {}).items():
                if results.get("findings"):
                    for finding in results["findings"]:
                        findings.append(
                            {
                                "reviewer": reviewer_name,
                                "type": finding.get("type", "info"),
                                "severity": finding.get("severity", "low"),
                                "message": finding.get("message", ""),
                                "location": finding.get("location"),
                                "suggestion": finding.get("suggestion"),
                            }
                        )

                if results.get("recommendations"):
                    for rec in results["recommendations"]:
                        recommendations.append(
                            {
                                "reviewer": reviewer_name,
                                "category": rec.get("category", "general"),
                                "priority": rec.get("priority", "medium"),
                                "action": rec.get("action", ""),
                                "rationale": rec.get("rationale", ""),
                            }
                        )

        # Extract scores by category
        scores = review_data.get("scores", {})
        category_scores = {}

        for reviewer_name, results in review_data.get("reviewers", {}).items():
            if results.get("score") is not None:
                category_scores[reviewer_name] = results["score"]

        # Get PII detection results
        pii_detected = []
        pii_reviewer = review_data.get("reviewers", {}).get("pii_detector", {})
        if pii_reviewer.get("findings"):
            for finding in pii_reviewer["findings"]:
                if finding.get("type") == "pii":
                    pii_detected.append(
                        {
                            "type": finding.get("pii_type", "unknown"),
                            "location": finding.get("location"),
                            "confidence": finding.get("confidence", 0.0),
                            "masked_value": finding.get("masked_value"),
                        }
                    )

        return DocumentReviewResponse(
            document_id=document_id,
            overall_score=review_data.get("overall_score", 0.0),
            quality_gate_passed=review_data.get("quality_gate_passed", False),
            category_scores=category_scores,
            findings=findings,
            recommendations=recommendations,
            pii_detected=pii_detected,
            review_metadata={
                "reviewers_used": list(review_data.get("reviewers", {}).keys()),
                "review_duration": review_data.get("duration", 0.0),
                "word_count": review_data.get("word_count", 0),
                "readability_score": review_data.get("readability_score"),
            },
            reviewed_at=review_result.get("timestamp"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reviewing document: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{document_id}/quality", response_model=DocumentQualityResponse)
async def get_document_quality(
    document_id: str,
    calculate_trends: bool = Query(False, description="Include quality trends over time"),
) -> DocumentQualityResponse:
    """
    Get quality metrics and analysis for a document.

    Provides focused quality assessment including scores,
    metrics, and improvement opportunities.
    """
    try:
        config, storage, review_engine = get_managers()

        # Get document
        document = storage.get_document(document_id)
        if not document:
            raise HTTPException(status_code=404, detail=f"Document '{document_id}' not found")

        # Get quality analysis
        logger.info(f"Analyzing quality for document: {document_id}")
        quality_result = review_engine.analyze_quality(document_id)

        if not quality_result.get("success"):
            raise HTTPException(
                status_code=500, detail=quality_result.get("error", "Quality analysis failed")
            )

        quality_data = quality_result.get("quality", {})

        # Calculate quality metrics
        metrics = {
            "readability_score": quality_data.get("readability_score", 0.0),
            "completeness_score": quality_data.get("completeness_score", 0.0),
            "accuracy_score": quality_data.get("accuracy_score", 0.0),
            "consistency_score": quality_data.get("consistency_score", 0.0),
            "structure_score": quality_data.get("structure_score", 0.0),
        }

        # Determine quality status
        overall_score = quality_data.get("overall_score", 0.0)
        if overall_score >= 90:
            status = "excellent"
        elif overall_score >= 80:
            status = "good"
        elif overall_score >= 70:
            status = "acceptable"
        elif overall_score >= 60:
            status = "needs_improvement"
        else:
            status = "poor"

        # Generate improvement suggestions
        improvement_areas = []
        if metrics["readability_score"] < 70:
            improvement_areas.append(
                {
                    "area": "readability",
                    "current_score": metrics["readability_score"],
                    "target_score": 80,
                    "suggestions": [
                        "Simplify complex sentences",
                        "Use more common vocabulary",
                        "Break up long paragraphs",
                    ],
                }
            )

        if metrics["completeness_score"] < 80:
            improvement_areas.append(
                {
                    "area": "completeness",
                    "current_score": metrics["completeness_score"],
                    "target_score": 90,
                    "suggestions": [
                        "Add missing sections",
                        "Include more examples",
                        "Provide additional context",
                    ],
                }
            )

        if metrics["structure_score"] < 75:
            improvement_areas.append(
                {
                    "area": "structure",
                    "current_score": metrics["structure_score"],
                    "target_score": 85,
                    "suggestions": [
                        "Improve heading hierarchy",
                        "Add table of contents",
                        "Reorganize content flow",
                    ],
                }
            )

        # Get quality trends if requested
        quality_trends = []
        if calculate_trends:
            try:
                # Get historical quality data (simplified - would use real historical analysis)
                history = storage.get_document_history(document_id)
                if history and history.get("success"):
                    versions = history.get("versions", [])
                    for version in versions[-10:]:  # Last 10 versions
                        if version.get("quality_score"):
                            quality_trends.append(
                                {
                                    "timestamp": version.get("timestamp"),
                                    "score": version.get("quality_score"),
                                    "version": version.get("version", "unknown"),
                                }
                            )
            except Exception as e:
                logger.warning(f"Could not calculate quality trends: {e}")

        # Calculate target scores for improvement
        target_scores = {}
        for metric, score in metrics.items():
            if score < 80:
                target_scores[metric] = min(100, score + 20)  # Aim for +20 points
            else:
                target_scores[metric] = min(100, score + 10)  # Aim for +10 points

        return DocumentQualityResponse(
            document_id=document_id,
            overall_score=overall_score,
            status=status,
            metrics=metrics,
            improvement_areas=improvement_areas,
            target_scores=target_scores,
            quality_trends=quality_trends,
            benchmark_comparison={
                "industry_average": 75.0,
                "project_average": quality_data.get("project_average", 70.0),
                "best_in_project": quality_data.get("best_in_project", 85.0),
            },
            last_review_date=document.get("last_reviewed"),
            estimated_improvement_time=len(improvement_areas) * 30,  # 30 minutes per area
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error analyzing document quality: {e}")
        raise HTTPException(status_code=500, detail=str(e))
