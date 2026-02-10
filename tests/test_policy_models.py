"""
Tests for core policy models and interfaces.
"""

import pytest

from policy_engine.interfaces import PolicyModule
from policy_engine.models import PolicyContext, PolicyOutcome, PolicyResult


class TestPolicyOutcome:
    """Test PolicyOutcome enum and precedence logic."""

    def test_outcome_values(self):
        """Test that all expected outcomes exist."""
        assert PolicyOutcome.ALLOW == "ALLOW"
        assert PolicyOutcome.BLOCK == "BLOCK"
        assert PolicyOutcome.REDACT == "REDACT"
        assert PolicyOutcome.ESCALATE == "ESCALATE"

    def test_precedence_order(self):
        """Test that precedence follows: BLOCK > ESCALATE > REDACT > ALLOW."""
        assert PolicyOutcome.get_precedence(PolicyOutcome.BLOCK) == 1
        assert PolicyOutcome.get_precedence(PolicyOutcome.ESCALATE) == 2
        assert PolicyOutcome.get_precedence(PolicyOutcome.REDACT) == 3
        assert PolicyOutcome.get_precedence(PolicyOutcome.ALLOW) == 4

    def test_resolve_precedence_block_wins(self):
        """Test that BLOCK takes precedence over all others."""
        outcomes = [
            PolicyOutcome.ALLOW,
            PolicyOutcome.REDACT,
            PolicyOutcome.BLOCK,
            PolicyOutcome.ESCALATE,
        ]
        assert PolicyOutcome.resolve_precedence(outcomes) == PolicyOutcome.BLOCK

    def test_resolve_precedence_escalate_over_redact(self):
        """Test that ESCALATE takes precedence over REDACT and ALLOW."""
        outcomes = [PolicyOutcome.ALLOW, PolicyOutcome.REDACT, PolicyOutcome.ESCALATE]
        assert PolicyOutcome.resolve_precedence(outcomes) == PolicyOutcome.ESCALATE

    def test_resolve_precedence_redact_over_allow(self):
        """Test that REDACT takes precedence over ALLOW."""
        outcomes = [PolicyOutcome.ALLOW, PolicyOutcome.REDACT]
        assert PolicyOutcome.resolve_precedence(outcomes) == PolicyOutcome.REDACT

    def test_resolve_precedence_empty_list(self):
        """Test that empty list defaults to ALLOW."""
        assert PolicyOutcome.resolve_precedence([]) == PolicyOutcome.ALLOW


class TestPolicyContext:
    """Test PolicyContext model."""

    def test_create_minimal_context(self):
        """Test creating context with only required fields."""
        context = PolicyContext(
            prompt="Test prompt",
            user_id="user123",
            checkpoint="input",
        )
        assert context.prompt == "Test prompt"
        assert context.user_id == "user123"
        assert context.checkpoint == "input"
        assert context.response is None
        assert context.prior_outcomes == []

    def test_create_full_context(self):
        """Test creating context with all fields."""
        context = PolicyContext(
            prompt="Test prompt",
            response="Test response",
            user_id="user123",
            user_role="analyst",
            user_email="user@example.com",
            data_classification="confidential",
            customer_id="customer1",
            vertical="finance",
            request_id="req123",
            checkpoint="output",
            prior_outcomes=[PolicyOutcome.ALLOW],
            metadata={"key": "value"},
        )
        assert context.user_role == "analyst"
        assert context.vertical == "finance"
        assert context.prior_outcomes == [PolicyOutcome.ALLOW]

    def test_context_validation(self):
        """Test that required fields are enforced."""
        with pytest.raises(Exception):  # Pydantic validation error
            PolicyContext()  # Missing required fields


class TestPolicyResult:
    """Test PolicyResult model."""

    def test_create_allow_result(self):
        """Test creating an ALLOW result."""
        result = PolicyResult(
            outcome=PolicyOutcome.ALLOW,
            reason="No issues found",
            policy_name="test_policy",
        )
        assert result.outcome == PolicyOutcome.ALLOW
        assert result.reason == "No issues found"
        assert result.modified_content is None

    def test_create_redact_result(self):
        """Test creating a REDACT result with modified content."""
        result = PolicyResult(
            outcome=PolicyOutcome.REDACT,
            reason="PII detected and redacted",
            policy_name="pii_detection",
            modified_content="Hello [REDACTED:PII:ref_123]",
            redaction_tokens={"ref_123": "John Doe"},
        )
        assert result.outcome == PolicyOutcome.REDACT
        assert result.modified_content == "Hello [REDACTED:PII:ref_123]"
        assert result.redaction_tokens == {"ref_123": "John Doe"}

    def test_confidence_score_validation(self):
        """Test that confidence score must be between 0 and 1."""
        # Valid scores
        result1 = PolicyResult(
            outcome=PolicyOutcome.ALLOW,
            reason="Test",
            policy_name="test",
            confidence_score=0.5,
        )
        assert result1.confidence_score == 0.5

        # Invalid scores should raise validation error
        with pytest.raises(Exception):  # Pydantic validation error
            PolicyResult(
                outcome=PolicyOutcome.ALLOW,
                reason="Test",
                policy_name="test",
                confidence_score=1.5,  # > 1.0
            )


class TestPolicyModuleInterface:
    """Test PolicyModule abstract interface."""

    def test_cannot_instantiate_abstract_class(self):
        """Test that PolicyModule cannot be instantiated directly."""
        with pytest.raises(TypeError):
            PolicyModule()  # Abstract class cannot be instantiated

    def test_concrete_implementation(self):
        """Test that a concrete implementation works."""
        from policies.example_policy import ExamplePolicy

        policy = ExamplePolicy()
        assert isinstance(policy, PolicyModule)
        assert policy.name == "example_policy"

        context = PolicyContext(
            prompt="Short prompt",
            user_id="user123",
            checkpoint="input",
        )
        result = policy.evaluate(context)
        assert isinstance(result, PolicyResult)
        # result.outcome is a string due to use_enum_values=True, so check if it's a valid enum value
        assert result.outcome in [outcome.value for outcome in PolicyOutcome]

