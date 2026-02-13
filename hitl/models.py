"""Pydantic models for HITL reviews - data contracts."""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class ReviewStatus(str, Enum):
    """Review queue status."""
    
    PENDING = "pending"
    ASSIGNED = "assigned"
    PROCESSING = "processing"
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"


class ReviewCreate(BaseModel):
    """
    Model for creating a review (escalation).
    
    Used when escalating a request for human review.
    """
    
    request_id: str = Field(..., description="Request identifier")
    trace_id: Optional[str] = Field(None, description="Trace ID for correlation")
    checkpoint: str = Field(..., description="Checkpoint: 'input' or 'output'")
    reason: str = Field(..., description="Policy reason for escalation")
    context_data: Dict[str, Any] = Field(..., description="Full PolicyContext as dict")
    prompt: Optional[str] = Field(None, description="User prompt (for quick access)")
    response: Optional[str] = Field(None, description="LLM response (if output checkpoint)")
    priority: int = Field(0, description="Review priority (higher = more urgent)")
    expires_at: Optional[datetime] = Field(None, description="Review expiration time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(use_enum_values=True)


class Review(BaseModel):
    """
    Model for a review as stored/returned from the database.
    
    Represents a complete review record.
    """
    
    id: int = Field(..., description="Review ID (primary key)")
    request_id: str = Field(..., description="Request identifier")
    trace_id: Optional[str] = Field(None, description="Trace ID for correlation")
    checkpoint: str = Field(..., description="Checkpoint: 'input' or 'output'")
    reason: str = Field(..., description="Policy reason for escalation")
    context_data: Dict[str, Any] = Field(..., description="Full PolicyContext snapshot")
    prompt: Optional[str] = Field(None, description="User prompt")
    response: Optional[str] = Field(None, description="LLM response (if output checkpoint)")
    status: ReviewStatus = Field(..., description="Current review status")
    priority: int = Field(0, description="Review priority")
    assigned_to: Optional[str] = Field(None, description="Assigned reviewer user_id")
    locked_until: Optional[datetime] = Field(None, description="Lock expiration time")
    reviewed_by: Optional[str] = Field(None, description="User who made the decision")
    review_notes: Optional[str] = Field(None, description="Reviewer's notes")
    decision_timestamp: Optional[datetime] = Field(None, description="When decision was made")
    created_at: datetime = Field(..., description="Review creation time")
    assigned_at: Optional[datetime] = Field(None, description="When review was assigned")
    expires_at: Optional[datetime] = Field(None, description="Review expiration time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    
    model_config = ConfigDict(use_enum_values=True)


class ReviewUpdate(BaseModel):
    """
    Model for updating a review.
    
    Used when updating review status, assignment, or adding notes.
    """
    
    status: Optional[ReviewStatus] = Field(None, description="New review status")
    assigned_to: Optional[str] = Field(None, description="Assign to reviewer user_id")
    review_notes: Optional[str] = Field(None, description="Reviewer's notes")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    model_config = ConfigDict(use_enum_values=True)


class ReviewQuery(BaseModel):
    """
    Model for querying reviews with filters.
    
    Used for filtering reviews by various criteria.
    """
    
    status: Optional[ReviewStatus] = Field(None, description="Filter by status")
    request_id: Optional[str] = Field(None, description="Filter by request ID")
    trace_id: Optional[str] = Field(None, description="Filter by trace ID")
    checkpoint: Optional[str] = Field(None, description="Filter by checkpoint")
    assigned_to: Optional[str] = Field(None, description="Filter by assigned reviewer")
    start_time: Optional[datetime] = Field(None, description="Start time for time range")
    end_time: Optional[datetime] = Field(None, description="End time for time range")
    limit: Optional[int] = Field(None, ge=1, le=1000, description="Maximum number of results")
    offset: Optional[int] = Field(None, ge=0, description="Offset for pagination")
    
    model_config = ConfigDict(use_enum_values=True)


class ReviewResponse(BaseModel):
    """
    Model for API response containing reviews.
    
    Used for returning query results.
    """
    
    reviews: list[Review] = Field(..., description="List of reviews")
    count: int = Field(..., description="Total number of reviews returned")
    total: Optional[int] = Field(None, description="Total number of reviews matching query")
    
    model_config = ConfigDict(use_enum_values=True)


class ReviewDecision(BaseModel):
    """
    Model for making a review decision (approve/reject).
    
    Used when a reviewer makes a decision.
    """
    
    decision: ReviewStatus = Field(..., description="Decision: 'approved' or 'rejected'")
    review_notes: Optional[str] = Field(None, description="Reviewer's notes explaining decision")
    metadata: Optional[Dict[str, Any]] = Field(None, description="Additional metadata")
    
    model_config = ConfigDict(use_enum_values=True)

