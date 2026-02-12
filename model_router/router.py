"""
Model Router Core - Routes LLM requests to appropriate providers.

Handles provider selection, retries, fallbacks, and error handling.
"""

import time
from typing import List, Optional

from model_router.config import ModelRouterConfig
from model_router.exceptions import (
    ModelNotFoundError,
    ModelRouterError,
    ProviderError,
    TimeoutError,
)
from model_router.models import LLMRequest, LLMResponse
from model_router.providers import (
    AnthropicProvider,
    LLMProvider,
    OllamaProvider,
    OpenAIProvider,
)


class ModelRouter:
    """
    Routes LLM requests to the appropriate provider based on model name.
    
    Handles:
    - Provider selection (which provider supports the requested model)
    - Retries (up to max_retries)
    - Fallback (try fallback_model if primary fails)
    - Error handling and timeouts
    """

    def __init__(self, config: ModelRouterConfig):
        """
        Initialize the Model Router.
        
        Args:
            config: ModelRouterConfig with provider settings, timeouts, retries
            
        Raises:
            AuthenticationError: If required API keys are missing
        """
        self._config = config
        self._providers: List[LLMProvider] = []
        
        # Initialize providers based on available API keys
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize available LLM providers from config."""
        
        # Initialize Ollama (default for local models)
        if self._config.use_ollama:
            try:
                self._providers.append(
                    OllamaProvider(
                        base_url=self._config.ollama_base_url,
                        timeout=self._config.timeout_seconds,
                    )
                )
            except Exception as e:
                # TODO: Log warning instead of silently failing
                pass
        
        # Initialize OpenAI if API key is available
        if self._config.openai_api_key:
            try:
                self._providers.append(OpenAIProvider(self._config.openai_api_key))
            except Exception as e:
                # TODO: Log warning instead of silently failing
                pass
        
        # Initialize Anthropic if API key is available
        if self._config.anthropic_api_key:
            try:
                self._providers.append(AnthropicProvider(self._config.anthropic_api_key))
            except Exception as e:
                # TODO: Log warning instead of silently failing
                pass
        
        if not self._providers:
            raise ModelRouterError(
                "No LLM providers available. Ollama is enabled by default for local models. "
                "Make sure Ollama is running (ollama serve) or configure API keys (OPENAI_API_KEY or ANTHROPIC_API_KEY)."
            )

    def _find_provider(self, model_name: str) -> Optional[LLMProvider]:
        """
        Find the provider that supports the given model.
        
        Args:
            model_name: Model identifier (e.g., "gpt-4", "claude-3-opus")
            
        Returns:
            LLMProvider that supports the model, or None if not found
        """
        for provider in self._providers:
            if provider.supports_model(model_name):
                return provider
        return None

    def route(self, request: LLMRequest) -> LLMResponse:
        """
        Route an LLM request to the appropriate provider.
        
        Handles:
        - Model selection (uses request.model or config.default_model)
        - Provider lookup
        - Retries (up to max_retries)
        - Fallback (tries fallback_model if primary fails)
        
        Args:
            request: LLMRequest with messages, model (optional), parameters
            
        Returns:
            LLMResponse with generated content and metadata
            
        Raises:
            ModelNotFoundError: If model is not supported by any provider
            ProviderError: If all retries and fallbacks fail
            TimeoutError: If request times out
        """
        # Determine which model to use
        model_to_use = request.model or self._config.default_model
        
        try:
            return self._route_with_retries(request, model_to_use)
        except (ProviderError, ModelNotFoundError) as e:
            # If primary fails and fallback is configured, try fallback
            if self._config.fallback_model and model_to_use != self._config.fallback_model:
                try:
                    # Create new request with fallback model
                    fallback_request = request.model_copy(update={"model": self._config.fallback_model})
                    return self._route_with_retries(fallback_request, self._config.fallback_model)
                except Exception as fallback_error:
                    # Both primary and fallback failed
                    raise ProviderError(
                        f"Both primary model '{model_to_use}' and fallback model '{self._config.fallback_model}' failed. "
                        f"Primary error: {e}, Fallback error: {fallback_error}"
                    ) from fallback_error
            else:
                # No fallback configured or already tried fallback
                raise

    def _route_with_retries(
        self, request: LLMRequest, model_name: str
    ) -> LLMResponse:
        """
        Route request to provider with retry logic.
        
        Args:
            request: LLMRequest to route
            model_name: Model identifier to use
            
        Returns:
            LLMResponse from provider
            
        Raises:
            ModelNotFoundError: If model not supported
            ProviderError: If all retries fail
        """

        provider = self._find_provider(model_name)
        if not provider:
            raise ModelNotFoundError(
                f"Model '{model_name}' is not supported by any available provider. "
                f"Available providers: {[p.name for p in self._providers]}"
            )
        
        if request.model != model_name:
            request = request.model_copy(update={"model": model_name})
        
        last_error = None
        for attempt in range(self._config.max_retries + 1):
            try:
                start_time = time.time()
                response = provider.generate(request)
                
                if not response.metadata:
                    response.metadata = {}
                response.metadata["router_attempt"] = attempt + 1
                response.metadata["router_total_attempts"] = self._config.max_retries + 1
                
                return response
            except (ProviderError, TimeoutError) as e:
                last_error = e
                # Don't retry on authentication errors or model not found
                if isinstance(e, (ModelNotFoundError,)):
                    raise
                # Continue to retry for other errors
                if attempt < self._config.max_retries:
                    # TODO: Add exponential backoff
                    continue
                else:
                    # All retries exhausted
                    raise ProviderError(
                        f"Provider '{provider.name}' failed after {self._config.max_retries + 1} attempts: {e}"
                    ) from e
        
        # Should never reach here, but just in case
        if last_error:
            raise ProviderError(f"Failed to route request: {last_error}") from last_error
        raise ProviderError("Failed to route request: Unknown error")

    def get_supported_models(self) -> List[str]:
        """
        Get list of all models supported by available providers.
        
        Returns:
            List of model identifiers supported by at least one provider
        """
        models = set()
        for provider in self._providers:
            models.update(provider.get_supported_models())
        return sorted(list(models))

    def get_providers(self) -> List[str]:
        """
        Get list of available provider names.
        
        Returns:
            List of provider names (e.g., ["openai", "anthropic"])
        """
        return [provider.name for provider in self._providers]

