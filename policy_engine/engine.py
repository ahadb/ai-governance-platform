"""
Policy Engine - Main orchestrator for policy evaluation.

Ties together the registry and config loader to evaluate policies
against requests and responses.
"""

import time
from typing import List, Optional

from policy_engine.config_loader import PolicyConfig, load_policy_config
from policy_engine.interfaces import PolicyModule
from policy_engine.models import (
    PolicyContext,
    PolicyEvaluationResult,
    PolicyOutcome,
    PolicyResult,
)
from policy_engine.registry import PolicyRegistry


class PolicyEngine:
    """
    Main policy engine that orchestrates policy evaluation.
    
    Combines the registry (policy modules) and config loader (which policies
    to run) to evaluate requests/responses against active policies.
    """

    def __init__(
        self,
        registry: PolicyRegistry,
        config_path: Optional[str] = None,
    ):
        """
        Initialize the policy engine.
        
        Args:
            registry: PolicyRegistry containing registered policy modules
            config_path: Path to YAML config file. If None, no config is loaded.
                        Can be loaded later with load_configuration().
        """
        self._registry = registry
        self._config_path: Optional[str] = config_path
        self._active_policies: List[tuple[str, PolicyModule]] = []  # (name, module) tuples
        
        if config_path:
            self.load_configuration(config_path)

    def load_configuration(self, config_path: str) -> None:
        """
        Load policy configuration from YAML file.
        
        Loads config, matches policies to registry, and builds the list
        of active (enabled) policies.
        
        Args:
            config_path: Path to YAML configuration file
            
        Raises:
            FileNotFoundError: If config file doesn't exist
            ValueError: If config references policies not in registry
        """
        self._config_path = config_path
        policy_configs = load_policy_config(config_path)
        
        # Match config to registry and build active policies list
        self._active_policies = []
        missing_policies = []
        
        for policy_config in policy_configs:
            policy_name = policy_config.name
            policy_module = self._registry.get_policy(policy_name)
            
            if policy_module is None:
                missing_policies.append(policy_name)
                continue  # Skip policies not in registry
            
            if policy_config.enabled:
                # Configure the policy with its config
                policy_module.configure(policy_config.config)
                self._active_policies.append((policy_name, policy_module))
        
        if missing_policies:
            # TODO: Replace print() with proper logging (structlog)
            # TODO: Make this configurable - fail hard in production, warn in dev
            print(f"Warning: Config references policies not in registry: {missing_policies}")

    def get_active_policies(self) -> List[tuple[str, PolicyModule]]:
        """
        Get list of active (enabled) policies.
        
        Returns:
            List of (name, PolicyModule) tuples for enabled policies
        """
        return self._active_policies.copy()

    def evaluate(self, context: PolicyContext) -> PolicyEvaluationResult:
        """
        Evaluate policies against the given context.
        
        Runs all active policies in sequence, collects results, and applies
        precedence rules to determine the final outcome.
        
        Args:
            context: PolicyContext containing request/response data
            
        Returns:
            PolicyEvaluationResult with final outcome and all individual results
        """
        start_time = time.time()
        all_results: List[PolicyResult] = []
        evaluated_policy_names: List[str] = []
        
        # Run each active policy
        for policy_name, policy_module in self._active_policies:
            try:
                # Evaluate policy
                result = policy_module.evaluate(context)
                all_results.append(result)
                evaluated_policy_names.append(policy_name)
                
                # Update context with prior outcomes for next policy
                context.prior_outcomes.append(result.outcome)
                
            except Exception as e:
                # Policy evaluation failed - log and continue or fail?
                # For now, we'll create a BLOCK result for safety
                error_result = PolicyResult(
                    outcome=PolicyOutcome.BLOCK,
                    reason=f"Policy '{policy_name}' evaluation failed: {str(e)}",
                    policy_name=policy_name,
                    confidence_score=1.0,
                )
                all_results.append(error_result)
                evaluated_policy_names.append(policy_name)
                context.prior_outcomes.append(PolicyOutcome.BLOCK)
        
        # Apply precedence rules to determine final outcome
        if not all_results:
            # No policies ran - default to ALLOW
            final_outcome = PolicyOutcome.ALLOW
            final_result = PolicyResult(
                outcome=PolicyOutcome.ALLOW,
                reason="No active policies to evaluate",
                policy_name="system",
                confidence_score=1.0,
            )
        else:
            # Get outcomes from all results
            outcomes = [result.outcome for result in all_results]
            final_outcome = PolicyOutcome.resolve_precedence(outcomes)
            
            # Find the result that produced the final outcome
            # (the most restrictive one)
            final_result = next(
                (result for result in all_results if result.outcome == final_outcome),
                all_results[0],  # Fallback to first result
            )
        
        # Calculate evaluation time
        evaluation_time_ms = (time.time() - start_time) * 1000
        
        return PolicyEvaluationResult(
            final_outcome=final_outcome,
            final_result=final_result,
            all_results=all_results,
            evaluated_policies=evaluated_policy_names,
            evaluation_time_ms=evaluation_time_ms,
        )

    def register_policy(self, name: str, policy: PolicyModule) -> None:
        """
        Register a policy module.
        
        Convenience method that delegates to registry.
        
        Args:
            name: Policy name
            policy: PolicyModule instance
        """
        self._registry.register(name, policy)
        
        # If config is loaded, reload to pick up new policy
        if self._config_path:
            self.load_configuration(self._config_path)

