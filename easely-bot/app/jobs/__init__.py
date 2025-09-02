"""
Background Jobs Package for Easely

This package contains Easely's "Automated Workforce" - standalone, independent 
programs that perform critical system-wide tasks on scheduled intervals.

These jobs are designed to run as Render Cron Jobs and operate asynchronously
from the main web server to ensure optimal performance and reliability.

Job Modules:
-----------
- send_reminders: The "Town Crier" - Sends proactive assignment reminders
- check_expiries: The "Subscription Manager" - Handles premium subscription expiration  
- refresh_data: The "Data Auditor" - Syncs local database with Canvas API

Architecture:
------------
Each job is a complete, executable Python script that:
1. Initializes its own database connection
2. Performs its specific task
3. Logs results and exits cleanly

Jobs are NOT imported into the main application - they run independently
via Render's Cron Job service on their own schedules.
"""

# Import shared utilities that jobs might need
from typing import Dict, List, Optional
import logging
import sys
from datetime import datetime, timezone

# Jobs are standalone scripts, but we can provide common utilities
def setup_job_logging(job_name: str) -> logging.Logger:
    """
    Set up standardized logging for background jobs.
    
    Args:
        job_name: Name of the job (e.g., 'send_reminders')
        
    Returns:
        Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(sys.stdout)
        ]
    )
    return logging.getLogger(job_name)

def job_error_handler(job_name: str, error: Exception):
    """
    Standardized error handling for jobs.
    
    Args:
        job_name: Name of the job that failed
        error: The exception that occurred
    """
    logger = logging.getLogger(job_name)
    logger.error(f"Critical error in {job_name}: {error}")
    sys.exit(1)

def log_job_summary(job_name: str, stats: Dict, start_time: datetime):
    """
    Log a standardized job completion summary.
    
    Args:
        job_name: Name of the completed job
        stats: Dictionary of job statistics
        start_time: When the job started
    """
    logger = logging.getLogger(job_name)
    end_time = datetime.now(timezone.utc)
    execution_time = (end_time - start_time).total_seconds()
    
    logger.info(f"=== {job_name.title()} Job Summary ===")
    for key, value in stats.items():
        logger.info(f"{key}: {value}")
    logger.info(f"Execution time: {execution_time:.2f} seconds")
    logger.info(f"Completed at: {end_time.isoformat()}")

# Common job configuration
JOB_SCHEDULES = {
    'send_reminders': '0 * * * *',      # Every hour
    'check_expiries': '0 0 * * *',      # Daily at midnight
    'refresh_data': '0 */4 * * *'       # Every 4 hours
}

# Export utilities that jobs can use
__all__ = [
    'setup_job_logging',
    'job_error_handler', 
    'log_job_summary',
    'JOB_SCHEDULES'
]

# Note: Individual job modules (send_reminders.py, check_expiries.py, refresh_data.py)
# are NOT imported here as they are standalone executable scripts