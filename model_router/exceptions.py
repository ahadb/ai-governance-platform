"""
Custom exceptions for Model Router.
"""

#TODO
class ModelRouterError(Exception):
    """Base exception for all Model Router errors."""
    pass


class ProviderError(ModelRouterError):
    """Error from a specific LLM provider."""
    pass


class ModelNotFoundError(ModelRouterError):
    """Requested model is not supported by any provider."""
    pass


class TimeoutError(ModelRouterError):
    """Request timed out."""
    pass


class RateLimitError(ModelRouterError):
    """Rate limit exceeded."""
    pass


class AuthenticationError(ModelRouterError):
    """Authentication failed (invalid API key)."""
    pass

