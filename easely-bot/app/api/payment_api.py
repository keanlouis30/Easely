"""
Payment API Module - The "Payment Terminal"

This module centralizes all payment-related logic and abstracts payment providers.
Currently implements Ko-fi integration with future-proofing for other providers.
"""

import logging
from typing import Dict, Optional, Any
from datetime import datetime, timedelta
from config.settings import (
    KOFI_PAYMENT_URL, 
    KOFI_WEBHOOK_TOKEN,
    PREMIUM_PRICE_USD,
    PREMIUM_DURATION_DAYS
)

# Set up logging
logger = logging.getLogger(__name__)

# Payment provider constants
PAYMENT_PROVIDER = "kofi"  # Current provider: "kofi", future: "stripe", "paypal", etc.


class PaymentError(Exception):
    """Base exception for payment-related errors"""
    pass


class PaymentProviderError(PaymentError):
    """Raised when there's an issue with the payment provider"""
    pass


def get_premium_payment_url(user_id: Optional[str] = None, 
                          custom_data: Optional[Dict[str, Any]] = None) -> str:
    """
    Get the payment URL for Easely Premium subscription.
    
    Args:
        user_id (Optional[str]): User's Facebook Messenger ID for tracking
        custom_data (Optional[Dict]): Additional data to include in payment
        
    Returns:
        str: Complete payment URL for the user
        
    Note:
        Currently returns Ko-fi URL. Future versions may generate
        dynamic payment sessions with other providers.
    """
    try:
        base_url = KOFI_PAYMENT_URL
        
        if not base_url:
            logger.error("KOFI_PAYMENT_URL not configured in settings")
            raise PaymentError("Payment URL not configured")
        
        # For Ko-fi, we use a simple static URL approach
        # The user_id will be handled through the activation flow
        payment_url = base_url
        
        # Future enhancement: Add user_id as URL parameter for Ko-fi
        # or create dynamic payment sessions for other providers
        if user_id and PAYMENT_PROVIDER == "kofi":
            # Ko-fi supports custom data through URL parameters
            # This can help with order tracking
            payment_url += f"?c={user_id}"
        
        logger.info(f"Generated payment URL for user {user_id or 'anonymous'}")
        return payment_url
        
    except Exception as e:
        logger.error(f"Error generating payment URL: {e}")
        raise PaymentError(f"Could not generate payment URL: {e}")


def get_payment_info() -> Dict[str, Any]:
    """
    Get information about the current payment plan and pricing.
    
    Returns:
        Dict[str, Any]: Payment plan details including price, duration, features
    """
    return {
        "provider": PAYMENT_PROVIDER,
        "price_usd": PREMIUM_PRICE_USD,
        "duration_days": PREMIUM_DURATION_DAYS,
        "currency": "USD",
        "plan_name": "Easely Premium Access Pass",
        "billing_cycle": "manual_renewal",  # Not auto-renewal
        "features": [
            "Full proximity reminders (1 week, 3 days, 1 day, 8 hours, 2 hours, 1 hour)",
            "Unlimited manual task creation",
            "AI-powered outline generation",
            "Personalized weekly digest",
            "Calendar export to Excel",
            "Priority support"
        ],
        "payment_method": "one_time_payment"  # 30-day access pass
    }


def calculate_expiry_date(start_date: Optional[datetime] = None) -> datetime:
    """
    Calculate when premium access should expire.
    
    Args:
        start_date (Optional[datetime]): When premium access starts (defaults to now)
        
    Returns:
        datetime: When premium access expires
    """
    if start_date is None:
        start_date = datetime.utcnow()
    
    expiry_date = start_date + timedelta(days=PREMIUM_DURATION_DAYS)
    logger.debug(f"Calculated expiry date: {expiry_date}")
    
    return expiry_date


