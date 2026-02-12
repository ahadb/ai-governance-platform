"""
FastAPI routes for the Gateway API.
"""

import uuid

import structlog.contextvars
from common.logging import get_logger
from fastapi import FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware

from gateway.models import ChatRequest, ChatResponse, ErrorResponse
from gateway.orchestrator import GatewayOrchestrator

logger = get_logger(__name__)


def create_app(
    orchestrator: GatewayOrchestrator,
    enable_cors: bool = True,
) -> FastAPI:
    """
    Create and configure the FastAPI application.
    
    Args:
        orchestrator: GatewayOrchestrator instance
        enable_cors: Whether to enable CORS middleware
        
    Returns:
        Configured FastAPI app
    """
    app = FastAPI(
        title="AI Governance Platform Gateway",
        description="API Gateway for enterprise LLM deployments with governance",
        version="0.1.0",
    )
    
    if enable_cors:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # TODO: Configure allowed origins from config
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
    
    @app.get("/health")
    async def health():
        """Health check endpoint."""
        return {"status": "healthy"}
    
    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest, response: Response):
        """
        Main chat endpoint with dual checkpoint validation.
        
        Processes requests through:
        1. Input policy evaluation
        2. LLM routing and generation
        3. Output policy evaluation
        4. Response (possibly redacted)
        """
        # Generate trace_id for end-to-end correlation
        trace_id = str(uuid.uuid4())
        
        # Bind trace_id to logger context - will appear in all subsequent logs
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(trace_id=trace_id)
        
        try:
            # Extract user info from request (in production, get from auth token)
            user_id = request.user_id or "anonymous"
            
            # Process request through orchestrator (pass trace_id)
            llm_response, input_result, output_result = orchestrator.process_request(
                prompt=request.messages[-1].content,  # Use last message as prompt
                user_id=user_id,
                model=request.model,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
                metadata={**(request.metadata or {}), "trace_id": trace_id},
            )
            
            # Add trace_id to response headers
            response.headers["X-Trace-Id"] = trace_id
            
            # Build response
            return ChatResponse(
                content=llm_response.content,
                model=llm_response.model,
                provider=llm_response.provider,
                finish_reason=llm_response.finish_reason,
                usage=llm_response.usage,
                policy_outcome=output_result.final_outcome,
                redacted=output_result.final_outcome == "REDACT",
                metadata={
                    **llm_response.metadata,
                    "trace_id": trace_id,
                    "input_policy_outcome": input_result.final_outcome,
                    "output_policy_outcome": output_result.final_outcome,
                    "policies_evaluated": output_result.evaluated_policies,
                },
            )
            
        except ValueError as e:
            # Policy blocked or escalated
            error_msg = str(e)
            if "blocked" in error_msg.lower():
                logger.warning(
                    "api_request_blocked",
                    user_id=user_id,
                    error=error_msg,
                    error_code="POLICY_BLOCKED",
                )
                exc = HTTPException(
                    status_code=403,
                    detail=ErrorResponse(
                        error=error_msg,
                        error_code="POLICY_BLOCKED",
                        details={"reason": error_msg, "trace_id": trace_id},
                    ).model_dump(),
                )
                exc.headers = {"X-Trace-Id": trace_id}
                raise exc
            elif "escalated" in error_msg.lower():
                logger.info(
                    "api_request_escalated",
                    user_id=user_id,
                    error=error_msg,
                    error_code="POLICY_ESCALATED",
                )
                exc = HTTPException(
                    status_code=202,  # Accepted but pending review
                    detail=ErrorResponse(
                        error=error_msg,
                        error_code="POLICY_ESCALATED",
                        details={"reason": error_msg, "trace_id": trace_id},
                    ).model_dump(),
                )
                exc.headers = {"X-Trace-Id": trace_id}
                raise exc
            else:
                logger.warning(
                    "api_request_validation_error",
                    user_id=user_id,
                    error=error_msg,
                )
                exc = HTTPException(status_code=400, detail=error_msg)
                exc.headers = {"X-Trace-Id": trace_id}
                raise exc
                
        except Exception as e:
            # Other errors (router errors, etc.)
            logger.error(
                "api_request_error",
                user_id=user_id,
                error=str(e),
                error_type=type(e).__name__,
                error_code="INTERNAL_ERROR",
            )
            exc = HTTPException(
                status_code=500,
                detail=ErrorResponse(
                    error=str(e),
                    error_code="INTERNAL_ERROR",
                    details={"type": type(e).__name__, "trace_id": trace_id},
                ).model_dump(),
            )
            exc.headers = {"X-Trace-Id": trace_id}
            raise exc
        finally:
            # Clear contextvars after request completes
            structlog.contextvars.clear_contextvars()
    
    return app

