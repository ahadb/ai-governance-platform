"""
Main entry point for AI Governance Platform Gateway.

Initializes all components and starts the FastAPI server.
"""

import os

from dotenv import load_dotenv

load_dotenv()

from audit import AuditDB, AuditRepository, AuditService
from common.logging import configure_logging, get_logger
from gateway import create_app, GatewayOrchestrator
from model_router import ModelRouter, load_router_config
from policies.example_policy import ExamplePolicy
from policies.finance import MNPIPolicy, PIIDetectionPolicy
from policy_engine.engine import PolicyEngine
from policy_engine.registry import PolicyRegistry

log_level = os.getenv("LOG_LEVEL", "INFO")
configure_logging(log_level=log_level)
logger = get_logger(__name__)

if os.getenv("DATABASE_URL"):
    logger.debug("env_file_loaded", database_url_configured=True)
else:
    logger.warning("env_file_missing_database_url", hint="Create .env file with DATABASE_URL")


def create_gateway_app(config_path: str = "config/default.yaml"):
    """
    Create and configure the Gateway application.
    
    Args:
        config_path: Path to configuration YAML file
        
    Returns:
        Configured FastAPI app
    """
    # Initialize Audit Database
    logger.info("initializing_audit_database")
    audit_status = "disabled"
    try:
        audit_db = AuditDB.from_env()
        audit_db.initialize()
        
        # Test connection
        if audit_db.test_connection():
            audit_status = "connected"
            logger.info("audit_database_connected")
        else:
            audit_status = "connection_failed"
            logger.warning("audit_database_connection_failed", hint="Check DATABASE_URL and ensure database exists")
    except Exception as e:
        audit_status = f"initialization_failed: {e}"
        logger.error(
            "audit_database_initialization_failed",
            error=str(e),
            error_type=type(e).__name__,
            hint="Audit logging will be disabled. Check DATABASE_URL in .env file.",
        )
        audit_db = None
    
    # Initialize Audit Service (or None if DB failed)
    audit_service = None
    if audit_db:
        try:
            audit_repository = AuditRepository(audit_db)
            audit_service = AuditService(audit_repository)
            audit_status = "initialized"
            logger.info("audit_service_initialized")
        except Exception as e:
            audit_status = f"service_failed: {e}"
            logger.error(
                "audit_service_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
    else:
        audit_status = "disabled (database unavailable)"
    
    # Initialize Policy Engine
    logger.info("initializing_policy_engine")
    policy_registry = PolicyRegistry()
    
    # Register policies
    policy_registry.register("example_policy", ExamplePolicy())
    policy_registry.register("pii_detection", PIIDetectionPolicy())
    policy_registry.register("mnpi_check", MNPIPolicy())
    
    # Create engine with config and audit service
    policy_engine = PolicyEngine(
        policy_registry,
        config_path=config_path,
        audit=audit_service,  # Inject audit service
    )
    active_policies = len(policy_engine.get_active_policies())
    logger.info(
        "policy_engine_initialized",
        active_policies=active_policies,
        config_path=config_path,
    )
    
    # Initialize Model Router with audit service
    logger.info("initializing_model_router")
    router_config = load_router_config(config_path)
    model_router = ModelRouter(router_config, audit=audit_service)  # Inject audit service
    providers = model_router.get_providers()
    providers_str = ", ".join(providers) if providers else "none"
    logger.info("model_router_initialized", providers=providers)
    
    # Create orchestrator with audit service
    orchestrator = GatewayOrchestrator(
        policy_engine=policy_engine,
        model_router=model_router,
        audit=audit_service,  # Pass real audit service (or None if failed)
    )
    
    app = create_app(orchestrator, enable_cors=True)
    
    app.state.audit_db = audit_db
    
    app.state.init_info = {
        "audit_status": audit_status,
        "active_policies": active_policies,
        "providers": providers_str,
    }
    
    # TODO: improve log level labels
    @app.on_event("startup")
    async def print_initialization_summary():
        """Print initialization summary after uvicorn startup messages."""
        init_info = app.state.init_info
        print(f"INFO:     Audit Service {init_info['audit_status']}")
        print(f"INFO:     Policy Engine initialized ({init_info['active_policies']} active policies)")
        print(f"INFO:     Model Router initialized (providers: {init_info['providers']})")
        print("INFO:     Gateway initialization complete")
    
    return app


app = create_gateway_app()


if __name__ == "__main__":
    import atexit
    import uvicorn
    
    # Register shutdown handler to close database pool
    def shutdown_handler():
        """Close database connections on shutdown."""
        if hasattr(app.state, "audit_db") and app.state.audit_db:
            logger.info("closing_audit_database_connections")
            app.state.audit_db.close()
    
    atexit.register(shutdown_handler)
    
    logger.info(
        "starting_gateway_server",
        host="0.0.0.0",
        port=8000,
        docs_url="http://0.0.0.0:8000/docs",
    )
    
    # Use import string for reload to work properly
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

