"""
Tests for Policy Registry.
"""

import pytest

from policy_engine.interfaces import PolicyModule
from policy_engine.models import PolicyContext, PolicyOutcome, PolicyResult
from policy_engine.registry import PolicyRegistry
from policies.example_policy import ExamplePolicy


class TestPolicyRegistry:
    """Test PolicyRegistry functionality."""

    def test_initialization(self):
        """Test that registry starts empty."""
        registry = PolicyRegistry()
        assert registry.count() == 0
        assert registry.get_all_policies() == {}

    def test_register_policy(self):
        """Test registering a policy."""
        registry = PolicyRegistry()
        policy = ExamplePolicy()
        
        registry.register("example", policy)
        
        assert registry.is_registered("example")
        assert registry.count() == 1
        assert registry.get_policy("example") == policy

    def test_register_duplicate_raises_error(self):
        """Test that registering duplicate name raises KeyError."""
        registry = PolicyRegistry()
        policy1 = ExamplePolicy()
        policy2 = ExamplePolicy()
        
        registry.register("example", policy1)
        
        with pytest.raises(KeyError, match="already registered"):
            registry.register("example", policy2)

    def test_register_empty_name_raises_error(self):
        """Test that registering with empty name raises ValueError."""
        registry = PolicyRegistry()
        policy = ExamplePolicy()
        
        with pytest.raises(ValueError, match="cannot be empty"):
            registry.register("", policy)
        
        with pytest.raises(ValueError, match="cannot be empty"):
            registry.register("   ", policy)

    def test_register_non_policy_raises_error(self):
        """Test that registering non-PolicyModule raises ValueError."""
        registry = PolicyRegistry()
        
        with pytest.raises(ValueError, match="must be an instance of PolicyModule"):
            registry.register("invalid", "not a policy")

    def test_get_policy_existing(self):
        """Test retrieving an existing policy."""
        registry = PolicyRegistry()
        policy = ExamplePolicy()
        registry.register("example", policy)
         
        retrieved = registry.get_policy("example")
        assert retrieved == policy
        assert isinstance(retrieved, PolicyModule)

    def test_get_policy_nonexistent(self):
        """Test retrieving a non-existent policy returns None."""
        registry = PolicyRegistry()
        
        assert registry.get_policy("nonexistent") is None

    def test_get_all_policies(self):
        """Test getting all registered policies."""
        registry = PolicyRegistry()
        policy1 = ExamplePolicy()
        policy2 = ExamplePolicy()
        
        registry.register("policy1", policy1)
        registry.register("policy2", policy2)
        
        all_policies = registry.get_all_policies()
        assert len(all_policies) == 2
        assert all_policies["policy1"] == policy1
        assert all_policies["policy2"] == policy2
        # Should be a copy, not the original dict
        assert all_policies is not registry._policies

    def test_is_registered(self):
        """Test checking if policy is registered."""
        registry = PolicyRegistry()
        policy = ExamplePolicy()
        
        assert registry.is_registered("example") is False
        
        registry.register("example", policy)
        assert registry.is_registered("example") is True

    def test_get_policy_names(self):
        """Test getting list of policy names."""
        registry = PolicyRegistry()
        policy1 = ExamplePolicy()
        policy2 = ExamplePolicy()
        
        registry.register("policy1", policy1)
        registry.register("policy2", policy2)
        
        names = registry.get_policy_names()
        assert set(names) == {"policy1", "policy2"}

    def test_unregister_policy(self):
        """Test unregistering a policy."""
        registry = PolicyRegistry()
        policy = ExamplePolicy()
        
        registry.register("example", policy)
        assert registry.is_registered("example")
        
        registry.unregister("example")
        assert registry.is_registered("example") is False
        assert registry.get_policy("example") is None

    def test_unregister_nonexistent_raises_error(self):
        """Test that unregistering non-existent policy raises KeyError."""
        registry = PolicyRegistry()
        
        with pytest.raises(KeyError, match="is not registered"):
            registry.unregister("nonexistent")

    def test_clear_registry(self):
        """Test clearing all policies."""
        registry = PolicyRegistry()
        policy1 = ExamplePolicy()
        policy2 = ExamplePolicy()
        
        registry.register("policy1", policy1)
        registry.register("policy2", policy2)
        assert registry.count() == 2
        
        registry.clear()
        assert registry.count() == 0
        assert registry.get_all_policies() == {}

    def test_count(self):
        """Test counting registered policies."""
        registry = PolicyRegistry()
        assert registry.count() == 0
        
        registry.register("policy1", ExamplePolicy())
        assert registry.count() == 1
        
        registry.register("policy2", ExamplePolicy())
        assert registry.count() == 2
        
        registry.unregister("policy1")
        assert registry.count() == 1

