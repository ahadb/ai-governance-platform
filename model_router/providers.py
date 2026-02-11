"""
LLM Provider interface and implementations.

Defines the abstract interface that all LLM providers must implement,
and concrete implementations for OpenAI, Anthropic, etc.
"""

from abc import ABC, abstractmethod
from typing import List

from model_router.exceptions import ProviderError
from model_router.models import LLMRequest, LLMResponse


class LLMProvider(ABC):
    """
    Abstract base class for all LLM providers.
    
    Every provider (OpenAI, Anthropic, etc.) must implement this interface.
    This allows the Model Router to work with any provider uniformly.
    """

    @property
    @abstractmethod
    def name(self) -> str:
        """
        Return the provider name.
        
        Returns:
            Provider name (e.g., "openai", "anthropic")
        """
        pass

    @abstractmethod
    def supports_model(self, model_name: str) -> bool:
        """
        Check if this provider supports the given model.
        
        Args:
            model_name: Model identifier (e.g., "gpt-4", "claude-3-opus")
            
        Returns:
            True if provider supports this model, False otherwise
        """
        pass

    @abstractmethod
    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate a response from the LLM.
        
        Args:
            request: LLMRequest with messages, model, parameters
            
        Returns:
            LLMResponse with generated content and metadata
            
        Raises:
            ProviderError: If the provider API call fails
        """
        pass

    def get_supported_models(self) -> List[str]:
        """
        Get list of models supported by this provider.
        
        Returns:
            List of model identifiers
        """
        # Default implementation - subclasses can override
        return []


class OpenAIProvider(LLMProvider):
    """
    Provider implementation for OpenAI API.
    
    Supports models: gpt-4, gpt-4-turbo, gpt-3.5-turbo, etc.
    """

    def __init__(self, api_key: str):
        """
        Initialize OpenAI provider.
        
        Args:
            api_key: OpenAI API key
        """
        self._api_key = api_key
        self._name = "openai"
        # TODO: Fetch supported models dynamically from OpenAI API instead of hardcoding
        # This list gets stale quickly as new models are released
        self._supported_models = [
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4-turbo-preview",
            "gpt-3.5-turbo",
            "gpt-3.5-turbo-16k",
        ]
        
        # NOTE: Import OpenAI client (will fail if not installed)
        try:
            import openai
            self._client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError(
                "OpenAI package not installed. Install with: pip install openai"
            )

    @property
    def name(self) -> str:
        return self._name

    def supports_model(self, model_name: str) -> bool:
        """Check if OpenAI supports this model."""
        # OpenAI models typically start with "gpt-"
        return model_name in self._supported_models or model_name.startswith("gpt-")

    def get_supported_models(self) -> List[str]:
        """Get list of OpenAI models."""
        return self._supported_models.copy()

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using OpenAI API.
        
        Args:
            request: LLMRequest with messages and parameters
            
        Returns:
            LLMResponse with generated content
        """
        import time
        from model_router.exceptions import ProviderError, RateLimitError, AuthenticationError
        
        # Convert LLMRequest to OpenAI format
        openai_messages = [
            {"role": msg.role, "content": msg.content}
            for msg in request.messages
        ]
        
        # Prepare parameters
        params = {
            "model": request.model,
            "messages": openai_messages,
        }
        
        if request.temperature is not None:
            params["temperature"] = request.temperature
        
        if request.max_tokens is not None:
            params["max_tokens"] = request.max_tokens
        
        # Make API call
        start_time = time.time()
        try:
            response = self._client.chat.completions.create(**params)
        except Exception as e:
            # Handle specific OpenAI errors
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "429" in error_msg:
                raise RateLimitError(f"OpenAI rate limit exceeded: {e}") from e
            elif "authentication" in error_msg or "401" in error_msg or "invalid api key" in error_msg:
                raise AuthenticationError(f"OpenAI authentication failed: {e}") from e
            else:
                raise ProviderError(f"OpenAI API error: {e}") from e
        
        latency_ms = (time.time() - start_time) * 1000
        
        choice = response.choices[0]
        content = choice.message.content
        
        # Extract usage if available
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens,
            }
        
        return LLMResponse(
            content=content,
            model=request.model,
            provider=self.name,
            finish_reason=choice.finish_reason,
            usage=usage,
            latency_ms=latency_ms,
        )


