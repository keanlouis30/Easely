"""
Database Query Interface for Easely

This module serves as the "Expert Librarian" - the sole interface for all
database operations. It abstracts SQLAlchemy complexity and provides clean,
business-logic focused functions for the rest of the application.

All functions take a session as the first parameter and handle data integrity
through proper transaction management.
"""

import logging
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Dict, Any, Tuple

from sqlalchemy import and_, or_, func, desc, asc
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from .models import User, Task, Course, SubscriptionTier, TaskSource

# Configure logging
logger = logging.getLogger(__name__)


# =============================================================================
# USER OPERATIONS
# =============================================================================

def get_user_by_messenger_id(session: Session, messenger_id: str) -> Optional[User]:
    """
    Retrieve user by their Facebook Messenger ID.
    
    Args:
        session: Database session
        messenger_id: Facebook Messenger user ID
        
    Returns:
        User object if found, None otherwise
    """
    try:
        user = session.query(User).filter(
            User.messenger_id == messenger_id,
            User.is_active == True
        ).first()
        
        if user:
            # Update last activity timestamp
            user.last_active_at = datetime.now(timezone.utc)
            session.commit()
            
        return user
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching user by messenger_id {messenger_id}: {e}")
        session.rollback()
        return None


def create_user(session: Session, user_data: Dict[str, Any]) -> Optional[User]:
    """
    Create a new user account.
    
    Args:
        session: Database session
        user_data: Dictionary containing user information
                  Required: messenger_id
                  Optional: canvas_token, canvas_user_id, canvas_base_url, timezone
                  
    Returns:
        Created User object, None if creation failed
    """
    try:
        # Set month reset date to start of current month
        now = datetime.now(timezone.utc)
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        user = User(
            messenger_id=user_data['messenger_id'],
            canvas_token=user_data.get('canvas_token'),
            canvas_user_id=user_data.get('canvas_user_id'),
            canvas_base_url=user_data.get('canvas_base_url'),
            timezone=user_data.get('timezone', 'UTC'),
            month_reset_date=month_start,
            last_active_at=now
        )
        
        session.add(user)
        session.commit()
        
        logger.info(f"Created new user: messenger_id={user_data['messenger_id']}")
        return user
        
    except IntegrityError as e:
        logger.error(f"User creation failed - duplicate messenger_id {user_data['messenger_id']}: {e}")
        session.rollback()
        return None
    except SQLAlchemyError as e:
        logger.error(f"Error creating user: {e}")
        session.rollback()
        return None


def update_user_canvas_info(session: Session, user_id: int, canvas_data: Dict[str, Any]) -> bool:
    """
    Update user's Canvas integration information.
    
    Args:
        session: Database session
        user_id: User ID
        canvas_data: Dictionary with canvas_token, canvas_user_id, canvas_base_url
        
    Returns:
        True if successful, False otherwise
    """
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        user.canvas_token = canvas_data.get('canvas_token', user.canvas_token)
        user.canvas_user_id = canvas_data.get('canvas_user_id', user.canvas_user_id)
        user.canvas_base_url = canvas_data.get('canvas_base_url', user.canvas_base_url)
        user.token_invalid = False  # Reset token status
        user.last_sync_at = datetime.now(timezone.utc)
        
        session.commit()
        logger.info(f"Updated Canvas info for user {user_id}")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error updating Canvas info for user {user_id}: {e}")
        session.rollback()
        return False


def update_user_subscription(session: Session, user_id: int, tier: SubscriptionTier, 
                           expiry_date: Optional[datetime] = None) -> bool:
    """
    Update user's subscription tier and expiry date.
    
    Args:
        session: Database session
        user_id: User ID
        tier: New subscription tier
        expiry_date: Subscription expiry date (required for premium)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        user.subscription_tier = tier
        user.subscription_expiry_date = expiry_date
        
        session.commit()
        logger.info(f"Updated subscription for user {user_id} to {tier.value}")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error updating subscription for user {user_id}: {e}")
        session.rollback()
        return False


def mark_user_token_invalid(session: Session, user_id: int) -> bool:
    """
    Mark user's Canvas token as invalid (e.g., revoked).
    
    Args:
        session: Database session
        user_id: User ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        user.token_invalid = True
        session.commit()
        
        logger.info(f"Marked token invalid for user {user_id}")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error marking token invalid for user {user_id}: {e}")
        session.rollback()
        return False


