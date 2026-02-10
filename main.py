"""
Main entry point for AI Governance Platform.

Demonstrates MNPI and PII detection policies in action.
"""

from policy_engine.engine import PolicyEngine
from policy_engine.models import PolicyContext, PolicyOutcome
from policy_engine.registry import PolicyRegistry
from policies.finance import MNPIPolicy, PIIDetectionPolicy


def evaluate_and_display(engine: PolicyEngine, prompt: str, description: str):
    """Helper function to evaluate a prompt and display results."""
    print(f"\n{'='*70}")
    print(f"Test: {description}")
    print(f"{'='*70}")
    print(f"Prompt: {prompt}")
    
    context = PolicyContext(
        prompt=prompt,
        user_id="user123",
        checkpoint="input",
    )
    
    result = engine.evaluate(context)
    
    print(f"\nResult:")
    print(f"  Final Outcome: {result.final_outcome}")
    print(f"  Reason: {result.final_result.reason}")
    print(f"  Policies Evaluated: {len(result.evaluated_policies)}")
    print(f"  Evaluation Time: {result.evaluation_time_ms:.2f}ms")
    
    if result.all_results:
        print(f"\nIndividual Policy Results:")
        for policy_result in result.all_results:
            print(f"  - {policy_result.policy_name}: {policy_result.outcome}")
            print(f"    Reason: {policy_result.reason}")
            if policy_result.outcome == PolicyOutcome.REDACT:
                print(f"    Modified Content: {policy_result.modified_content[:100]}...")
                if policy_result.redaction_tokens:
                    print(f"    Redactions: {len(policy_result.redaction_tokens)} items")


def main():
    """Demonstrate MNPI and PII detection policies."""
    
    # Step 1: Create registry and register policies
    print("Setting up policy engine...")
    registry = PolicyRegistry()
    
    # Register financial policies
    registry.register("pii_detection", PIIDetectionPolicy())
    registry.register("mnpi_check", MNPIPolicy())
    
    # Step 2: Create engine with config
    config_path = "config/default.yaml"
    engine = PolicyEngine(registry, config_path=config_path)
    
    print(f"\nActive policies: {len(engine.get_active_policies())}")
    for name, _ in engine.get_active_policies():
        print(f"  - {name}")
    
    # Step 3: Test different scenarios
    
    # Test 1: Clean prompt (should pass)
    evaluate_and_display(
        engine,
        "What is the weather today?",
        "Clean prompt (no PII, no MNPI)"
    )
    
    # Test 2: PII in prompt (should REDACT)
    evaluate_and_display(
        engine,
        "Please send the report to john.doe@example.com or call me at 555-123-4567",
        "PII Detection (email and phone)"
    )
    
    # Test 3: SSN in prompt (should REDACT)
    evaluate_and_display(
        engine,
        "My social security number is 123-45-6789",
        "PII Detection (SSN)"
    )
    
    # Test 4: Restricted security (should BLOCK if configured)
    evaluate_and_display(
        engine,
        "What's the current price of AAPL stock?",
        "MNPI Check (ticker symbol - may block if on watchlist)"
    )
    
    # Test 5: MNPI keywords (should BLOCK)
    evaluate_and_display(
        engine,
        "I have insider information about an upcoming merger",
        "MNPI Check (insider information keywords)"
    )
    
    # Test 6: Combined PII and MNPI (BLOCK should win due to precedence)
    evaluate_and_display(
        engine,
        "Contact me at user@example.com about the confidential deal",
        "Combined PII + MNPI (precedence test)"
    )
    
    print(f"\n{'='*70}")
    print("All tests completed!")
    print(f"{'='*70}")


if __name__ == "__main__":
    main()

