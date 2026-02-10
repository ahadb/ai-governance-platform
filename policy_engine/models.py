"""
Core data models for policy evaluation.

Defines PolicyOutcome, PolicyContext, and related structures that form
the contract between the policy engine and policy modules.
"""

from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, ConfigDict, Field


class PolicyOutcome(str, Enum):
    """
    The four possible outcomes of policy evaluation.
    
    Precedence (most to least restrictive):
    1. BLOCK - Stops flow immediately
    2. ESCALATE - Requires human review
    3. REDACT - Modifies content but allows
    4. ALLOW - Proceeds unchanged
    """

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    REDACT = "REDACT"
    ESCALATE = "ESCALATE"

    @classmethod
    def get_precedence(cls, outcome: "PolicyOutcome") -> int:
        """
        Get precedence value for outcome comparison.
        Lower number = higher precedence (more restrictive).
        """
        precedence_map = {
            cls.BLOCK: 1,
            cls.ESCALATE: 2,
            cls.REDACT: 3,
            cls.ALLOW: 4,
        }
        return precedence_map.get(outcome, 4)

    @classmethod
    def resolve_precedence(cls, outcomes: list["PolicyOutcome"]) -> "PolicyOutcome":
        """
        Resolve multiple outcomes to the most restrictive one.
        
        Args:
            outcomes: List of policy outcomes to resolve
            
        Returns:
            The most restrictive outcome based on precedence rules
        """
        if not outcomes:
            return cls.ALLOW

        return min(outcomes, key=cls.get_precedence)


class PolicyContext(BaseModel):
    """
    Universal context passed to every policy module for evaluation.
    
    This must be comprehensive upfront as it's the only data policies receive.
    Changes to PolicyContext break all existing policies, so design carefully.
    """

    # Request content
    prompt: str = Field(..., description="The user's prompt/request content")
    response: Optional[str] = Field(
        None, description="LLM response (only present for output checkpoint evaluation)"
    )

    # User identity
    user_id: str = Field(..., description="Unique identifier for the user")
    user_role: Optional[str] = Field(None, description="User's role (e.g., 'trader', 'analyst')")
    user_email: Optional[str] = Field(None, description="User's email address")

    # Data classification
    data_classification: Optional[str] = Field(
        None, description="Data classification level (e.g., 'public', 'confidential', 'restricted')"
    )

    # Metadata
    customer_id: Optional[str] = Field(None, description="Customer/tenant identifier")
    vertical: Optional[str] = Field(
        None, description="Industry vertical (e.g., 'finance', 'healthcare', 'government')"
    )
    request_id: Optional[str] = Field(None, description="Unique request identifier for tracing")

    # Checkpoint information
    checkpoint: str = Field(
        ..., description="Which checkpoint: 'input' or 'output'"
    )

    # Prior policy decisions (if running multiple policies)
    prior_outcomes: list[PolicyOutcome] = Field(
        default_factory=list,
        description="Outcomes from previously evaluated policies in this request",
    )

    # Additional metadata (extensible)
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context-specific metadata",
    )

    model_config = ConfigDict(use_enum_values=True)


class PolicyResult(BaseModel):
    """
    Complete result from a policy evaluation, including outcome and details.
    """

    outcome: PolicyOutcome = Field(..., description="The policy decision")
    reason: str = Field(..., description="Human-readable explanation of the decision")
    modified_content: Optional[str] = Field(
        None,
        description="Modified content (only present for REDACT outcome). Original stored separately.",
    )
    confidence_score: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score of the policy decision (0.0 to 1.0)",
    )
    policy_name: str = Field(..., description="Name of the policy that produced this result")
    redaction_tokens: Optional[Dict[str, str]] = Field(
        None,
        description="Mapping of redaction tokens to original values (for REDACT outcomes)",
    )

    model_config = ConfigDict(use_enum_values=True)


class PolicyEvaluationResult(BaseModel):
    """
    Complete result from Policy Engine evaluation.
    
    Contains the final outcome after running all active policies and
    applying precedence rules, plus all individual policy results.
    """

    final_outcome: PolicyOutcome = Field(..., description="Final outcome after precedence resolution")
    final_result: PolicyResult = Field(..., description="The PolicyResult that produced the final outcome")
    all_results: list[PolicyResult] = Field(
        default_factory=list,
        description="All policy evaluation results (for debugging and audit)",
    )
    evaluated_policies: list[str] = Field(
        default_factory=list,
        description="Names of policies that were evaluated",
    )
    evaluation_time_ms: float = Field(
        ...,
        description="Time taken for evaluation in milliseconds",
    )

    model_config = ConfigDict(use_enum_values=True)

