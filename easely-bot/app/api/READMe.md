# Easely API Module Documentation

## Overview
The `/Easely/easely-bot/app/api/` directory contains the core API integration modules for the Easely bot. These modules serve as bridges between the bot's core functionality and external services (Facebook Messenger, Canvas LMS, and payment providers).

## Module Architecture

```
app/api/
├── __init__.py          # Package initialization and exports
├── canvas_api.py        # Canvas LMS integration
├── messenger_api.py     # Facebook Messenger integration
└── payment_api.py       # Payment provider integration
```

---

## 1. `__init__.py` - Package Initialization

### Purpose
Creates a clean, unified interface for importing API functions throughout the application.

### Key Features
- **Unified Imports**: Allows importing from `app.api` instead of individual modules
- **Selective Exports**: Uses `__all__` to control what gets exported
- **Package Metadata**: Includes version and description information

### Exported Functions

#### Messenger API Functions
- `send_text_message()` - Send simple text messages
- `send_button_template()` - Send messages with clickable buttons
- `send_quick_replies()` - Send messages with quick reply options
- `send_generic_template()` - Send carousel/card messages
- `send_typing_indicator()` - Show typing indicator
- `send_welcome_message()` - Easely-specific welcome message
- `send_task_menu()` - Main task management menu
- `send_error_message()` - Context-aware error messages
- `create_button()` - Helper for button creation
- `create_quick_reply()` - Helper for quick reply creation

#### Canvas API Functions
- `validate_token()` - Validate Canvas API tokens
- `get_courses()` - Fetch user's courses
- `get_assignments()` - Fetch assignments across courses
- `get_calendar_events()` - Fetch calendar events
- `create_calendar_event()` - Create new calendar events
- `update_calendar_event()` - Update existing events
- `delete_calendar_event()` - Delete calendar events
- `test_token_permissions()` - Test token capabilities
- `CanvasAPIError` - Canvas API exception
- `TokenInvalidError` - Invalid/revoked token exception
- `RateLimitError` - Rate limit exceeded exception

#### Payment API Functions
- `get_premium_payment_url()` - Get payment URL
- `get_payment_info()` - Get pricing and plan details
- `calculate_expiry_date()` - Calculate premium expiry
- `parse_payment_notification()` - Process payment webhooks
- `generate_activation_instructions()` - Create activation messages
- `get_payment_success_message()` - Generate success messages
- `format_price_display()` - Format prices for display
- `PaymentError` - Payment exception
- `PaymentProviderError` - Payment provider exception

### Usage Example
```python
from app.api import (
    send_text_message,
    validate_token,
    get_premium_payment_url,
    CanvasAPIError
)
```

---

## 2. `canvas_api.py` - Canvas LMS Integration

### Purpose
The "Bridge to Canvas" - handles all communication with Canvas LMS API for reading assignments and creating calendar events.

### Core Responsibilities
- **Authentication Management**: Bearer token handling for all Canvas requests
- **Data Fetching**: Retrieve assignments, courses, and calendar events
- **Data Creation**: Create calendar events for manual tasks
- **Data Parsing**: Convert Canvas JSON responses to clean Python dictionaries
- **Error Handling**: Manage token issues, rate limits, and API errors

### Key Classes & Exceptions

#### `CanvasAPIError(Exception)`
Base exception for Canvas API issues.

#### `TokenInvalidError(CanvasAPIError)`
Raised when Canvas token is invalid or revoked.

#### `RateLimitError(CanvasAPIError)`
Raised when Canvas API rate limit is exceeded.

### Core Functions

#### `validate_token(token: str) -> Tuple[bool, Optional[Dict]]`
**Purpose**: Validate a Canvas API token and retrieve user information.

**Parameters**:
- `token` (str): Canvas API token to validate

**Returns**: 
- Tuple of (is_valid: bool, user_info: Dict or None)
- user_info contains: `id`, `name`, `email`, `login_id`

**Usage Example**:
```python
is_valid, user_info = validate_token(user_token)
if is_valid:
    print(f"Token valid for {user_info['name']}")
```

#### `get_courses(token: str) -> List[Dict[str, Any]]`
**Purpose**: Fetch all active courses for a user.

