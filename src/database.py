"""
Database initialization and session management.

This module provides database setup, table creation, and session management
for the TA-DSS application. It supports both SQLite (MVP) and PostgreSQL (prod).
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from src.config import settings
from src.models.position_model import Base
from src.models.ohlcv_cache_model import OHLCVCache


# =============================================================================
# DATABASE ENGINE SETUP
# =============================================================================


def create_db_engine(database_url: str | None = None) -> Engine:
    """
    Create and configure a SQLAlchemy database engine.

    Args:
        database_url: Database connection URL. Defaults to settings.database_url.

    Returns:
        Configured SQLAlchemy engine instance.

    Examples:
        >>> engine = create_db_engine("sqlite:///./data/positions.db")
        >>> engine = create_db_engine("postgresql://user:pass@localhost/db")
    """
    db_url = database_url or settings.database_url

    connect_args = {}

    # SQLite-specific configuration
    if db_url.startswith("sqlite"):
        connect_args["check_same_thread"] = False

    # Create engine with connection pooling
    engine = create_engine(
        db_url,
        connect_args=connect_args,
        pool_pre_ping=True,  # Enable connection health checks
        echo=settings.is_development,  # Log SQL in development
    )

    return engine


# =============================================================================
# SQLITE OPTIMIZATIONS
# =============================================================================


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """
    Configure SQLite pragmas for better performance and reliability.

    This event listener runs on every new connection to the database.
    """
    if isinstance(dbapi_connection, type(None)):
        return

    try:
        # Check if this is a SQLite connection
        if "sqlite" in str(type(dbapi_connection)):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA journal_mode=WAL")  # Write-Ahead Logging
            cursor.execute("PRAGMA foreign_keys=ON")  # Enable foreign key constraints
            cursor.execute("PRAGMA busy_timeout=5000")  # Wait 5s for locks
            cursor.close()
    except Exception:
        # Silently ignore for non-SQLite databases
        pass


# =============================================================================
# SESSION MANAGEMENT
# =============================================================================


class DatabaseSession:
    """
    Database session manager with lazy initialization.

    This class provides a thread-safe session factory that can be used
    for dependency injection in FastAPI.
    """

    def __init__(self, database_url: str | None = None):
        """
        Initialize the session manager.

        Args:
            database_url: Database connection URL. Defaults to settings.
        """
        self._engine: Engine | None = None
        self._session_factory: sessionmaker | None = None
        self._database_url = database_url

    @property
    def engine(self) -> Engine:
        """Get or create the database engine."""
        if self._engine is None:
            self._engine = create_db_engine(self._database_url)
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Get or create the session factory."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine,
                expire_on_commit=False,
            )
        return self._session_factory

    def create_session(self) -> Session:
        """
        Create a new database session.

        Returns:
            A new SQLAlchemy Session instance.
        """
        return self.session_factory()

    def init_db(self) -> None:
        """
        Initialize the database by creating all tables.

        This method creates all tables defined in the Base metadata.
        It's safe to call multiple times - existing tables are not modified.
        """
        Base.metadata.create_all(bind=self.engine)

    def drop_db(self) -> None:
        """
        Drop all tables from the database.

        WARNING: This will delete all data. Use with caution.
        """
        Base.metadata.drop_all(bind=self.engine)


# =============================================================================
# GLOBAL SESSION MANAGER
# =============================================================================

# Global database session manager instance
db_manager = DatabaseSession()


# =============================================================================
# FASTAPI DEPENDENCY INJECTION
# =============================================================================


def get_db_session() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database session injection.

    This function yields a database session and ensures proper cleanup
    (closing the session) after the request is complete.

    Yields:
        SQLAlchemy Session instance for the request lifecycle.

    Example:
        @app.get("/positions")
        def list_positions(db: Session = Depends(get_db_session)):
            return db.query(Position).all()
    """
    session = db_manager.create_session()
    try:
        yield session
    finally:
        session.close()


# =============================================================================
# CONTEXT MANAGER
# =============================================================================


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.

    Use this for database operations outside of FastAPI request context,
    such as in background jobs or scripts.

    Yields:
        SQLAlchemy Session instance.

    Example:
        with get_db_context() as db:
            positions = db.query(Position).all()
            for pos in positions:
                print(pos.pair)
    """
    session = db_manager.create_session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# =============================================================================
# INITIALIZATION SCRIPT
# =============================================================================


def initialize_database(verbose: bool = True) -> None:
    """
    Initialize the database and create all tables.

    This is the main entry point for database initialization.
    Call this on application startup.

    Args:
        verbose: If True, print initialization status messages.

    Example:
        initialize_database(verbose=True)
    """
    if verbose:
        print(f"Initializing database: {settings.database_url}")

    # Create tables
    db_manager.init_db()

    if verbose:
        print("✓ Database tables created successfully")

        # Print table info
        from sqlalchemy import inspect

        inspector = inspect(db_manager.engine)
        tables = inspector.get_table_names()
        print(f"✓ Tables: {', '.join(tables)}")
        
        # Ensure OHLCV cache table exists
        from src.models.ohlcv_cache_model import create_ohlcv_cache_table
        create_ohlcv_cache_table(db_manager.engine)
        if verbose:
            print("✓ OHLCV cache table ready")


def reset_database(verbose: bool = True) -> None:
    """
    Reset the database by dropping and recreating all tables.

    WARNING: This will delete all data. Use only in development/testing.

    Args:
        verbose: If True, print status messages.
    """
    if verbose:
        print("WARNING: Resetting database - all data will be lost!")

    db_manager.drop_db()
    db_manager.init_db()

    if verbose:
        print("✓ Database reset successfully")


# =============================================================================
# CLI ENTRY POINT
# =============================================================================


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        command = sys.argv[1]

        if command == "init":
            initialize_database(verbose=True)
        elif command == "reset":
            confirm = input("Are you sure you want to reset the database? [y/N]: ")
            if confirm.lower() == "y":
                reset_database(verbose=True)
            else:
                print("Database reset cancelled.")
        else:
            print(f"Unknown command: {command}")
            print("Usage: python -m src.database [init|reset]")
    else:
        # Default: initialize
        initialize_database(verbose=True)
