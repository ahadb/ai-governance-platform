"""
Configuration loader for policy engine.

Loads policy configuration from YAML files and returns structured
PolicyConfig objects that the engine can use to determine which
policies to run and how to configure them.
"""

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class PolicyConfig(BaseModel):
    """
    Configuration for a single policy module.
    
    Represents the configuration loaded from YAML for one policy,
    including whether it's enabled and its specific settings.
    """

    name: str = Field(..., description="Name of the policy (must match registered policy name)")
    enabled: bool = Field(..., description="Whether this policy should be evaluated")
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Policy-specific configuration dictionary",
    )


def load_policy_config(config_path: str) -> List[PolicyConfig]:
    """
    Load policy configuration from a YAML file.
    
    Reads the YAML file, extracts the 'policies' section, and returns
    a list of PolicyConfig objects.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        List of PolicyConfig objects, one for each policy in the config
        
    Raises:
        FileNotFoundError: If the config file doesn't exist
        yaml.YAMLError: If the YAML file is invalid
        ValueError: If the config structure is invalid (missing 'policies' key, etc.)
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
    
    if "policies" not in data:
        raise ValueError("Config file must contain a 'policies' key")
    
    policies_data = data["policies"]
    
    if not isinstance(policies_data, list):
        raise ValueError(f"'policies' must be a list, got {type(policies_data)}")
    
    policy_configs = []
    for i, policy_data in enumerate(policies_data):
        if not isinstance(policy_data, dict):
            raise ValueError(f"Policy at index {i} must be a dictionary, got {type(policy_data)}")
        
        if "name" not in policy_data:
            raise ValueError(f"Policy at index {i} is missing required 'name' field")
        
        if "enabled" not in policy_data:
            raise ValueError(f"Policy at index {i} is missing required 'enabled' field")
        
        try:
            policy_config = PolicyConfig(
                name=policy_data["name"],
                enabled=bool(policy_data["enabled"]),  # Ensure it's a boolean
                config=policy_data.get("config", {}),
            )
            policy_configs.append(policy_config)
        except Exception as e:
            raise ValueError(f"Invalid policy configuration at index {i}: {e}") from e
    
    return policy_configs


def get_enabled_policies(config_path: str) -> List[PolicyConfig]:
    """
    Get only the enabled policies from the configuration.
    
    Convenience function that filters out disabled policies.
    
    Args:
        config_path: Path to the YAML configuration file
        
    Returns:
        List of PolicyConfig objects for enabled policies only
    """
    all_policies = load_policy_config(config_path)
    return [policy for policy in all_policies if policy.enabled]

