"""
Tests for configuration loader.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from policy_engine.config_loader import PolicyConfig, get_enabled_policies, load_policy_config


class TestPolicyConfig:
    """Test PolicyConfig model."""

    def test_create_policy_config(self):
        """Test creating a PolicyConfig."""
        config = PolicyConfig(
            name="test_policy",
            enabled=True,
            config={"key": "value"},
        )
        assert config.name == "test_policy"
        assert config.enabled is True
        assert config.config == {"key": "value"}

    def test_policy_config_defaults(self):
        """Test PolicyConfig with minimal fields."""
        config = PolicyConfig(name="test", enabled=False)
        assert config.name == "test"
        assert config.enabled is False
        assert config.config == {}  # Default empty dict

    def test_policy_config_validation(self):
        """Test that PolicyConfig validates required fields."""
        with pytest.raises(Exception):  # Pydantic validation error
            PolicyConfig()  # Missing required fields


class TestLoadPolicyConfig:
    """Test load_policy_config function."""

    def test_load_valid_config(self):
        """Test loading a valid configuration file."""
        config_data = {
            "policies": [
                {"name": "policy1", "enabled": True, "config": {"key": "value"}},
                {"name": "policy2", "enabled": False, "config": {}},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            policies = load_policy_config(temp_path)
            assert len(policies) == 2
            assert policies[0].name == "policy1"
            assert policies[0].enabled is True
            assert policies[0].config == {"key": "value"}
            assert policies[1].name == "policy2"
            assert policies[1].enabled is False
        finally:
            Path(temp_path).unlink()

    def test_load_config_missing_file(self):
        """Test that missing config file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_policy_config("/nonexistent/path/config.yaml")

    def test_load_config_invalid_yaml(self):
        """Test that invalid YAML raises YAMLError."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write("invalid: yaml: content: [")
            temp_path = f.name
        
        try:
            with pytest.raises(yaml.YAMLError):
                load_policy_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_config_missing_policies_key(self):
        """Test that config without 'policies' key raises ValueError."""
        config_data = {"other_key": "value"}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="must contain a 'policies' key"):
                load_policy_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_config_policies_not_list(self):
        """Test that 'policies' must be a list."""
        config_data = {"policies": "not a list"}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="must be a list"):
                load_policy_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_config_missing_name_field(self):
        """Test that policy missing 'name' field raises ValueError."""
        config_data = {"policies": [{"enabled": True}]}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="missing required 'name' field"):
                load_policy_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_config_missing_enabled_field(self):
        """Test that policy missing 'enabled' field raises ValueError."""
        config_data = {"policies": [{"name": "test"}]}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            with pytest.raises(ValueError, match="missing required 'enabled' field"):
                load_policy_config(temp_path)
        finally:
            Path(temp_path).unlink()

    def test_load_config_boolean_conversion(self):
        """Test that enabled field is converted to boolean."""
        config_data = {
            "policies": [
                {"name": "policy1", "enabled": 1},  # Truthy value
                {"name": "policy2", "enabled": 0},  # Falsy value
                {"name": "policy3", "enabled": "true"},  # String
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            policies = load_policy_config(temp_path)
            assert policies[0].enabled is True
            assert policies[1].enabled is False
            assert policies[2].enabled is True  # Non-empty string is truthy
        finally:
            Path(temp_path).unlink()

    def test_load_config_empty_policies_list(self):
        """Test loading config with empty policies list."""
        config_data = {"policies": []}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            policies = load_policy_config(temp_path)
            assert policies == []
        finally:
            Path(temp_path).unlink()

    def test_load_config_missing_config_key(self):
        """Test that missing 'config' key defaults to empty dict."""
        config_data = {"policies": [{"name": "test", "enabled": True}]}
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            policies = load_policy_config(temp_path)
            assert policies[0].config == {}
        finally:
            Path(temp_path).unlink()

    def test_load_real_config_file(self):
        """Test loading the actual default.yaml config file."""
        config_path = Path(__file__).parent.parent / "config" / "default.yaml"
        if config_path.exists():
            policies = load_policy_config(str(config_path))
            assert len(policies) > 0
            # Verify structure
            for policy in policies:
                assert isinstance(policy, PolicyConfig)
                assert policy.name
                assert isinstance(policy.enabled, bool)

    def test_load_fixture_valid_config(self):
        """Test loading a fixture YAML file."""
        fixture_path = Path(__file__).parent / "fixtures" / "valid_config.yaml"
        policies = load_policy_config(str(fixture_path))
        
        assert len(policies) == 3
        assert policies[0].name == "test_policy_1"
        assert policies[0].enabled is True
        assert policies[0].config == {"setting1": "value1", "setting2": 42}
        
        assert policies[1].name == "test_policy_2"
        assert policies[1].enabled is False
        
        assert policies[2].name == "test_policy_3"
        assert policies[2].enabled is True
        assert policies[2].config == {}

    def test_load_fixture_minimal_config(self):
        """Test loading minimal fixture config."""
        fixture_path = Path(__file__).parent / "fixtures" / "minimal_config.yaml"
        policies = load_policy_config(str(fixture_path))
        
        assert len(policies) == 1
        assert policies[0].name == "simple_policy"
        assert policies[0].enabled is True
        assert policies[0].config == {}  # Defaults to empty dict

    def test_load_fixture_multiple_policies(self):
        """Test loading config with multiple policies."""
        fixture_path = Path(__file__).parent / "fixtures" / "multiple_policies.yaml"
        policies = load_policy_config(str(fixture_path))
        
        assert len(policies) == 4
        policy_names = [p.name for p in policies]
        assert set(policy_names) == {"policy_a", "policy_b", "policy_c", "policy_d"}
        
        # Check enabled status
        enabled = [p for p in policies if p.enabled]
        assert len(enabled) == 3
        assert "policy_c" not in [p.name for p in enabled]


class TestGetEnabledPolicies:
    """Test get_enabled_policies convenience function."""

    def test_get_enabled_policies_filters(self):
        """Test that get_enabled_policies only returns enabled policies."""
        config_data = {
            "policies": [
                {"name": "policy1", "enabled": True},
                {"name": "policy2", "enabled": False},
                {"name": "policy3", "enabled": True},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            enabled = get_enabled_policies(temp_path)
            assert len(enabled) == 2
            assert all(policy.enabled for policy in enabled)
            assert enabled[0].name == "policy1"
            assert enabled[1].name == "policy3"
        finally:
            Path(temp_path).unlink()

    def test_get_enabled_policies_all_disabled(self):
        """Test when all policies are disabled."""
        config_data = {
            "policies": [
                {"name": "policy1", "enabled": False},
                {"name": "policy2", "enabled": False},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            enabled = get_enabled_policies(temp_path)
            assert enabled == []
        finally:
            Path(temp_path).unlink()