class AnthropicProvider(LLMProvider):
    """
    Provider implementation for Anthropic (Claude) API.
    
    Supports models: claude-3-opus, claude-3-sonnet, claude-3-haiku, etc.
    """

    def __init__(self, api_key: str):
        """
        Initialize Anthropic provider.
        
        Args:
            api_key: Anthropic API key
        """
        self._api_key = api_key
        self._name = "anthropic"
        # TODO: Fetch supported models dynamically from Anthropic API
        # Model names include version dates which change over time
        self._supported_models = [
            "claude-3-opus-20240229",
            "claude-3-sonnet-20240229",
            "claude-3-haiku-20240307",
            "claude-3-5-sonnet-20241022",
            "claude-3-5-haiku-20241022",
        ]
        
        # NOTE: Import Anthropic client (will fail if not installed)
        try:
            import anthropic
            self._client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError(
                "Anthropic package not installed. Install with: pip install anthropic"
            )

    @property
    def name(self) -> str:
        return self._name

    def supports_model(self, model_name: str) -> bool:
        """Check if Anthropic supports this model."""
        return model_name in self._supported_models or model_name.startswith("claude-")

    def get_supported_models(self) -> List[str]:
        """Get list of Anthropic models."""
        return self._supported_models.copy()

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using Anthropic API.
        
        Args:
            request: LLMRequest with messages and parameters
            
        Returns:
            LLMResponse with generated content
        """
        import time
        from model_router.exceptions import ProviderError, RateLimitError, AuthenticationError
        
        # Anthropic uses a different message format
        # Convert system message if present
        system_message = None
        messages = []
        
        for msg in request.messages:
            if msg.role == "system":
                system_message = msg.content
            else:
                # Anthropic uses "user" and "assistant" roles
                messages.append({
                    "role": msg.role,
                    "content": msg.content
                })
        
        params = {
            "model": request.model,
            "messages": messages,
            "max_tokens": request.max_tokens or 1024,  # Anthropic requires max_tokens
        }
        
        if system_message:
            params["system"] = system_message
        
        if request.temperature is not None:
            params["temperature"] = request.temperature
        
        # Make API call
        start_time = time.time()
        try:
            response = self._client.messages.create(**params)
        except Exception as e:
            # Handle specific Anthropic errors
            error_msg = str(e).lower()
            if "rate limit" in error_msg or "429" in error_msg:
                raise RateLimitError(f"Anthropic rate limit exceeded: {e}") from e
            elif "authentication" in error_msg or "401" in error_msg or "api key" in error_msg:
                raise AuthenticationError(f"Anthropic authentication failed: {e}") from e
            else:
                raise ProviderError(f"Anthropic API error: {e}") from e
        
        latency_ms = (time.time() - start_time) * 1000
        
        # Extract response
        # Anthropic returns content as a list of text blocks
        content_blocks = response.content
        content = "".join(
            block.text for block in content_blocks if hasattr(block, "text")
        )
        
        # Extract usage if available
        usage = None
        if hasattr(response, "usage") and response.usage:
            usage = {
                "prompt_tokens": response.usage.input_tokens,
                "completion_tokens": response.usage.output_tokens,
                "total_tokens": response.usage.input_tokens + response.usage.output_tokens,
            }
        
        # Extract finish reason
        finish_reason = None
        if hasattr(response, "stop_reason"):
            finish_reason = response.stop_reason
        
        return LLMResponse(
            content=content,
            model=request.model,
            provider=self.name,
            finish_reason=finish_reason,
            usage=usage,
            latency_ms=latency_ms,
        )