def validate_webhook_token(received_token: str) -> bool:
    """
    Validate webhook token from payment provider.
    
    Args:
        received_token (str): Token received from webhook
        
    Returns:
        bool: True if token is valid, False otherwise
        
    Note:
        Ko-fi doesn't provide webhook tokens by default, but this
        function is ready for future webhook implementations.
    """
    if not KOFI_WEBHOOK_TOKEN:
        logger.warning("No webhook token configured - skipping validation")
        return True  # Allow if no token is configured
    
    is_valid = received_token == KOFI_WEBHOOK_TOKEN
    
    if not is_valid:
        logger.warning("Invalid webhook token received")
    
    return is_valid


def parse_payment_notification(notification_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse payment notification from provider webhook.
    
    Args:
        notification_data (Dict): Raw notification data from webhook
        
    Returns:
        Optional[Dict]: Parsed payment information or None if invalid
        
    Note:
        Currently designed for Ko-fi webhook format. Will be extended
        for other payment providers in the future.
    """
    try:
        if PAYMENT_PROVIDER == "kofi":
            return _parse_kofi_notification(notification_data)
        else:
            logger.error(f"Unknown payment provider: {PAYMENT_PROVIDER}")
            return None
            
    except Exception as e:
        logger.error(f"Error parsing payment notification: {e}")
        return None


def _parse_kofi_notification(data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Parse Ko-fi webhook notification.
    
    Args:
        data (Dict): Ko-fi webhook data
        
    Returns:
        Optional[Dict]: Parsed Ko-fi payment data
        
    Ko-fi webhook format (example):
    {
        "verification_token": "your_verification_token",
        "message_id": "unique_message_id",
        "timestamp": "2023-01-01T12:00:00Z",
        "type": "Donation",
        "is_public": true,
        "from_name": "Supporter Name",
        "message": "Thanks for the great app!",
        "amount": "5.00",
        "url": "https://ko-fi.com/...",
        "email": "supporter@example.com",
        "currency": "USD",
        "is_subscription_payment": false,
        "is_first_subscription_payment": false,
        "kofi_transaction_id": "transaction_id_here"
    }
    """
    try:
        # Extract essential payment information
        payment_info = {
            "transaction_id": data.get("kofi_transaction_id"),
            "message_id": data.get("message_id"),
            "amount": float(data.get("amount", 0)),
            "currency": data.get("currency", "USD"),
            "payer_name": data.get("from_name"),
            "payer_email": data.get("email"),
            "message": data.get("message", ""),
            "timestamp": data.get("timestamp"),
            "is_subscription": data.get("is_subscription_payment", False),
            "payment_type": data.get("type", "Donation"),
            "verification_token": data.get("verification_token")
        }
        
        # Validate required fields
        if not payment_info["transaction_id"] or payment_info["amount"] <= 0:
            logger.warning("Invalid Ko-fi payment notification - missing required fields")
            return None
        
        # Check if amount matches expected premium price
        expected_amount = float(PREMIUM_PRICE_USD)
        if abs(payment_info["amount"] - expected_amount) > 0.01:  # Allow small floating point differences
            logger.warning(f"Payment amount {payment_info['amount']} doesn't match expected {expected_amount}")
            # Don't return None - log but still process (user might have paid more as tip)
        
        logger.info(f"Successfully parsed Ko-fi payment: {payment_info['transaction_id']}")
        return payment_info
        
    except (KeyError, ValueError, TypeError) as e:
        logger.error(f"Error parsing Ko-fi notification: {e}")
        return None


def generate_activation_instructions(user_id: str) -> Dict[str, str]:
    """
    Generate instructions for user to activate their premium subscription.
    
    Args:
        user_id (str): User's Facebook Messenger ID
        
    Returns:
        Dict[str, str]: Activation instructions and details
    """
    instructions = {
        "title": "🎉 Payment Successful!",
        "main_message": (
            "Thank you for upgrading to Easely Premium! 🌟\n\n"
            "To activate your premium features, simply type:\n"
            "**ACTIVATE**\n\n"
            "Your premium access includes:\n"
            "✅ Full proximity reminders\n"
            "✅ Unlimited manual tasks\n"
            "✅ AI-powered outline generation\n"
            "✅ Weekly digest reports\n"
            "✅ Calendar export feature"
        ),
        "activation_keyword": "ACTIVATE",
        "support_message": (
            "If you experience any issues, please contact support or "
            "send me a message with your order details."
        ),
        "duration": f"{PREMIUM_DURATION_DAYS} days"
    }
    
    return instructions


# Future-proofing functions for other payment providers

def _generate_stripe_payment_session(user_id: str, amount: float) -> str:
    """
    Future implementation for Stripe payment sessions.
    
    Args:
        user_id (str): User identifier
        amount (float): Payment amount
        
    Returns:
        str: Stripe checkout session URL
        
    Note: This is a placeholder for future Stripe integration
    """
    # TODO: Implement Stripe checkout session creation
    # This would involve:
    # 1. Creating a Stripe checkout session
    # 2. Including user_id in metadata
    # 3. Setting up success/cancel URLs
    # 4. Returning the checkout session URL
    raise NotImplementedError("Stripe integration not yet implemented")


def _generate_paypal_payment_session(user_id: str, amount: float) -> str:
    """
    Future implementation for PayPal payment sessions.
    
    Args:
        user_id (str): User identifier
        amount (float): Payment amount
        
    Returns:
        str: PayPal payment URL
        
    Note: This is a placeholder for future PayPal integration
    """
    # TODO: Implement PayPal payment session creation
    raise NotImplementedError("PayPal integration not yet implemented")


def get_supported_payment_methods() -> list[str]:
    """
    Get list of currently supported payment methods.
    
    Returns:
        list[str]: List of supported payment provider names
    """
    return [PAYMENT_PROVIDER]


def is_payment_provider_available() -> bool:
    """
    Check if the current payment provider is properly configured.
    
    Returns:
        bool: True if payment provider is available and configured
    """
    if PAYMENT_PROVIDER == "kofi":
        return bool(KOFI_PAYMENT_URL)
    
    # Future providers would have their own checks here
    return False


# Utility functions for payment management

def format_price_display(amount: float, currency: str = "USD") -> str:
    """
    Format price for display to users.
    
    Args:
        amount (float): Price amount
        currency (str): Currency code
        
    Returns:
        str: Formatted price string
    """
    if currency.upper() == "USD":
        return f"${amount:.2f}"
    else:
        return f"{amount:.2f} {currency}"


def get_payment_success_message(payment_info: Dict[str, Any]) -> str:
    """
    Generate a success message for completed payments.
    
    Args:
        payment_info (Dict): Payment information from webhook
        
    Returns:
        str: Formatted success message
    """
    amount_display = format_price_display(
        payment_info.get("amount", PREMIUM_PRICE_USD),
        payment_info.get("currency", "USD")
    )
    
    message = (
        f"🎉 Payment of {amount_display} received!\n\n"
        f"Transaction ID: {payment_info.get('transaction_id', 'N/A')}\n"
        f"Thank you for supporting Easely! 💙\n\n"
        f"Type **ACTIVATE** to enable your {PREMIUM_DURATION_DAYS}-day premium access."
    )
    
    return message


# Debug and testing functions

def get_test_payment_data() -> Dict[str, Any]:
    """
    Get sample payment data for testing purposes.
    
    Returns:
        Dict[str, Any]: Sample payment notification data
        
    Note: Only available in development/testing environments
    """
    return {
        "verification_token": "test_token",
        "message_id": "test_message_123",
        "timestamp": datetime.utcnow().isoformat(),
        "type": "Donation",
        "is_public": True,
        "from_name": "Test User",
        "message": "Test payment for Easely Premium",
        "amount": str(PREMIUM_PRICE_USD),
        "currency": "USD",
        "is_subscription_payment": False,
        "kofi_transaction_id": "test_transaction_123",
        "email": "test@example.com"
    }