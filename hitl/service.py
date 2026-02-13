"""HITL service - business logic layer for human-in-the-loop reviews."""

from typing import List, Optional

from common.logging import get_logger
from hitl.models import (
    Review,
    ReviewCreate,
    ReviewDecision,
    ReviewQuery,
    ReviewResponse,
    ReviewStatus,
)
from hitl.repository import HITLRepository
from policy_engine.models import PolicyContext

logger = get_logger(__name__)


class HITLService:
    """Service for human-in-the-loop review management."""

    def __init__(self, repository: HITLRepository):
        """
        Initialize HITL service.
        
        Args:
            repository: HITLRepository instance for data access
        """
        self._repository = repository

    def escalate(
        self,
        request_id: str,
        context: PolicyContext,
        reason: str,
    ) -> str:
        """
        Escalate a request for human review (enqueue).
        
        This method provides the same interface as HITLStub for easy replacement.
        
        Args:
            request_id: Request identifier
            context: PolicyContext with full request/response context
            reason: Policy reason for escalation
            
        Returns:
            Review ID (string) for tracking
        """
        try:
            # Extract trace_id from context metadata
            trace_id = context.metadata.get("trace_id") if context.metadata else None
            
            # Convert PolicyContext to dict for storage
            context_data = context.model_dump()
            
            # Create review
            review_create = ReviewCreate(
                request_id=request_id,
                trace_id=trace_id,
                checkpoint=context.checkpoint,
                reason=reason,
                context_data=context_data,
                prompt=context.prompt,
                response=context.response,
                priority=0,  # Default priority (can be enhanced later)
                metadata={},
            )
            
            review = self._repository.create_review(review_create)
            
            logger.info(
                "hitl_review_created",
                review_id=review.id,
                request_id=request_id,
                trace_id=trace_id,
                checkpoint=context.checkpoint,
                reason=reason,
            )
            
            return str(review.id)
        except Exception as e:
            # Don't fail the main request if HITL escalation fails
            # Log the error but return a stub review ID
            logger.error(
                "hitl_escalation_failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            # Return a stub ID so the request can continue
            # In production, you might want to raise or handle differently
            return f"review_failed_{request_id}"

    def approve(
        self,
        review_id: int,
        reviewed_by: str,
        review_notes: Optional[str] = None,
    ) -> Review:
        """
        Approve a review.
        
        Args:
            review_id: Review ID
            reviewed_by: User ID who approved
            review_notes: Optional notes
            
        Returns:
            Updated Review model
        """
        try:
            review = self._repository.make_decision(
                review_id=review_id,
                decision=ReviewStatus.APPROVED,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
            )
            
            logger.info(
                "hitl_review_approved",
                review_id=review_id,
                reviewed_by=reviewed_by,
                request_id=review.request_id,
            )
            
            return review
        except Exception as e:
            logger.error(
                "hitl_review_approval_failed",
                review_id=review_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def reject(
        self,
        review_id: int,
        reviewed_by: str,
        review_notes: Optional[str] = None,
    ) -> Review:
        """
        Reject a review.
        
        Args:
            review_id: Review ID
            reviewed_by: User ID who rejected
            review_notes: Optional notes
            
        Returns:
            Updated Review model
        """
        try:
            review = self._repository.make_decision(
                review_id=review_id,
                decision=ReviewStatus.REJECTED,
                reviewed_by=reviewed_by,
                review_notes=review_notes,
            )
            
            logger.info(
                "hitl_review_rejected",
                review_id=review_id,
                reviewed_by=reviewed_by,
                request_id=review.request_id,
            )
            
            return review
        except Exception as e:
            logger.error(
                "hitl_review_rejection_failed",
                review_id=review_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_review(self, review_id: int) -> Optional[Review]:
        """
        Get a review by ID.
        
        Args:
            review_id: Review ID
            
        Returns:
            Review model or None if not found
        """
        return self._repository.get_review_by_id(review_id)

    def dequeue_review(
        self,
        assigned_to: str,
        lock_duration_seconds: int = 300,
        limit: int = 1,
    ) -> List[Review]:
        """
        Dequeue next pending review(s) for a reviewer.
        
        This is the core queue operation - safely picks up the next pending review
        without race conditions, even with multiple workers.
        
        Args:
            assigned_to: User ID to assign the review to
            lock_duration_seconds: How long to lock the review (default: 5 minutes)
            limit: Maximum number of reviews to dequeue (default: 1)
            
        Returns:
            List of Review models (empty if no pending reviews)
        """
        try:
            reviews = self._repository.dequeue_review(
                assigned_to=assigned_to,
                lock_duration_seconds=lock_duration_seconds,
                limit=limit,
            )
            
            if reviews:
                logger.info(
                    "hitl_reviews_dequeued",
                    count=len(reviews),
                    assigned_to=assigned_to,
                    review_ids=[r.id for r in reviews],
                )
            
            return reviews
        except Exception as e:
            logger.error(
                "hitl_review_dequeue_failed",
                assigned_to=assigned_to,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_reviews_by_request_id(self, request_id: str) -> List[Review]:
        """
        Get all reviews for a request.
        
        Args:
            request_id: Request identifier
            
        Returns:
            List of Review models
        """
        return self._repository.get_reviews_by_request_id(request_id)

    def get_reviews_by_trace_id(self, trace_id: str) -> List[Review]:
        """
        Get all reviews for a trace.
        
        Args:
            trace_id: Trace identifier
            
        Returns:
            List of Review models
        """
        return self._repository.get_reviews_by_trace_id(trace_id)

    def query_reviews(self, query: ReviewQuery) -> ReviewResponse:
        """
        Query reviews with filters.
        
        Args:
            query: ReviewQuery model with filters
            
        Returns:
            ReviewResponse with reviews and count
        """
        reviews = self._repository.query_reviews(
            status=query.status,
            request_id=query.request_id,
            trace_id=query.trace_id,
            checkpoint=query.checkpoint,
            assigned_to=query.assigned_to,
            start_time=query.start_time,
            end_time=query.end_time,
            limit=query.limit,
            offset=query.offset,
        )
        
        return ReviewResponse(
            reviews=reviews,
            count=len(reviews),
            total=len(reviews),  # TODO: Add total count query if needed for pagination
        )

    def check_approved_review(
        self,
        prompt: str,
        user_id: str,
        checkpoint: str,
        max_age_days: int = 7,
    ) -> Optional[Review]:
        """
        Check if there's an approved review that should bypass escalation.
        
        This implements the bypass logic: if a user has an approved review
        for the same prompt, checkpoint, and user, we can skip escalation.
        
        Args:
            prompt: User's prompt to check
            user_id: User identifier
            checkpoint: Checkpoint ('input' or 'output')
            max_age_days: Maximum age of approval in days (default: 7)
            
        Returns:
            Review if found, None otherwise
        """
        try:
            from datetime import datetime, timedelta
            from hitl.models import ReviewStatus

            # Calculate cutoff time
            cutoff_time = datetime.utcnow() - timedelta(days=max_age_days)

            # Query for approved reviews matching criteria
            reviews = self._repository.query_reviews(
                status=ReviewStatus.APPROVED,
                checkpoint=checkpoint,
                start_time=cutoff_time,
                limit=100,  # Reasonable limit
            )

            # Filter by exact prompt match and user_id
            for review in reviews:
                # Check prompt match (exact for v1)
                if review.prompt != prompt:
                    continue

                # Check user_id match (from context_data)
                review_user_id = review.context_data.get("user_id")
                if review_user_id != user_id:
                    continue

                # Found a match!
                logger.info(
                    "hitl_bypass_review_found",
                    review_id=review.id,
                    user_id=user_id,
                    checkpoint=checkpoint,
                    prompt_length=len(prompt),
                )
                return review

            # No matching approved review found
            return None
        except Exception as e:
            logger.error(
                "hitl_bypass_check_failed",
                user_id=user_id,
                checkpoint=checkpoint,
                error=str(e),
                error_type=type(e).__name__,
            )
            # On error, don't bypass (fail secure)
            return None