def increment_user_monthly_tasks(session: Session, user_id: int) -> bool:
    """
    Increment user's monthly manual task counter.
    
    Args:
        session: Database session
        user_id: User ID
        
    Returns:
        True if successful, False otherwise
    """
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
            
        # Check if month has reset
        now = datetime.now(timezone.utc)
        if now >= user.month_reset_date + timedelta(days=31):
            # Reset counter and date
            user.manual_tasks_this_month = 1
            user.month_reset_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:
            user.manual_tasks_this_month += 1
            
        session.commit()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error incrementing monthly tasks for user {user_id}: {e}")
        session.rollback()
        return False


# =============================================================================
# COURSE OPERATIONS
# =============================================================================

def create_or_update_courses(session: Session, user_id: int, courses_data: List[Dict[str, Any]]) -> bool:
    """
    Create or update courses for a user (used during Canvas sync).
    
    Args:
        session: Database session
        user_id: User ID
        courses_data: List of course dictionaries with canvas_course_id, course_name, etc.
        
    Returns:
        True if successful, False otherwise
    """
    try:
        for course_data in courses_data:
            # Check if course already exists
            existing_course = session.query(Course).filter(
                Course.user_id == user_id,
                Course.canvas_course_id == course_data['canvas_course_id']
            ).first()
            
            if existing_course:
                # Update existing course
                existing_course.course_name = course_data['course_name']
                existing_course.course_code = course_data.get('course_code')
                existing_course.is_active = course_data.get('is_active', True)
            else:
                # Create new course
                new_course = Course(
                    user_id=user_id,
                    canvas_course_id=course_data['canvas_course_id'],
                    course_name=course_data['course_name'],
                    course_code=course_data.get('course_code'),
                    is_active=course_data.get('is_active', True)
                )
                session.add(new_course)
        
        session.commit()
        logger.info(f"Created/updated {len(courses_data)} courses for user {user_id}")
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error creating/updating courses for user {user_id}: {e}")
        session.rollback()
        return False


def get_user_courses(session: Session, user_id: int, active_only: bool = True) -> List[Course]:
    """
    Get all courses for a user.
    
    Args:
        session: Database session
        user_id: User ID
        active_only: Whether to return only active courses
        
    Returns:
        List of Course objects
    """
    try:
        query = session.query(Course).filter(Course.user_id == user_id)
        
        if active_only:
            query = query.filter(Course.is_active == True)
            
        return query.order_by(Course.course_name).all()
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching courses for user {user_id}: {e}")
        return []


# =============================================================================
# TASK OPERATIONS - CRUD
# =============================================================================

def bulk_create_tasks(session: Session, user_id: int, tasks_data: List[Dict[str, Any]]) -> int:
    """
    Bulk create tasks during initial Canvas sync.
    
    Args:
        session: Database session
        user_id: User ID
        tasks_data: List of task dictionaries
        
    Returns:
        Number of tasks created
    """
    try:
        tasks_created = 0
        
        for task_data in tasks_data:
            # Check if task already exists (prevent duplicates)
            existing_task = None
            
            if task_data.get('canvas_assignment_id'):
                existing_task = session.query(Task).filter(
                    Task.user_id == user_id,
                    Task.canvas_assignment_id == task_data['canvas_assignment_id']
                ).first()
            elif task_data.get('canvas_event_id'):
                existing_task = session.query(Task).filter(
                    Task.user_id == user_id,
                    Task.canvas_event_id == task_data['canvas_event_id']
                ).first()
            
            if not existing_task:
                # Find course if specified
                course_id = None
                if task_data.get('canvas_course_id'):
                    course = session.query(Course).filter(
                        Course.user_id == user_id,
                        Course.canvas_course_id == task_data['canvas_course_id']
                    ).first()
                    if course:
                        course_id = course.id
                
                # Create new task
                new_task = Task(
                    user_id=user_id,
                    course_id=course_id,
                    canvas_assignment_id=task_data.get('canvas_assignment_id'),
                    canvas_event_id=task_data.get('canvas_event_id'),
                    title=task_data['title'],
                    description=task_data.get('description'),
                    due_date=task_data['due_date'],
                    source=TaskSource(task_data.get('source', 'canvas_assignment')),
                    assignment_type=task_data.get('assignment_type'),
                    points_possible=task_data.get('points_possible'),
                    submission_types=task_data.get('submission_types')
                )
                
                session.add(new_task)
                tasks_created += 1
        
        session.commit()
        logger.info(f"Bulk created {tasks_created} tasks for user {user_id}")
        return tasks_created
        
    except SQLAlchemyError as e:
        logger.error(f"Error bulk creating tasks for user {user_id}: {e}")
        session.rollback()
        return 0


