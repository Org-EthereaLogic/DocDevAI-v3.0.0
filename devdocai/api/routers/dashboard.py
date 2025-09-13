"""Dashboard and statistics endpoints."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List

from fastapi import APIRouter, HTTPException, Query

from ...core.config import ConfigurationManager
from ...core.storage import StorageManager
from ...core.tracking import TrackingMatrix
from ..models.dashboard import (
    DashboardStatsResponse,
    ProjectHealthResponse,
    ProjectListResponse,
    ProjectSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["dashboard"])

# Singleton instances
_config_manager = None
_storage_manager = None
_tracking_matrix = None


def get_managers():
    """Get or initialize manager instances."""
    global _config_manager, _storage_manager, _tracking_matrix

    if _config_manager is None:
        try:
            _config_manager = ConfigurationManager()
            _storage_manager = StorageManager(_config_manager)
            _tracking_matrix = TrackingMatrix(_storage_manager)
            logger.info("Dashboard managers initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize dashboard managers: {e}")
            raise

    return _config_manager, _storage_manager, _tracking_matrix


@router.get("/dashboard/stats", response_model=DashboardStatsResponse)
async def get_dashboard_stats(
    days: int = Query(30, description="Number of days for statistics", ge=1, le=365)
) -> DashboardStatsResponse:
    """
    Get overall dashboard statistics.

    Returns metrics about document generation, quality scores,
    and system usage over the specified time period.
    """
    try:
        config, storage, tracking = get_managers()

        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)

        # Get document statistics from storage
        all_docs = storage.list_documents()
        recent_docs = []
        for doc in all_docs:
            created_str = doc.get("created_at")
            if created_str:
                try:
                    created_date = datetime.fromisoformat(created_str.replace("Z", "+00:00"))
                    if created_date >= start_date:
                        recent_docs.append(doc)
                except (ValueError, TypeError):
                    continue

        # Calculate statistics
        total_documents = len(all_docs)
        recent_documents = len(recent_docs)

        # Document type distribution
        doc_types = {}
        for doc in all_docs:
            doc_type = doc.get("type", "unknown")
            doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

        # Average quality score (if available)
        quality_scores = [
            doc.get("quality_score", 0) for doc in all_docs if doc.get("quality_score")
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.0

        # Get dependency tracking stats
        dependency_count = 0
        try:
            graph = tracking.get_dependency_graph()
            if graph:
                dependency_count = len(graph.get("edges", []))
        except Exception as e:
            logger.warning(f"Could not get dependency stats: {e}")

        # Build response
        return DashboardStatsResponse(
            total_documents=total_documents,
            recent_documents=recent_documents,
            average_quality_score=round(avg_quality, 2),
            document_types=doc_types,
            total_dependencies=dependency_count,
            time_period_days=days,
            generated_today=sum(
                1
                for doc in all_docs
                if doc.get("created_at")
                and datetime.fromisoformat(doc.get("created_at")).date() == datetime.now().date()
            ),
            active_projects=len(set(doc.get("project_id", "default") for doc in all_docs)),
        )

    except Exception as e:
        logger.error(f"Error getting dashboard stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects", response_model=ProjectListResponse)
async def list_projects(
    limit: int = Query(100, description="Maximum number of projects", ge=1, le=1000),
    offset: int = Query(0, description="Number of projects to skip", ge=0),
) -> ProjectListResponse:
    """
    List all projects with document counts and basic information.

    Projects are identified by unique project_id in documents.
    """
    try:
        config, storage, tracking = get_managers()

        # Get all documents and group by project
        all_docs = storage.list_documents()
        projects_map: Dict[str, List] = {}

        for doc in all_docs:
            project_id = doc.get("project_id", "default")
            if project_id not in projects_map:
                projects_map[project_id] = []
            projects_map[project_id].append(doc)

        # Build project summaries
        project_summaries = []
        for project_id, docs in projects_map.items():
            # Calculate project metrics
            doc_types = {}
            for doc in docs:
                doc_type = doc.get("type", "unknown")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

            # Get latest update time
            update_times = []
            for doc in docs:
                update_str = doc.get("updated_at") or doc.get("created_at")
                if update_str:
                    try:
                        update_time = datetime.fromisoformat(update_str.replace("Z", "+00:00"))
                        update_times.append(update_time)
                    except (ValueError, TypeError):
                        continue
            last_updated = max(update_times) if update_times else None

            # Calculate health score (simple heuristic)
            has_readme = "readme" in doc_types
            has_api_doc = "api_doc" in doc_types
            has_changelog = "changelog" in doc_types
            completeness = sum([has_readme, has_api_doc, has_changelog]) / 3

            quality_scores = [
                doc.get("quality_score", 0) for doc in docs if doc.get("quality_score")
            ]
            avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.5

            health_score = round((completeness * 0.6 + avg_quality * 0.4) * 100, 1)

            project_summaries.append(
                ProjectSummary(
                    project_id=project_id,
                    name=project_id.replace("_", " ").title(),
                    document_count=len(docs),
                    document_types=doc_types,
                    last_updated=last_updated,
                    health_score=health_score,
                )
            )

        # Sort by last updated (most recent first)
        project_summaries.sort(key=lambda p: p.last_updated or datetime.min, reverse=True)

        # Apply pagination
        paginated = project_summaries[offset : offset + limit]

        return ProjectListResponse(
            projects=paginated, total=len(project_summaries), limit=limit, offset=offset
        )

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/projects/{project_id}/health", response_model=ProjectHealthResponse)
async def get_project_health(project_id: str) -> ProjectHealthResponse:
    """
    Get detailed health score and metrics for a specific project.

    Health score is calculated based on:
    - Documentation completeness
    - Document quality scores
    - Update frequency
    - Dependency tracking
    """
    try:
        config, storage, tracking = get_managers()

        # Get project documents
        all_docs = storage.list_documents()
        project_docs = [doc for doc in all_docs if doc.get("project_id", "default") == project_id]

        if not project_docs:
            raise HTTPException(status_code=404, detail=f"Project '{project_id}' not found")

        # Calculate completeness metrics
        doc_types = set(doc.get("type") for doc in project_docs)
        essential_docs = {"readme", "api_doc", "changelog"}
        missing_docs = list(essential_docs - doc_types)
        completeness_score = len(doc_types & essential_docs) / len(essential_docs) * 100

        # Calculate quality metrics
        quality_scores = [
            doc.get("quality_score", 0) for doc in project_docs if doc.get("quality_score")
        ]
        avg_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 50.0

        # Calculate update frequency
        update_times = []
        for doc in project_docs:
            update_str = doc.get("updated_at") or doc.get("created_at")
            if update_str:
                try:
                    update_time = datetime.fromisoformat(update_str.replace("Z", "+00:00"))
                    update_times.append(update_time)
                except (ValueError, TypeError):
                    continue

        if len(update_times) >= 2:
            update_times.sort()
            deltas = [
                (update_times[i + 1] - update_times[i]).days for i in range(len(update_times) - 1)
            ]
            avg_update_frequency = sum(deltas) / len(deltas)
        else:
            avg_update_frequency = 30  # Default to monthly

        # Freshness score (0-100 based on last update)
        if update_times:
            days_since_update = (datetime.now() - max(update_times)).days
            freshness_score = max(0, 100 - (days_since_update * 2))  # -2 points per day
        else:
            freshness_score = 0

        # Get dependency health
        dependency_issues = []
        try:
            for doc in project_docs:
                if doc.get("id"):
                    deps = tracking.get_dependencies(doc["id"])
                    if deps and deps.get("missing_dependencies"):
                        dependency_issues.extend(deps["missing_dependencies"])
        except Exception as e:
            logger.warning(f"Could not check dependencies: {e}")

        dependency_score = (
            100 if not dependency_issues else max(0, 100 - len(dependency_issues) * 10)
        )

        # Calculate overall health score
        health_score = round(
            completeness_score * 0.3
            + avg_quality * 0.3
            + freshness_score * 0.2
            + dependency_score * 0.2,
            1,
        )

        # Determine health status
        if health_score >= 80:
            status = "healthy"
        elif health_score >= 60:
            status = "needs_attention"
        else:
            status = "critical"

        # Build recommendations
        recommendations = []
        if missing_docs:
            recommendations.append(f"Add missing documentation: {', '.join(missing_docs)}")
        if avg_quality < 70:
            recommendations.append("Improve document quality scores through review and enhancement")
        if freshness_score < 50:
            recommendations.append("Update documentation - content may be outdated")
        if dependency_issues:
            recommendations.append(f"Fix {len(dependency_issues)} dependency issues")

        return ProjectHealthResponse(
            project_id=project_id,
            health_score=health_score,
            status=status,
            metrics={
                "completeness_score": round(completeness_score, 1),
                "quality_score": round(avg_quality, 1),
                "freshness_score": round(freshness_score, 1),
                "dependency_score": round(dependency_score, 1),
            },
            document_count=len(project_docs),
            last_updated=max(update_times) if update_times else None,
            missing_documents=missing_docs,
            recommendations=recommendations,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting project health: {e}")
        raise HTTPException(status_code=500, detail=str(e))
