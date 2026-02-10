"""
Example policy module demonstrating the PolicyModule interface.

This is a simple example that can be used as a template for creating
new policy modules.
"""

from policy_engine.interfaces import PolicyModule
from policy_engine.models import PolicyContext, PolicyOutcome, PolicyResult


class ExamplePolicy(PolicyModule):
    """
    Example policy that demonstrates the interface contract.
    
    This policy always returns ALLOW - replace the logic with your
    actual policy evaluation.
    """

    def __init__(self):
        self._name = "example_policy"

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        """
        Evaluate the policy.
        
        In a real policy, you would:
        - Analyze the prompt content
        - Check against watchlists, patterns, ML models
        - Make decision based on business rules
        - Return appropriate outcome
        """
        # Example: Simple check on prompt length
        if len(context.prompt) > 10000:
            return PolicyResult(
                outcome=PolicyOutcome.BLOCK,
                reason="Prompt exceeds maximum length",
                policy_name=self.name,
                confidence_score=1.0,
            )

        return PolicyResult(
            outcome=PolicyOutcome.ALLOW,
            reason="No issues detected",
            policy_name=self.name,
            confidence_score=1.0,
        )

    def configure(self, config: dict) -> None:
        """Configure the policy with settings from config file."""
        # Example: Read configuration
        # self.max_length = config.get("max_length", 10000)
        pass