def create_manual_task(session: Session, user_id: int, task_data: Dict[str, Any]) -> Optional[Task]:
    """
    Create a manual task (user-generated).
    
    Args:
        session: Database session
        user_id: User ID
        task_data: Dictionary with title, due_date, description, course_id, canvas_event_id
        
    Returns:
        Created Task object, None if creation failed
    """
    try:
        new_task = Task(
            user_id=user_id,
            course_id=task_data.get('course_id'),
            canvas_event_id=task_data.get('canvas_event_id'),  # From Canvas API response
            title=task_data['title'],
            description=task_data.get('description'),
            due_date=task_data['due_date'],
            source=TaskSource.MANUAL_ENTRY
        )
        
        session.add(new_task)
        session.commit()
        
        logger.info(f"Created manual task '{task_data['title']}' for user {user_id}")
        return new_task
        
    except SQLAlchemyError as e:
        logger.error(f"Error creating manual task for user {user_id}: {e}")
        session.rollback()
        return None


def update_task(session: Session, task_id: int, updates: Dict[str, Any]) -> bool:
    """
    Update an existing task.
    
    Args:
        session: Database session
        task_id: Task ID
        updates: Dictionary of fields to update
        
    Returns:
        True if successful, False otherwise
    """
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        for key, value in updates.items():
            if hasattr(task, key):
                setattr(task, key, value)
        
        session.commit()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error updating task {task_id}: {e}")
        session.rollback()
        return False


def mark_task_completed(session: Session, task_id: int) -> bool:
    """
    Mark a task as completed.
    
    Args:
        session: Database session
        task_id: Task ID
        
    Returns:
        True if successful, False otherwise
    """
    return update_task(session, task_id, {'is_completed': True})


def soft_delete_task(session: Session, task_id: int) -> bool:
    """
    Soft delete a task (set is_deleted flag).
    
    Args:
        session: Database session
        task_id: Task ID
        
    Returns:
        True if successful, False otherwise
    """
    return update_task(session, task_id, {'is_deleted': True})


# =============================================================================
# TASK FILTERING - ON-DEMAND MENU FUNCTIONS
# =============================================================================

def get_tasks_due_today(session: Session, user_id: int) -> List[Task]:
    """
    Get all tasks due within the next 24 hours.
    
    Args:
        session: Database session
        user_id: User ID
        
    Returns:
        List of Task objects due today
    """
    try:
        now = datetime.now(timezone.utc)
        tomorrow = now + timedelta(days=1)
        
        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.is_deleted == False,
            Task.is_completed == False,
            Task.due_date >= now,
            Task.due_date <= tomorrow
        ).order_by(Task.due_date).all()
        
        return tasks
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching tasks due today for user {user_id}: {e}")
        return []


def get_tasks_due_this_week(session: Session, user_id: int) -> List[Task]:
    """
    Get all tasks due in the next 7 days.
    
    Args:
        session: Database session
        user_id: User ID
        
    Returns:
        List of Task objects due this week
    """
    try:
        now = datetime.now(timezone.utc)
        next_week = now + timedelta(days=7)
        
        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.is_deleted == False,
            Task.is_completed == False,
            Task.due_date >= now,
            Task.due_date <= next_week
        ).order_by(Task.due_date).all()
        
        return tasks
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching tasks due this week for user {user_id}: {e}")
        return []


