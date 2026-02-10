"""
Tests for Policy Engine.
"""

import tempfile
from pathlib import Path

import pytest
import yaml

from policy_engine.engine import PolicyEngine
from policy_engine.models import PolicyContext, PolicyOutcome, PolicyResult
from policy_engine.registry import PolicyRegistry
from policies.example_policy import ExamplePolicy


class TestPolicyEngine:
    """Test PolicyEngine functionality."""

    def test_initialization_without_config(self):
        """Test engine initialization without config."""
        registry = PolicyRegistry()
        engine = PolicyEngine(registry)
        
        assert engine._registry == registry
        assert engine._config_path is None
        assert len(engine.get_active_policies()) == 0

    def test_initialization_with_config(self):
        """Test engine initialization with config path."""
        registry = PolicyRegistry()
        registry.register("test_policy", ExamplePolicy())
        
        config_data = {
            "policies": [
                {"name": "test_policy", "enabled": True},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(registry, config_path=temp_path)
            assert engine._config_path == temp_path
            assert len(engine.get_active_policies()) == 1
        finally:
            Path(temp_path).unlink()

    def test_load_configuration(self):
        """Test loading configuration after initialization."""
        registry = PolicyRegistry()
        registry.register("policy1", ExamplePolicy())
        registry.register("policy2", ExamplePolicy())
        
        config_data = {
            "policies": [
                {"name": "policy1", "enabled": True},
                {"name": "policy2", "enabled": False},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(registry)
            engine.load_configuration(temp_path)
            
            active = engine.get_active_policies()
            assert len(active) == 1
            assert active[0][0] == "policy1"  # name
            assert isinstance(active[0][1], ExamplePolicy)  # module
        finally:
            Path(temp_path).unlink()

    def test_load_configuration_missing_policy(self):
        """Test that missing policies in registry are handled gracefully."""
        registry = PolicyRegistry()
        # Don't register "policy1"
        
        config_data = {
            "policies": [
                {"name": "policy1", "enabled": True},  # Not in registry
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(registry, config_path=temp_path)
            # Should not raise error, just log warning
            assert len(engine.get_active_policies()) == 0
        finally:
            Path(temp_path).unlink()

    def test_evaluate_no_policies(self):
        """Test evaluation when no policies are active."""
        registry = PolicyRegistry()
        engine = PolicyEngine(registry)
        
        context = PolicyContext(
            prompt="Test prompt",
            user_id="user123",
            checkpoint="input",
        )
        
        result = engine.evaluate(context)
        
        assert result.final_outcome == PolicyOutcome.ALLOW
        assert result.final_result.reason == "No active policies to evaluate"
        assert len(result.all_results) == 0
        assert len(result.evaluated_policies) == 0

    def test_evaluate_single_policy(self):
        """Test evaluation with a single active policy."""
        registry = PolicyRegistry()
        policy = ExamplePolicy()
        registry.register("example", policy)
        
        config_data = {
            "policies": [
                {"name": "example", "enabled": True},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(registry, config_path=temp_path)
            
            context = PolicyContext(
                prompt="Short prompt",
                user_id="user123",
                checkpoint="input",
            )
            
            result = engine.evaluate(context)
            
            assert result.final_outcome == PolicyOutcome.ALLOW
            assert len(result.all_results) == 1
            assert result.all_results[0].policy_name == "example"
            assert len(result.evaluated_policies) == 1
            assert result.evaluated_policies[0] == "example"
            assert result.evaluation_time_ms >= 0
        finally:
            Path(temp_path).unlink()

    def test_evaluate_multiple_policies(self):
        """Test evaluation with multiple active policies."""
        registry = PolicyRegistry()
        
        # Create multiple policies
        policy1 = ExamplePolicy()
        policy2 = ExamplePolicy()
        policy3 = ExamplePolicy()
        
        registry.register("policy1", policy1)
        registry.register("policy2", policy2)
        registry.register("policy3", policy3)
        
        config_data = {
            "policies": [
                {"name": "policy1", "enabled": True},
                {"name": "policy2", "enabled": True},
                {"name": "policy3", "enabled": False},  # Disabled
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(registry, config_path=temp_path)
            
            context = PolicyContext(
                prompt="Test prompt",
                user_id="user123",
                checkpoint="input",
            )
            
            result = engine.evaluate(context)
            
            # Should have evaluated 2 policies (policy3 is disabled)
            assert len(result.evaluated_policies) == 2
            assert "policy1" in result.evaluated_policies
            assert "policy2" in result.evaluated_policies
            assert "policy3" not in result.evaluated_policies
            assert len(result.all_results) == 2
        finally:
            Path(temp_path).unlink()

    def test_evaluate_precedence_block_wins(self):
        """Test that BLOCK outcome takes precedence."""
        registry = PolicyRegistry()
        
        # Create a policy that returns BLOCK
        class BlockingPolicy(ExamplePolicy):
            def evaluate(self, context):
                return PolicyResult(
                    outcome=PolicyOutcome.BLOCK,
                    reason="Blocked by test policy",
                    policy_name=self.name,
                    confidence_score=1.0,
                )
        
        policy1 = ExamplePolicy()  # Returns ALLOW
        policy2 = BlockingPolicy()  # Returns BLOCK
        
        registry.register("allow_policy", policy1)
        registry.register("block_policy", policy2)
        
        config_data = {
            "policies": [
                {"name": "allow_policy", "enabled": True},
                {"name": "block_policy", "enabled": True},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(registry, config_path=temp_path)
            
            context = PolicyContext(
                prompt="Test",
                user_id="user123",
                checkpoint="input",
            )
            
            result = engine.evaluate(context)
            
            # BLOCK should win
            assert result.final_outcome == PolicyOutcome.BLOCK
            assert result.final_result.outcome == PolicyOutcome.BLOCK
            assert result.final_result.policy_name == "block_policy"
        finally:
            Path(temp_path).unlink()

    def test_evaluate_updates_context_prior_outcomes(self):
        """Test that context.prior_outcomes is updated during evaluation."""
        registry = PolicyRegistry()
        
        policy1 = ExamplePolicy()
        policy2 = ExamplePolicy()
        
        registry.register("policy1", policy1)
        registry.register("policy2", policy2)
        
        config_data = {
            "policies": [
                {"name": "policy1", "enabled": True},
                {"name": "policy2", "enabled": True},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(registry, config_path=temp_path)
            
            context = PolicyContext(
                prompt="Test",
                user_id="user123",
                checkpoint="input",
            )
            
            assert len(context.prior_outcomes) == 0
            
            result = engine.evaluate(context)
            
            # Context should have been updated with outcomes
            assert len(context.prior_outcomes) == 2
            assert all(outcome in PolicyOutcome for outcome in context.prior_outcomes)
        finally:
            Path(temp_path).unlink()

    def test_register_policy_reloads_config(self):
        """Test that registering a policy reloads config if loaded."""
        registry = PolicyRegistry()
        
        config_data = {
            "policies": [
                {"name": "new_policy", "enabled": True},
            ]
        }
        
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            yaml.dump(config_data, f)
            temp_path = f.name
        
        try:
            engine = PolicyEngine(registry, config_path=temp_path)
            # No policies registered yet
            assert len(engine.get_active_policies()) == 0
            
            # Register policy that matches config
            policy = ExamplePolicy()
            engine.register_policy("new_policy", policy)
            
            # Config should be reloaded and policy should be active
            assert len(engine.get_active_policies()) == 1
        finally:
            Path(temp_path).unlink()

