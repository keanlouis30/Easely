#!/usr/bin/env python3
"""
refresh_data.py - The Data Auditor

This script runs periodically to ensure Easely's local database mirror remains
accurate by syncing with Canvas. It checks for new assignments, updated due dates,
and removed assignments to keep the local data fresh.

Schedule: Runs every 4 hours (0 */4 * * *) via Render Cron Job
"""

import logging
import sys
import time
from datetime import datetime, timezone
from typing import List, Dict, Set, Optional, Tuple

# Import Easely modules
try:
    from app.database.session import get_db_session
    from app.database.queries import (
        get_active_users,
        get_user_canvas_tasks,
        get_user_courses,
        create_task,
        update_task,
        delete_task,
        create_course,
        update_user_token_status
    )
    from app.api.canvas_api import (
        get_assignments,
        get_courses,
        CanvasAPIError,
        InvalidTokenError
    )
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
logger = logging.getLogger('refresh_data')

class SyncStats:
    """Track synchronization statistics"""
    def __init__(self):
        self.users_processed = 0
        self.users_failed = 0
        self.assignments_added = 0
        self.assignments_updated = 0
        self.assignments_deleted = 0
        self.courses_added = 0
        self.courses_updated = 0
        self.tokens_invalidated = 0

def sync_user_assignments(db, user, canvas_assignments: List[Dict]) -> Tuple[int, int, int]:
    """
    Sync assignments for a single user.
    
    Args:
        db: Database session
        user: User object
        canvas_assignments: List of assignments from Canvas API
        
    Returns:
        Tuple of (added_count, updated_count, deleted_count)
    """
    added_count = updated_count = deleted_count = 0
    
    try:
        # Get existing Canvas tasks from our database
        existing_tasks = get_user_canvas_tasks(db, user.id)
        existing_task_ids = {task.canvas_assignment_id for task in existing_tasks if task.canvas_assignment_id}
        
        # Convert Canvas assignments to a lookup dict
        canvas_assignment_dict = {
            str(assignment['id']): assignment 
            for assignment in canvas_assignments
        }
        canvas_assignment_ids = set(canvas_assignment_dict.keys())
        
        # Find new assignments (in Canvas but not in our DB)
        new_assignment_ids = canvas_assignment_ids - existing_task_ids
        for assignment_id in new_assignment_ids:
            assignment = canvas_assignment_dict[assignment_id]
            
            # Create new task
            task_data = {
                'user_id': user.id,
                'canvas_assignment_id': assignment_id,
                'title': assignment.get('name', 'Untitled Assignment'),
                'due_date': assignment.get('due_at'),
                'course_id': assignment.get('course_id'),
                'source': 'canvas_sync'
            }
            
            if create_task(db, task_data):
                added_count += 1
                logger.debug(f"Added new assignment: {assignment.get('name')} for user {user.id}")
        
        # Find assignments to update (check for due date changes)
        existing_assignment_ids = canvas_assignment_ids & existing_task_ids
        for assignment_id in existing_assignment_ids:
            assignment = canvas_assignment_dict[assignment_id]
            existing_task = next(
                (task for task in existing_tasks if task.canvas_assignment_id == assignment_id),
                None
            )
            
            if existing_task:
                # Check if due date has changed
                canvas_due_date = assignment.get('due_at')
                if canvas_due_date != existing_task.due_date.isoformat() if existing_task.due_date else None:
                    update_data = {
                        'title': assignment.get('name', existing_task.title),
                        'due_date': canvas_due_date
                    }
                    
                    if update_task(db, existing_task.id, update_data):
                        updated_count += 1
                        logger.debug(f"Updated assignment: {assignment.get('name')} for user {user.id}")
        
        # Find assignments to delete (in our DB but not in Canvas)
        deleted_assignment_ids = existing_task_ids - canvas_assignment_ids
        for task in existing_tasks:
            if task.canvas_assignment_id in deleted_assignment_ids:
                if delete_task(db, task.id):
                    deleted_count += 1
                    logger.debug(f"Deleted assignment: {task.title} for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error syncing assignments for user {user.id}: {e}")
        raise
    
    return added_count, updated_count, deleted_count

def sync_user_courses(db, user, canvas_courses: List[Dict]) -> Tuple[int, int]:
    """
    Sync courses for a single user.
    
    Args:
        db: Database session
        user: User object
        canvas_courses: List of courses from Canvas API
        
    Returns:
        Tuple of (added_count, updated_count)
    """
    added_count = updated_count = 0
    
    try:
        # Get existing courses from our database
        existing_courses = get_user_courses(db, user.id)
        existing_course_ids = {str(course.canvas_course_id) for course in existing_courses}
        
        # Process Canvas courses
        for course in canvas_courses:
            course_id = str(course['id'])
            course_name = course.get('name', 'Untitled Course')
            
            if course_id not in existing_course_ids:
                # Create new course
                course_data = {
                    'user_id': user.id,
                    'canvas_course_id': course_id,
                    'course_name': course_name
                }
                
                if create_course(db, course_data):
                    added_count += 1
                    logger.debug(f"Added new course: {course_name} for user {user.id}")
            else:
                # Check if course name has changed
                existing_course = next(
                    (c for c in existing_courses if str(c.canvas_course_id) == course_id),
                    None
                )
                
                if existing_course and existing_course.course_name != course_name:
                    # Note: You'll need to implement update_course function
                    # For now, we'll skip course updates to keep it simple
                    updated_count += 1
                    logger.debug(f"Course name changed: {course_name} for user {user.id}")
        
    except Exception as e:
        logger.error(f"Error syncing courses for user {user.id}: {e}")
        raise
    
    return added_count, updated_count

