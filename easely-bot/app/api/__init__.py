"""
API Package Initialization

This module exposes the main functions from all API modules,
providing a clean interface for the rest of the application.
"""

# Import main functions from each API module
from .messenger_api import (
    send_text_message,
    send_button_template,
    send_quick_replies,
    send_generic_template,
    send_typing_indicator,
    send_welcome_message,
    send_task_menu,
    send_error_message,
    create_button,
    create_quick_reply
)

from .canvas_api import (
    validate_token,
    get_courses,
    get_assignments,
    get_calendar_events,
    create_calendar_event,
    update_calendar_event,
    delete_calendar_event,
    test_token_permissions,
    CanvasAPIError,
    TokenInvalidError,
    RateLimitError
)

from .payment_api import (
    get_premium_payment_url,
    get_payment_info,
    calculate_expiry_date,
    parse_payment_notification,
    generate_activation_instructions,
    get_payment_success_message,
    format_price_display,
    PaymentError,
    PaymentProviderError
)

# Define what gets exported when someone does "from app.api import *"
__all__ = [
    # Messenger API
    'send_text_message',
    'send_button_template',
    'send_quick_replies',
    'send_generic_template',
    'send_typing_indicator',
    'send_welcome_message',
    'send_task_menu',
    'send_error_message',
    'create_button',
    'create_quick_reply',
    
    # Canvas API
    'validate_token',
    'get_courses',
    'get_assignments',
    'get_calendar_events',
    'create_calendar_event',
    'update_calendar_event',
    'delete_calendar_event',
    'test_token_permissions',
    'CanvasAPIError',
    'TokenInvalidError',
    'RateLimitError',
    
    # Payment API
    'get_premium_payment_url',
    'get_payment_info',
    'calculate_expiry_date',
    'parse_payment_notification',
    'generate_activation_instructions',
    'get_payment_success_message',
    'format_price_display',
    'PaymentError',
    'PaymentProviderError'
]

# Package metadata
__version__ = '1.0.0'
__author__ = 'Easely Bot'
__description__ = 'API modules for Canvas, Messenger, and Payment integration'