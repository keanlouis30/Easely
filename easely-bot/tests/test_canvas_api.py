"""
Test suite for the Canvas API module.

This module tests the canvas_api.py functionality without making actual HTTP requests
to the Canvas LMS. It uses mocking to simulate Canvas API responses and verifies
that our parsing and data transformation logic works correctly.
"""

import pytest
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone
import json

# Import the module we're testing
# Note: Adjust import path based on actual project structure
from app.api.canvas_api import (
    get_assignments,
    get_courses, 
    create_calendar_event,
    validate_token,
    CanvasAPIError
)


class TestCanvasAPIDataParsing:
    """Test suite for Canvas API data parsing functions."""
    
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Sample Canvas API response data for assignments
        self.sample_assignments_response = [
            {
                "id": 12345,
                "name": "Final Essay - Literature Analysis",
                "due_at": "2024-12-15T23:59:00Z",
                "html_url": "https://canvas.university.edu/courses/1001/assignments/12345",
                "course_id": 1001,
                "points_possible": 100.0,
                "submission_types": ["online_text_entry"],
                "description": "<p>Write a 5-page essay analyzing...</p>",
                "locked": False,
                "unlock_at": None,
                "lock_at": None
            },
            {
                "id": 12346,
                "name": "Math Quiz 3",
                "due_at": "2024-12-10T14:30:00Z",
                "html_url": "https://canvas.university.edu/courses/1002/assignments/12346",
                "course_id": 1002,
                "points_possible": 50.0,
                "submission_types": ["online_quiz"],
                "description": "<p>Quiz covering chapters 7-9</p>",
                "locked": False,
                "unlock_at": None,
                "lock_at": "2024-12-10T14:45:00Z"
            },
            {
                "id": 12347,
                "name": "No Due Date Assignment",
                "due_at": None,
                "html_url": "https://canvas.university.edu/courses/1001/assignments/12347",
                "course_id": 1001,
                "points_possible": 25.0,
                "submission_types": ["online_upload"],
                "description": None,
                "locked": False,
                "unlock_at": None,
                "lock_at": None
            }
        ]
        
        # Sample Canvas API response data for courses
        self.sample_courses_response = [
            {
                "id": 1001,
                "name": "English Literature 101",
                "course_code": "ENG101",
                "workflow_state": "available",
                "account_id": 1,
                "root_account_id": 1,
                "enrollment_term_id": 123,
                "start_at": "2024-09-01T08:00:00Z",
                "end_at": "2024-12-20T17:00:00Z"
            },
            {
                "id": 1002,
                "name": "Calculus I",
                "course_code": "MATH151",
                "workflow_state": "available", 
                "account_id": 1,
                "root_account_id": 1,
                "enrollment_term_id": 123,
                "start_at": "2024-09-01T08:00:00Z",
                "end_at": "2024-12-20T17:00:00Z"
            },
            {
                "id": 1003,
                "name": "Concluded Course",
                "course_code": "OLD101",
                "workflow_state": "concluded",
                "account_id": 1,
                "root_account_id": 1,
                "enrollment_term_id": 122,
                "start_at": "2024-01-15T08:00:00Z",
                "end_at": "2024-05-15T17:00:00Z"
            }
        ]
        
        # Sample successful token validation response
        self.sample_user_profile_response = {
            "id": 54321,
            "name": "John Doe",
            "short_name": "John",
            "sortable_name": "Doe, John",
            "avatar_url": "https://canvas.university.edu/avatar.png",
            "primary_email": "john.doe@university.edu",
            "login_id": "johndoe",
            "calendar": {
                "ics": "https://canvas.university.edu/feeds/calendars/user_123.ics"
            }
        }

    @patch('app.api.canvas_api.requests.get')
    def test_get_assignments_successful_parsing(self, mock_get):
        """Test that get_assignments correctly parses Canvas API response."""
        # Mock the API response
        mock_response = Mock()
        mock_response.json.return_value = self.sample_assignments_response
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Call the function
        result = get_assignments("fake_token", "fake_base_url")
        
        # Verify the API was called correctly
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "assignments" in call_args[0][0]  # URL contains 'assignments'
        assert call_args[1]['headers']['Authorization'] == 'Bearer fake_token'
        
        # Verify the parsed result
        assert isinstance(result, list)
        assert len(result) == 2  # Should exclude assignment without due_at
        
        # Test first assignment parsing
        first_assignment = result[0]
        assert first_assignment['canvas_assignment_id'] == 12345
        assert first_assignment['title'] == "Final Essay - Literature Analysis"
        assert first_assignment['due_date'] == datetime(2024, 12, 15, 23, 59, tzinfo=timezone.utc)
        assert first_assignment['course_id'] == 1001
        assert first_assignment['source'] == 'canvas'
        
        # Test second assignment parsing
        second_assignment = result[1]
        assert second_assignment['canvas_assignment_id'] == 12346
        assert second_assignment['title'] == "Math Quiz 3"
        assert second_assignment['due_date'] == datetime(2024, 12, 10, 14, 30, tzinfo=timezone.utc)
        assert second_assignment['course_id'] == 1002
        assert second_assignment['source'] == 'canvas'

    @patch('app.api.canvas_api.requests.get')
    def test_get_assignments_filters_no_due_date(self, mock_get):
        """Test that assignments without due dates are filtered out."""
        # Mock response with assignment that has no due_at
        mock_response = Mock()
        mock_response.json.return_value = [self.sample_assignments_response[2]]  # No due date assignment
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = get_assignments("fake_token", "fake_base_url")
        
        # Should return empty list since assignment has no due_at
        assert result == []

    @patch('app.api.canvas_api.requests.get')
    def test_get_courses_successful_parsing(self, mock_get):
        """Test that get_courses correctly parses Canvas API response."""
        mock_response = Mock()
        mock_response.json.return_value = self.sample_courses_response
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = get_courses("fake_token", "fake_base_url")
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "courses" in call_args[0][0]
        assert call_args[1]['headers']['Authorization'] == 'Bearer fake_token'
        
        # Verify parsing (should exclude concluded courses)
        assert isinstance(result, list)
        assert len(result) == 2  # Should exclude concluded course
        
        first_course = result[0]
        assert first_course['canvas_course_id'] == 1001
        assert first_course['course_name'] == "English Literature 101"
        
        second_course = result[1] 
        assert second_course['canvas_course_id'] == 1002
        assert second_course['course_name'] == "Calculus I"

    @patch('app.api.canvas_api.requests.get')
    def test_get_courses_filters_concluded(self, mock_get):
        """Test that concluded courses are filtered out."""
        mock_response = Mock()
        mock_response.json.return_value = [self.sample_courses_response[2]]  # Concluded course only
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = get_courses("fake_token", "fake_base_url")
        
        assert result == []

    @patch('app.api.canvas_api.requests.get')
    def test_validate_token_success(self, mock_get):
        """Test successful token validation."""
        mock_response = Mock()
        mock_response.json.return_value = self.sample_user_profile_response
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = validate_token("valid_token", "fake_base_url")
        
        # Verify API call
        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert "users/self" in call_args[0][0]
        assert call_args[1]['headers']['Authorization'] == 'Bearer valid_token'
        
        # Verify result
        assert result is True

    @patch('app.api.canvas_api.requests.get')
    def test_validate_token_failure(self, mock_get):
        """Test token validation failure."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_get.return_value = mock_response
        
        result = validate_token("invalid_token", "fake_base_url")
        
        assert result is False


class TestCanvasAPIEventCreation:
    """Test suite for Canvas calendar event creation."""
    
    def setup_method(self):
        """Set up test fixtures for event creation tests."""
        self.sample_event_data = {
            'title': 'Study Session for Finals',
            'due_date': datetime(2024, 12, 20, 15, 30, tzinfo=timezone.utc),
            'course_id': 1001,
            'description': 'Group study session in library'
        }
        
        self.sample_canvas_event_response = {
            "id": 98765,
            "title": "Study Session for Finals",
            "start_at": "2024-12-20T15:30:00Z",
            "end_at": "2024-12-20T16:30:00Z",
            "description": "Group study session in library",
            "context_code": "course_1001",
            "workflow_state": "active",
            "url": "https://canvas.university.edu/calendar?event_id=98765",
            "html_url": "https://canvas.university.edu/calendar?event_id=98765",
            "all_day": False,
            "created_at": "2024-12-01T10:00:00Z",
            "updated_at": "2024-12-01T10:00:00Z"
        }

    @patch('app.api.canvas_api.requests.post')
    def test_create_calendar_event_success(self, mock_post):
        """Test successful calendar event creation."""
        mock_response = Mock()
        mock_response.json.return_value = self.sample_canvas_event_response
        mock_response.status_code = 201
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = create_calendar_event(
            token="fake_token",
            base_url="fake_base_url",
            **self.sample_event_data
        )
        
        # Verify API call was made correctly
        mock_post.assert_called_once()
        call_args = mock_post.call_args
        
        # Check URL
        assert "calendar_events" in call_args[0][0]
        
        # Check headers
        assert call_args[1]['headers']['Authorization'] == 'Bearer fake_token'
        assert call_args[1]['headers']['Content-Type'] == 'application/json'
        
        # Check request payload
        payload = json.loads(call_args[1]['data'])
        assert payload['calendar_event']['title'] == 'Study Session for Finals'
        assert payload['calendar_event']['start_at'] == '2024-12-20T15:30:00Z'
        assert payload['calendar_event']['description'] == 'Group study session in library'
        assert payload['calendar_event']['context_code'] == 'course_1001'
        
        # Check return value
        assert result == 98765

    @patch('app.api.canvas_api.requests.post')
    def test_create_calendar_event_personal(self, mock_post):
        """Test creating a personal calendar event (no course)."""
        mock_response = Mock()
        mock_response.json.return_value = {**self.sample_canvas_event_response, "context_code": "user_54321"}
        mock_response.status_code = 201
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # Test data without course_id (personal event)
        personal_event_data = {
            'title': 'Personal Reminder',
            'due_date': datetime(2024, 12, 25, 10, 0, tzinfo=timezone.utc),
            'course_id': None,
            'description': 'Don\'t forget to call mom'
        }
        
        result = create_calendar_event(
            token="fake_token",
            base_url="fake_base_url", 
            **personal_event_data
        )
        
        # Verify the payload doesn't include context_code for personal events
        call_args = mock_post.call_args
        payload = json.loads(call_args[1]['data'])
        
        # Personal events should not have context_code in the request
        assert 'context_code' not in payload['calendar_event']
        assert payload['calendar_event']['title'] == 'Personal Reminder'

    @patch('app.api.canvas_api.requests.post')
    def test_create_calendar_event_api_error(self, mock_post):
        """Test handling of Canvas API errors during event creation."""
        mock_response = Mock()
        mock_response.status_code = 400
        mock_response.json.return_value = {"errors": [{"message": "Invalid date format"}]}
        mock_response.raise_for_status.side_effect = Exception("Bad Request")
        mock_post.return_value = mock_response
        
        # Should raise CanvasAPIError
        with pytest.raises(CanvasAPIError) as exc_info:
            create_calendar_event(
                token="fake_token",
                base_url="fake_base_url",
                **self.sample_event_data
            )
        
        assert "Canvas API error" in str(exc_info.value)


class TestCanvasAPIErrorHandling:
    """Test suite for Canvas API error handling."""
    
    @patch('app.api.canvas_api.requests.get')
    def test_get_assignments_api_error(self, mock_get):
        """Test handling of API errors in get_assignments."""
        mock_response = Mock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("Unauthorized")
        mock_get.return_value = mock_response
        
        with pytest.raises(CanvasAPIError) as exc_info:
            get_assignments("invalid_token", "fake_base_url")
        
        assert "Canvas API error" in str(exc_info.value)

    @patch('app.api.canvas_api.requests.get')
    def test_get_courses_api_error(self, mock_get):
        """Test handling of API errors in get_courses."""
        mock_response = Mock()
        mock_response.status_code = 500
        mock_response.raise_for_status.side_effect = Exception("Internal Server Error")
        mock_get.return_value = mock_response
        
        with pytest.raises(CanvasAPIError):
            get_courses("fake_token", "fake_base_url")

    @patch('app.api.canvas_api.requests.get')
    def test_network_error_handling(self, mock_get):
        """Test handling of network errors."""
        mock_get.side_effect = Exception("Connection timeout")
        
        with pytest.raises(CanvasAPIError) as exc_info:
            get_assignments("fake_token", "fake_base_url")
        
        assert "Canvas API error" in str(exc_info.value)


class TestCanvasAPIEdgeCases:
    """Test suite for edge cases and data validation."""
    
    @patch('app.api.canvas_api.requests.get')
    def test_empty_assignments_response(self, mock_get):
        """Test handling of empty assignments response."""
        mock_response = Mock()
        mock_response.json.return_value = []
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        result = get_assignments("fake_token", "fake_base_url")
        
        assert result == []

    @patch('app.api.canvas_api.requests.get')
    def test_malformed_date_handling(self, mock_get):
        """Test handling of malformed date strings in Canvas response."""
        malformed_assignment = {
            "id": 12345,
            "name": "Test Assignment",
            "due_at": "invalid-date-string",
            "html_url": "https://canvas.university.edu/courses/1001/assignments/12345",
            "course_id": 1001,
            "points_possible": 100.0,
            "submission_types": ["online_text_entry"],
            "description": "Test description",
            "locked": False,
            "unlock_at": None,
            "lock_at": None
        }
        
        mock_response = Mock()
        mock_response.json.return_value = [malformed_assignment]
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Should handle malformed dates gracefully by excluding the assignment
        result = get_assignments("fake_token", "fake_base_url")
        assert result == []

    @patch('app.api.canvas_api.requests.get')
    def test_missing_required_fields(self, mock_get):
        """Test handling of assignments with missing required fields."""
        incomplete_assignment = {
            "id": 12345,
            "name": "Test Assignment",
            # Missing due_at, course_id, etc.
        }
        
        mock_response = Mock()
        mock_response.json.return_value = [incomplete_assignment]
        mock_response.status_code = 200
        mock_response.raise_for_status.return_value = None
        mock_get.return_value = mock_response
        
        # Should handle missing fields gracefully
        result = get_assignments("fake_token", "fake_base_url")
        assert result == []


if __name__ == "__main__":
    # This allows running the tests directly with: python test_canvas_api.py
    pytest.main([__file__])