**Parameters**:
- `token` (str): Valid Canvas API token

**Returns**: List of course dictionaries with:
- `id` - Canvas course ID
- `name` - Course name
- `course_code` - Course code (e.g., "CS101")
- `term` - Academic term name
- `start_at` - Course start date
- `end_at` - Course end date

**Example Output**:
```python
[
    {
        "id": 12345,
        "name": "Introduction to Computer Science",
        "course_code": "CS101",
        "term": "Fall 2024",
        "start_at": "2024-08-26T00:00:00Z",
        "end_at": "2024-12-15T23:59:59Z"
    }
]
```

#### `get_assignments(token: str) -> List[Dict[str, Any]]`
**Purpose**: Fetch all upcoming assignments across all user's courses.

**Parameters**:
- `token` (str): Valid Canvas API token

**Returns**: List of assignment dictionaries with:
- `id` - Canvas assignment ID
- `title` - Assignment name
- `due_date` - Due date as datetime object
- `course_id` - Associated course ID
- `course_name` - Course name
- `course_code` - Course code
- `points_possible` - Maximum points
- `submission_types` - List of allowed submission types
- `html_url` - Direct link to assignment
- `is_submitted` - Boolean submission status
- `source` - Always "canvas_assignment"

**Example Output**:
```python
[
    {
        "id": 67890,
        "title": "Programming Assignment 1",
        "due_date": datetime(2024, 9, 15, 23, 59, 59),
        "course_id": 12345,
        "course_name": "Introduction to Computer Science",
        "course_code": "CS101",
        "points_possible": 100,
        "submission_types": ["online_text_entry", "online_upload"],
        "html_url": "https://canvas.edu/courses/12345/assignments/67890",
        "is_submitted": False,
        "source": "canvas_assignment"
    }
]
```

#### `create_calendar_event(token: str, event_data: Dict[str, Any]) -> Optional[int]`
**Purpose**: Create a new calendar event in Canvas (for manual tasks).

**Parameters**:
- `token` (str): Valid Canvas API token
- `event_data` (Dict): Event details

**Event Data Format**:
```python
{
    "title": "Study Session",
    "start_at": datetime_object,
    "description": "Optional description",
    "course_id": 12345  # Optional - for course context
}
```

**Returns**: Canvas event ID (int) if successful, None if failed

**Usage Example**:
```python
event_data = {
    "title": "Study for Midterm",
    "start_at": datetime(2024, 10, 1, 14, 0),
    "description": "Review chapters 1-5",
    "course_id": 12345
}
event_id = create_calendar_event(token, event_data)
```

#### `test_token_permissions(token: str) -> Dict[str, bool]`
**Purpose**: Test what permissions a Canvas token has.

**Returns**: Dictionary of permission tests:
```python
{
    "read_user": True/False,
    "read_courses": True/False,
    "read_assignments": True/False,
    "read_calendar": True/False,
    "write_calendar": True/False
}
```

### Internal Helper Functions

#### `_get_canvas_domain_from_token(token: str) -> Optional[str]`
**Purpose**: Auto-detect Canvas domain from token by testing common domains.

#### `_make_canvas_request(endpoint, token, method="GET", data=None, params=None)`
**Purpose**: Make authenticated requests to Canvas API with error handling.

### Error Handling Strategy

The module implements comprehensive error handling:

1. **Token Validation**: Automatic domain detection and token verification
2. **Rate Limiting**: Built-in delays and retry logic for batch operations
3. **Network Errors**: Timeout and connection error handling
4. **API Errors**: Specific handling for 401 (auth), 429 (rate limit), and other HTTP errors

### Integration Points

- **Called by `event_handler.py`**: During onboarding (token validation, initial sync) and manual task creation
- **Called by `refresh_data.py`**: Background job for periodic data synchronization
- **Uses global variable `CANVAS_API_BASE`**: Cached Canvas domain URL

---

## 3. `messenger_api.py` - Facebook Messenger Integration

### Purpose
The "Mouth" of the bot - handles all outbound communication to Facebook Messenger users.

