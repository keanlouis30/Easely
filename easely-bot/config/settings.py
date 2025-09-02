"""
Easely Configuration Settings
============================

This module serves as the centralized configuration hub for the Easely application.
It handles all environment variables, secrets, and application settings following
the Twelve-Factor App methodology for clean separation of configuration from code.

Core Responsibilities:
- Load and validate environment variables
- Centralize all secrets and API keys
- Define application-wide constants
- Provide type-safe configuration access
"""

import os
from typing import Optional


# =============================================================================
# Environment Variable Loading Helper
# =============================================================================

def get_env_var(key: str, default: Optional[str] = None, required: bool = False) -> str:
    """
    Safely retrieve environment variables with validation.
    
    Args:
        key: Environment variable name
        default: Default value if not found
        required: Whether this variable is required for app to function
        
    Returns:
        Environment variable value as string
        
    Raises:
        ValueError: If required variable is missing
    """
    value = os.getenv(key, default)
    
    if required and not value:
        raise ValueError(f"Required environment variable '{key}' is not set")
    
    return value


# =============================================================================
# Database Configuration
# =============================================================================

# PostgreSQL connection string - critical for all database operations
DATABASE_URI = get_env_var(
    "DATABASE_URL", 
    required=True
)

# Database connection pool settings
DB_POOL_SIZE = int(get_env_var("DB_POOL_SIZE", "10"))
DB_MAX_OVERFLOW = int(get_env_var("DB_MAX_OVERFLOW", "20"))
DB_POOL_TIMEOUT = int(get_env_var("DB_POOL_TIMEOUT", "30"))


# =============================================================================
# Facebook Messenger API Configuration
# =============================================================================

# Page Access Token for sending messages via Messenger API
MESSENGER_ACCESS_TOKEN = get_env_var(
    "MESSENGER_ACCESS_TOKEN",
    required=True
)

# Webhook verification token for Facebook security
FACEBOOK_VERIFY_TOKEN = get_env_var(
    "FACEBOOK_VERIFY_TOKEN",
    required=True
)

# Facebook API version and base URL
FACEBOOK_API_VERSION = get_env_var("FACEBOOK_API_VERSION", "v18.0")
MESSENGER_API_BASE_URL = f"https://graph.facebook.com/{FACEBOOK_API_VERSION}/me/messages"


# =============================================================================
# Canvas LMS API Configuration
# =============================================================================

# Base URL for Canvas API calls
CANVAS_API_BASE_URL = get_env_var(
    "CANVAS_API_BASE_URL", 
    "https://canvas.instructure.com"
)

# API rate limiting settings
CANVAS_API_RATE_LIMIT = int(get_env_var("CANVAS_API_RATE_LIMIT", "100"))
CANVAS_API_TIMEOUT = int(get_env_var("CANVAS_API_TIMEOUT", "30"))

# Canvas API endpoints (relative to base URL)
CANVAS_ASSIGNMENTS_ENDPOINT = "/api/v1/courses/{course_id}/assignments"
CANVAS_CALENDAR_EVENTS_ENDPOINT = "/api/v1/calendar_events"
CANVAS_COURSES_ENDPOINT = "/api/v1/courses"
CANVAS_USER_PROFILE_ENDPOINT = "/api/v1/users/self/profile"


# =============================================================================
# Payment & Monetization Configuration
# =============================================================================

# Ko-fi payment integration
KOFI_BASE_URL = get_env_var("KOFI_BASE_URL", "https://ko-fi.com")
KOFI_USERNAME = get_env_var("KOFI_USERNAME")  # Your Ko-fi username
PAYMENT_URL = f"{KOFI_BASE_URL}/{KOFI_USERNAME}" if KOFI_USERNAME else None

# Subscription pricing and duration
PREMIUM_PRICE_USD = float(get_env_var("PREMIUM_PRICE_USD", "5.00"))
SUBSCRIPTION_DURATION_DAYS = int(get_env_var("SUBSCRIPTION_DURATION_DAYS", "30"))

