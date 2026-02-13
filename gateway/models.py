"""
HTTP request and response models for the Gateway API.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class ChatMessage(BaseModel):
    """A single message in a chat conversation."""

    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content")


class ChatRequest(BaseModel):
    """HTTP request model for chat endpoint."""

    messages: List[ChatMessage] = Field(
        ..., min_length=1, description="List of messages in the conversation"
    )
    model: Optional[str] = Field(
        None, description="Model identifier (e.g., 'gpt-4', 'claude-3-opus'). If not provided, uses default."
    )
    temperature: Optional[float] = Field(
        None, ge=0.0, le=2.0, description="Sampling temperature (0.0 to 2.0)"
    )
    max_tokens: Optional[int] = Field(None, gt=0, description="Maximum tokens to generate")
    user_id: Optional[str] = Field(None, description="User identifier for tracking")
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional request metadata"
    )

    model_config = ConfigDict(use_enum_values=True)


class ChatResponse(BaseModel):
    """HTTP response model for chat endpoint."""

    content: str = Field(..., description="Generated text/content from the LLM")
    model: str = Field(..., description="The LLM model that generated the response")
    provider: str = Field(..., description="The LLM provider used (e.g., 'openai', 'anthropic')")
    finish_reason: Optional[str] = Field(
        None, description="Reason the LLM stopped generating (e.g., 'stop', 'length')"
    )
    usage: Optional[Dict[str, Any]] = Field(
        None, description="Token usage statistics"
    )
    policy_outcome: Optional[str] = Field(
        None, description="Final policy outcome (ALLOW, BLOCK, REDACT, ESCALATE)"
    )
    redacted: bool = Field(
        False, description="Whether content was redacted by policies"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional response metadata"
    )

    model_config = ConfigDict(use_enum_values=True)


class ErrorResponse(BaseModel):
    """Error response model."""

    error: str = Field(..., description="Error message")
    error_code: str = Field(..., description="Error code (e.g., 'POLICY_BLOCKED', 'MODEL_NOT_FOUND')")
    details: Optional[Dict[str, Any]] = Field(
        None, description="Additional error details"
    )

    model_config = ConfigDict(use_enum_values=True)


class EscalateResponse(BaseModel):
    """Response model for escalated requests pending human review."""

    review_id: str = Field(..., description="Review ID for tracking the escalation")
    status: str = Field(default="pending_review", description="Status of the request")
    message: str = Field(..., description="Human-readable message about the escalation")
    reason: str = Field(..., description="Policy reason for escalation")
    trace_id: str = Field(..., description="Trace ID for end-to-end correlation")
    checkpoint: Optional[str] = Field(
        None, description="Checkpoint where escalation occurred ('input' or 'output')"
    )

    model_config = ConfigDict(use_enum_values=True)

