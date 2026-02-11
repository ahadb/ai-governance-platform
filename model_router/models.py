"""
Core data models for Model Router.

Defines LLMRequest and LLMResponse structures that standardize
communication between the router and LLM providers.
"""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class LLMMessage(BaseModel):
    """
    A single message in a conversation.
    
    Represents one turn in a chat conversation (user, assistant, system).
    """

    role: str = Field(..., description="Message role: 'user', 'assistant', or 'system'")
    content: str = Field(..., description="Message content/text")

    model_config = ConfigDict(use_enum_values=True)


class LLMRequest(BaseModel):
    """
    Standardized request format for LLM calls.
    
    This is the universal format that the Model Router accepts,
    regardless of which provider (OpenAI, Anthropic, etc.) will handle it.
    """

    messages: List[LLMMessage] = Field(
        ...,
        description="List of messages in the conversation (chat format)",
    )
    model: str = Field(..., description="Model identifier (e.g., 'gpt-4', 'claude-3-opus')")
    temperature: Optional[float] = Field(
        None,
        ge=0.0,
        le=2.0,
        description="Sampling temperature (0.0 to 2.0)",
    )
    max_tokens: Optional[int] = Field(
        None,
        gt=0,
        description="Maximum tokens to generate",
    )
    user_id: Optional[str] = Field(
        None,
        description="User identifier for tracking and rate limiting",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional request metadata",
    )

    model_config = ConfigDict(use_enum_values=True)

    def to_simple_prompt(self) -> str:
        """
        Convert messages to a simple prompt string.
        
        Useful for single-turn requests or logging.
        Returns the last user message, or concatenates all messages.
        """
        if not self.messages:
            return ""
        
        # If single user message, return it
        user_messages = [msg.content for msg in self.messages if msg.role == "user"]
        if len(user_messages) == 1:
            return user_messages[0]
        
        # Otherwise, format as conversation
        formatted = []
        for msg in self.messages:
            formatted.append(f"{msg.role}: {msg.content}")
        return "\n".join(formatted)


class LLMResponse(BaseModel):
    """
    Standardized response format from LLM calls.
    
    This is the universal format returned by the Model Router,
    regardless of which provider generated it.
    """

    content: str = Field(..., description="Generated text/content from the LLM")
    model: str = Field(..., description="Model that generated the response")
    provider: str = Field(..., description="Provider that handled the request (e.g., 'openai', 'anthropic')")
    finish_reason: Optional[str] = Field(
        None,
        description="Reason for completion (e.g., 'stop', 'length', 'content_filter')",
    )
    usage: Optional[Dict[str, int]] = Field(
        None,
        description="Token usage: {'prompt_tokens': X, 'completion_tokens': Y, 'total_tokens': Z}",
    )
    latency_ms: Optional[float] = Field(
        None,
        description="Request latency in milliseconds",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional response metadata",
    )

    model_config = ConfigDict(use_enum_values=True)

    @property
    def prompt_tokens(self) -> Optional[int]:
        """Get prompt tokens from usage dict."""
        return self.usage.get("prompt_tokens") if self.usage else None

    @property
    def completion_tokens(self) -> Optional[int]:
        """Get completion tokens from usage dict."""
        return self.usage.get("completion_tokens") if self.usage else None

    @property
    def total_tokens(self) -> Optional[int]:
        """Get total tokens from usage dict."""
        return self.usage.get("total_tokens") if self.usage else None

