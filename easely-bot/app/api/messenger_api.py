"""
Messenger API Module - The "Mouth" of Easely Bot

This module handles all outbound communication to Facebook Messenger.
It formats messages, handles API requests, and manages authentication.
"""

import requests
import logging
from typing import List, Dict, Any, Optional
from config.settings import MESSENGER_ACCESS_TOKEN

# Set up logging
logger = logging.getLogger(__name__)

# Facebook Graph API endpoint for sending messages
MESSENGER_API_URL = "https://graph.facebook.com/v18.0/me/messages"


def send_text_message(user_id: str, text: str) -> bool:
    """
    Send a simple text message to a user.
    
    Args:
        user_id (str): The recipient's Facebook user ID
        text (str): The message text to send
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    payload = {
        "recipient": {"id": user_id},
        "message": {"text": text}
    }
    
    return _send_message(payload)


def send_button_template(user_id: str, text: str, buttons: List[Dict[str, Any]]) -> bool:
    """
    Send a message with clickable buttons.
    
    Args:
        user_id (str): The recipient's Facebook user ID
        text (str): The message text to display above buttons
        buttons (List[Dict]): List of button objects with title, type, and payload/url
        
    Example button formats:
        Postback button: {"type": "postback", "title": "Button Text", "payload": "ACTION_PAYLOAD"}
        URL button: {"type": "web_url", "title": "Button Text", "url": "https://example.com"}
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    # Validate buttons (max 3 buttons allowed by Messenger)
    if len(buttons) > 3:
        logger.warning(f"Too many buttons ({len(buttons)}). Only first 3 will be sent.")
        buttons = buttons[:3]
    
    payload = {
        "recipient": {"id": user_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": buttons
                }
            }
        }
    }
    
    return _send_message(payload)


def send_quick_replies(user_id: str, text: str, quick_replies: List[Dict[str, Any]]) -> bool:
    """
    Send a message with quick reply options.
    
    Args:
        user_id (str): The recipient's Facebook user ID
        text (str): The message text to display
        quick_replies (List[Dict]): List of quick reply objects
        
    Example quick reply format:
        {"content_type": "text", "title": "Display Text", "payload": "ACTION_PAYLOAD"}
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    # Validate quick replies (max 13 allowed by Messenger)
    if len(quick_replies) > 13:
        logger.warning(f"Too many quick replies ({len(quick_replies)}). Only first 13 will be sent.")
        quick_replies = quick_replies[:13]
    
    payload = {
        "recipient": {"id": user_id},
        "message": {
            "text": text,
            "quick_replies": quick_replies
        }
    }
    
    return _send_message(payload)


def send_generic_template(user_id: str, elements: List[Dict[str, Any]]) -> bool:
    """
    Send a generic template (carousel) message.
    
    Args:
        user_id (str): The recipient's Facebook user ID
        elements (List[Dict]): List of template elements
        
    Example element format:
        {
            "title": "Element Title",
            "subtitle": "Element description",
            "image_url": "https://example.com/image.jpg",  # Optional
            "buttons": [...]  # Optional, same format as button_template
        }
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    # Validate elements (max 10 elements allowed by Messenger)
    if len(elements) > 10:
        logger.warning(f"Too many elements ({len(elements)}). Only first 10 will be sent.")
        elements = elements[:10]
    
    payload = {
        "recipient": {"id": user_id},
        "message": {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "elements": elements
                }
            }
        }
    }
    
    return _send_message(payload)


def send_typing_indicator(user_id: str, action: str = "typing_on") -> bool:
    """
    Send typing indicator to show bot is processing.
    
    Args:
        user_id (str): The recipient's Facebook user ID
        action (str): Either "typing_on" or "typing_off"
        
    Returns:
        bool: True if sent successfully, False otherwise
    """
    payload = {
        "recipient": {"id": user_id},
        "sender_action": action
    }
    
    return _send_message(payload)


def send_persistent_menu_setup(menu_items: List[Dict[str, Any]]) -> bool:
    """
    Set up the persistent menu for the bot (appears in chat interface).
    This is a one-time setup, not sent to individual users.
    
    Args:
        menu_items (List[Dict]): List of menu items
        
    Example menu item:
        {
            "type": "postback",
            "title": "Menu Item",
            "payload": "MENU_PAYLOAD"
        }
        
    Returns:
        bool: True if setup successful, False otherwise
    """
    url = "https://graph.facebook.com/v18.0/me/messenger_profile"
    
    payload = {
        "persistent_menu": [
            {
                "locale": "default",
                "composer_input_disabled": False,
                "call_to_actions": menu_items
            }
        ]
    }
    
    params = {"access_token": MESSENGER_ACCESS_TOKEN}
    
    try:
        response = requests.post(url, json=payload, params=params, timeout=30)
        
        if response.status_code == 200:
            logger.info("Persistent menu set up successfully")
            return True
        else:
            logger.error(f"Failed to set up persistent menu: {response.status_code} - {response.text}")
            return False
            
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error setting up persistent menu: {e}")
        return False


