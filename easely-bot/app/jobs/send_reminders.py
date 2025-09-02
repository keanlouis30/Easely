#!/usr/bin/env python3
"""
send_reminders.py - The Town Crier

This is the most important background job in Easely. It runs hourly to send
proactive reminders to users about upcoming assignments based on their
subscription tier and reminder preferences.

Schedule: Runs every hour at the top of the hour (0 * * * *) via Render Cron Job
"""

import logging
import sys
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Set, Optional, Tuple
from dataclasses import dataclass

# Import Easely modules
try:
    from app.database.session import get_db_session
    from app.database.queries import (
        get_tasks_needing_reminders,
        update_task_last_reminder,
        get_user_reminder_preferences
    )
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
logger = logging.getLogger('send_reminders')

@dataclass
class ReminderWindow:
    """Defines a reminder window with timing and message template"""
    name: str
    hours_before: int
    message_template: str
    emoji: str

# Define reminder windows for different subscription tiers
FREE_TIER_WINDOWS = [
    ReminderWindow(
        name="24_hour",
        hours_before=24,
        message_template="🔔 Reminder: '{title}' is due in 24 hours!\n\nDue: {due_date}",
        emoji="🔔"
    )
]

PREMIUM_TIER_WINDOWS = [
    ReminderWindow(
        name="1_week",
        hours_before=168,  # 7 days * 24 hours
        message_template="📅 Weekly heads-up: '{title}' is due in 1 week.\n\nDue: {due_date}\n\nTime to start planning! 📚",
        emoji="📅"
    ),
    ReminderWindow(
        name="3_days",
        hours_before=72,   # 3 days * 24 hours
        message_template="⚠️ Important: '{title}' is due in 3 days!\n\nDue: {due_date}\n\nMake sure you're on track! 🎯",
        emoji="⚠️"
    ),
    ReminderWindow(
        name="24_hours",
        hours_before=24,
        message_template="🔔 Reminder: '{title}' is due tomorrow!\n\nDue: {due_date}\n\nFinal stretch! 💪",
        emoji="🔔"
    ),
    ReminderWindow(
        name="8_hours",
        hours_before=8,
        message_template="🚨 Urgent: '{title}' is due in 8 hours!\n\nDue: {due_date}\n\nTime to finish up! ⏰",
        emoji="🚨"
    ),
    ReminderWindow(
        name="2_hours",
        hours_before=2,
        message_template="🔥 Final call: '{title}' is due in 2 hours!\n\nDue: {due_date}\n\nLast chance! 🏃‍♂️",
        emoji="🔥"
    ),
    ReminderWindow(
        name="1_hour",
        hours_before=1,
        message_template="⏱️ FINAL WARNING: '{title}' is due in 1 hour!\n\nDue: {due_date}\n\nSubmit now! 🚀",
        emoji="⏱️"
    )
]

class ReminderStats:
    """Track reminder sending statistics"""
    def __init__(self):
        self.total_tasks_checked = 0
        self.reminders_sent = 0
        self.reminders_failed = 0
        self.users_notified = 0
        self.free_tier_reminders = 0
        self.premium_tier_reminders = 0
        self.reminder_breakdown = {}  # window_name -> count

def format_due_date(due_date: datetime) -> str:
    """
    Format due date for display in reminder messages.
    
    Args:
        due_date: The due date as a datetime object
        
    Returns:
        Formatted date string
    """
    try:
        # Convert to local time if needed (assuming UTC stored in DB)
        if due_date.tzinfo is None:
            due_date = due_date.replace(tzinfo=timezone.utc)
        
        # Format as readable string
        return due_date.strftime("%B %d, %Y at %I:%M %p UTC")
    except Exception as e:
        logger.warning(f"Error formatting due date {due_date}: {e}")
        return str(due_date)

def create_reminder_message(task, window: ReminderWindow) -> str:
    """
    Create a personalized reminder message for a task.
    
    Args:
        task: Task object from database
        window: ReminderWindow object with message template
        
    Returns:
        Formatted reminder message
    """
    try:
        formatted_date = format_due_date(task.due_date)
        
        message = window.message_template.format(
            title=task.title,
            due_date=formatted_date
        )
        
        # Add course context if available
        if hasattr(task, 'course_name') and task.course_name:
            message += f"\nCourse: {task.course_name}"
        
        return message
        
    except Exception as e:
        logger.error(f"Error creating reminder message for task {task.id}: {e}")
        # Fallback message
        return f"{window.emoji} Reminder: '{task.title}' is due soon!"

