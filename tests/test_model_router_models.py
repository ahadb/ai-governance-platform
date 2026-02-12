"""
Tests for Model Router models.
"""

import pytest

from model_router.models import LLMMessage, LLMRequest, LLMResponse


class TestLLMMessage:
    """Test LLMMessage model."""

    def test_create_message(self):
        """Test creating a message."""
        message = LLMMessage(role="user", content="Hello, world!")
        assert message.role == "user"
        assert message.content == "Hello, world!"

    def test_message_validation(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):  # Pydantic validation error
            LLMMessage()  # Missing required fields


class TestLLMRequest:
    """Test LLMRequest model."""

    def test_create_simple_request(self):
        """Test creating a simple request with single message."""
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello")],
            model="gpt-4",
        )
        assert len(request.messages) == 1
        assert request.model == "gpt-4"
        assert request.temperature is None

    def test_create_full_request(self):
        """Test creating a request with all fields."""
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content="You are a helpful assistant"),
                LLMMessage(role="user", content="What is 2+2?"),
            ],
            model="gpt-4",
            temperature=0.7,
            max_tokens=100,
            user_id="user123",
            metadata={"key": "value"},
        )
        assert len(request.messages) == 2
        assert request.temperature == 0.7
        assert request.max_tokens == 100
        assert request.user_id == "user123"
        assert request.metadata == {"key": "value"}

    def test_to_simple_prompt_single_message(self):
        """Test converting single message to simple prompt."""
        request = LLMRequest(
            messages=[LLMMessage(role="user", content="Hello")],
            model="gpt-4",
        )
        assert request.to_simple_prompt() == "Hello"

    def test_to_simple_prompt_multiple_messages(self):
        """Test converting multiple messages to formatted prompt."""
        request = LLMRequest(
            messages=[
                LLMMessage(role="system", content="You are helpful"),
                LLMMessage(role="user", content="Hello"),
                LLMMessage(role="assistant", content="Hi there!"),
                LLMMessage(role="user", content="How are you?"),
            ],
            model="gpt-4",
        )
        prompt = request.to_simple_prompt()
        assert "system: You are helpful" in prompt
        assert "user: Hello" in prompt
        assert "assistant: Hi there!" in prompt

    def test_temperature_validation(self):
        """Test that temperature must be in valid range."""
        # Valid temperatures
        request1 = LLMRequest(
            messages=[LLMMessage(role="user", content="test")],
            model="gpt-4",
            temperature=0.0,
        )
        assert request1.temperature == 0.0

        request2 = LLMRequest(
            messages=[LLMMessage(role="user", content="test")],
            model="gpt-4",
            temperature=2.0,
        )
        assert request2.temperature == 2.0

        # Invalid temperatures should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            LLMRequest(
                messages=[LLMMessage(role="user", content="test")],
                model="gpt-4",
                temperature=3.0,  # > 2.0
            )

    def test_max_tokens_validation(self):
        """Test that max_tokens must be positive."""
        with pytest.raises(Exception):  # Pydantic validation error
            LLMRequest(
                messages=[LLMMessage(role="user", content="test")],
                model="gpt-4",
                max_tokens=0,  # Must be > 0
            )


class TestLLMResponse:
    """Test LLMResponse model."""

    def test_create_simple_response(self):
        """Test creating a simple response."""
        response = LLMResponse(
            content="Hello, I'm an AI assistant.",
            model="gpt-4",
            provider="openai",
        )
        assert response.content == "Hello, I'm an AI assistant."
        assert response.model == "gpt-4"
        assert response.provider == "openai"

    def test_create_full_response(self):
        """Test creating a response with all fields."""
        response = LLMResponse(
            content="Response text",
            model="gpt-4",
            provider="openai",
            finish_reason="stop",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
            latency_ms=150.5,
            metadata={"key": "value"},
        )
        assert response.finish_reason == "stop"
        assert response.usage == {"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30}
        assert response.latency_ms == 150.5

    def test_token_properties(self):
        """Test token usage properties."""
        response = LLMResponse(
            content="Test",
            model="gpt-4",
            provider="openai",
            usage={"prompt_tokens": 10, "completion_tokens": 20, "total_tokens": 30},
        )
        assert response.prompt_tokens == 10
        assert response.completion_tokens == 20
        assert response.total_tokens == 30

    def test_token_properties_none(self):
        """Test token properties when usage is None."""
        response = LLMResponse(
            content="Test",
            model="gpt-4",
            provider="openai",
        )
        assert response.prompt_tokens is None
        assert response.completion_tokens is None
        assert response.total_tokens is None

    def test_response_validation(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):  # Pydantic validation error
            LLMResponse()  # Missing required fields

