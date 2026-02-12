"""Pydantic models for audit events - data contracts."""

from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class AuditEventCreate(BaseModel):
    """
    Model for creating an audit event.
    
    Used when inserting events into the database.
    """

    request_id: str = Field(..., description="Unique request identifier")
    event_type: str = Field(..., description="Type of event (e.g., 'request_received', 'policy_blocked')")
    data: Dict[str, Any] = Field(..., description="Event data dictionary")
    trace_id: Optional[str] = Field(None, description="Trace ID for end-to-end correlation")

    model_config = ConfigDict(use_enum_values=True)


class AuditEvent(BaseModel):
    """
    Model for an audit event as stored/returned from the database.
    
    Represents a complete audit event record.
    """

    id: int = Field(..., description="Database primary key")
    trace_id: Optional[str] = Field(None, description="Trace ID for correlation")
    request_id: str = Field(..., description="Request identifier")
    event_type: str = Field(..., description="Type of event")
    event_data: Dict[str, Any] = Field(..., description="Event data (JSONB from database)")
    timestamp: datetime = Field(..., description="Event timestamp")

    model_config = ConfigDict(use_enum_values=True)


class AuditEventQuery(BaseModel):
    """
    Model for querying audit events with filters.
    
    Used for filtering events by various criteria.
    """

    trace_id: Optional[str] = Field(None, description="Filter by trace ID")
    request_id: Optional[str] = Field(None, description="Filter by request ID")
    user_id: Optional[str] = Field(None, description="Filter by user ID (searches event_data)")
    event_type: Optional[str] = Field(None, description="Filter by event type")
    start_time: Optional[datetime] = Field(None, description="Start time for time range filter")
    end_time: Optional[datetime] = Field(None, description="End time for time range filter")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Maximum number of results")

    model_config = ConfigDict(use_enum_values=True)


class AuditEventResponse(BaseModel):
    """
    Model for API response containing audit events.
    
    Used for returning query results.
    """

    events: list[AuditEvent] = Field(..., description="List of audit events")
    count: int = Field(..., description="Total number of events returned")
    trace_id: Optional[str] = Field(None, description="Trace ID if query was filtered by trace_id")

    model_config = ConfigDict(use_enum_values=True)


class PolicyViolationSummary(BaseModel):
    """
    Model for policy violation summary/statistics.
    
    Used for compliance reporting.
    """

    total_violations: int = Field(..., description="Total number of violations")
    blocked_count: int = Field(..., description="Number of BLOCK outcomes")
    escalated_count: int = Field(..., description="Number of ESCALATE outcomes")
    time_range_start: Optional[datetime] = Field(None, description="Start of time range")
    time_range_end: Optional[datetime] = Field(None, description="End of time range")
    violations: list[AuditEvent] = Field(default_factory=list, description="List of violation events")

    model_config = ConfigDict(use_enum_values=True)