def get_overdue_tasks(session: Session, user_id: int) -> List[Task]:
    """
    Get all overdue tasks for a user.
    
    Args:
        session: Database session
        user_id: User ID
        
    Returns:
        List of overdue Task objects
    """
    try:
        now = datetime.now(timezone.utc)
        
        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.is_deleted == False,
            Task.is_completed == False,
            Task.due_date < now
        ).order_by(desc(Task.due_date)).all()  # Most recently overdue first
        
        return tasks
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching overdue tasks for user {user_id}: {e}")
        return []


def get_all_upcoming_tasks(session: Session, user_id: int, limit: int = 20) -> List[Task]:
    """
    Get all upcoming tasks for a user (paginated).
    
    Args:
        session: Database session
        user_id: User ID
        limit: Maximum number of tasks to return
        
    Returns:
        List of upcoming Task objects
    """
    try:
        now = datetime.now(timezone.utc)
        
        tasks = session.query(Task).filter(
            Task.user_id == user_id,
            Task.is_deleted == False,
            Task.is_completed == False,
            Task.due_date >= now
        ).order_by(Task.due_date).limit(limit).all()
        
        return tasks
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching upcoming tasks for user {user_id}: {e}")
        return []


# =============================================================================
# BACKGROUND JOB FUNCTIONS
# =============================================================================

def get_tasks_needing_reminders(session: Session) -> Dict[str, List[Task]]:
    """
    Get tasks that need reminders sent (for reminder background job).
    
    Returns:
        Dictionary mapping reminder types to lists of tasks
    """
    try:
        now = datetime.now(timezone.utc)
        
        # Define time windows for each reminder type
        reminder_windows = {
            '1_week': (now + timedelta(days=6, hours=23), now + timedelta(days=7, hours=1)),
            '3_days': (now + timedelta(days=2, hours=23), now + timedelta(days=3, hours=1)),
            '1_day': (now + timedelta(hours=23), now + timedelta(hours=25)),
            '8_hours': (now + timedelta(hours=7), now + timedelta(hours=9)),
            '2_hours': (now + timedelta(hours=1), now + timedelta(hours=3)),
            '1_hour': (now + timedelta(minutes=30), now + timedelta(minutes=90))
        }
        
        results = {}
        
        for reminder_type, (start_time, end_time) in reminder_windows.items():
            # Build query for this reminder type
            query = session.query(Task).join(User).filter(
                Task.is_deleted == False,
                Task.is_completed == False,
                Task.due_date >= start_time,
                Task.due_date <= end_time,
                User.is_active == True,
                User.reminder_enabled == True
            )
            
            # Add reminder-specific filters
            if reminder_type == '1_week':
                query = query.filter(
                    Task.reminder_1_week_sent == False,
                    User.subscription_tier == SubscriptionTier.PREMIUM
                )
            elif reminder_type == '3_days':
                query = query.filter(
                    Task.reminder_3_days_sent == False,
                    User.subscription_tier == SubscriptionTier.PREMIUM
                )
            elif reminder_type == '1_day':
                query = query.filter(Task.reminder_1_day_sent == False)  # All users get 1-day
            elif reminder_type == '8_hours':
                query = query.filter(
                    Task.reminder_8_hours_sent == False,
                    User.subscription_tier == SubscriptionTier.PREMIUM
                )
            elif reminder_type == '2_hours':
                query = query.filter(
                    Task.reminder_2_hours_sent == False,
                    User.subscription_tier == SubscriptionTier.PREMIUM
                )
            elif reminder_type == '1_hour':
                query = query.filter(
                    Task.reminder_1_hour_sent == False,
                    User.subscription_tier == SubscriptionTier.PREMIUM
                )
            
            results[reminder_type] = query.all()
        
        return results
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching tasks needing reminders: {e}")
        return {}


