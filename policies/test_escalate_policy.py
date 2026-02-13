"""
Test policy that returns ESCALATE for testing HITL module.

This is a temporary test policy - replace with real escalation logic.
"""

from policy_engine.interfaces import PolicyModule
from policy_engine.models import PolicyContext, PolicyOutcome, PolicyResult


class TestEscalatePolicy(PolicyModule):
    """
    Test policy that escalates requests containing specific keywords.
    
    Use this to test the HITL module.
    """

    def __init__(self):
        self._name = "test_escalate"

    @property
    def name(self) -> str:
        return self._name

    def evaluate(self, context: PolicyContext) -> PolicyResult:
        """
        Evaluate the policy.
        
        Escalates if prompt contains "escalate" or "review needed".
        """
        prompt_lower = context.prompt.lower()
        
        # Check for escalation keywords
        escalation_keywords = [
            "escalate",
            "review needed",
            "human review",
            "needs approval",
            "senior review",
        ]
        
        if any(keyword in prompt_lower for keyword in escalation_keywords):
            return PolicyResult(
                outcome=PolicyOutcome.ESCALATE,
                reason="Request contains keywords requiring human review",
                policy_name=self.name,
                confidence_score=0.9,
            )

        return PolicyResult(
            outcome=PolicyOutcome.ALLOW,
            reason="No escalation keywords detected",
            policy_name=self.name,
            confidence_score=1.0,
        )

    def configure(self, config: dict) -> None:
        """Configure the policy with settings from config file."""
        pass

