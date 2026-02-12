"""
Gateway Orchestrator - Implements the dual checkpoint validation flow.

Orchestrates Policy Engine and Model Router to process LLM requests
with governance at both input and output stages.
"""

import uuid
from typing import Optional

from model_router import LLMMessage, LLMRequest, LLMResponse, ModelRouter
from model_router.exceptions import ModelRouterError
from policy_engine.engine import PolicyEngine
from policy_engine.models import PolicyContext, PolicyOutcome, PolicyEvaluationResult

# TODO: Replace with real audit module when implemented
class AuditStub:
    """Stub for audit logging - will be replaced with real implementation."""
    
    def log(self, request_id: str, event_type: str, data: dict) -> None:
        """Stub audit logging - does nothing for now."""
        pass

# TODO: Replace with real HITL module when implemented
class HITLStub:
    """Stub for human-in-the-loop - will be replaced with real implementation."""
    
    def escalate(self, request_id: str, context: PolicyContext, reason: str) -> str:
        """
        Stub escalation - returns a review ID but doesn't actually queue.
        
        Returns:
            Review ID (stub value)
        """
        return f"review_{uuid.uuid4().hex[:8]}"


class GatewayOrchestrator:
    """
    Orchestrates the dual checkpoint validation flow.
    
    Flow:
    1. Input checkpoint: Evaluate policies on user prompt
    2. If ALLOW/REDACT: Route to Model Router
    3. Output checkpoint: Evaluate policies on LLM response
    4. Return response (possibly redacted)
    """

    def __init__(
        self,
        policy_engine: PolicyEngine,
        model_router: ModelRouter,
        audit: Optional[AuditStub] = None,
        hitl: Optional[HITLStub] = None,
    ):
        """
        Initialize the Gateway Orchestrator.
        
        Args:
            policy_engine: PolicyEngine instance for policy evaluation
            model_router: ModelRouter instance for LLM routing
            audit: Audit module (stub for now)
            hitl: HITL module (stub for now)
        """
        self._policy_engine = policy_engine
        self._model_router = model_router
        self._audit = audit or AuditStub()
        self._hitl = hitl or HITLStub()

    def process_request(
        self,
        prompt: str,
        user_id: str,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
        user_role: Optional[str] = None,
        user_email: Optional[str] = None,
        metadata: Optional[dict] = None,
    ) -> tuple[LLMResponse, PolicyEvaluationResult, PolicyEvaluationResult]:
        """
        Process an LLM request through the dual checkpoint flow.
        
        Args:
            prompt: User's input prompt
            user_id: User identifier
            model: Model to use (optional, uses router default if not provided)
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            user_role: User's role (optional)
            user_email: User's email (optional)
            metadata: Additional metadata
            
        Returns:
            Tuple of (LLMResponse, input_policy_result, output_policy_result)
            
        Raises:
            ValueError: If input policies BLOCK or ESCALATE
            ModelRouterError: If model routing fails
        """
        request_id = str(uuid.uuid4())
        metadata = metadata or {}
        
        # Log request
        self._audit.log(
            request_id,
            "request_received",
            {"user_id": user_id, "prompt_length": len(prompt)},
        )
        
        # ===== INPUT CHECKPOINT =====
        input_context = PolicyContext(
            prompt=prompt,
            user_id=user_id,
            user_role=user_role,
            user_email=user_email,
            checkpoint="input",
            request_id=request_id,
            metadata=metadata,
        )
        
        input_result = self._policy_engine.evaluate(input_context)
        
        # Log input evaluation
        self._audit.log(
            request_id,
            "input_policy_evaluation",
            {
                "outcome": input_result.final_outcome,
                "policies_evaluated": input_result.evaluated_policies,
            },
        )
        
        # Handle input checkpoint outcomes
        if input_result.final_outcome == PolicyOutcome.BLOCK:
            self._audit.log(request_id, "request_blocked", {"reason": input_result.final_result.reason})
            raise ValueError(f"Request blocked by policy: {input_result.final_result.reason}")
        
        if input_result.final_outcome == PolicyOutcome.ESCALATE:
            review_id = self._hitl.escalate(request_id, input_context, input_result.final_result.reason)
            self._audit.log(request_id, "request_escalated", {"review_id": review_id})
            raise ValueError(
                f"Request escalated for human review (ID: {review_id}): {input_result.final_result.reason}"
            )
        
        # Use redacted prompt if REDACT outcome
        prompt_to_use = (
            input_result.final_result.modified_content
            if input_result.final_outcome == PolicyOutcome.REDACT
            and input_result.final_result.modified_content
            else prompt
        )
        
        # ===== ROUTE TO MODEL ROUTER =====
        # Convert to LLMRequest format
        llm_request = LLMRequest(
            messages=[
                LLMMessage(role="user", content=prompt_to_use)
            ],
            model=model or "",  # Empty string will trigger router default
            temperature=temperature,
            max_tokens=max_tokens,
            user_id=user_id,
            metadata={**metadata, "request_id": request_id, "input_redacted": input_result.final_outcome == PolicyOutcome.REDACT},
        )
        
        try:
            llm_response = self._model_router.route(llm_request)
        except ModelRouterError as e:
            self._audit.log(request_id, "router_error", {"error": str(e)})
            raise
        
        # Log LLM response
        self._audit.log(
            request_id,
            "llm_response_received",
            {
                "model": llm_response.model,
                "provider": llm_response.provider,
                "content_length": len(llm_response.content),
            },
        )
        
        # ===== OUTPUT CHECKPOINT =====
        output_context = PolicyContext(
            prompt=prompt_to_use,  # Use the prompt that was actually sent
            response=llm_response.content,
            user_id=user_id,
            user_role=user_role,
            user_email=user_email,
            checkpoint="output",
            request_id=request_id,
            prior_outcomes=[input_result.final_outcome],  # Include input outcome
            metadata={**metadata, "input_redacted": input_result.final_outcome == PolicyOutcome.REDACT},
        )
        
        output_result = self._policy_engine.evaluate(output_context)
        
        # Log output evaluation
        self._audit.log(
            request_id,
            "output_policy_evaluation",
            {
                "outcome": output_result.final_outcome,
                "policies_evaluated": output_result.evaluated_policies,
            },
        )
        
        # Handle output checkpoint outcomes
        if output_result.final_outcome == PolicyOutcome.BLOCK:
            self._audit.log(request_id, "response_blocked", {"reason": output_result.final_result.reason})
            raise ValueError(f"Response blocked by policy: {output_result.final_result.reason}")
        
        if output_result.final_outcome == PolicyOutcome.ESCALATE:
            review_id = self._hitl.escalate(request_id, output_context, output_result.final_result.reason)
            self._audit.log(request_id, "response_escalated", {"review_id": review_id})
            raise ValueError(
                f"Response escalated for human review (ID: {review_id}): {output_result.final_result.reason}"
            )
        
        # Apply redaction to response if needed
        if output_result.final_outcome == PolicyOutcome.REDACT and output_result.final_result.modified_content:
            llm_response.content = output_result.final_result.modified_content
        
        # Log final response
        self._audit.log(
            request_id,
            "request_completed",
            {
                "final_outcome": output_result.final_outcome,
                "response_redacted": output_result.final_outcome == PolicyOutcome.REDACT,
            },
        )
        
        return llm_response, input_result, output_result