### Core Responsibilities
- **Message Construction**: Format JSON payloads for Messenger API
- **API Requests**: Make authenticated POST requests to Facebook Graph API
- **Authentication**: Handle Messenger access token for all requests
- **Error Handling**: Manage blocked users, invalid tokens, and API limits

### Core Functions

#### `send_text_message(user_id: str, text: str) -> bool`
**Purpose**: Send a simple text message to a user.

**Parameters**:
- `user_id` (str): Facebook user ID (recipient)
- `text` (str): Message text to send

**Returns**: Boolean indicating success/failure

**Usage Example**:
```python
success = send_text_message("1234567890", "Hello from Easely! 👋")
```

#### `send_button_template(user_id: str, text: str, buttons: List[Dict]) -> bool`
**Purpose**: Send a message with clickable buttons (max 3 buttons).

**Parameters**:
- `user_id` (str): Facebook user ID
- `text` (str): Message text above buttons
- `buttons` (List[Dict]): List of button objects

**Button Format**:
```python
# Postback button (sends payload to bot)
{"type": "postback", "title": "Button Text", "payload": "ACTION_PAYLOAD"}

# URL button (opens webpage)
{"type": "web_url", "title": "Button Text", "url": "https://example.com"}
```

**Usage Example**:
```python
buttons = [
    {"type": "postback", "title": "✅ I Agree", "payload": "CONSENT_AGREE"},
    {"type": "web_url", "title": "📜 Privacy Policy", "url": "https://easely.com/privacy"}
]
send_button_template("1234567890", "Welcome to Easely!", buttons)
```

#### `send_quick_replies(user_id: str, text: str, quick_replies: List[Dict]) -> bool`
**Purpose**: Send a message with quick reply options (max 13 replies).

**Parameters**:
- `user_id` (str): Facebook user ID
- `text` (str): Message text
- `quick_replies` (List[Dict]): List of quick reply objects

**Quick Reply Format**:
```python
{"content_type": "text", "title": "Display Text", "payload": "ACTION_PAYLOAD"}
```

**Usage Example**:
```python
quick_replies = [
    {"content_type": "text", "title": "🔥 Due Today", "payload": "GET_TASKS_TODAY"},
    {"content_type": "text", "title": "⏰ Due This Week", "payload": "GET_TASKS_WEEK"}
]
send_quick_replies("1234567890", "What would you like to see?", quick_replies)
```

#### `send_typing_indicator(user_id: str, action: str = "typing_on") -> bool`
**Purpose**: Show typing indicator to user.

**Parameters**:
- `user_id` (str): Facebook user ID
- `action` (str): "typing_on" or "typing_off"

### Easely-Specific Convenience Functions

#### `send_welcome_message(user_id: str) -> bool`
**Purpose**: Send the initial onboarding message with consent buttons.

**Features**:
- Welcome text explaining Easely's purpose
- Three buttons: "I Agree", "Privacy Policy", "Terms of Use"
- Opens policy links in Messenger WebView

#### `send_task_menu(user_id: str) -> bool`
**Purpose**: Send the main task management menu with quick replies.

**Quick Reply Options**:
- 🔥 Due Today (`GET_TASKS_TODAY`)
- ⏰ Due This Week (`GET_TASKS_WEEK`)
- ❗ Show Overdue (`GET_TASKS_OVERDUE`)
- 🗓 View All Upcoming (`GET_TASKS_ALL`)
- ➕ Add New Task (`ADD_TASK_START`)

#### `send_error_message(user_id: str, error_type: str = "general") -> bool`
**Purpose**: Send context-aware error messages.

**Error Types**:
- `"general"` - Generic error message
- `"canvas_token"` - Canvas connection issues
- `"rate_limit"` - Too many requests
- `"network"` - Connection problems
- `"invalid_input"` - User input issues

### Helper Functions

#### `create_button(button_type: str, title: str, payload_or_url: str) -> Dict`
**Purpose**: Create button objects for templates.

#### `create_quick_reply(title: str, payload: str) -> Dict`
**Purpose**: Create quick reply objects.

### Internal Functions

#### `_send_message(payload: Dict[str, Any]) -> bool`
**Purpose**: Internal function that handles actual API requests to Messenger.

