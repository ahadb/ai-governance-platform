"""
Structured logging configuration using structlog.

Configures JSON output with timestamps and log levels.
All logging uses event-style: logger.info("event_name", key=value)

See LOGGING.md for complete event format documentation and examples.
"""

import logging
import sys

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """
    Configure structlog with JSON output, timestamps, and log levels.
    
    Args:
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
    """
    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, log_level.upper()),
    )
    
    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,  # Add context variables
            structlog.processors.add_log_level,  # Add log level
            structlog.processors.TimeStamper(fmt="iso"),  # Add ISO timestamp
            structlog.processors.StackInfoRenderer(),  # Add stack info for exceptions
            structlog.processors.format_exc_info,  # Format exceptions
            structlog.processors.UnicodeDecoder(),  # Decode unicode
            structlog.processors.JSONRenderer(),  # JSON output
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(logging, log_level.upper())
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str = None) -> structlog.BoundLogger:
    """
    Get a configured structlog logger.
    
    Args:
        name: Logger name (usually __name__)
        
    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)

