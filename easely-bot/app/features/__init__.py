"""
Features Package - Easely's Specialist Workshop
==============================================

This package contains specialized modules for complex features that are too big
or too specialized to be handled directly in the main event_handler.

The features package follows the "Specialist's Workshop" philosophy:
- Each module is an expert in one specific domain
- The event_handler delegates complex tasks to these specialists
- Clean interfaces hide implementation complexity

Available Features:
- AI Tools: AI-powered assignment outline generation for premium users
- Calendar Generator: Excel calendar file generation and cloud delivery

Author: Easely Development Team
"""

# Version information
__version__ = "1.0.0"
__author__ = "Easely Development Team"

# Import main functions from each feature module
# These are the primary interfaces that other modules should use

try:
    from .ai_tools import generate_assignment_outline, AIServiceError
    AI_TOOLS_AVAILABLE = True
except ImportError as e:
    # Graceful degradation if AI tools dependencies are missing
    AI_TOOLS_AVAILABLE = False
    AIServiceError = Exception  # Fallback exception class
    
    def generate_assignment_outline(assignment_title: str, assignment_description: str) -> str:
        """Fallback function when AI tools are unavailable"""
        raise AIServiceError("AI tools are not available. Please check OpenAI API configuration.")

try:
    from .calendar_generator import create_and_upload_calendar_file, CalendarGeneratorError
    CALENDAR_GENERATOR_AVAILABLE = True
except ImportError as e:
    # Graceful degradation if calendar generator dependencies are missing
    CALENDAR_GENERATOR_AVAILABLE = False
    CalendarGeneratorError = Exception  # Fallback exception class
    
    def create_and_upload_calendar_file(user_id: str) -> str:
        """Fallback function when calendar generator is unavailable"""
        raise CalendarGeneratorError("Calendar generator is not available. Please check AWS S3 configuration.")

# Feature availability flags - useful for conditional feature enabling
FEATURES_STATUS = {
    'ai_tools': AI_TOOLS_AVAILABLE,
    'calendar_generator': CALENDAR_GENERATOR_AVAILABLE
}

# Public API - these are the functions that external modules should import
__all__ = [
    # AI Tools
    'generate_assignment_outline',
    'AIServiceError',
    
    # Calendar Generator
    'create_and_upload_calendar_file', 
    'CalendarGeneratorError',
    
    # Feature status
    'FEATURES_STATUS',
    'AI_TOOLS_AVAILABLE',
    'CALENDAR_GENERATOR_AVAILABLE'
]

# Convenience functions for feature availability checking
def is_ai_tools_available() -> bool:
    """
    Check if AI tools feature is available
    
    Returns:
        bool: True if AI tools can be used, False otherwise
    """
    return AI_TOOLS_AVAILABLE

def is_calendar_generator_available() -> bool:
    """
    Check if calendar generator feature is available
    
    Returns:
        bool: True if calendar generator can be used, False otherwise
    """
    return CALENDAR_GENERATOR_AVAILABLE

def get_available_features() -> list:
    """
    Get a list of currently available features
    
    Returns:
        list: List of feature names that are currently available
    """
    return [feature for feature, available in FEATURES_STATUS.items() if available]

def get_unavailable_features() -> list:
    """
    Get a list of currently unavailable features
    
    Returns:
        list: List of feature names that are currently unavailable
    """
    return [feature for feature, available in FEATURES_STATUS.items() if not available]

# Logging setup for the features package
import logging

# Create package-level logger
logger = logging.getLogger(__name__)
logger.info(f"Features package initialized. Available features: {get_available_features()}")

if get_unavailable_features():
    logger.warning(f"Some features are unavailable: {get_unavailable_features()}")