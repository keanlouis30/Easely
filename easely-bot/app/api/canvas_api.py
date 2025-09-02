"""
Canvas API Module - The "Bridge to Canvas"

This module handles all communication with the Canvas LMS API.
It manages authentication, data fetching, data creation, and response parsing.
"""

import requests
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import time

# Set up logging
logger = logging.getLogger(__name__)

# Canvas API base URL - this will be extracted from the token domain during validation
CANVAS_API_BASE = None


class CanvasAPIError(Exception):
    """Custom exception for Canvas API errors"""
    pass


class TokenInvalidError(CanvasAPIError):
    """Raised when Canvas token is invalid or revoked"""
    pass


class RateLimitError(CanvasAPIError):
    """Raised when Canvas API rate limit is exceeded"""
    pass


def _get_canvas_domain_from_token(token: str) -> Optional[str]:
    """
    Extract Canvas domain from token by making a test API call.
    Canvas tokens are domain-specific, so we need to determine the domain.
    
    Args:
        token (str): Canvas API token
        
    Returns:
        Optional[str]: Canvas domain (e.g., "canvas.instructure.com") or None if failed
    """
    # Common Canvas domains to try
    common_domains = [
        "canvas.instructure.com",
        "learning.instructure.com",
        "canvas.edu",
        "instructure.com"
    ]
    
    for domain in common_domains:
        try:
            url = f"https://{domain}/api/v1/users/self"
            headers = {"Authorization": f"Bearer {token}"}
            
            response = requests.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                logger.info(f"Successfully identified Canvas domain: {domain}")
                return domain
        except requests.exceptions.RequestException:
            continue
    
    logger.error("Could not identify Canvas domain from token")
    return None


def _make_canvas_request(endpoint: str, token: str, method: str = "GET", 
                        data: Optional[Dict] = None, params: Optional[Dict] = None) -> requests.Response:
    """
    Make an authenticated request to the Canvas API.
    
    Args:
        endpoint (str): API endpoint (e.g., "/api/v1/users/self")
        token (str): Canvas API token
        method (str): HTTP method (GET, POST, PUT, DELETE)
        data (Optional[Dict]): Request body data for POST/PUT requests
        params (Optional[Dict]): URL parameters
        
    Returns:
        requests.Response: The response object
        
    Raises:
        TokenInvalidError: If token is invalid or revoked
        RateLimitError: If rate limit is exceeded
        CanvasAPIError: For other API errors
    """
    global CANVAS_API_BASE
    
    # If we don't have the base URL yet, determine it from the token
    if CANVAS_API_BASE is None:
        domain = _get_canvas_domain_from_token(token)
        if domain is None:
            raise TokenInvalidError("Could not validate Canvas domain for token")
        CANVAS_API_BASE = f"https://{domain}"
    
    url = f"{CANVAS_API_BASE}{endpoint}"
    headers = {"Authorization": f"Bearer {token}"}
    
    try:
        response = requests.request(
            method=method,
            url=url,
            headers=headers,
            json=data if data else None,
            params=params,
            timeout=30
        )
        
        # Handle rate limiting
        if response.status_code == 429:
            logger.warning("Canvas API rate limit exceeded")
            raise RateLimitError("Canvas API rate limit exceeded")
        
        # Handle authentication errors
        if response.status_code == 401:
            logger.error("Canvas API token invalid or revoked")
            raise TokenInvalidError("Canvas API token is invalid or revoked")
        
        # Handle other client/server errors
        if response.status_code >= 400:
            error_msg = f"Canvas API error {response.status_code}: {response.text}"
            logger.error(error_msg)
            raise CanvasAPIError(error_msg)
        
        return response
        
    except requests.exceptions.Timeout:
        logger.error("Timeout connecting to Canvas API")
        raise CanvasAPIError("Timeout connecting to Canvas API")
    except requests.exceptions.ConnectionError:
        logger.error("Connection error to Canvas API")
        raise CanvasAPIError("Connection error to Canvas API")
    except requests.exceptions.RequestException as e:
        logger.error(f"Unexpected error connecting to Canvas API: {e}")
        raise CanvasAPIError(f"Unexpected error: {e}")


