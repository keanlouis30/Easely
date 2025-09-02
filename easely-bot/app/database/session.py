"""
Database Session Management for Easely

This module acts as the "Key and Address" to Easely's PostgreSQL database.
It's responsible for establishing and managing database connections using SQLAlchemy.

Core Responsibilities:
- Read database configuration from settings
- Create and configure the SQLAlchemy engine
- Provide session factory for database operations
- Offer context manager for clean session handling
"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool

# Import database configuration
from ..config.settings import DATABASE_URI

# Configure logging for database operations
logger = logging.getLogger(__name__)

# Global engine instance - created once when module is imported
engine: Engine = None
SessionLocal: sessionmaker = None


def create_database_engine() -> Engine:
    """
    Create and configure the SQLAlchemy database engine.
    
    The engine manages a pool of connections to PostgreSQL and is created
    only once when the application starts.
    
    Returns:
        Engine: Configured SQLAlchemy engine instance
    """
    try:
        # Create engine with production-ready configuration
        db_engine = create_engine(
            DATABASE_URI,
            # Connection pool settings for efficiency
            poolclass=QueuePool,
            pool_size=5,  # Number of connections to maintain
            max_overflow=10,  # Additional connections when pool is full
            pool_pre_ping=True,  # Validate connections before use
            pool_recycle=3600,  # Recycle connections every hour
            # Echo SQL queries in development (set to False in production)
            echo=False,
            # Additional connection arguments
            connect_args={
                "sslmode": "require",  # Ensure SSL connection to Render PostgreSQL
                "connect_timeout": 10,  # Timeout for initial connection
                "application_name": "easely-bot"  # Identify our app in PostgreSQL logs
            }
        )
        
        logger.info("Database engine created successfully")
        return db_engine
        
    except Exception as e:
        logger.error(f"Failed to create database engine: {e}")
        raise


def initialize_database():
    """
    Initialize the global database engine and session factory.
    
    This function should be called once when the application starts.
    """
    global engine, SessionLocal
    
    if engine is None:
        engine = create_database_engine()
        SessionLocal = sessionmaker(
            bind=engine,
            autocommit=False,  # Manual transaction control
            autoflush=False,   # Manual flushing for better control
            expire_on_commit=False  # Keep objects accessible after commit
        )
        logger.info("Database session factory initialized")


def get_session_factory() -> sessionmaker:
    """
    Get the session factory for creating new database sessions.
    
    Returns:
        sessionmaker: The configured session factory
    """
    if SessionLocal is None:
        initialize_database()
    return SessionLocal


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager that provides a database session for a single unit of work.
    
    This is the primary way to interact with the database. It automatically
    handles connection cleanup and error management.
    
    Usage:
        with get_db_session() as session:
            user = session.query(User).filter(User.messenger_id == "123").first()
            # Session is automatically closed when exiting the with block
    
    Yields:
        Session: SQLAlchemy session object for database operations
    
    Raises:
        SQLAlchemyError: If database operation fails
    """
    if SessionLocal is None:
        initialize_database()
    
    session = SessionLocal()
    try:
        logger.debug("Database session created")
        yield session
        
        # Commit any pending transactions
        session.commit()
        logger.debug("Database session committed successfully")
        
    except SQLAlchemyError as e:
        # Rollback on any database error
        session.rollback()
        logger.error(f"Database session error, rolling back: {e}")
        raise
        
    except Exception as e:
        # Rollback on any unexpected error
        session.rollback()
        logger.error(f"Unexpected error in database session: {e}")
        raise
        
    finally:
        # Always close the session to return connection to pool
        session.close()
        logger.debug("Database session closed")


def get_engine() -> Engine:
    """
    Get the database engine instance.
    
    Useful for operations that require direct engine access,
    such as creating tables or running raw SQL.
    
    Returns:
        Engine: The SQLAlchemy engine instance
    """
    if engine is None:
        initialize_database()
    return engine


def health_check() -> bool:
    """
    Perform a simple health check on the database connection.
    
    Returns:
        bool: True if database is accessible, False otherwise
    """
    try:
        with get_db_session() as session:
            # Simple query to test connection
            session.execute("SELECT 1")
            logger.info("Database health check passed")
            return True
            
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def close_all_connections():
    """
    Close all database connections and dispose of the engine.
    
    This should be called when the application is shutting down
    to ensure clean resource cleanup.
    """
    global engine, SessionLocal
    
    if engine:
        engine.dispose()
        logger.info("Database engine disposed")
        
    engine = None
    SessionLocal = None


# Initialize database when module is imported
try:
    initialize_database()
except Exception as e:
    logger.error(f"Failed to initialize database on import: {e}")
    # Don't raise here to allow application to start and show proper error messages