**Features**:
- Uses `MESSENGER_ACCESS_TOKEN` from config
- Comprehensive error logging
- Handles specific error cases (blocked users, permission denied)
- Network timeout and retry logic

### Error Handling

The module handles various Messenger API errors:

1. **HTTP 400 with error code 551**: User has blocked the bot
2. **HTTP 400 with error code 200**: Permission denied
3. **HTTP 401**: Invalid access token
4. **Network errors**: Timeout and connection issues

### Messenger API Limits

The module enforces Messenger platform limits:
- **Buttons**: Maximum 3 per template
- **Quick Replies**: Maximum 13 per message
- **Title Length**: Maximum 20 characters for buttons/quick replies

### Integration Points

- **Called by `event_handler.py`**: Primary usage for responding to user interactions
- **Called by background jobs**: Proactive messaging (reminders, notifications)
- **Uses `config/settings.py`**: For `MESSENGER_ACCESS_TOKEN`

---

## 4. `payment_api.py` - Payment Provider Integration

### Purpose
The "Payment Terminal" - centralizes all payment-related logic and abstracts payment providers.

### Core Responsibilities
- **Payment URL Generation**: Create payment links for premium upgrades
- **Provider Abstraction**: Hide payment provider details from rest of app
- **Webhook Processing**: Handle payment notifications (future-ready)
- **Activation Management**: Generate activation instructions and success messages

### Current Implementation
- **Provider**: Ko-fi (simple URL-based payments)
- **Model**: Manual 30-day renewal (not auto-subscription)
- **Flow**: User pays → Manual activation with "ACTIVATE" keyword

### Core Functions

#### `get_premium_payment_url(user_id: Optional[str] = None) -> str`
**Purpose**: Get payment URL for Easely Premium subscription.

**Parameters**:
- `user_id` (Optional[str]): Facebook Messenger ID for tracking

**Returns**: Complete payment URL (Ko-fi page)

**Usage Example**:
```python
payment_url = get_premium_payment_url("1234567890")
# Returns: "https://ko-fi.com/easely?c=1234567890"
```

#### `get_payment_info() -> Dict[str, Any]`
**Purpose**: Get comprehensive information about the premium plan.

**Returns**: Dictionary with plan details:
```python
{
    "provider": "kofi",
    "price_usd": 4.99,
    "duration_days": 30,
    "currency": "USD",
    "plan_name": "Easely Premium Access Pass",
    "billing_cycle": "manual_renewal",
    "features": [
        "Full proximity reminders (1 week, 3 days, 1 day, 8 hours, 2 hours, 1 hour)",
        "Unlimited manual task creation",
        "AI-powered outline generation",
        "Personalized weekly digest",
        "Calendar export to Excel",
        "Priority support"
    ],
    "payment_method": "one_time_payment"
}
```

#### `calculate_expiry_date(start_date: Optional[datetime] = None) -> datetime`
**Purpose**: Calculate when premium access expires.

**Parameters**:
- `start_date` (Optional[datetime]): Start date (defaults to now)

**Returns**: Expiry datetime (start_date + PREMIUM_DURATION_DAYS)

#### `generate_activation_instructions(user_id: str) -> Dict[str, str]`
**Purpose**: Generate instructions for premium activation.

**Returns**: Dictionary with activation details:
```python
{
    "title": "🎉 Payment Successful!",
    "main_message": "Thank you for upgrading to Easely Premium! 🌟\n\nTo activate your premium features, simply type:\n**ACTIVATE**\n\n...",
    "activation_keyword": "ACTIVATE",
    "support_message": "If you experience any issues...",
    "duration": "30 days"
}
```

### Webhook Processing (Future-Ready)

#### `parse_payment_notification(notification_data: Dict) -> Optional[Dict]`
**Purpose**: Parse payment webhook notifications from Ko-fi.

**Ko-fi Webhook Format**:
```python
{
    "verification_token": "your_token",
    "message_id": "unique_id",
    "timestamp": "2024-01-01T12:00:00Z",
    "type": "Donation",
    "from_name": "Supporter Name",
    "amount": "4.99",
    "currency": "USD",
    "kofi_transaction_id": "transaction_id",
    "email": "user@example.com"
}
```

