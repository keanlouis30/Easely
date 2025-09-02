"""
Database Package for Easely

This package provides the complete database layer for Easely, including:
- SQLAlchemy models (User, Task, Course)
- Database session management
- Query interface for all database operations

Usage:
    from app.database import get_db_session, User, queries
    
    with get_db_session() as session:
        user = queries.get_user_by_messenger_id(session, "12345")
"""

# Import core session management
from .session import (
    get_db_session,
    get_engine, 
    get_session_factory,
    initialize_database,
    health_check,
    close_all_connections
)

# Import all models for easy access
from .models import (
    Base,
    User,
    Task, 
    Course,
    SubscriptionTier,
    TaskSource,
    create_all_tables,
    drop_all_tables
)

# Import the queries module (not individual functions to avoid namespace pollution)
from . import queries

# Package metadata
__version__ = "1.0.0"
__author__ = "Easely Development Team"

# Define what gets imported with "from app.database import *"
__all__ = [
    # Session management
    "get_db_session",
    "get_engine", 
    "get_session_factory",
    "initialize_database",
    "health_check",
    "close_all_connections",
    
    # Models
    "Base",
    "User",
    "Task",
    "Course", 
    "SubscriptionTier",
    "TaskSource",
    "create_all_tables",
    "drop_all_tables",
    
    # Query interface
    "queries"
]

# Optional: Package-level initialization
def initialize():
    """
    Initialize the database package.
    
    This function can be called during application startup to ensure
    the database is properly configured.
    """
    try:
        initialize_database()
        return True
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Failed to initialize database package: {e}")
        return False

# Optional: Quick health check function
def is_healthy():
    """
    Quick health check for the entire database system.
    
    Returns:
        bool: True if database is accessible and healthy
    """
    try:
        return health_check()
    except Exception:
        return False