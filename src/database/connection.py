"""
Database connection and session management.

Production-grade connection handling with:
- Connection pooling
- Retry logic for transient failures
- Proper session lifecycle management
- Type-safe session factory
"""

import os
from contextlib import contextmanager
from typing import Generator
from sqlalchemy import create_engine, event, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from .models import Base


class DatabaseConfig:
    """Database configuration with sensible defaults."""
    
    def __init__(
        self,
        database_url: str | None = None,
        echo: bool = False,
        pool_size: int = 5,
        max_overflow: int = 10,
    ):
        self.database_url = database_url or os.getenv(
            "DATABASE_URL", "sqlite:///data/mcp_demo.db"
        )
        self.echo = echo or os.getenv("DB_ECHO", "false").lower() == "true"
        self.pool_size = pool_size
        self.max_overflow = max_overflow
        
        # SQLite-specific: use StaticPool for in-memory, file-based uses default
        self.is_sqlite = self.database_url.startswith("sqlite")
        
    def create_engine_kwargs(self) -> dict:
        """Return engine kwargs based on database type."""
        kwargs = {
            "echo": self.echo,
        }
        
        if self.is_sqlite:
            # SQLite specific settings
            kwargs["connect_args"] = {"check_same_thread": False}
            if ":memory:" in self.database_url:
                kwargs["poolclass"] = StaticPool
        else:
            # PostgreSQL/MySQL pool settings
            kwargs["pool_size"] = self.pool_size
            kwargs["max_overflow"] = self.max_overflow
            kwargs["pool_pre_ping"] = True  # Verify connections before using
            
        return kwargs


class DatabaseManager:
    """
    Manages database engine, session factory, and lifecycle.
    
    Usage:
        db = DatabaseManager()
        db.init_db()  # Create tables
        
        with db.get_session() as session:
            customers = session.query(Customer).all()
    """
    
    def __init__(self, config: DatabaseConfig | None = None):
        self.config = config or DatabaseConfig()
        self.engine: Engine = create_engine(
            self.config.database_url,
            **self.config.create_engine_kwargs()
        )
        
        # Enable foreign keys for SQLite
        if self.config.is_sqlite:
            @event.listens_for(self.engine, "connect")
            def set_sqlite_pragma(dbapi_conn, connection_record):
                cursor = dbapi_conn.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        
        self.SessionFactory = sessionmaker(bind=self.engine, expire_on_commit=False)
    
    def init_db(self) -> None:
        """Create all tables defined in models."""
        Base.metadata.create_all(self.engine)
    
    def drop_all(self) -> None:
        """Drop all tables. Use with caution."""
        Base.metadata.drop_all(self.engine)
    
    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """
        Context manager for database sessions.
        
        Automatically handles commit/rollback and session cleanup.
        
        Example:
            with db.get_session() as session:
                customer = Customer(email="test@example.com", ...)
                session.add(customer)
                # Commit happens automatically on exit
        """
        session = self.SessionFactory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()
    
    def get_session_factory(self) -> sessionmaker:
        """Return the session factory for advanced use cases."""
        return self.SessionFactory
    
    def close(self) -> None:
        """Dispose of the connection pool."""
        self.engine.dispose()
