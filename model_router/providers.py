"""
LLM Provider interface and implementations.

Defines the abstract interface that all LLM providers must implement,
and concrete implementations for OpenAI, Anthropic, etc.
"""

import time
from abc import ABC, abstractmethod
from typing import List, Optional

import httpx

from common.logging import get_logger
from model_router.exceptions import ProviderError, TimeoutError
from model_router.models import LLMRequest, LLMResponse

logger = get_logger(__name__)


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


class OllamaProvider(LLMProvider):
    """
    Provider implementation for local Ollama models.
    
    Connects to a local Ollama instance running on http://localhost:11434.
    Supports any model installed in Ollama (llama2, mistral, codellama, etc.).
    """

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 60.0):
        """
        Initialize Ollama provider.
        
        Args:
            base_url: Base URL for Ollama API (default: http://localhost:11434)
            timeout: Request timeout in seconds (default: 60.0)
        """
        self._name = "ollama"
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        
        # Try to fetch available models from Ollama
        self._supported_models: List[str] = []
        try:
            self._refresh_models()
        except Exception:
            # If Ollama is not running, we'll use a default list
            # User can still specify models and we'll try to use them
            self._supported_models = [
                "llama2",
                "mistral",
                "codellama",
                "phi",
                "neural-chat",
                "starling-lm",
            ]

    def _refresh_models(self) -> None:
        """Fetch available models from Ollama API."""
        try:
            response = self._client.get(f"{self._base_url}/api/tags")
            if response.status_code == 200:
                data = response.json()
                self._supported_models = [
                    model["name"] for model in data.get("models", [])
                ]
        except Exception:
            # If we can't fetch, keep existing list or use defaults
            pass

    @property
    def name(self) -> str:
        return self._name

    def supports_model(self, model_name: str) -> bool:
        """
        Check if Ollama supports this model.
        
        Ollama is flexible - if model is installed, it will work.
        We check if it's in our known list, or if it looks like an Ollama model name.
        """
        # Refresh models list to get latest installed models
        self._refresh_models()
        
        # Check if model is in our list
        if model_name in self._supported_models:
            return True
        
        # Ollama model names are typically lowercase with hyphens/underscores
        # If it's not a known OpenAI/Anthropic model pattern, assume it's Ollama
        if not (model_name.startswith("gpt-") or model_name.startswith("claude-")):
            return True  # Assume it's an Ollama model
        
        return False

    def get_supported_models(self) -> List[str]:
        """Get list of models available in Ollama."""
        self._refresh_models()
        return self._supported_models.copy()

    def generate(self, request: LLMRequest) -> LLMResponse:
        """
        Generate response using Ollama API.
        
        Args:
            request: LLMRequest with messages, model, parameters
            
        Returns:
            LLMResponse with generated content
            
        Raises:
            ProviderError: If Ollama API call fails
            TimeoutError: If request times out
        """
        start_time = time.time()
        
        # Convert messages to Ollama format
        # Ollama uses a simple prompt string or messages array
        prompt = request.messages[-1].content if request.messages else ""
        
        # For multi-turn, combine messages
        if len(request.messages) > 1:
            prompt_parts = []
            for msg in request.messages:
                role = msg.role
                content = msg.content
                if role == "system":
                    prompt_parts.append(f"System: {content}")
                elif role == "user":
                    prompt_parts.append(f"User: {content}")
                elif role == "assistant":
                    prompt_parts.append(f"Assistant: {content}")
            prompt = "\n".join(prompt_parts)
        
        # Prepare Ollama API request
        ollama_request = {
            "model": request.model,
            "prompt": prompt,
            "stream": False,  # We want complete response
        }
        
        # Add optional parameters
        if request.temperature is not None:
            ollama_request["options"] = {
                "temperature": request.temperature,
            }
        if request.max_tokens is not None:
            if "options" not in ollama_request:
                ollama_request["options"] = {}
            ollama_request["options"]["num_predict"] = request.max_tokens
        
        try:
            response = self._client.post(
                f"{self._base_url}/api/generate",
                json=ollama_request,
            )
            response.raise_for_status()
            
            data = response.json()
            content = data.get("response", "")
            latency_ms = (time.time() - start_time) * 1000
            
            # Ollama doesn't provide detailed token usage in the same format
            # Estimate from response
            estimated_prompt_tokens = len(prompt.split())
            estimated_completion_tokens = len(content.split())
            
            return LLMResponse(
                content=content,
                model=request.model,
                provider=self.name,
                finish_reason="stop",
                usage={
                    "prompt_tokens": estimated_prompt_tokens,
                    "completion_tokens": estimated_completion_tokens,
                    "total_tokens": estimated_prompt_tokens + estimated_completion_tokens,
                },
                latency_ms=latency_ms,
                metadata={
                    "ollama_base_url": self._base_url,
                    "model_family": data.get("model", ""),
                },
            )
            
        except httpx.TimeoutException as e:
            raise TimeoutError(f"Ollama request timed out: {e}") from e
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ProviderError(
                    f"Ollama: Model '{request.model}' not found. "
                    f"Install it with: ollama pull {request.model}"
                ) from e
            raise ProviderError(
                f"Ollama API error (status {e.response.status_code}): {e.response.text}"
            ) from e
        except Exception as e:
            raise ProviderError(f"Unexpected error calling Ollama: {e}") from e

