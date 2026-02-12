"""Database connection pool and management for audit module."""

import os
from contextlib import contextmanager
from typing import Optional

import psycopg2
from psycopg2 import pool
from psycopg2.extras import RealDictCursor

from common.logging import get_logger

logger = get_logger(__name__)


class AuditDB:
    """Database connection pool manager for audit events."""

    def __init__(
        self,
        database_url: str,
        pool_size: int = 10,
        pool_max_overflow: int = 5,
    ):
        """
        Initialize AuditDB instance.
        
        Args:
            database_url: PostgreSQL connection string
            pool_size: Number of connections to keep in pool
            pool_max_overflow: Additional connections allowed beyond pool_size
        """
        self._database_url = database_url
        self._pool_size = pool_size
        self._pool_max_overflow = pool_max_overflow
        self._pool: Optional[pool.ThreadedConnectionPool] = None

    @classmethod
    def from_env(cls) -> "AuditDB":
        """
        Create AuditDB instance from environment variables.
        
        Reads:
            DATABASE_URL: PostgreSQL connection string (required)
            DB_POOL_SIZE: Pool size (default: 10)
            DB_POOL_MAX_OVERFLOW: Max overflow (default: 5)
        """
        database_url = os.getenv("DATABASE_URL")
        if not database_url:
            raise ValueError(
                "DATABASE_URL environment variable is required. "
                "Example: postgresql://user:password@localhost:5432/audit_db"
            )
        
        pool_size = int(os.getenv("DB_POOL_SIZE", "10"))
        pool_max_overflow = int(os.getenv("DB_POOL_MAX_OVERFLOW", "5"))
        
        return cls(
            database_url=database_url,
            pool_size=pool_size,
            pool_max_overflow=pool_max_overflow,
        )

    def initialize(self) -> None:
        """Initialize the connection pool. Call once at startup."""
        if self._pool is not None:
            logger.warning("connection_pool_already_initialized")
            return

        try:
            min_conn = 1
            max_conn = self._pool_size + self._pool_max_overflow

            self._pool = pool.ThreadedConnectionPool(
                minconn=min_conn,
                maxconn=max_conn,
                dsn=self._database_url,
            )

            logger.info(
                "connection_pool_initialized",
                min_connections=min_conn,
                max_connections=max_conn,
            )
        except psycopg2.Error as e:
            logger.error(
                "connection_pool_initialization_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise

    def close(self) -> None:
        """Close all connections in the pool. Call at shutdown."""
        if self._pool is not None:
            try:
                self._pool.closeall()
                logger.info("connection_pool_closed")
            except Exception as e:
                logger.error(
                    "connection_pool_close_failed",
                    error=str(e),
                    error_type=type(e).__name__,
                )
            finally:
                self._pool = None

    @contextmanager
    def get_connection(self):
        """
        Context manager for getting a database connection from the pool.
        
        Usage:
            with db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM audit_events")
        """
        if self._pool is None:
            raise RuntimeError(
                "Connection pool not initialized. Call initialize() first."
            )

        conn = None
        try:
            conn = self._pool.getconn()
            yield conn
            conn.commit()
        except psycopg2.Error as e:
            if conn:
                conn.rollback()
            logger.error(
                "database_connection_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(
                "unexpected_database_error",
                error=str(e),
                error_type=type(e).__name__,
            )
            raise
        finally:
            if conn:
                self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self, dict_cursor: bool = False):
        """
        Context manager for getting a database cursor.
        
        Args:
            dict_cursor: If True, returns RealDictCursor (results as dicts)
        """
        with self.get_connection() as conn:
            if dict_cursor:
                cursor = conn.cursor(cursor_factory=RealDictCursor)
            else:
                cursor = conn.cursor()

            try:
                yield cursor
            finally:
                cursor.close()

    def test_connection(self) -> bool:
        """Test database connection. Returns True if successful."""
        try:
            with self.get_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    cursor.fetchone()
            logger.info("database_connection_test_successful")
            return True
        except Exception as e:
            logger.error(
                "database_connection_test_failed",
                error=str(e),
                error_type=type(e).__name__,
            )
            return False
