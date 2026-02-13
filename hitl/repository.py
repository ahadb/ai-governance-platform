"""Repository for HITL reviews - raw SQL data access layer with queue support."""

import json
from datetime import datetime, timedelta
from typing import List, Optional

import psycopg2.extras

from audit.db import AuditDB
from common.logging import get_logger
from hitl.models import Review, ReviewCreate, ReviewStatus, ReviewUpdate

logger = get_logger(__name__)


class HITLRepository:
    """Repository for HITL review storage and queue operations."""

    def __init__(self, db: AuditDB):
        """
        Initialize HITL repository.
        
        Args:
            db: AuditDB instance for database connections
        """
        self._db = db

    def create_review(self, review_create: ReviewCreate) -> Review:
        """
        Create a new review (enqueue).
        
        Args:
            review_create: ReviewCreate model with review data
            
        Returns:
            Created Review model
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    INSERT INTO hitl_reviews 
                        (request_id, trace_id, checkpoint, reason, context_data, 
                         prompt, response, priority, expires_at, metadata, status)
                    VALUES 
                        (%s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s::jsonb, 'pending')
                    RETURNING 
                        id, request_id, trace_id, checkpoint, reason, context_data,
                        prompt, response, status, priority, assigned_to, locked_until,
                        reviewed_by, review_notes, decision_timestamp, created_at,
                        assigned_at, expires_at, metadata
                    """,
                    (
                        review_create.request_id,
                        review_create.trace_id,
                        review_create.checkpoint,
                        review_create.reason,
                        json.dumps(review_create.context_data),
                        review_create.prompt,
                        review_create.response,
                        review_create.priority,
                        review_create.expires_at,
                        json.dumps(review_create.metadata),
                    ),
                )
                row = cursor.fetchone()
                return Review(**row)
        except Exception as e:
            logger.error(
                "hitl_review_create_failed",
                request_id=review_create.request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def dequeue_review(
        self,
        assigned_to: str,
        lock_duration_seconds: int = 300,
        limit: int = 1,
    ) -> List[Review]:
        """
        Dequeue next pending review(s) using SELECT FOR UPDATE SKIP LOCKED.
        
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
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Use SELECT FOR UPDATE SKIP LOCKED to safely dequeue
                    # This prevents race conditions with multiple workers
                    locked_until = datetime.utcnow() + timedelta(seconds=lock_duration_seconds)
                    
                    cursor.execute(
                        """
                        UPDATE hitl_reviews
                        SET 
                            status = 'assigned',
                            assigned_to = %s,
                            assigned_at = NOW(),
                            locked_until = %s
                        WHERE id IN (
                            SELECT id
                            FROM hitl_reviews
                            WHERE status = 'pending'
                                AND (expires_at IS NULL OR expires_at > NOW())
                            ORDER BY priority DESC, created_at ASC
                            LIMIT %s
                            FOR UPDATE SKIP LOCKED
                        )
                        RETURNING 
                            id, request_id, trace_id, checkpoint, reason, context_data,
                            prompt, response, status, priority, assigned_to, locked_until,
                            reviewed_by, review_notes, decision_timestamp, created_at,
                            assigned_at, expires_at, metadata
                        """,
                        (assigned_to, locked_until, limit),
                    )
                    rows = cursor.fetchall()
                    conn.commit()
                    return [Review(**row) for row in rows]
        except Exception as e:
            logger.error(
                "hitl_review_dequeue_failed",
                assigned_to=assigned_to,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_review_by_id(self, review_id: int) -> Optional[Review]:
        """
        Get a review by ID.
        
        Args:
            review_id: Review ID
            
        Returns:
            Review model or None if not found
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    SELECT 
                        id, request_id, trace_id, checkpoint, reason, context_data,
                        prompt, response, status, priority, assigned_to, locked_until,
                        reviewed_by, review_notes, decision_timestamp, created_at,
                        assigned_at, expires_at, metadata
                    FROM hitl_reviews
                    WHERE id = %s
                    """,
                    (review_id,),
                )
                row = cursor.fetchone()
                return Review(**row) if row else None
        except Exception as e:
            logger.error(
                "hitl_review_get_failed",
                review_id=review_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def update_review(self, review_id: int, review_update: ReviewUpdate) -> Review:
        """
        Update a review (status, assignment, notes, etc.).
        
        Args:
            review_id: Review ID
            review_update: ReviewUpdate model with changes
            
        Returns:
            Updated Review model
        """
        try:
            with self._db.get_connection() as conn:
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    # Build dynamic UPDATE query
                    updates = []
                    params = []
                    
                    if review_update.status:
                        updates.append("status = %s")
                        # Handle both enum and string (due to use_enum_values=True)
                        status_value = (
                            review_update.status.value
                            if isinstance(review_update.status, ReviewStatus)
                            else str(review_update.status)
                        )
                        params.append(status_value)
                        # Set decision_timestamp if approving/rejecting
                        status_enum = (
                            review_update.status
                            if isinstance(review_update.status, ReviewStatus)
                            else ReviewStatus(review_update.status)
                        )
                        if status_enum in [ReviewStatus.APPROVED, ReviewStatus.REJECTED]:
                            updates.append("decision_timestamp = NOW()")
                    
                    if review_update.assigned_to is not None:
                        updates.append("assigned_to = %s")
                        params.append(review_update.assigned_to)
                        if review_update.assigned_to:
                            updates.append("assigned_at = NOW()")
                        else:
                            updates.append("assigned_at = NULL")
                    
                    if review_update.review_notes is not None:
                        updates.append("review_notes = %s")
                        params.append(review_update.review_notes)
                    
                    if review_update.metadata is not None:
                        updates.append("metadata = %s::jsonb")
                        params.append(json.dumps(review_update.metadata))
                    
                    if not updates:
                        # No updates, just return current review
                        return self.get_review_by_id(review_id)
                    
                    params.append(review_id)
                    query = f"""
                        UPDATE hitl_reviews
                        SET {', '.join(updates)}
                        WHERE id = %s
                        RETURNING 
                            id, request_id, trace_id, checkpoint, reason, context_data,
                            prompt, response, status, priority, assigned_to, locked_until,
                            reviewed_by, review_notes, decision_timestamp, created_at,
                            assigned_at, expires_at, metadata
                    """
                    cursor.execute(query, tuple(params))
                    row = cursor.fetchone()
                    conn.commit()
                    return Review(**row) if row else None
        except Exception as e:
            logger.error(
                "hitl_review_update_failed",
                review_id=review_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def make_decision(
        self,
        review_id: int,
        decision: ReviewStatus,
        reviewed_by: str,
        review_notes: Optional[str] = None,
    ) -> Review:
        """
        Make a review decision (approve/reject).
        
        Args:
            review_id: Review ID
            decision: ReviewStatus.APPROVED or ReviewStatus.REJECTED
            reviewed_by: User ID who made the decision
            review_notes: Optional notes explaining the decision
            
        Returns:
            Updated Review model
        """
        if decision not in [ReviewStatus.APPROVED, ReviewStatus.REJECTED]:
            raise ValueError(f"Decision must be APPROVED or REJECTED, got {decision}")
        
        review_update = ReviewUpdate(
            status=decision,
            review_notes=review_notes,
        )
        review = self.update_review(review_id, review_update)
        
        # Update reviewed_by separately
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    UPDATE hitl_reviews
                    SET reviewed_by = %s
                    WHERE id = %s
                    RETURNING 
                        id, request_id, trace_id, checkpoint, reason, context_data,
                        prompt, response, status, priority, assigned_to, locked_until,
                        reviewed_by, review_notes, decision_timestamp, created_at,
                        assigned_at, expires_at, metadata
                    """,
                    (reviewed_by, review_id),
                )
                row = cursor.fetchone()
                return Review(**row) if row else review
        except Exception as e:
            logger.error(
                "hitl_review_decision_failed",
                review_id=review_id,
                decision=decision.value,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_reviews_by_request_id(self, request_id: str) -> List[Review]:
        """
        Get all reviews for a given request_id.
        
        Args:
            request_id: Request identifier
            
        Returns:
            List of Review models
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    SELECT 
                        id, request_id, trace_id, checkpoint, reason, context_data,
                        prompt, response, status, priority, assigned_to, locked_until,
                        reviewed_by, review_notes, decision_timestamp, created_at,
                        assigned_at, expires_at, metadata
                    FROM hitl_reviews
                    WHERE request_id = %s
                    ORDER BY created_at DESC
                    """,
                    (request_id,),
                )
                rows = cursor.fetchall()
                return [Review(**row) for row in rows]
        except Exception as e:
            logger.error(
                "hitl_reviews_query_failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_reviews_by_trace_id(self, trace_id: str) -> List[Review]:
        """
        Get all reviews for a given trace_id.
        
        Args:
            trace_id: Trace identifier
            
        Returns:
            List of Review models
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    SELECT 
                        id, request_id, trace_id, checkpoint, reason, context_data,
                        prompt, response, status, priority, assigned_to, locked_until,
                        reviewed_by, review_notes, decision_timestamp, created_at,
                        assigned_at, expires_at, metadata
                    FROM hitl_reviews
                    WHERE trace_id = %s
                    ORDER BY created_at DESC
                    """,
                    (trace_id,),
                )
                rows = cursor.fetchall()
                return [Review(**row) for row in rows]
        except Exception as e:
            logger.error(
                "hitl_reviews_query_failed",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def query_reviews(
        self,
        status: Optional[ReviewStatus] = None,
        request_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        checkpoint: Optional[str] = None,
        assigned_to: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> List[Review]:
        """
        Query reviews with various filters.
        
        Args:
            status: Filter by status
            request_id: Filter by request ID
            trace_id: Filter by trace ID
            checkpoint: Filter by checkpoint
            assigned_to: Filter by assigned reviewer
            start_time: Start time filter
            end_time: End time filter
            limit: Maximum number of results
            offset: Offset for pagination
            
        Returns:
            List of Review models
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                query = """
                    SELECT 
                        id, request_id, trace_id, checkpoint, reason, context_data,
                        prompt, response, status, priority, assigned_to, locked_until,
                        reviewed_by, review_notes, decision_timestamp, created_at,
                        assigned_at, expires_at, metadata
                    FROM hitl_reviews
                    WHERE 1=1
                """
                params = []
                
                if status:
                    query += " AND status = %s"
                    # Handle both enum and string (due to use_enum_values=True)
                    status_value = (
                        status.value if isinstance(status, ReviewStatus) else str(status)
                    )
                    params.append(status_value)
                
                if request_id:
                    query += " AND request_id = %s"
                    params.append(request_id)
                
                if trace_id:
                    query += " AND trace_id = %s"
                    params.append(trace_id)
                
                if checkpoint:
                    query += " AND checkpoint = %s"
                    params.append(checkpoint)
                
                if assigned_to:
                    query += " AND assigned_to = %s"
                    params.append(assigned_to)
                
                if start_time:
                    query += " AND created_at >= %s"
                    params.append(start_time)
                
                if end_time:
                    query += " AND created_at <= %s"
                    params.append(end_time)
                
                query += " ORDER BY priority DESC, created_at DESC"
                
                if limit:
                    query += " LIMIT %s"
                    params.append(limit)
                
                if offset:
                    query += " OFFSET %s"
                    params.append(offset)
                
                cursor.execute(query, tuple(params) if params else None)
                rows = cursor.fetchall()
                return [Review(**row) for row in rows]
        except Exception as e:
            logger.error(
                "hitl_reviews_query_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

