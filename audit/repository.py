"""Repository for audit events - raw SQL data access layer."""

import json
from datetime import datetime
from typing import List, Optional

from audit.db import AuditDB
from common.logging import get_logger
from audit.models import AuditEvent, AuditEventCreate

logger = get_logger(__name__)


class AuditRepository:
    """Repository for audit event storage and retrieval."""

    def __init__(self, db: AuditDB):
        """
        Initialize audit repository.
        
        Args:
            db: AuditDB instance for database connections
        """
        self._db = db

    def insert_event(
        self,
        request_id: str,
        event_type: str,
        data: dict,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Insert an audit event into the database.
        
        Args:
            request_id: Unique request identifier
            event_type: Type of event (e.g., "request_received", "policy_blocked")
            data: Event data dictionary (will be stored as JSONB)
            trace_id: Optional trace ID for correlation
        """
        # Validate input using Pydantic model
        event_create = AuditEventCreate(
            request_id=request_id,
            event_type=event_type,
            data=data,
            trace_id=trace_id,
        )
        try:
            with self._db.get_cursor() as cursor:
                cursor.execute(
                    """
                    INSERT INTO audit_events 
                        (trace_id, request_id, event_type, event_data, timestamp)
                    VALUES 
                        (%s, %s, %s, %s::jsonb, NOW())
                    """,
                    (
                        event_create.trace_id,
                        event_create.request_id,
                        event_create.event_type,
                        json.dumps(event_create.data),
                    ),
                )
        except Exception as e:
            logger.error(
                "audit_event_insert_failed",
                request_id=request_id,
                event_type=event_type,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_events_by_trace_id(self, trace_id: str) -> List[AuditEvent]:
        """
        Get all events for a given trace_id.
        
        Args:
            trace_id: Trace identifier
            
        Returns:
            List of AuditEvent models
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    SELECT 
                        id,
                        trace_id,
                        request_id,
                        event_type,
                        event_data,
                        timestamp
                    FROM audit_events
                    WHERE trace_id = %s
                    ORDER BY timestamp ASC
                    """,
                    (trace_id,),
                )
                rows = cursor.fetchall()
                return [AuditEvent(**row) for row in rows]
        except Exception as e:
            logger.error(
                "audit_events_query_failed",
                trace_id=trace_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_events_by_request_id(self, request_id: str) -> List[AuditEvent]:
        """
        Get all events for a given request_id.
        
        Args:
            request_id: Request identifier
            
        Returns:
            List of AuditEvent models
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                cursor.execute(
                    """
                    SELECT 
                        id,
                        trace_id,
                        request_id,
                        event_type,
                        event_data,
                        timestamp
                    FROM audit_events
                    WHERE request_id = %s
                    ORDER BY timestamp ASC
                    """,
                    (request_id,),
                )
                rows = cursor.fetchall()
                return [AuditEvent(**row) for row in rows]
        except Exception as e:
            logger.error(
                "audit_events_query_failed",
                request_id=request_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_events_by_user_id(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """
        Get all events for a given user_id within optional time range.
        
        Args:
            user_id: User identifier
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of AuditEvent models
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                query = """
                    SELECT 
                        id,
                        trace_id,
                        request_id,
                        event_type,
                        event_data,
                        timestamp
                    FROM audit_events
                    WHERE event_data->>'user_id' = %s
                """
                params = [user_id]

                if start_time:
                    query += " AND timestamp >= %s"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= %s"
                    params.append(end_time)

                query += " ORDER BY timestamp DESC"

                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                return [AuditEvent(**row) for row in rows]
        except Exception as e:
            logger.error(
                "audit_events_query_failed",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_policy_violations(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> List[AuditEvent]:
        """
        Get all policy violation events (BLOCK, ESCALATE outcomes).
        
        Args:
            start_time: Optional start time filter
            end_time: Optional end time filter
            
        Returns:
            List of AuditEvent models
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                query = """
                    SELECT 
                        id,
                        trace_id,
                        request_id,
                        event_type,
                        event_data,
                        timestamp
                    FROM audit_events
                    WHERE event_type IN ('request_blocked', 'response_blocked', 'request_escalated', 'response_escalated')
                """
                params = []

                if start_time:
                    query += " AND timestamp >= %s"
                    params.append(start_time)

                if end_time:
                    query += " AND timestamp <= %s"
                    params.append(end_time)

                query += " ORDER BY timestamp DESC"

                cursor.execute(query, tuple(params) if params else None)
                rows = cursor.fetchall()
                return [AuditEvent(**row) for row in rows]
        except Exception as e:
            logger.error(
                "audit_violations_query_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def get_events_by_event_type(
        self,
        event_type: str,
        limit: Optional[int] = None,
    ) -> List[AuditEvent]:
        """
        Get events by event type.
        
        Args:
            event_type: Event type to filter by
            limit: Optional limit on number of results
            
        Returns:
            List of AuditEvent models
        """
        try:
            with self._db.get_cursor(dict_cursor=True) as cursor:
                query = """
                    SELECT 
                        id,
                        trace_id,
                        request_id,
                        event_type,
                        event_data,
                        timestamp
                    FROM audit_events
                    WHERE event_type = %s
                    ORDER BY timestamp DESC
                """
                params = [event_type]

                if limit:
                    query += " LIMIT %s"
                    params.append(limit)

                cursor.execute(query, tuple(params))
                rows = cursor.fetchall()
                return [AuditEvent(**row) for row in rows]
        except Exception as e:
            logger.error(
                "audit_events_query_failed",
                event_type=event_type,
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

