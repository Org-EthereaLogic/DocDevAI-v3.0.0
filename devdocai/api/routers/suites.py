"""Document suite management endpoints."""

import logging
from typing import Optional

from fastapi import APIRouter, HTTPException, Query

from ...core.config import ConfigurationManager
from ...core.storage import StorageManager
from ...core.suite import SuiteManager
from ...core.tracking import TrackingMatrix
from ..models.suites import (
    CreateSuiteRequest,
    DependencyTrackingResponse,
    SuiteDetailResponse,
    SuiteListResponse,
    SuiteMetadata,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/suites", tags=["suites"])

# Singleton instances
_config_manager = None
_storage_manager = None
_suite_manager = None
_tracking_matrix = None


def get_managers():
    """Get or initialize manager instances."""
    global _config_manager, _storage_manager, _suite_manager, _tracking_matrix

    if _config_manager is None:
        try:
            _config_manager = ConfigurationManager()
            _storage_manager = StorageManager(_config_manager)
            _suite_manager = SuiteManager(_storage_manager)
            _tracking_matrix = TrackingMatrix(_storage_manager)
            logger.info("Suite managers initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize suite managers: {e}")
            raise

    return _config_manager, _storage_manager, _suite_manager, _tracking_matrix


@router.get("", response_model=SuiteListResponse)
async def list_suites(
    status: Optional[str] = Query(
        None, description="Filter by status", pattern="^(active|archived|draft)$"
    ),
    project_id: Optional[str] = Query(None, description="Filter by project"),
    limit: int = Query(50, description="Maximum number of suites", ge=1, le=200),
    offset: int = Query(0, description="Number of suites to skip", ge=0),
) -> SuiteListResponse:
    """
    List document suites with filtering and pagination.

    A suite is a collection of related documents that are managed together
    for consistency and completeness.
    """
    try:
        config, storage, suite_manager, tracking = get_managers()

        # Get all suites
        all_suites = suite_manager.list_suites()

        # Apply filters
        filtered_suites = all_suites

        if status:
            filtered_suites = [s for s in filtered_suites if s.get("status") == status]

        if project_id:
            filtered_suites = [s for s in filtered_suites if s.get("project_id") == project_id]

        # Sort by last modified (most recent first)
        filtered_suites.sort(
            key=lambda s: s.get("updated_at", s.get("created_at", "")), reverse=True
        )

        # Apply pagination
        total = len(filtered_suites)
        paginated = filtered_suites[offset : offset + limit]

        # Convert to response models
        suite_list = []
        for suite in paginated:
            # Get document count and types
            document_ids = suite.get("document_ids", [])
            documents = []
            for doc_id in document_ids:
                try:
                    doc = storage.get_document(doc_id)
                    if doc:
                        documents.append(doc)
                except Exception:
                    continue  # Skip missing documents

            doc_types = {}
            for doc in documents:
                doc_type = doc.get("type", "unknown")
                doc_types[doc_type] = doc_types.get(doc_type, 0) + 1

            # Calculate completion percentage
            total_docs = len(document_ids)
            completed_docs = len([d for d in documents if d.get("status") == "completed"])
            completion_percentage = (completed_docs / total_docs * 100) if total_docs > 0 else 0

            suite_metadata = SuiteMetadata(
                id=suite.get("id"),
                name=suite.get("name"),
                description=suite.get("description"),
                status=suite.get("status", "draft"),
                project_id=suite.get("project_id"),
                document_count=len(documents),
                document_types=doc_types,
                completion_percentage=round(completion_percentage, 1),
                created_at=suite.get("created_at"),
                updated_at=suite.get("updated_at"),
            )
            suite_list.append(suite_metadata)

        return SuiteListResponse(suites=suite_list, total=total, limit=limit, offset=offset)

    except Exception as e:
        logger.error(f"Error listing suites: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", response_model=SuiteDetailResponse)
async def create_suite(request: CreateSuiteRequest) -> SuiteDetailResponse:
    """
    Create a new document suite.

    A suite groups related documents for coordinated management,
    ensuring consistency and completeness across the documentation set.
    """
    try:
        config, storage, suite_manager, tracking = get_managers()

        # Validate document IDs if provided
        if request.document_ids:
            for doc_id in request.document_ids:
                doc = storage.get_document(doc_id)
                if not doc:
                    raise HTTPException(status_code=400, detail=f"Document '{doc_id}' not found")

        # Create suite
        suite_data = {
            "name": request.name,
            "description": request.description,
            "project_id": request.project_id,
            "document_ids": request.document_ids or [],
            "status": "draft",
            "consistency_rules": request.consistency_rules or {},
            "metadata": request.metadata or {},
        }

        result = suite_manager.create_suite(suite_data)

        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to create suite")
            )

        suite_id = result.get("suite_id")

        # Get the created suite for response
        suite = suite_manager.get_suite(suite_id)
        if not suite:
            raise HTTPException(status_code=500, detail="Failed to retrieve created suite")

        # Get documents in suite
        documents = []
        for doc_id in suite.get("document_ids", []):
            try:
                doc = storage.get_document(doc_id)
                if doc:
                    documents.append(
                        {
                            "id": doc.get("id"),
                            "title": doc.get("title", "Untitled"),
                            "type": doc.get("type", "unknown"),
                            "status": doc.get("status", "draft"),
                            "updated_at": doc.get("updated_at"),
                        }
                    )
            except Exception:
                continue

        # Calculate consistency score (placeholder - would use real analysis)
        consistency_score = 100.0  # New suite starts with perfect consistency

        return SuiteDetailResponse(
            id=suite.get("id"),
            name=suite.get("name"),
            description=suite.get("description"),
            status=suite.get("status"),
            project_id=suite.get("project_id"),
            documents=documents,
            consistency_rules=suite.get("consistency_rules", {}),
            consistency_score=consistency_score,
            metadata=suite.get("metadata", {}),
            created_at=suite.get("created_at"),
            updated_at=suite.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error creating suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{suite_id}", response_model=SuiteDetailResponse)
async def get_suite(suite_id: str) -> SuiteDetailResponse:
    """
    Get detailed information about a specific suite.

    Returns complete suite information including documents,
    consistency analysis, and dependency tracking.
    """
    try:
        config, storage, suite_manager, tracking = get_managers()

        # Get suite
        suite = suite_manager.get_suite(suite_id)
        if not suite:
            raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")

        # Get documents in suite
        documents = []
        for doc_id in suite.get("document_ids", []):
            try:
                doc = storage.get_document(doc_id)
                if doc:
                    documents.append(
                        {
                            "id": doc.get("id"),
                            "title": doc.get("title", "Untitled"),
                            "type": doc.get("type", "unknown"),
                            "status": doc.get("status", "draft"),
                            "updated_at": doc.get("updated_at"),
                            "quality_score": doc.get("quality_score", 0),
                        }
                    )
            except Exception:
                continue

        # Analyze consistency
        consistency_result = suite_manager.analyze_consistency(suite_id)
        consistency_score = (
            consistency_result.get("score", 0) if consistency_result.get("success") else 0
        )

        return SuiteDetailResponse(
            id=suite.get("id"),
            name=suite.get("name"),
            description=suite.get("description"),
            status=suite.get("status"),
            project_id=suite.get("project_id"),
            documents=documents,
            consistency_rules=suite.get("consistency_rules", {}),
            consistency_score=consistency_score,
            metadata=suite.get("metadata", {}),
            created_at=suite.get("created_at"),
            updated_at=suite.get("updated_at"),
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{suite_id}/tracking", response_model=DependencyTrackingResponse)
async def get_suite_tracking(suite_id: str) -> DependencyTrackingResponse:
    """
    Get dependency tracking information for a suite.

    Returns the dependency graph and impact analysis for all
    documents in the suite.
    """
    try:
        config, storage, suite_manager, tracking = get_managers()

        # Verify suite exists
        suite = suite_manager.get_suite(suite_id)
        if not suite:
            raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")

        document_ids = suite.get("document_ids", [])

        if not document_ids:
            return DependencyTrackingResponse(
                suite_id=suite_id,
                dependencies=[],
                impact_analysis={},
                circular_references=[],
                orphaned_documents=[],
                statistics={
                    "total_documents": 0,
                    "total_dependencies": 0,
                    "max_depth": 0,
                    "average_dependencies": 0.0,
                },
            )

        # Get dependency information for all documents in suite
        dependencies = []
        all_deps = set()

        for doc_id in document_ids:
            try:
                deps = tracking.get_dependencies(doc_id)
                if deps and deps.get("success"):
                    dep_info = deps.get("dependencies", {})
                    for target_id in dep_info.get("depends_on", []):
                        dependencies.append(
                            {"source": doc_id, "target": target_id, "type": "depends_on"}
                        )
                        all_deps.add((doc_id, target_id))

                    for target_id in dep_info.get("referenced_by", []):
                        dependencies.append(
                            {"source": target_id, "target": doc_id, "type": "references"}
                        )
                        all_deps.add((target_id, doc_id))
            except Exception:
                continue

        # Perform impact analysis for each document
        impact_analysis = {}
        for doc_id in document_ids:
            try:
                impact = tracking.analyze_impact(doc_id)
                if impact and impact.get("success"):
                    impact_analysis[doc_id] = {
                        "affected_documents": impact.get("affected_documents", []),
                        "impact_score": impact.get("impact_score", 0),
                        "critical_path": impact.get("critical_path", False),
                    }
            except Exception:
                impact_analysis[doc_id] = {
                    "affected_documents": [],
                    "impact_score": 0,
                    "critical_path": False,
                }

        # Detect circular references
        circular_refs = []
        try:
            graph_data = tracking.get_dependency_graph()
            if graph_data and graph_data.get("success"):
                circular_refs = graph_data.get("circular_references", [])
        except Exception:
            pass

        # Find orphaned documents (no dependencies)
        all_referenced = set()
        for dep in dependencies:
            all_referenced.add(dep["source"])
            all_referenced.add(dep["target"])

        orphaned = [doc_id for doc_id in document_ids if doc_id not in all_referenced]

        # Calculate statistics
        total_dependencies = len(all_deps)
        avg_deps = total_dependencies / len(document_ids) if document_ids else 0

        # Calculate max depth (simplified)
        max_depth = 0
        for doc_id in document_ids:
            depth = len([d for d in dependencies if d["source"] == doc_id])
            max_depth = max(max_depth, depth)

        return DependencyTrackingResponse(
            suite_id=suite_id,
            dependencies=dependencies,
            impact_analysis=impact_analysis,
            circular_references=circular_refs,
            orphaned_documents=orphaned,
            statistics={
                "total_documents": len(document_ids),
                "total_dependencies": total_dependencies,
                "max_depth": max_depth,
                "average_dependencies": round(avg_deps, 2),
            },
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting suite tracking: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{suite_id}")
async def update_suite(suite_id: str, request: CreateSuiteRequest) -> SuiteDetailResponse:
    """
    Update an existing suite.

    Updates suite metadata, document list, and consistency rules.
    """
    try:
        config, storage, suite_manager, tracking = get_managers()

        # Verify suite exists
        existing_suite = suite_manager.get_suite(suite_id)
        if not existing_suite:
            raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")

        # Validate document IDs if provided
        if request.document_ids:
            for doc_id in request.document_ids:
                doc = storage.get_document(doc_id)
                if not doc:
                    raise HTTPException(status_code=400, detail=f"Document '{doc_id}' not found")

        # Update suite
        update_data = {
            "name": request.name,
            "description": request.description,
            "project_id": request.project_id,
            "document_ids": request.document_ids or [],
            "consistency_rules": request.consistency_rules or {},
            "metadata": request.metadata or {},
        }

        result = suite_manager.update_suite(suite_id, update_data)

        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to update suite")
            )

        # Return updated suite details
        return await get_suite(suite_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{suite_id}")
async def delete_suite(suite_id: str) -> dict:
    """
    Delete a suite.

    Removes the suite but preserves all documents.
    Documents can be reassigned to other suites if needed.
    """
    try:
        config, storage, suite_manager, tracking = get_managers()

        # Verify suite exists
        suite = suite_manager.get_suite(suite_id)
        if not suite:
            raise HTTPException(status_code=404, detail=f"Suite '{suite_id}' not found")

        # Delete suite
        result = suite_manager.delete_suite(suite_id)

        if not result.get("success"):
            raise HTTPException(
                status_code=500, detail=result.get("error", "Failed to delete suite")
            )

        return {"success": True, "message": f"Suite '{suite_id}' deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting suite: {e}")
        raise HTTPException(status_code=500, detail=str(e))