def mark_reminder_sent(session: Session, task_id: int, reminder_type: str) -> bool:
    """
    Mark a specific reminder as sent for a task.
    
    Args:
        session: Database session
        task_id: Task ID
        reminder_type: Type of reminder ('1_week', '3_days', etc.)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        task = session.query(Task).filter(Task.id == task_id).first()
        if not task:
            return False
        
        task.mark_reminder_sent(reminder_type)
        session.commit()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error marking reminder sent for task {task_id}: {e}")
        session.rollback()
        return False


def get_expired_premium_users(session: Session) -> List[User]:
    """
    Get users whose premium subscriptions have expired.
    
    Returns:
        List of User objects with expired premium subscriptions
    """
    try:
        now = datetime.now(timezone.utc)
        
        expired_users = session.query(User).filter(
            User.subscription_tier == SubscriptionTier.PREMIUM,
            User.subscription_expiry_date < now,
            User.is_active == True
        ).all()
        
        return expired_users
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching expired premium users: {e}")
        return []


def downgrade_expired_users(session: Session, user_ids: List[int]) -> int:
    """
    Downgrade expired premium users to free tier.
    
    Args:
        session: Database session
        user_ids: List of user IDs to downgrade
        
    Returns:
        Number of users downgraded
    """
    try:
        downgraded_count = session.query(User).filter(
            User.id.in_(user_ids)
        ).update(
            {
                User.subscription_tier: SubscriptionTier.FREE,
                User.subscription_expiry_date: None
            },
            synchronize_session=False
        )
        
        session.commit()
        logger.info(f"Downgraded {downgraded_count} expired premium users")
        return downgraded_count
        
    except SQLAlchemyError as e:
        logger.error(f"Error downgrading expired users: {e}")
        session.rollback()
        return 0


def get_users_for_weekly_digest(session: Session) -> List[User]:
    """
    Get premium users who should receive the weekly digest.
    
    Returns:
        List of premium User objects with weekly digest enabled
    """
    try:
        users = session.query(User).filter(
            User.subscription_tier == SubscriptionTier.PREMIUM,
            User.weekly_digest_enabled == True,
            User.is_active == True,
            User.token_invalid == False
        ).all()
        
        # Filter to only include users with active subscriptions
        active_premium_users = [user for user in users if user.is_premium]
        
        return active_premium_users
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching users for weekly digest: {e}")
        return []


# =============================================================================
# DATA REFRESH FUNCTIONS
# =============================================================================

def get_users_for_canvas_refresh(session: Session, batch_size: int = 10) -> List[User]:
    """
    Get a batch of users for Canvas data refresh (staggered updates).
    
    Args:
        session: Database session
        batch_size: Number of users to return for processing
        
    Returns:
        List of User objects that need Canvas refresh
    """
    try:
        # Get users who haven't been synced recently or have invalid tokens reset
        cutoff_time = datetime.now(timezone.utc) - timedelta(hours=6)  # Sync every 6 hours
        
        users = session.query(User).filter(
            User.is_active == True,
            User.canvas_token.isnot(None),
            or_(
                User.last_sync_at.is_(None),
                User.last_sync_at < cutoff_time,
                User.token_invalid == False  # Include users whose tokens were recently fixed
            )
        ).order_by(
            User.last_sync_at.asc().nullsfirst()  # Prioritize never-synced users
        ).limit(batch_size).all()
        
        return users
        
    except SQLAlchemyError as e:
        logger.error(f"Error fetching users for Canvas refresh: {e}")
        return []


def update_user_last_sync(session: Session, user_id: int, success: bool = True) -> bool:
    """
    Update user's last sync timestamp and token status.
    
    Args:
        session: Database session
        user_id: User ID
        success: Whether the sync was successful
        
    Returns:
        True if successful, False otherwise
    """
    try:
        user = session.query(User).filter(User.id == user_id).first()
        if not user:
            return False
        
        if success:
            user.last_sync_at = datetime.now(timezone.utc)
            user.token_invalid = False
        else:
            user.token_invalid = True
        
        session.commit()
        return True
        
    except SQLAlchemyError as e:
        logger.error(f"Error updating last sync for user {user_id}: {e}")
        session.rollback()
        return False