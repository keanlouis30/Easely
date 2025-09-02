#!/usr/bin/env python3
"""
check_expiries.py - The Subscription Manager

This script runs daily to check for expired premium subscriptions and revert
users back to the free tier. It's part of Easely's automated workforce that
ensures only actively paying users have access to premium features.

Schedule: Runs once daily at midnight (0 0 * * *) via Render Cron Job
"""

import logging
import sys
from datetime import datetime, timezone
from typing import List, Optional

# Import Easely modules
try:
    from app.database.session import get_db_session
    from app.database.queries import get_expired_premium_users, revert_user_to_free
    from app.api.messenger_api import send_text_message
    from config.settings import get_settings
except ImportError as e:
    print(f"Error importing required modules: {e}")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('check_expiries')

def send_expiry_notification(messenger_id: str) -> bool:
    """
    Send a polite notification to user about their premium expiration.
    
    Args:
        messenger_id: The user's Messenger ID
        
    Returns:
        bool: True if message was sent successfully, False otherwise
    """
    message = (
        "Hi! Your Easely Premium access has expired. 😊\n\n"
        "We hope you enjoyed the enhanced features! You can renew at any time "
        "by visiting the menu and selecting 'Upgrade to Premium'.\n\n"
        "Don't worry - your free Easely account is still active and you'll "
        "continue receiving your daily assignment reminders!"
    )
    
    try:
        success = send_text_message(messenger_id, message)
        if success:
            logger.info(f"Sent expiry notification to user {messenger_id}")
        else:
            logger.warning(f"Failed to send expiry notification to user {messenger_id}")
        return success
    except Exception as e:
        logger.error(f"Error sending expiry notification to user {messenger_id}: {e}")
        return False

def process_expired_users() -> int:
    """
    Main function to process all expired premium users.
    
    Returns:
        int: Number of users successfully reverted to free tier
    """
    db = get_db_session()
    reverted_count = 0
    notification_count = 0
    
    try:
        # Get all expired premium users
        logger.info("Querying for expired premium users...")
        expired_users = get_expired_premium_users(db)
        
        if not expired_users:
            logger.info("No expired premium users found.")
            return 0
        
        logger.info(f"Found {len(expired_users)} expired premium users to process.")
        
        # Process each expired user
        for user in expired_users:
            try:
                # Revert user to free tier
                success = revert_user_to_free(db, user.id)
                
                if success:
                    reverted_count += 1
                    logger.info(f"Reverted user {user.id} (messenger_id: {user.messenger_id}) to free tier")
                    
                    # Send notification to user
                    if send_expiry_notification(user.messenger_id):
                        notification_count += 1
                else:
                    logger.error(f"Failed to revert user {user.id} to free tier")
                    
            except Exception as e:
                logger.error(f"Error processing user {user.id}: {e}")
                continue
        
        # Commit all changes
        db.commit()
        logger.info(f"Successfully processed {reverted_count} expired users")
        logger.info(f"Sent expiry notifications to {notification_count} users")
        
    except Exception as e:
        logger.error(f"Error during expired users processing: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    return reverted_count

def main():
    """
    Main entry point for the check_expiries script.
    """
    logger.info("=== Easely Subscription Expiry Check Started ===")
    start_time = datetime.now(timezone.utc)
    
    try:
        # Load settings
        settings = get_settings()
        logger.info("Settings loaded successfully")
        
        # Process expired users
        reverted_count = process_expired_users()
        
        # Calculate execution time
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        
        # Log summary
        logger.info("=== Expiry Check Summary ===")
        logger.info(f"Users reverted to free tier: {reverted_count}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Completed at: {end_time.isoformat()}")
        logger.info("=== Easely Subscription Expiry Check Completed ===")
        
    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()