**Returns**: Parsed payment information or None if invalid

#### `validate_webhook_token(received_token: str) -> bool`
**Purpose**: Validate webhook authenticity (when Ko-fi webhook token is configured).

### Utility Functions

#### `format_price_display(amount: float, currency: str = "USD") -> str`
**Purpose**: Format prices for user display.

**Example**: `format_price_display(4.99, "USD")` → `"$4.99"`

#### `get_payment_success_message(payment_info: Dict) -> str`
**Purpose**: Generate success message for completed payments.

**Returns**: Formatted message with transaction details and activation instructions.

### Future-Proofing Architecture

The module includes placeholder functions for other payment providers:

#### `_generate_stripe_payment_session(user_id: str, amount: float) -> str`
**Purpose**: Future Stripe integration (creates checkout sessions).

#### `_generate_paypal_payment_session(user_id: str, amount: float) -> str`
**Purpose**: Future PayPal integration.

### Configuration Requirements

The module expects these settings in `config/settings.py`:

```python
KOFI_PAYMENT_URL = "https://ko-fi.com/your-page"
KOFI_WEBHOOK_TOKEN = "optional_webhook_token"
PREMIUM_PRICE_USD = 4.99
PREMIUM_DURATION_DAYS = 30
```

### Error Handling

#### `PaymentError(Exception)`
Base exception for payment-related issues.

#### `PaymentProviderError(PaymentError)`
Specific to payment provider problems.

### Integration Points

- **Called by `event_handler.py`**: When users request premium upgrade
- **Future webhook endpoint**: For automatic premium activation
- **Uses `config/settings.py`**: For Ko-fi configuration and pricing

### Testing Support

#### `get_test_payment_data() -> Dict`
**Purpose**: Generate sample payment data for development/testing.

---

## Module Integration Flow

### Onboarding Flow
1. **Messenger API**: Send welcome message with consent buttons
2. **Messenger API**: Send token request message
3. **Canvas API**: Validate provided token
4. **Canvas API**: Perform initial sync (get courses, assignments)
5. **Messenger API**: Send success message with assignment list

### Daily Usage Flow
1. **Messenger API**: Receive user interaction
2. **Canvas API**: Query local database (via database layer)
3. **Messenger API**: Send filtered results

### Premium Upgrade Flow
1. **Messenger API**: Send upgrade offer
2. **Payment API**: Generate payment URL
3. **Messenger API**: Send payment button with URL
4. **Payment API**: Process webhook (future) or manual activation
5. **Messenger API**: Send activation confirmation

### Background Job Flow
1. **Canvas API**: Refresh data from Canvas
2. **Messenger API**: Send proactive reminders
3. **Payment API**: Check subscription expiries

## Best Practices for Using These Modules

### Error Handling
```python
from app.api import send_text_message, get_assignments, CanvasAPIError

try:
    assignments = get_assignments(user_token)
    send_text_message(user_id, f"Found {len(assignments)} assignments")
except CanvasAPIError as e:
    send_error_message(user_id, "canvas_token")
```

### Rate Limiting
```python
from app.api import send_typing_indicator, send_text_message

# Show typing while processing
send_typing_indicator(user_id, "typing_on")
# Process data...
send_text_message(user_id, "Here are your assignments...")
send_typing_indicator(user_id, "typing_off")
```

### Payment Integration
```python
from app.api import get_premium_payment_url, send_button_template

payment_url = get_premium_payment_url(user_id)
buttons = [
    {"type": "web_url", "title": "💰 Upgrade to Premium", "url": payment_url}
]
send_button_template(user_id, "Ready to unlock premium features?", buttons)
```

## Summary

The API modules provide a clean, abstracted interface to external services while maintaining separation of concerns:

- **`messenger_api.py`**: Pure output, handles all Messenger communication
- **`canvas_api.py`**: Bidirectional bridge to Canvas LMS with comprehensive data parsing
- **`payment_api.py`**: Provider-agnostic payment handling with future-proofing
- **`__init__.py`**: Clean package interface for easy importing

Each module includes comprehensive error handling, logging, and is designed to work seamlessly with the rest of the Easely application architecture.