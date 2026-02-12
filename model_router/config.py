"""
Configuration loader for Model Router.

Loads Model Router configuration from YAML files and environment variables.
"""

import os
import yaml
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

# NOTE: this is not a runtime module, it's just configuration for the model_router
class ModelRouterConfig(BaseModel):
    """
    Configuration for Model Router.
    
    Contains settings for model selection, timeouts, retries, and provider setup.
    """

    default_model: str = Field(..., description="Default model to use (e.g., 'gpt-4')")
    fallback_model: Optional[str] = Field(
        None,
        description="Fallback model if default fails (e.g., 'gpt-3.5-turbo')",
    )
    timeout_seconds: float = Field(
        default=30.0,
        gt=0,
        description="Request timeout in seconds",
    )
    max_retries: int = Field(
        default=3,
        ge=0,
        description="Maximum number of retry attempts on failure",
    )
    openai_api_key: Optional[str] = Field(
        None,
        description="OpenAI API key (from env: OPENAI_API_KEY)",
    )
    anthropic_api_key: Optional[str] = Field(
        None,
        description="Anthropic API key (from env: ANTHROPIC_API_KEY)",
    )
    use_ollama: bool = Field(
        default=True,
        description="Use Ollama provider for local models (default: true)",
    )
    ollama_base_url: str = Field(
        default="http://localhost:11434",
        description="Base URL for Ollama API",
    )

    model_config = ConfigDict(use_enum_values=True)


def load_router_config(config_path: str) -> ModelRouterConfig:
    """
    Load Model Router configuration from a YAML file.
    
    Reads the YAML file, extracts the 'model_router' section, and loads
    API keys from environment variables.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        ModelRouterConfig object with all router settings
        
    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
        ValueError: If the config structure is invalid or missing required fields
    """
    config_file = Path(config_path)
    
    if not config_file.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_file, "r") as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        raise yaml.YAMLError(f"Invalid YAML in config file {config_path}: {e}") from e
    
    if not isinstance(data, dict):
        raise ValueError(f"Config file must contain a YAML dictionary, got {type(data)}")
    
    if "model_router" not in data:
        raise ValueError("Config file must contain a 'model_router' key")
    
    router_data = data["model_router"]
    
    if not isinstance(router_data, dict):
        raise ValueError(f"'model_router' must be a dictionary, got {type(router_data)}")
    
    openai_key = os.getenv("OPENAI_API_KEY")
    anthropic_key = os.getenv("ANTHROPIC_API_KEY")
    
    try:
        config = ModelRouterConfig(
            default_model=router_data.get("default_model", "llama2"),
            fallback_model=router_data.get("fallback_model"),
            timeout_seconds=float(router_data.get("timeout_seconds", 60.0)),
            max_retries=int(router_data.get("max_retries", 3)),
            openai_api_key=openai_key,
            anthropic_api_key=anthropic_key,
            use_ollama=bool(router_data.get("use_ollama", True)),
            ollama_base_url=router_data.get("ollama_base_url", "http://localhost:11434"),
        )
    except Exception as e:
        raise ValueError(f"Invalid Model Router configuration: {e}") from e
    
    if not config.default_model:
        raise ValueError("'default_model' is required in model_router configuration")
    
    return config