def should_send_reminder(task, window: ReminderWindow, current_time: datetime) -> bool:
    """
    Determine if a reminder should be sent for a task at a specific window.
    
    Args:
        task: Task object from database
        window: ReminderWindow to check
        current_time: Current datetime
        
    Returns:
        Boolean indicating if reminder should be sent
    """
    try:
        # Calculate target reminder time
        target_reminder_time = task.due_date - timedelta(hours=window.hours_before)
        
        # Check if we're within the reminder window (±30 minutes for flexibility)
        time_diff = abs((current_time - target_reminder_time).total_seconds())
        within_window = time_diff <= 1800  # 30 minutes in seconds
        
        if not within_window:
            return False
        
        # Check if we've already sent this type of reminder
        last_reminder_field = f"last_{window.name}_reminder"
        if hasattr(task, last_reminder_field):
            last_sent = getattr(task, last_reminder_field)
            if last_sent and last_sent >= target_reminder_time - timedelta(hours=1):
                return False  # Already sent within the last hour
        
        return True
        
    except Exception as e:
        logger.error(f"Error checking reminder timing for task {task.id}: {e}")
        return False

def send_reminder_to_user(task, window: ReminderWindow) -> bool:
    """
    Send a reminder message to a user.
    
    Args:
        task: Task object with user information
        window: ReminderWindow object
        
    Returns:
        Boolean indicating if message was sent successfully
    """
    try:
        message = create_reminder_message(task, window)
        
        success = send_text_message(task.user.messenger_id, message)
        
        if success:
            logger.info(f"Sent {window.name} reminder for task '{task.title}' to user {task.user_id}")
        else:
            logger.warning(f"Failed to send {window.name} reminder for task {task.id}")
        
        return success
        
    except Exception as e:
        logger.error(f"Error sending reminder for task {task.id}: {e}")
        return False

def process_reminders() -> ReminderStats:
    """
    Main function to process and send all due reminders.
    
    Returns:
        ReminderStats: Statistics about the reminder process
    """
    db = get_db_session()
    stats = ReminderStats()
    current_time = datetime.now(timezone.utc)
    
    try:
        logger.info("Querying for tasks needing reminders...")
        
        # Get all tasks that might need reminders
        tasks_needing_reminders = get_tasks_needing_reminders(db, current_time)
        
        if not tasks_needing_reminders:
            logger.info("No tasks found needing reminders.")
            return stats
        
        logger.info(f"Found {len(tasks_needing_reminders)} tasks to check for reminders.")
        stats.total_tasks_checked = len(tasks_needing_reminders)
        
        notified_users = set()
        
        # Process each task
        for task in tasks_needing_reminders:
            try:
                # Determine subscription tier and available windows
                if task.user.subscription_tier == 'premium':
                    available_windows = PREMIUM_TIER_WINDOWS
                else:
                    available_windows = FREE_TIER_WINDOWS
                
                # Check each reminder window
                for window in available_windows:
                    if should_send_reminder(task, window, current_time):
                        # Send reminder
                        success = send_reminder_to_user(task, window)
                        
                        if success:
                            stats.reminders_sent += 1
                            notified_users.add(task.user_id)
                            
                            # Track by subscription tier
                            if task.user.subscription_tier == 'premium':
                                stats.premium_tier_reminders += 1
                            else:
                                stats.free_tier_reminders += 1
                            
                            # Track by reminder type
                            if window.name not in stats.reminder_breakdown:
                                stats.reminder_breakdown[window.name] = 0
                            stats.reminder_breakdown[window.name] += 1
                            
                            # Update last reminder timestamp in database
                            update_task_last_reminder(db, task.id, window.name, current_time)
                            
                        else:
                            stats.reminders_failed += 1
                        
                        # Break after sending one reminder per task per run
                        break
                
            except Exception as e:
                logger.error(f"Error processing task {task.id}: {e}")
                stats.reminders_failed += 1
                continue
        
        stats.users_notified = len(notified_users)
        
        # Commit database updates
        db.commit()
        logger.info(f"Successfully sent {stats.reminders_sent} reminders")
        
    except Exception as e:
        logger.error(f"Error during reminder processing: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    return stats

def main():
    """
    Main entry point for the send_reminders script.
    """
    logger.info("=== Easely Reminder Service Started ===")
    start_time = datetime.now(timezone.utc)
    
    try:
        # Load settings
        settings = get_settings()
        logger.info("Settings loaded successfully")
        
        # Process reminders
        stats = process_reminders()
        
        # Calculate execution time
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        
        # Log comprehensive summary
        logger.info("=== Reminder Service Summary ===")
        logger.info(f"Tasks checked: {stats.total_tasks_checked}")
        logger.info(f"Reminders sent successfully: {stats.reminders_sent}")
        logger.info(f"Reminders failed: {stats.reminders_failed}")
        logger.info(f"Unique users notified: {stats.users_notified}")
        logger.info(f"Free tier reminders: {stats.free_tier_reminders}")
        logger.info(f"Premium tier reminders: {stats.premium_tier_reminders}")
        
        # Log breakdown by reminder type
        if stats.reminder_breakdown:
            logger.info("Reminder breakdown by type:")
            for window_name, count in stats.reminder_breakdown.items():
                logger.info(f"  {window_name}: {count}")
        
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Completed at: {end_time.isoformat()}")
        logger.info("=== Easely Reminder Service Completed ===")
        
    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()