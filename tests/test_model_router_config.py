"""
Tests for Model Router configuration loader.
"""

import os
import tempfile
from pathlib import Path

import pytest
import yaml

from model_router.config import ModelRouterConfig, load_router_config


class TestModelRouterConfig:
    """Test ModelRouterConfig model."""

    def test_create_config(self):
        """Test creating a ModelRouterConfig."""
        config = ModelRouterConfig(
            default_model="gpt-4",
            fallback_model="gpt-3.5-turbo",
            timeout_seconds=30.0,
            max_retries=3,
        )
        assert config.default_model == "gpt-4"
        assert config.fallback_model == "gpt-3.5-turbo"
        assert config.timeout_seconds == 30.0
        assert config.max_retries == 3

    def test_config_defaults(self):
        """Test config with minimal fields."""
        config = ModelRouterConfig(default_model="gpt-4")
        assert config.default_model == "gpt-4"
        assert config.timeout_seconds == 30.0  # Default
        assert config.max_retries == 3  # Default
        assert config.fallback_model is None

    def test_config_validation(self):
        """Test that config validates required fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            ModelRouterConfig()  # Missing required default_model

    def test_timeout_validation(self):
        """Test that timeout must be positive."""
        with pytest.raises(Exception):  # Pydantic validation error
            ModelRouterConfig(
                default_model="gpt-4",
                timeout_seconds=-1,  # Must be > 0
            )

    def test_max_retries_validation(self):
        """Test that max_retries must be non-negative."""
        # Valid: 0 or positive
        config1 = ModelRouterConfig(default_model="gpt-4", max_retries=0)
        assert config1.max_retries == 0

        # Invalid: negative
        with pytest.raises(Exception):  # Pydantic validation error
            ModelRouterConfig(
                default_model="gpt-4",
                max_retries=-1,  # Must be >= 0
            )


class TestLoadRouterConfig:
    """Test load_router_config function."""

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_data = {
            "model_router": {
                "default_model": "gpt-4",
                "fallback_model": "gpt-3.5-turbo",
                "timeout_seconds": 30,
                "max_retries": 3,
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_router_config(temp_path)
            assert config.default_model == "gpt-4"
            assert config.fallback_model == "gpt-3.5-turbo"
            assert config.timeout_seconds == 30.0
            assert config.max_retries == 3
        finally:
            Path(temp_path).unlink()

    def test_load_config_with_env_vars(self, monkeypatch):
        """Test that API keys are loaded from environment variables."""
        # Set environment variables
        monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-anthropic-key")
        
        config_data = {
            "model_router": {
                "default_model": "gpt-4",
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_router_config(temp_path)
            assert config.openai_api_key == "test-openai-key"
            assert config.anthropic_api_key == "test-anthropic-key"
        finally:
            Path(temp_path).unlink()

    def test_load_config_missing_file(self):
        """Test that missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_router_config("/nonexistent/path/config.yaml")

    def test_load_config_invalid_yaml(self):
        """Test that invalid YAML raises YAMLError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                load_router_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_config_missing_model_router_key(self):
        """Test that config without 'model_router' key raises ValueError."""
        config_data = {"other_key": "value"}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="must contain a 'model_router' key"):
                load_router_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_config_defaults(self):
        """Test that missing optional fields use defaults."""
        config_data = {
            "model_router": {
                "default_model": "gpt-4",
                # Missing timeout_seconds and max_retries
            }
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            config = load_router_config(temp_path)
            assert config.default_model == "gpt-4"
            assert config.timeout_seconds == 30.0  # Default
            assert config.max_retries == 3  # Default
        finally:
            Path(temp_path).unlink()

    def test_load_real_config_file(self):
        """Test loading the actual default.yaml config file."""
        config_path = Path(__file__).parent.parent / "config" / "default.yaml"
        if config_path.exists():
            config = load_router_config(str(config_path))
            assert config.default_model
            assert isinstance(config.timeout_seconds, float)
            assert isinstance(config.max_retries, int)