# Free tier limitations
FREE_TIER_TASK_LIMIT = int(get_env_var("FREE_TIER_TASK_LIMIT", "5"))
FREE_TIER_REMINDER_HOURS = int(get_env_var("FREE_TIER_REMINDER_HOURS", "24"))


# =============================================================================
# AI Service Configuration
# =============================================================================

# AI service for outline generation (OpenAI, Claude, etc.)
AI_SERVICE_PROVIDER = get_env_var("AI_SERVICE_PROVIDER", "openai")
AI_SERVICE_API_KEY = get_env_var("AI_SERVICE_API_KEY")
AI_SERVICE_MODEL = get_env_var("AI_SERVICE_MODEL", "gpt-3.5-turbo")
AI_MAX_TOKENS = int(get_env_var("AI_MAX_TOKENS", "500"))


# =============================================================================
# Security & Encryption Configuration
# =============================================================================

# Encryption key for Canvas tokens (must be 32 bytes for Fernet)
ENCRYPTION_KEY = get_env_var(
    "ENCRYPTION_KEY",
    required=True
)

# Session security
SECRET_KEY = get_env_var(
    "SECRET_KEY",
    required=True
)

# HTTPS enforcement in production
FORCE_HTTPS = get_env_var("FORCE_HTTPS", "false").lower() == "true"


# =============================================================================
# Application Behavior Configuration
# =============================================================================

# Bot identity
BOT_NAME = "Easely"
BOT_DESCRIPTION = "Your Personal Academic Assistant"
BOT_VERSION = "1.0.0"

# Task management settings
TASK_PAGE_SIZE = int(get_env_var("TASK_PAGE_SIZE", "10"))
MAX_UPCOMING_TASKS = int(get_env_var("MAX_UPCOMING_TASKS", "50"))

# Reminder timing configuration (in hours before due date)
PREMIUM_REMINDER_SCHEDULE = [
    168,  # 1 week (7 * 24)
    72,   # 3 days (3 * 24)
    24,   # 1 day
    8,    # 8 hours
    2,    # 2 hours
    1     # 1 hour
]

# Time zone handling
DEFAULT_TIMEZONE = get_env_var("DEFAULT_TIMEZONE", "UTC")

# Date/time formats
DATE_FORMAT = get_env_var("DATE_FORMAT", "%Y-%m-%d")
DATETIME_FORMAT = get_env_var("DATETIME_FORMAT", "%Y-%m-%d %H:%M:%S")
USER_FRIENDLY_DATE_FORMAT = get_env_var("USER_FRIENDLY_DATE_FORMAT", "%B %d, %Y")
USER_FRIENDLY_TIME_FORMAT = get_env_var("USER_FRIENDLY_TIME_FORMAT", "%I:%M %p")


# =============================================================================
# Background Job Configuration
# =============================================================================

# Reminder job settings
REMINDER_JOB_INTERVAL_MINUTES = int(get_env_var("REMINDER_JOB_INTERVAL", "60"))
DATA_REFRESH_INTERVAL_HOURS = int(get_env_var("DATA_REFRESH_INTERVAL", "6"))
SUBSCRIPTION_CHECK_INTERVAL_HOURS = int(get_env_var("SUBSCRIPTION_CHECK_INTERVAL", "24"))

# Batch processing for API rate limiting
SYNC_BATCH_SIZE = int(get_env_var("SYNC_BATCH_SIZE", "10"))
SYNC_BATCH_DELAY_SECONDS = int(get_env_var("SYNC_BATCH_DELAY", "2"))


# =============================================================================
# Logging & Monitoring Configuration
# =============================================================================

# Logging level
LOG_LEVEL = get_env_var("LOG_LEVEL", "INFO").upper()

# Enable detailed logging for debugging
DEBUG_MODE = get_env_var("DEBUG_MODE", "false").lower() == "true"

# External monitoring service
SENTRY_DSN = get_env_var("SENTRY_DSN")  # Optional error tracking


# =============================================================================
# Environment Detection
# =============================================================================

# Detect deployment environment
ENVIRONMENT = get_env_var("ENVIRONMENT", "development").lower()
IS_PRODUCTION = ENVIRONMENT == "production"
IS_DEVELOPMENT = ENVIRONMENT == "development"

