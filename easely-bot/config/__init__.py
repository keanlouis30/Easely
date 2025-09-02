"""
Easely Configuration Package
============================

This __init__.py file serves as the "Official Stamp" that designates the config 
directory as a legitimate Python package. Its presence enables clean, absolute 
imports throughout the Easely application.

Purpose:
- Package Declaration: Tells Python this directory is an importable package
- Import Enablement: Allows other modules to use statements like:
  `from config.settings import DATABASE_URI`
- Namespace Organization: Creates a clean config.* namespace for all settings

Without this file, imports from the config directory would fail.

Architecture Philosophy:
This follows the principle of explicit package structure, making the codebase
more maintainable and the import system more predictable.
"""

# This file is intentionally minimal - its presence is its primary function.
# However, we can optionally expose commonly used settings at the package level
# for even cleaner imports throughout the application.

# Optional: Make frequently used settings available at package level
try:
    from .settings import (
        # Core application identity
        BOT_NAME,
        BOT_VERSION,
        
        # Critical API configurations
        DATABASE_URI,
        MESSENGER_ACCESS_TOKEN,
        CANVAS_API_BASE_URL,
        
        # Environment detection
        IS_PRODUCTION,
        IS_DEVELOPMENT,
        DEBUG_MODE,
        
        # Feature flags
        ENABLE_AI_FEATURES,
        ENABLE_PREMIUM_FEATURES,
        MAINTENANCE_MODE
    )
    
    # Package metadata
    __version__ = BOT_VERSION
    __name__ = "Easely Configuration"
    
except ImportError:
    # If settings.py has issues, don't break the entire package import
    # This allows for graceful error handling during development
    pass

# Export validation function for startup checks
try:
    from .settings import validate_configuration, print_config_summary
except ImportError:
    pass