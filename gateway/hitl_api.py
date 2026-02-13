"""HITL review management API endpoints."""

import uuid

import structlog.contextvars
from common.logging import get_logger
from fastapi import APIRouter, Body, HTTPException, Query
from hitl.models import ReviewDecision, ReviewQuery, ReviewResponse
from hitl.service import HITLService

logger = get_logger(__name__)


def create_hitl_router(hitl_service: HITLService) -> APIRouter:
    """
    Create FastAPI router for HITL review management endpoints.
    
    Args:
        hitl_service: HITLService instance
        
    Returns:
        Configured APIRouter
    """
    router = APIRouter(prefix="/api/hitl", tags=["HITL"])

    @router.get("/reviews", response_model=ReviewResponse)
    async def list_reviews(
        status: str | None = Query(None, description="Filter by status"),
        request_id: str | None = Query(None, description="Filter by request ID"),
        trace_id: str | None = Query(None, description="Filter by trace ID"),
        checkpoint: str | None = Query(None, description="Filter by checkpoint"),
        assigned_to: str | None = Query(None, description="Filter by assigned reviewer"),
        limit: int | None = Query(None, ge=1, le=1000, description="Maximum results"),
        offset: int | None = Query(None, ge=0, description="Offset for pagination"),
    ):
        """
        List reviews with optional filters.
        """
        api_trace_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=api_trace_id)

        try:
            from datetime import datetime
            from hitl.models import ReviewStatus

            query = ReviewQuery(
                status=ReviewStatus(status) if status else None,
                request_id=request_id,
                trace_id=trace_id,  # Use the query parameter trace_id from user
                checkpoint=checkpoint,
                assigned_to=assigned_to,
                limit=limit,
                offset=offset,
            )

            result = hitl_service.query_reviews(query)

            logger.info(
                "hitl_reviews_listed",
                count=result.count,
                filters={
                    "status": status,
                    "request_id": request_id,
                    "checkpoint": checkpoint,
                },
            )

            return result
        except Exception as e:
            logger.error(
                "hitl_reviews_list_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            structlog.contextvars.clear_contextvars()

    @router.get("/reviews/{review_id}")
    async def get_review(review_id: int):
        """
        Get a specific review by ID.
        """
        trace_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        try:
            review = hitl_service.get_review(review_id)
            if not review:
                raise HTTPException(status_code=404, detail=f"Review {review_id} not found")

            logger.info("hitl_review_retrieved", review_id=review_id)
            return review
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "hitl_review_get_failed",
                review_id=review_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            structlog.contextvars.clear_contextvars()

    @router.post("/reviews/{review_id}/approve")
    async def approve_review(
        review_id: int,
        reviewed_by: str = Query(..., description="User ID of reviewer"),
        review_notes: str | None = Query(None, description="Optional notes explaining the approval"),
    ):
        """
        Approve a review.
        
        Query parameters:
        - reviewed_by: User ID of reviewer (required)
        - review_notes: Optional notes (optional)
        """
        trace_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        try:
            review = hitl_service.approve(
                review_id=review_id,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
            )

            logger.info(
                "hitl_review_approved_via_api",
                review_id=review_id,
                reviewed_by=reviewed_by,
            )

            return {
                "message": "Review approved successfully",
                "review": review,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "hitl_review_approval_failed",
                review_id=review_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            structlog.contextvars.clear_contextvars()

    @router.post("/reviews/{review_id}/reject")
    async def reject_review(
        review_id: int,
        reviewed_by: str = Query(..., description="User ID of reviewer"),
        review_notes: str | None = Query(None, description="Optional notes explaining the rejection"),
    ):
        """
        Reject a review.
        
        Query parameters:
        - reviewed_by: User ID of reviewer (required)
        - review_notes: Optional notes (optional)
        """
        trace_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        try:
            review = hitl_service.reject(
                review_id=review_id,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
            )

            logger.info(
                "hitl_review_rejected_via_api",
                review_id=review_id,
                reviewed_by=reviewed_by,
            )

            return {
                "message": "Review rejected successfully",
                "review": review,
            }
        except HTTPException:
            raise
        except Exception as e:
            logger.error(
                "hitl_review_rejection_failed",
                review_id=review_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            structlog.contextvars.clear_contextvars()

    @router.post("/reviews/dequeue")
    async def dequeue_review(
        assigned_to: str = Query(..., description="User ID to assign review to"),
        limit: int = Query(1, ge=1, le=10, description="Number of reviews to dequeue"),
    ):
        """
        Dequeue next pending review(s) from the queue.
        
        This is the core queue operation - safely picks up the next pending review
        without race conditions, even with multiple workers.
        """
        trace_id = str(uuid.uuid4())
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)

        try:
            reviews = hitl_service.dequeue_review(
                assigned_to=assigned_to,
                limit=limit,
            )

            logger.info(
                "hitl_reviews_dequeued_via_api",
                count=len(reviews),
                assigned_to=assigned_to,
            )

            return {
                "message": f"Dequeued {len(reviews)} review(s)",
                "reviews": reviews,
            }
        except Exception as e:
            logger.error(
                "hitl_review_dequeue_failed",
                assigned_to=assigned_to,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise HTTPException(status_code=500, detail=str(e))
        finally:
            structlog.contextvars.clear_contextvars()

    return router

