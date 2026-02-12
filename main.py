"""
Main entry point for AI Governance Platform Gateway.

Initializes all components and starts the FastAPI server.
"""

from policy_engine.engine import PolicyEngine
from policy_engine.registry import PolicyRegistry
from model_router import ModelRouter, load_router_config
from gateway import create_app, GatewayOrchestrator
from policies.finance import MNPIPolicy, PIIDetectionPolicy
from policies.example_policy import ExamplePolicy


def create_gateway_app(config_path: str = "config/default.yaml"):
    """
    Create and configure the Gateway application.
    
    Args:
        config_path: Path to configuration YAML file
        
    Returns:
        Configured FastAPI app
    """
    # Initialize Policy Engine
    print("Initializing Policy Engine...")
    policy_registry = PolicyRegistry()
    
    # Register policies
    policy_registry.register("example_policy", ExamplePolicy())
    policy_registry.register("pii_detection", PIIDetectionPolicy())
    policy_registry.register("mnpi_check", MNPIPolicy())
    
    # Create engine with config
    policy_engine = PolicyEngine(policy_registry, config_path=config_path)
    print(f"Policy Engine initialized with {len(policy_engine.get_active_policies())} active policies")
    
    # Initialize Model Router
    print("Initializing Model Router...")
    router_config = load_router_config(config_path)
    model_router = ModelRouter(router_config)
    print(f"Model Router initialized with providers: {model_router.get_providers()}")
    
    # Create orchestrator
    orchestrator = GatewayOrchestrator(
        policy_engine=policy_engine,
        model_router=model_router,
    )
    
    # Create FastAPI app
    app = create_app(orchestrator, enable_cors=True)
    
    return app


# Create app instance for direct import
app = create_gateway_app()


if __name__ == "__main__":
    import uvicorn
    
    print("\n" + "="*70)
    print("AI Governance Platform Gateway")
    print("="*70)
    print("Starting server on http://0.0.0.0:8000")
    print("API docs available at http://0.0.0.0:8000/docs")
    print("="*70 + "\n")
    
    # Use import string for reload to work properly
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

