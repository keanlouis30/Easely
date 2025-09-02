"""
Test suite for app/core/event_handler.py

This module tests the "Master Chess Simulator" - the decision-making logic and orchestration
of the event handler without any external dependencies. All external modules are mocked to
test pure logic and conversation flow.

Key Testing Philosophy:
- Mock everything external (database, APIs)
- Test conversation flows and decision logic
- Verify correct function calls in correct order
- Assert proper data passing between modules
- Test all user interaction scenarios
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import pytest
from datetime import datetime, timedelta

# Import the module under test
from app.core.event_handler import handle_event, EventHandler

class TestEventHandlerOnboarding(unittest.TestCase):
    """Tests for new user onboarding flow"""
    
    def setUp(self):
        """Set up common test data"""
        self.messenger_id = "test_user_123"
        self.sample_token = "canvas_token_abc123"
        
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    @patch('app.core.event_handler.canvas_api')
    def test_new_user_first_contact(self, mock_canvas, mock_messenger, mock_queries):
        """Test: New user sends first message - should get consent request"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = None  # New user
        
        event = {
            "sender": {"id": self.messenger_id},
            "message": {"text": "Hi"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_queries.get_user_by_messenger_id.assert_called_once_with(self.messenger_id)
        mock_messenger.send_button_template.assert_called_once()
        
        # Verify the consent buttons were sent
        call_args = mock_messenger.send_button_template.call_args[1]
        self.assertIn("✅ I Agree, Let's Go!", str(call_args))
        self.assertIn("📜 Privacy Policy", str(call_args))
        self.assertIn("⚖ Terms of Use", str(call_args))
        
        # Verify no Canvas API calls were made yet
        mock_canvas.validate_token.assert_not_called()
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    @patch('app.core.event_handler.canvas_api')
    def test_user_consent_agreement(self, mock_canvas, mock_messenger, mock_queries):
        """Test: User agrees to terms - should get token request"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = None
        
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "CONSENT_AGREED"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_messenger.send_quick_reply.assert_called_once()
        
        # Verify token request message with options
        call_args = mock_messenger.send_quick_reply.call_args[1]
        self.assertIn("Canvas Access Token", str(call_args))
        self.assertIn("Show me how", str(call_args))
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    @patch('app.core.event_handler.canvas_api')
    def test_valid_token_submission_success(self, mock_canvas, mock_messenger, mock_queries):
        """Test: User submits valid token - should trigger initial sync"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = None
        mock_canvas.validate_token.return_value = {"id": 12345, "name": "John Doe"}
        mock_canvas.get_assignments.return_value = [
            {"title": "Math Homework", "due_at": "2025-08-28T23:59:00Z"},
            {"title": "History Essay", "due_at": "2025-08-30T23:59:00Z"}
        ]
        mock_canvas.get_courses.return_value = [
            {"id": 101, "name": "Mathematics 101"},
            {"id": 102, "name": "History 201"}
        ]
        
        event = {
            "sender": {"id": self.messenger_id},
            "message": {"text": self.sample_token}
        }
        
        # Act
        handle_event(event)
        
        # Assert - Verify the complete onboarding sequence
        mock_canvas.validate_token.assert_called_once_with(self.sample_token)
        mock_queries.create_user.assert_called_once_with(
            messenger_id=self.messenger_id,
            canvas_token=self.sample_token,
            canvas_user_id=12345
        )
        
        # Verify initial sync was triggered
        mock_canvas.get_assignments.assert_called_once_with(self.sample_token, 12345)
        mock_canvas.get_courses.assert_called_once_with(self.sample_token, 12345)
        mock_queries.bulk_insert_tasks.assert_called_once()
        mock_queries.bulk_insert_courses.assert_called_once()
        
        # Verify success message with assignments preview
        mock_messenger.send_text.assert_called()
        success_message = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("Welcome to Easely, John!", success_message)
        self.assertIn("Math Homework", success_message)
        self.assertIn("History Essay", success_message)
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    @patch('app.core.event_handler.canvas_api')
    def test_invalid_token_submission(self, mock_canvas, mock_messenger, mock_queries):
        """Test: User submits invalid token - should get error message"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = None
        mock_canvas.validate_token.side_effect = Exception("Invalid token")
        
        event = {
            "sender": {"id": self.messenger_id},
            "message": {"text": "invalid_token_123"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_canvas.validate_token.assert_called_once_with("invalid_token_123")
        mock_messenger.send_text.assert_called()
        
        error_message = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("invalid", error_message.lower())
        self.assertIn("tutorial", error_message.lower())
        
        # Verify no user was created
        mock_queries.create_user.assert_not_called()


class TestEventHandlerReturningUser(unittest.TestCase):
    """Tests for returning user interactions"""
    
    def setUp(self):
        """Set up common test data for returning users"""
        self.messenger_id = "returning_user_456"
        self.mock_user = {
            "id": 1,
            "messenger_id": self.messenger_id,
            "canvas_token": "valid_token_456",
            "canvas_user_id": 67890,
            "subscription_tier": "free",
            "subscription_expiry_date": datetime.utcnow() + timedelta(days=10)
        }
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_returning_user_greeting_shows_menu(self, mock_messenger, mock_queries):
        """Test: Returning user says 'Hi' - should get task management menu"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user
        
        event = {
            "sender": {"id": self.messenger_id},
            "message": {"text": "Hi"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_messenger.send_quick_reply.assert_called_once()
        
        # Verify menu options are present
        call_args = mock_messenger.send_quick_reply.call_args[1]
        menu_text = str(call_args)
        self.assertIn("🔥 Due Today", menu_text)
        self.assertIn("⏰ Due This Week", menu_text)
        self.assertIn("❗ Show Overdue", menu_text)
        self.assertIn("🗓 View All Upcoming", menu_text)
        self.assertIn("＋ Add New Task", menu_text)
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_due_today_filter_with_tasks(self, mock_messenger, mock_queries):
        """Test: User requests 'Due Today' - should show today's tasks"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user
        mock_queries.get_tasks_due_in_next_24_hours.return_value = [
            {
                "title": "Submit Lab Report",
                "due_date": datetime.utcnow() + timedelta(hours=6),
                "course_name": "Chemistry 101"
            },
            {
                "title": "Math Quiz",
                "due_date": datetime.utcnow() + timedelta(hours=12),
                "course_name": "Mathematics 101"
            }
        ]
        
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "GET_TASKS_TODAY"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_queries.get_tasks_due_in_next_24_hours.assert_called_once_with(1)  # user_id
        mock_messenger.send_text.assert_called()
        
        response_text = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("Due Today", response_text)
        self.assertIn("Submit Lab Report", response_text)
        self.assertIn("Math Quiz", response_text)
        self.assertIn("Chemistry 101", response_text)
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_due_today_filter_no_tasks(self, mock_messenger, mock_queries):
        """Test: User requests 'Due Today' with no tasks - should show encouraging message"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user
        mock_queries.get_tasks_due_in_next_24_hours.return_value = []
        
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "GET_TASKS_TODAY"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_queries.get_tasks_due_in_next_24_hours.assert_called_once_with(1)
        mock_messenger.send_text.assert_called()
        
        response_text = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("Nothing due today", response_text.lower())
        self.assertIn("great job", response_text.lower())
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_overdue_tasks_filter(self, mock_messenger, mock_queries):
        """Test: User requests overdue tasks - should show past due items"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user
        mock_queries.get_overdue_tasks.return_value = [
            {
                "title": "Late Assignment",
                "due_date": datetime.utcnow() - timedelta(days=2),
                "course_name": "English 101"
            }
        ]
        
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "GET_OVERDUE_TASKS"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_queries.get_overdue_tasks.assert_called_once_with(1)
        mock_messenger.send_text.assert_called()
        
        response_text = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("Overdue", response_text)
        self.assertIn("Late Assignment", response_text)


class TestEventHandlerTaskManagement(unittest.TestCase):
    """Tests for manual task creation flow"""
    
    def setUp(self):
        """Set up test data for task management"""
        self.messenger_id = "task_user_789"
        self.mock_user_free = {
            "id": 2,
            "messenger_id": self.messenger_id,
            "canvas_token": "token_789",
            "canvas_user_id": 11111,
            "subscription_tier": "free",
            "subscription_expiry_date": datetime.utcnow() + timedelta(days=5)
        }
        self.mock_user_premium = {
            **self.mock_user_free,
            "subscription_tier": "premium"
        }
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_add_task_initiation_free_user_under_limit(self, mock_messenger, mock_queries):
        """Test: Free user wants to add task (under monthly limit)"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user_free
        mock_queries.get_user_monthly_task_count.return_value = 3  # Under 5 limit
        
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "ADD_NEW_TASK"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_queries.get_user_monthly_task_count.assert_called_once_with(2)
        mock_messenger.send_text.assert_called()
        
        response_text = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("What's the task", response_text)
        # Should not mention upgrade since under limit
        self.assertNotIn("upgrade", response_text.lower())
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_add_task_initiation_free_user_at_limit(self, mock_messenger, mock_queries):
        """Test: Free user at monthly limit - should suggest upgrade"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user_free
        mock_queries.get_user_monthly_task_count.return_value = 5  # At limit
        
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "ADD_NEW_TASK"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_messenger.send_button_template.assert_called()
        
        call_args = mock_messenger.send_button_template.call_args[1]
        message_text = str(call_args)
        self.assertIn("monthly limit", message_text.lower())
        self.assertIn("upgrade", message_text.lower())
        self.assertIn("premium", message_text.lower())
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_add_task_initiation_premium_user(self, mock_messenger, mock_queries):
        """Test: Premium user adds task - no limit checking"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user_premium
        
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "ADD_NEW_TASK"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        # Should NOT check monthly limit for premium users
        mock_queries.get_user_monthly_task_count.assert_not_called()
        mock_messenger.send_text.assert_called()
        
        response_text = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("What's the task", response_text)


class TestEventHandlerTaskCreationFlow(unittest.TestCase):
    """Tests for the complete task creation conversation flow"""
    
    def setUp(self):
        """Set up test data for task creation flow"""
        self.messenger_id = "flow_user_999"
        self.mock_user = {
            "id": 3,
            "messenger_id": self.messenger_id,
            "canvas_token": "token_999",
            "canvas_user_id": 22222,
            "subscription_tier": "premium"
        }
        self.mock_courses = [
            {"id": 201, "name": "Advanced Physics"},
            {"id": 202, "name": "Computer Science 101"}
        ]
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    @patch('app.core.event_handler.canvas_api')
    def test_complete_task_creation_flow(self, mock_canvas, mock_messenger, mock_queries):
        """Test: Complete flow from task title to Canvas creation"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user
        mock_queries.get_user_courses.return_value = self.mock_courses
        mock_canvas.create_calendar_event.return_value = {"id": 98765}
        
        # Simulate the conversation flow
        task_title = "Complete Final Project"
        
        # Step 1: User provides task title
        event1 = {
            "sender": {"id": self.messenger_id},
            "message": {"text": task_title}
        }
        
        # Mock the conversation state tracking (in real app, this would be stored)
        with patch('app.core.event_handler.get_conversation_state') as mock_state:
            mock_state.return_value = {"awaiting": "task_title"}
            
            # Act
            handle_event(event1)
            
            # Assert Step 1: Should ask for date/time
            mock_messenger.send_quick_reply.assert_called()
            call_args = mock_messenger.send_quick_reply.call_args[1]
            self.assertIn("Today", str(call_args))
            self.assertIn("Tomorrow", str(call_args))
            self.assertIn("Choose Date", str(call_args))
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    @patch('app.core.event_handler.canvas_api')
    def test_task_creation_with_course_selection(self, mock_canvas, mock_messenger, mock_queries):
        """Test: Task creation with course assignment"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.mock_user
        mock_queries.get_user_courses.return_value = self.mock_courses
        mock_canvas.create_calendar_event.return_value = {"id": 98765}
        mock_queries.create_manual_task.return_value = True
        
        # Simulate user choosing a course
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "SELECT_COURSE_201"}
        }
        
        with patch('app.core.event_handler.get_conversation_state') as mock_state:
            mock_state.return_value = {
                "awaiting": "course_selection",
                "task_data": {
                    "title": "Study for Midterm",
                    "due_date": "2025-08-30T14:00:00Z"
                }
            }
            
            # Act
            handle_event(event)
            
            # Assert
            mock_canvas.create_calendar_event.assert_called_once()
            call_args = mock_canvas.create_calendar_event.call_args[1]
            
            # Verify correct data passed to Canvas API
            self.assertEqual(call_args['title'], "Study for Midterm")
            self.assertEqual(call_args['course_id'], 201)
            self.assertIn("2025-08-30T14:00:00Z", call_args['start_at'])
            
            # Verify task stored in database
            mock_queries.create_manual_task.assert_called_once()
            
            # Verify success message sent
            mock_messenger.send_text.assert_called()
            success_text = mock_messenger.send_text.call_args[1]['text']
            self.assertIn("created", success_text.lower())
            self.assertIn("Study for Midterm", success_text)


class TestEventHandlerErrorHandling(unittest.TestCase):
    """Tests for error handling scenarios"""
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    @patch('app.core.event_handler.canvas_api')
    def test_database_error_handling(self, mock_canvas, mock_messenger, mock_queries):
        """Test: Database connection error - should send user-friendly error"""
        # Arrange
        mock_queries.get_user_by_messenger_id.side_effect = Exception("Database connection failed")
        
        event = {
            "sender": {"id": "error_user_123"},
            "message": {"text": "Hi"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_messenger.send_text.assert_called()
        error_message = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("temporarily unavailable", error_message.lower())
        self.assertNotIn("Database connection failed", error_message)  # No technical details
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    @patch('app.core.event_handler.canvas_api')
    def test_canvas_api_error_during_sync(self, mock_canvas, mock_messenger, mock_queries):
        """Test: Canvas API fails during sync - should inform user appropriately"""
        # Arrange
        mock_user = {
            "id": 4,
            "messenger_id": "sync_error_user",
            "canvas_token": "failing_token",
            "canvas_user_id": 33333
        }
        mock_queries.get_user_by_messenger_id.return_value = mock_user
        mock_canvas.get_assignments.side_effect = Exception("Canvas API rate limit exceeded")
        
        event = {
            "sender": {"id": "sync_error_user"},
            "postback": {"payload": "GET_TASKS_TODAY"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_messenger.send_text.assert_called()
        error_message = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("trouble connecting", error_message.lower())
        self.assertIn("canvas", error_message.lower())


class TestEventHandlerSubscriptionLogic(unittest.TestCase):
    """Tests for subscription tier logic and premium features"""
    
    def setUp(self):
        """Set up subscription test data"""
        self.messenger_id = "subscription_user_555"
        self.expired_user = {
            "id": 5,
            "messenger_id": self.messenger_id,
            "subscription_tier": "premium",
            "subscription_expiry_date": datetime.utcnow() - timedelta(days=1)  # Expired
        }
        self.active_premium_user = {
            "id": 5,
            "messenger_id": self.messenger_id,
            "subscription_tier": "premium",
            "subscription_expiry_date": datetime.utcnow() + timedelta(days=15)  # Active
        }
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_expired_premium_user_gets_downgraded(self, mock_messenger, mock_queries):
        """Test: Expired premium user should be treated as free tier"""
        # Arrange
        mock_queries.get_user_by_messenger_id.return_value = self.expired_user
        
        event = {
            "sender": {"id": self.messenger_id},
            "postback": {"payload": "ADD_NEW_TASK"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        # Should check monthly limit even though user has 'premium' tier (because expired)
        mock_queries.get_user_monthly_task_count.assert_called_once()
        
        # Should update user tier to 'free' in database
        mock_queries.update_user_subscription_tier.assert_called_once_with(5, "free")
    
    @patch('app.core.event_handler.queries')
    @patch('app.core.event_handler.messenger_api')
    def test_premium_activation_flow(self, mock_messenger, mock_queries):
        """Test: User activates premium with 'ACTIVATE' command"""
        # Arrange
        free_user = {
            "id": 6,
            "messenger_id": self.messenger_id,
            "subscription_tier": "free"
        }
        mock_queries.get_user_by_messenger_id.return_value = free_user
        
        event = {
            "sender": {"id": self.messenger_id},
            "message": {"text": "ACTIVATE"}
        }
        
        # Act
        handle_event(event)
        
        # Assert
        mock_queries.update_user_subscription_tier.assert_called_once_with(
            6, "premium", unittest.mock.ANY  # Any expiry date
        )
        mock_messenger.send_text.assert_called()
        
        activation_message = mock_messenger.send_text.call_args[1]['text']
        self.assertIn("Premium activated", activation_message)
        self.assertIn("unlimited", activation_message.lower())


if __name__ == '__main__':
    # Run with pytest for better output
    pytest.main([__file__, "-v"])