def _send_message(payload: Dict[str, Any]) -> bool:
    """
    Internal function to send message payload to Messenger API.
    
    Args:
        payload (Dict): The complete message payload
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    params = {"access_token": MESSENGER_ACCESS_TOKEN}
    
    try:
        response = requests.post(
            MESSENGER_API_URL, 
            json=payload, 
            params=params,
            timeout=30
        )
        
        if response.status_code == 200:
            logger.debug(f"Message sent successfully to user {payload['recipient']['id']}")
            return True
        else:
            # Log the error details
            error_data = response.json() if response.headers.get('content-type') == 'application/json' else response.text
            logger.error(f"Messenger API error {response.status_code}: {error_data}")
            
            # Handle specific error cases
            if response.status_code == 400:
                error_code = error_data.get('error', {}).get('code') if isinstance(error_data, dict) else None
                if error_code == 551:  # User has blocked the bot
                    logger.warning(f"User {payload['recipient']['id']} has blocked the bot")
                elif error_code == 200:  # Permission denied
                    logger.warning(f"Permission denied for user {payload['recipient']['id']}")
            elif response.status_code == 401:
                logger.error("Invalid access token - check MESSENGER_ACCESS_TOKEN")
            
            return False
            
    except requests.exceptions.Timeout:
        logger.error("Timeout sending message to Messenger API")
        return False
    except requests.exceptions.ConnectionError:
        logger.error("Connection error sending message to Messenger API")
        return False
    except requests.exceptions.RequestException as e:
        logger.error(f"Unexpected error sending message: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in _send_message: {e}")
        return False


# Convenience functions for common Easely-specific message patterns

def send_welcome_message(user_id: str) -> bool:
    """
    Send the initial welcome message with consent buttons.
    
    Args:
        user_id (str): The recipient's Facebook user ID
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    text = ("👋 Hello! I'm Easely, your personal Canvas assistant!\n\n"
            "I help students manage their academic workload by syncing with Canvas "
            "and sending smart reminders. I can also help you add custom tasks that "
            "sync back to your Canvas calendar.\n\n"
            "To get started, I'll need your permission to connect with your Canvas account.")
    
    buttons = [
        {
            "type": "postback",
            "title": "✅ I Agree, Let's Go!",
            "payload": "CONSENT_AGREE"
        },
        {
            "type": "web_url",
            "title": "📜 Privacy Policy",
            "url": "https://your-domain.com/privacy",
            "webview_height_ratio": "tall"
        },
        {
            "type": "web_url",
            "title": "⚖️ Terms of Use",
            "url": "https://your-domain.com/terms",
            "webview_height_ratio": "tall"
        }
    ]
    
    return send_button_template(user_id, text, buttons)


def send_task_menu(user_id: str) -> bool:
    """
    Send the main task management menu with quick reply options.
    
    Args:
        user_id (str): The recipient's Facebook user ID
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    text = "Welcome back to Easely! What would you like to see?"
    
    quick_replies = [
        {
            "content_type": "text",
            "title": "🔥 Due Today",
            "payload": "GET_TASKS_TODAY"
        },
        {
            "content_type": "text",
            "title": "⏰ Due This Week",
            "payload": "GET_TASKS_WEEK"
        },
        {
            "content_type": "text",
            "title": "❗ Show Overdue",
            "payload": "GET_TASKS_OVERDUE"
        },
        {
            "content_type": "text",
            "title": "🗓 View All Upcoming",
            "payload": "GET_TASKS_ALL"
        },
        {
            "content_type": "text",
            "title": "➕ Add New Task",
            "payload": "ADD_TASK_START"
        }
    ]
    
    return send_quick_replies(user_id, text, quick_replies)


def send_error_message(user_id: str, error_type: str = "general") -> bool:
    """
    Send an appropriate error message based on error type.
    
    Args:
        user_id (str): The recipient's Facebook user ID
        error_type (str): Type of error (general, canvas_token, rate_limit, etc.)
        
    Returns:
        bool: True if message sent successfully, False otherwise
    """
    error_messages = {
        "general": "😅 Oops! Something went wrong. Please try again in a moment.",
        "canvas_token": ("🔑 It looks like there's an issue with your Canvas connection. "
                        "Your token may have expired or been revoked. Please reconnect your account."),
        "rate_limit": ("⏳ I'm getting a lot of requests right now. Please wait a moment "
                      "and try again."),
        "network": ("🌐 I'm having trouble connecting to Canvas right now. "
                   "Please try again in a few minutes."),
        "invalid_input": ("❌ I didn't understand that input. Please try again or "
                         "use the menu options provided.")
    }
    
    message = error_messages.get(error_type, error_messages["general"])
    return send_text_message(user_id, message)


# Helper function to create button objects
def create_button(button_type: str, title: str, payload_or_url: str, **kwargs) -> Dict[str, Any]:
    """
    Create a button object for use in templates.
    
    Args:
        button_type (str): "postback" or "web_url"
        title (str): Button text (max 20 characters)
        payload_or_url (str): Postback payload or URL
        **kwargs: Additional button properties
        
    Returns:
        Dict: Button object
    """
    button = {
        "type": button_type,
        "title": title[:20]  # Ensure title doesn't exceed limit
    }
    
    if button_type == "postback":
        button["payload"] = payload_or_url
    elif button_type == "web_url":
        button["url"] = payload_or_url
        # Add optional web_url properties
        if "webview_height_ratio" in kwargs:
            button["webview_height_ratio"] = kwargs["webview_height_ratio"]
    
    return button


# Helper function to create quick reply objects
def create_quick_reply(title: str, payload: str) -> Dict[str, str]:
    """
    Create a quick reply object.
    
    Args:
        title (str): Display text (max 20 characters)
        payload (str): Postback payload when tapped
        
    Returns:
        Dict: Quick reply object
    """
    return {
        "content_type": "text",
        "title": title[:20],  # Ensure title doesn't exceed limit
        "payload": payload
    }