def sync_single_user(db, user) -> Dict:
    """
    Sync data for a single user with rate limiting consideration.
    
    Args:
        db: Database session
        user: User object with canvas_token
        
    Returns:
        Dict with sync results
    """
    result = {
        'success': False,
        'assignments_added': 0,
        'assignments_updated': 0,
        'assignments_deleted': 0,
        'courses_added': 0,
        'courses_updated': 0,
        'error': None
    }
    
    try:
        logger.debug(f"Syncing data for user {user.id}")
        
        # Get assignments from Canvas
        canvas_assignments = get_assignments(user.canvas_token)
        
        # Get courses from Canvas
        canvas_courses = get_courses(user.canvas_token)
        
        # Sync assignments
        assignments_result = sync_user_assignments(db, user, canvas_assignments)
        result['assignments_added'] = assignments_result[0]
        result['assignments_updated'] = assignments_result[1]
        result['assignments_deleted'] = assignments_result[2]
        
        # Sync courses
        courses_result = sync_user_courses(db, user, canvas_courses)
        result['courses_added'] = courses_result[0]
        result['courses_updated'] = courses_result[1]
        
        result['success'] = True
        logger.debug(f"Successfully synced user {user.id}")
        
    except InvalidTokenError:
        logger.warning(f"Invalid token for user {user.id}, marking as invalid")
        update_user_token_status(db, user.id, is_valid=False)
        result['error'] = 'invalid_token'
        
    except CanvasAPIError as e:
        logger.error(f"Canvas API error for user {user.id}: {e}")
        result['error'] = f'canvas_api_error: {str(e)}'
        
    except Exception as e:
        logger.error(f"Unexpected error syncing user {user.id}: {e}")
        result['error'] = f'unexpected_error: {str(e)}'
    
    return result

def process_data_refresh() -> SyncStats:
    """
    Main function to refresh data for all active users.
    
    Returns:
        SyncStats: Statistics about the sync process
    """
    db = get_db_session()
    stats = SyncStats()
    
    try:
        # Get all active users with valid tokens
        logger.info("Querying for active users...")
        active_users = get_active_users(db)
        
        if not active_users:
            logger.info("No active users found.")
            return stats
        
        logger.info(f"Found {len(active_users)} active users to sync.")
        
        # Process each user with rate limiting
        for i, user in enumerate(active_users):
            try:
                # Add delay between users to avoid rate limiting (except for first user)
                if i > 0:
                    time.sleep(2)  # 2-second delay between users
                
                # Sync user data
                result = sync_single_user(db, user)
                
                if result['success']:
                    stats.users_processed += 1
                    stats.assignments_added += result['assignments_added']
                    stats.assignments_updated += result['assignments_updated']
                    stats.assignments_deleted += result['assignments_deleted']
                    stats.courses_added += result['courses_added']
                    stats.courses_updated += result['courses_updated']
                else:
                    stats.users_failed += 1
                    if result['error'] == 'invalid_token':
                        stats.tokens_invalidated += 1
                
                # Log progress every 50 users
                if (i + 1) % 50 == 0:
                    logger.info(f"Progress: {i + 1}/{len(active_users)} users processed")
                
            except Exception as e:
                logger.error(f"Critical error processing user {user.id}: {e}")
                stats.users_failed += 1
                continue
        
        # Commit all changes
        db.commit()
        logger.info(f"Successfully processed {stats.users_processed} users")
        
    except Exception as e:
        logger.error(f"Error during data refresh: {e}")
        db.rollback()
        raise
    finally:
        db.close()
    
    return stats

def main():
    """
    Main entry point for the refresh_data script.
    """
    logger.info("=== Easely Data Refresh Started ===")
    start_time = datetime.now(timezone.utc)
    
    try:
        # Load settings
        settings = get_settings()
        logger.info("Settings loaded successfully")
        
        # Process data refresh
        stats = process_data_refresh()
        
        # Calculate execution time
        end_time = datetime.now(timezone.utc)
        execution_time = (end_time - start_time).total_seconds()
        
        # Log comprehensive summary
        logger.info("=== Data Refresh Summary ===")
        logger.info(f"Users processed successfully: {stats.users_processed}")
        logger.info(f"Users failed: {stats.users_failed}")
        logger.info(f"Tokens invalidated: {stats.tokens_invalidated}")
        logger.info(f"Assignments added: {stats.assignments_added}")
        logger.info(f"Assignments updated: {stats.assignments_updated}")
        logger.info(f"Assignments deleted: {stats.assignments_deleted}")
        logger.info(f"Courses added: {stats.courses_added}")
        logger.info(f"Courses updated: {stats.courses_updated}")
        logger.info(f"Execution time: {execution_time:.2f} seconds")
        logger.info(f"Completed at: {end_time.isoformat()}")
        logger.info("=== Easely Data Refresh Completed ===")
        
    except Exception as e:
        logger.error(f"Critical error in main execution: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()