def validate_token(token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
    """
    Validate a Canvas API token by making a test request.
    
    Args:
        token (str): Canvas API token to validate
        
    Returns:
        Tuple[bool, Optional[Dict]]: (is_valid, user_info)
        user_info contains id, name, email if valid
    """
    try:
        response = _make_canvas_request("/api/v1/users/self", token)
        user_data = response.json()
        
        # Extract essential user information
        user_info = {
            "id": user_data.get("id"),
            "name": user_data.get("name"),
            "email": user_data.get("email"),
            "login_id": user_data.get("login_id")
        }
        
        logger.info(f"Token validated successfully for user: {user_info['name']}")
        return True, user_info
        
    except (TokenInvalidError, CanvasAPIError) as e:
        logger.error(f"Token validation failed: {e}")
        return False, None


def get_courses(token: str) -> List[Dict[str, Any]]:
    """
    Fetch all active courses for a user.
    
    Args:
        token (str): Canvas API token
        
    Returns:
        List[Dict]: List of course dictionaries with id, name, code
        
    Raises:
        TokenInvalidError: If token is invalid
        CanvasAPIError: For other API errors
    """
    try:
        # Get active courses with enrollment state
        params = {
            "enrollment_state": "active",
            "per_page": 100,  # Get up to 100 courses per page
            "include": ["term"]
        }
        
        response = _make_canvas_request("/api/v1/courses", token, params=params)
        courses_data = response.json()
        
        # Parse and clean course data
        courses = []
        for course in courses_data:
            # Skip courses that are not published or accessible
            if not course.get("workflow_state") == "available":
                continue
                
            course_info = {
                "id": course.get("id"),
                "name": course.get("name", "Unnamed Course"),
                "course_code": course.get("course_code", ""),
                "term": course.get("term", {}).get("name", ""),
                "start_at": course.get("start_at"),
                "end_at": course.get("end_at")
            }
            courses.append(course_info)
        
        logger.info(f"Retrieved {len(courses)} active courses")
        return courses
        
    except (TokenInvalidError, RateLimitError):
        raise  # Re-raise these specific exceptions
    except Exception as e:
        logger.error(f"Error fetching courses: {e}")
        raise CanvasAPIError(f"Error fetching courses: {e}")


def get_assignments(token: str) -> List[Dict[str, Any]]:
    """
    Fetch all upcoming assignments across all courses.
    
    Args:
        token (str): Canvas API token
        
    Returns:
        List[Dict]: List of assignment dictionaries with essential info
        
    Raises:
        TokenInvalidError: If token is invalid
        CanvasAPIError: For other API errors
    """
    try:
        # First get all active courses
        courses = get_courses(token)
        
        all_assignments = []
        
        for course in courses:
            course_id = course["id"]
            
            # Get assignments for this course
            params = {
                "per_page": 100,
                "include": ["submission"],
                "order_by": "due_at"
            }
            
            try:
                response = _make_canvas_request(
                    f"/api/v1/courses/{course_id}/assignments", 
                    token, 
                    params=params
                )
                assignments_data = response.json()
                
                for assignment in assignments_data:
                    # Skip assignments without due dates or that are not published
                    if not assignment.get("due_at") or assignment.get("workflow_state") != "published":
                        continue
                    
                    # Parse due date
                    due_date = None
                    due_at_str = assignment.get("due_at")
                    if due_at_str:
                        try:
                            due_date = datetime.fromisoformat(due_at_str.replace('Z', '+00:00'))
                        except ValueError:
                            logger.warning(f"Could not parse due date: {due_at_str}")
                            continue
                    
                    # Check if assignment is already submitted
                    submission = assignment.get("submission", {})
                    is_submitted = submission.get("workflow_state") == "submitted"
                    
                    assignment_info = {
                        "id": assignment.get("id"),
                        "title": assignment.get("name", "Untitled Assignment"),
                        "due_date": due_date,
                        "course_id": course_id,
                        "course_name": course["name"],
                        "course_code": course["course_code"],
                        "points_possible": assignment.get("points_possible", 0),
                        "submission_types": assignment.get("submission_types", []),
                        "html_url": assignment.get("html_url"),
                        "is_submitted": is_submitted,
                        "source": "canvas_assignment"
                    }
                    
                    all_assignments.append(assignment_info)
                    
            except CanvasAPIError as e:
                logger.warning(f"Could not fetch assignments for course {course_id}: {e}")
                continue  # Skip this course and continue with others
        
        # Sort assignments by due date
        all_assignments.sort(key=lambda x: x["due_date"] or datetime.max.replace(tzinfo=timezone.utc))
        
        logger.info(f"Retrieved {len(all_assignments)} assignments across {len(courses)} courses")
        return all_assignments
        
    except (TokenInvalidError, RateLimitError):
        raise  # Re-raise these specific exceptions
    except Exception as e:
        logger.error(f"Error fetching assignments: {e}")
        raise CanvasAPIError(f"Error fetching assignments: {e}")


def get_calendar_events(token: str, start_date: Optional[datetime] = None, 
                       end_date: Optional[datetime] = None) -> List[Dict[str, Any]]:
    """
    Fetch calendar events (including manual entries) from Canvas.
    
    Args:
        token (str): Canvas API token
        start_date (Optional[datetime]): Start date for filtering events
        end_date (Optional[datetime]): End date for filtering events
        
    Returns:
        List[Dict]: List of calendar event dictionaries
        
    Raises:
        TokenInvalidError: If token is invalid
        CanvasAPIError: For other API errors
    """
    try:
        params = {
            "per_page": 100,
            "type": "event"  # Only get calendar events, not assignments
        }
        
        # Add date filters if provided
        if start_date:
            params["start_date"] = start_date.isoformat()
        if end_date:
            params["end_date"] = end_date.isoformat()
        
        response = _make_canvas_request("/api/v1/calendar_events", token, params=params)
        events_data = response.json()
        
        events = []
        for event in events_data:
            # Parse start date
            start_date_parsed = None
            start_at_str = event.get("start_at")
            if start_at_str:
                try:
                    start_date_parsed = datetime.fromisoformat(start_at_str.replace('Z', '+00:00'))
                except ValueError:
                    logger.warning(f"Could not parse event start date: {start_at_str}")
                    continue
            
            event_info = {
                "id": event.get("id"),
                "title": event.get("title", "Untitled Event"),
                "start_date": start_date_parsed,
                "end_date": None,  # Parse end_at if needed
                "description": event.get("description"),
                "location_name": event.get("location_name"),
                "html_url": event.get("html_url"),
                "context_name": event.get("context_name"),  # Course name
                "source": "canvas_event"
            }
            
            # Parse end date if present
            end_at_str = event.get("end_at")
            if end_at_str:
                try:
                    event_info["end_date"] = datetime.fromisoformat(end_at_str.replace('Z', '+00:00'))
                except ValueError:
                    pass
            
            events.append(event_info)
        
        logger.info(f"Retrieved {len(events)} calendar events")
        return events
        
    except (TokenInvalidError, RateLimitError):
        raise  # Re-raise these specific exceptions
    except Exception as e:
        logger.error(f"Error fetching calendar events: {e}")
        raise CanvasAPIError(f"Error fetching calendar events: {e}")


def create_calendar_event(token: str, event_data: Dict[str, Any]) -> Optional[int]:
    """
    Create a new calendar event in Canvas.
    
    Args:
        token (str): Canvas API token
        event_data (Dict): Event details including title, start_at, etc.
        
    Expected event_data format:
        {
            "title": "Event Title",
            "start_at": datetime_object,
            "description": "Optional description",
            "course_id": optional_course_id_for_context
        }
        
    Returns:
        Optional[int]: Canvas event ID if successful, None if failed
        
    Raises:
        TokenInvalidError: If token is invalid
        CanvasAPIError: For other API errors
    """
    try:
        # Prepare the event payload
        calendar_event = {
            "title": event_data.get("title", "New Event"),
            "start_at": event_data["start_at"].isoformat(),
        }
        
        # Add optional fields
        if "description" in event_data:
            calendar_event["description"] = event_data["description"]
        
        if "end_at" in event_data and event_data["end_at"]:
            calendar_event["end_at"] = event_data["end_at"].isoformat()
        
        # If course_id is provided, create event in course context
        if "course_id" in event_data and event_data["course_id"]:
            endpoint = f"/api/v1/courses/{event_data['course_id']}/calendar_events"
        else:
            endpoint = "/api/v1/calendar_events"
        
        payload = {"calendar_event": calendar_event}
        
        response = _make_canvas_request(endpoint, token, method="POST", data=payload)
        created_event = response.json()
        
        event_id = created_event.get("id")
        logger.info(f"Created calendar event with ID: {event_id}")
        
        return event_id
        
    except (TokenInvalidError, RateLimitError):
        raise  # Re-raise these specific exceptions
    except Exception as e:
        logger.error(f"Error creating calendar event: {e}")
        raise CanvasAPIError(f"Error creating calendar event: {e}")


def update_calendar_event(token: str, event_id: int, event_data: Dict[str, Any]) -> bool:
    """
    Update an existing calendar event in Canvas.
    
    Args:
        token (str): Canvas API token
        event_id (int): Canvas event ID to update
        event_data (Dict): Updated event details
        
    Returns:
        bool: True if successful, False otherwise
        
    Raises:
        TokenInvalidError: If token is invalid
        CanvasAPIError: For other API errors
    """
    try:
        # Prepare the update payload
        calendar_event = {}
        
        if "title" in event_data:
            calendar_event["title"] = event_data["title"]
        
        if "start_at" in event_data:
            calendar_event["start_at"] = event_data["start_at"].isoformat()
        
        if "description" in event_data:
            calendar_event["description"] = event_data["description"]
        
        if "end_at" in event_data and event_data["end_at"]:
            calendar_event["end_at"] = event_data["end_at"].isoformat()
        
        payload = {"calendar_event": calendar_event}
        
        response = _make_canvas_request(
            f"/api/v1/calendar_events/{event_id}", 
            token, 
            method="PUT", 
            data=payload
        )
        
        logger.info(f"Updated calendar event ID: {event_id}")
        return True
        
    except (TokenInvalidError, RateLimitError):
        raise  # Re-raise these specific exceptions
    except Exception as e:
        logger.error(f"Error updating calendar event {event_id}: {e}")
        raise CanvasAPIError(f"Error updating calendar event: {e}")


def delete_calendar_event(token: str, event_id: int) -> bool:
    """
    Delete a calendar event from Canvas.
    
    Args:
        token (str): Canvas API token
        event_id (int): Canvas event ID to delete
        
    Returns:
        bool: True if successful, False otherwise
        
    Raises:
        TokenInvalidError: If token is invalid
        CanvasAPIError: For other API errors
    """
    try:
        response = _make_canvas_request(
            f"/api/v1/calendar_events/{event_id}", 
            token, 
            method="DELETE"
        )
        
        logger.info(f"Deleted calendar event ID: {event_id}")
        return True
        
    except (TokenInvalidError, RateLimitError):
        raise  # Re-raise these specific exceptions
    except Exception as e:
        logger.error(f"Error deleting calendar event {event_id}: {e}")
        raise CanvasAPIError(f"Error deleting calendar event: {e}")


def test_token_permissions(token: str) -> Dict[str, bool]:
    """
    Test what permissions a Canvas token has.
    
    Args:
        token (str): Canvas API token
        
    Returns:
        Dict[str, bool]: Dictionary of permission tests and results
    """
    permissions = {
        "read_user": False,
        "read_courses": False,
        "read_assignments": False,
        "read_calendar": False,
        "write_calendar": False
    }
    
    try:
        # Test user read permission
        try:
            _make_canvas_request("/api/v1/users/self", token)
            permissions["read_user"] = True
        except CanvasAPIError:
            pass
        
        # Test courses read permission
        try:
            _make_canvas_request("/api/v1/courses", token, params={"per_page": 1})
            permissions["read_courses"] = True
        except CanvasAPIError:
            pass
        
        # Test calendar read permission
        try:
            _make_canvas_request("/api/v1/calendar_events", token, params={"per_page": 1})
            permissions["read_calendar"] = True
        except CanvasAPIError:
            pass
        
        # Test calendar write permission by attempting to create a test event
        # (We'll immediately delete it if successful)
        try:
            test_event = {
                "title": "Easely Test Event - Delete Me",
                "start_at": datetime.now(timezone.utc)
            }
            event_id = create_calendar_event(token, test_event)
            if event_id:
                permissions["write_calendar"] = True
                # Clean up the test event
                try:
                    delete_calendar_event(token, event_id)
                except:
                    pass  # Don't fail if cleanup fails
        except CanvasAPIError:
            pass
        
        logger.info(f"Token permission test results: {permissions}")
        
    except Exception as e:
        logger.error(f"Error testing token permissions: {e}")
    
    return permissions


# Rate limiting helper for batch operations
def batch_request_with_rate_limit(requests_list: List[callable], delay: float = 0.1) -> List[Any]:
    """
    Execute a list of Canvas API requests with rate limiting.
    
    Args:
        requests_list (List[callable]): List of request functions to execute
        delay (float): Delay between requests in seconds
        
    Returns:
        List[Any]: Results from each request
    """
    results = []
    
    for i, request_func in enumerate(requests_list):
        try:
            result = request_func()
            results.append(result)
        except RateLimitError:
            logger.warning(f"Rate limit hit on request {i+1}, waiting longer...")
            time.sleep(5)  # Wait 5 seconds on rate limit
            try:
                result = request_func()  # Retry once
                results.append(result)
            except Exception as e:
                logger.error(f"Request {i+1} failed after rate limit retry: {e}")
                results.append(None)
        except Exception as e:
            logger.error(f"Request {i+1} failed: {e}")
            results.append(None)
        
        # Add delay between requests
        if i < len(requests_list) - 1:  # Don't delay after the last request
            time.sleep(delay)
    
    return results