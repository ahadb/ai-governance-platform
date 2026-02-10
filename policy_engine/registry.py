"""
Policy Registry - Manages registration and retrieval of policy modules.

The registry stores all available policy modules and provides methods to
register, retrieve, and query policies.
"""

from typing import Dict, Optional

from policy_engine.interfaces import PolicyModule


class PolicyRegistry:
    """
    Registry for policy modules.
    
    Stores policy modules by name and provides methods to register,
    retrieve, and query registered policies.
    """

    def __init__(self):
        """Initialize an empty registry."""
        self._policies: Dict[str, PolicyModule] = {}

    def register(self, name: str, policy: PolicyModule) -> None:
        """
        Register a policy module.
        
        Args:
            name: Unique name for the policy (e.g., "pii_detection")
            policy: PolicyModule instance to register
            
        Raises:
            ValueError: If name is empty or policy is not a PolicyModule instance
            KeyError: If a policy with the same name is already registered
                      (to prevent accidental overwrites)
        """
        if not name or not name.strip():
            raise ValueError("Policy name cannot be empty")
        
        if not isinstance(policy, PolicyModule):
            raise ValueError(f"Policy must be an instance of PolicyModule, got {type(policy)}")
        
        if name in self._policies:
            raise KeyError(
                f"Policy '{name}' is already registered. "
                f"Use unregister() first or use a different name."
            )
        
        self._policies[name] = policy

    def unregister(self, name: str) -> None:
        """
        Unregister a policy module.
        
        Args:
            name: Name of the policy to unregister
            
        Raises:
            KeyError: If policy is not registered
        """
        if name not in self._policies:
            raise KeyError(f"Policy '{name}' is not registered")
        
        del self._policies[name]

    def get_policy(self, name: str) -> Optional[PolicyModule]:
        """
        Get a registered policy by name.
        
        Args:
            name: Name of the policy to retrieve
            
        Returns:
            PolicyModule instance if found, None otherwise
        """
        return self._policies.get(name)

    def get_all_policies(self) -> Dict[str, PolicyModule]:
        """
        Get all registered policies.
        
        Returns:
            Dictionary mapping policy names to PolicyModule instances
        """
        return self._policies.copy()  # Return copy to prevent external modification

    def is_registered(self, name: str) -> bool:
        """
        Check if a policy is registered.
        
        Args:
            name: Name of the policy to check
            
        Returns:
            True if policy is registered, False otherwise
        """
        return name in self._policies

    def get_policy_names(self) -> list[str]:
        """
        Get list of all registered policy names.
        
        Returns:
            List of policy names
        """
        return list(self._policies.keys())

    def clear(self) -> None:
        """Clear all registered policies."""
        self._policies.clear()

    def count(self) -> int:
        """
        Get the number of registered policies.
        
        Returns:
            Number of registered policies
        """
        return len(self._policies)

