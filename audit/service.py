"""Audit service - business logic layer for audit events."""

from datetime import datetime
from typing import Optional

from common.logging import get_logger
from audit.models import AuditEvent, AuditEventResponse
from audit.repository import AuditRepository

logger = get_logger(__name__)


class AuditService:
    """Service for audit event logging and retrieval."""

    def __init__(self, repository: AuditRepository):
        """
        Initialize audit service.
        
        Args:
            repository: AuditRepository instance for data access
        """
        self._repository = repository

    def log(
        self,
        request_id: str,
        event_type: str,
        data: dict,
        trace_id: Optional[str] = None,
    ) -> None:
        """
        Log an audit event.
        
        This method provides the same interface as AuditStub for easy replacement.
        
        Args:
            request_id: Unique request identifier
            event_type: Type of event (e.g., "request_received", "policy_blocked")
            data: Event data dictionary
            trace_id: Optional trace ID for correlation
        """
        try:
            # Extract trace_id from data if not provided directly
            if not trace_id and "trace_id" in data:
                trace_id = data.get("trace_id")

            self._repository.insert_event(
                request_id=request_id,
                event_type=event_type,
                data=data,
                trace_id=trace_id,
            )

            logger.debug(
                "audit_event_logged",
                request_id=request_id,
                event_type=event_type,
                trace_id=trace_id,
            )
        except Exception as e:
            # Don't fail the main request if audit logging fails
            # Log the error but don't raise
            logger.error(
                "audit_event_log_failed",
                request_id=request_id,
                event_type=event_type,
                error=str(e),
                error_type=type(e).__name__,
            )

    def get_events_by_trace_id(self, trace_id: str) -> AuditEventResponse:
        """Get all events for a trace_id."""
        events = self._repository.get_events_by_trace_id(trace_id)
        return AuditEventResponse(
            events=events,
            count=len(events),
            trace_id=trace_id,
        )

    def get_events_by_request_id(self, request_id: str) -> AuditEventResponse:
        """Get all events for a request_id."""
        events = self._repository.get_events_by_request_id(request_id)
        return AuditEventResponse(
            events=events,
            count=len(events),
            trace_id=events[0].trace_id if events else None,
        )

    def get_events_by_user_id(
        self,
        user_id: str,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> AuditEventResponse:
        """Get all events for a user_id within optional time range."""
        events = self._repository.get_events_by_user_id(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time,
        )
        return AuditEventResponse(
            events=events,
            count=len(events),
        )

    def get_policy_violations(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> list[AuditEvent]:
        """Get all policy violation events."""
        return self._repository.get_policy_violations(
            start_time=start_time,
            end_time=end_time,
        )