# Server configuration
PORT = int(get_env_var("PORT", "8000"))
HOST = get_env_var("HOST", "0.0.0.0")


# =============================================================================
# URL Configuration
# =============================================================================

# Base application URLs
if IS_PRODUCTION:
    BASE_URL = get_env_var("BASE_URL", required=True)
else:
    BASE_URL = f"http://localhost:{PORT}"

# Webhook endpoint
WEBHOOK_ENDPOINT = f"{BASE_URL}/webhook"

# Static page URLs (for privacy policy, terms of service)
PRIVACY_POLICY_URL = f"{BASE_URL}/privacy"
TERMS_OF_SERVICE_URL = f"{BASE_URL}/terms"


# =============================================================================
# Feature Flags & Toggles
# =============================================================================

# Enable/disable specific features
ENABLE_AI_FEATURES = get_env_var("ENABLE_AI_FEATURES", "true").lower() == "true"
ENABLE_PREMIUM_FEATURES = get_env_var("ENABLE_PREMIUM_FEATURES", "true").lower() == "true"
ENABLE_WEEKLY_DIGEST = get_env_var("ENABLE_WEEKLY_DIGEST", "true").lower() == "true"
ENABLE_CALENDAR_EXPORT = get_env_var("ENABLE_CALENDAR_EXPORT", "true").lower() == "true"

# Maintenance mode
MAINTENANCE_MODE = get_env_var("MAINTENANCE_MODE", "false").lower() == "true"
MAINTENANCE_MESSAGE = get_env_var(
    "MAINTENANCE_MESSAGE", 
    "Easely is currently undergoing maintenance. Please try again later!"
)


# =============================================================================
# Validation on Import
# =============================================================================

def validate_configuration():
    """
    Validate critical configuration values on application startup.
    
    Raises:
        ValueError: If any critical configuration is invalid
    """
    errors = []
    
    # Validate encryption key length
    if len(ENCRYPTION_KEY.encode()) != 44:  # Base64 encoded 32-byte key
        errors.append("ENCRYPTION_KEY must be a valid 32-byte base64-encoded string")
    
    # Validate database URI format
    if not DATABASE_URI.startswith(('postgresql://', 'postgres://')):
        errors.append("DATABASE_URI must be a valid PostgreSQL connection string")
    
    # Validate messenger token format
    if not MESSENGER_ACCESS_TOKEN.startswith('EAA'):
        errors.append("MESSENGER_ACCESS_TOKEN appears to be invalid format")
    
    # Validate premium settings
    if PREMIUM_PRICE_USD <= 0:
        errors.append("PREMIUM_PRICE_USD must be greater than 0")
    
    if SUBSCRIPTION_DURATION_DAYS <= 0:
        errors.append("SUBSCRIPTION_DURATION_DAYS must be greater than 0")
    
    if errors:
        raise ValueError(f"Configuration validation failed:\n" + "\n".join(f"- {error}" for error in errors))


# Auto-validate configuration when module is imported
if __name__ != "__main__":
    validate_configuration()


# =============================================================================
# Configuration Summary (for debugging)
# =============================================================================

def print_config_summary():
    """Print a summary of current configuration (hiding sensitive values)."""
    print(f"""
Easely Configuration Summary
============================
Environment: {ENVIRONMENT}
Bot Name: {BOT_NAME}
Version: {BOT_VERSION}
Base URL: {BASE_URL}
Database: {'✓ Connected' if DATABASE_URI else '✗ Not configured'}
Messenger API: {'✓ Configured' if MESSENGER_ACCESS_TOKEN else '✗ Not configured'}
Canvas API: {CANVAS_API_BASE_URL}
AI Features: {'Enabled' if ENABLE_AI_FEATURES else 'Disabled'}
Premium Features: {'Enabled' if ENABLE_PREMIUM_FEATURES else 'Disabled'}
Debug Mode: {'On' if DEBUG_MODE else 'Off'}
Maintenance Mode: {'On' if MAINTENANCE_MODE else 'Off'}
""")


if __name__ == "__main__":
    print_config_summary()