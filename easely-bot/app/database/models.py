"""
Database Models for Easely

This module contains the "Blueprints for the Filing Cabinets" - it defines
the structure of Easely's PostgreSQL database using SQLAlchemy ORM.

The models define three core entities:
- Users: Student accounts with Canvas integration
- Tasks: Assignments and events (both Canvas and manual)
- Courses: Canvas course information for optimization

These models serve as the single source of truth for the database schema
and are used by Alembic for database migrations.
"""

import enum
from datetime import datetime, timezone
from typing import List, Optional

from sqlalchemy import (
    Column, Integer, String, DateTime, Text, Boolean, 
    ForeignKey, Enum, Index, UniqueConstraint
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

# Create the declarative base class
Base = declarative_base()


class SubscriptionTier(enum.Enum):
    """Enumeration for user subscription levels"""
    FREE = "free"
    PREMIUM = "premium"


class TaskSource(enum.Enum):
    """Enumeration for task origin types"""
    CANVAS_ASSIGNMENT = "canvas_assignment"
    CANVAS_EVENT = "canvas_event"
    MANUAL_ENTRY = "manual_entry"


class User(Base):
    """
    User model representing a student with Canvas integration.
    
    This is the central entity that connects to Facebook Messenger
    and Canvas LMS. Each user has a unique messenger_id for chat
    interactions and stores encrypted Canvas credentials.
    """
    __tablename__ = 'users'

    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Facebook Messenger integration
    messenger_id = Column(String(50), unique=True, nullable=False, index=True)
    
    # Canvas LMS integration
    canvas_token = Column(Text, nullable=True)  # Encrypted Canvas access token
    canvas_user_id = Column(String(20), nullable=True, index=True)
    canvas_base_url = Column(String(255), nullable=True)  # e.g., "https://canvas.school.edu"
    
    # Subscription management
    subscription_tier = Column(
        Enum(SubscriptionTier), 
        default=SubscriptionTier.FREE, 
        nullable=False,
        index=True
    )
    subscription_expiry_date = Column(DateTime(timezone=True), nullable=True)
    
    # User preferences and settings
    timezone = Column(String(50), default='UTC', nullable=False)
    reminder_enabled = Column(Boolean, default=True, nullable=False)
    weekly_digest_enabled = Column(Boolean, default=True, nullable=False)
    
    # Account status tracking
    is_active = Column(Boolean, default=True, nullable=False)
    token_invalid = Column(Boolean, default=False, nullable=False)  # Track revoked tokens
    
    # Monthly limits for free tier
    manual_tasks_this_month = Column(Integer, default=0, nullable=False)
    month_reset_date = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    last_sync_at = Column(DateTime(timezone=True), nullable=True)  # Last Canvas sync
    last_active_at = Column(DateTime(timezone=True), nullable=True)  # Last chat interaction
    
    # Relationships
    tasks = relationship(
        "Task", 
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy="dynamic"  # Enable efficient querying
    )
    
    courses = relationship(
        "Course", 
        back_populates="user", 
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    def __repr__(self) -> str:
        return f"<User(id={self.id}, messenger_id='{self.messenger_id}', tier={self.subscription_tier.value})>"
    
    @property
    def is_premium(self) -> bool:
        """Check if user has active premium subscription"""
        if self.subscription_tier != SubscriptionTier.PREMIUM:
            return False
        if not self.subscription_expiry_date:
            return False
        return datetime.now(timezone.utc) < self.subscription_expiry_date
    
    @property
    def can_add_manual_task(self) -> bool:
        """Check if user can add another manual task this month"""
        if self.is_premium:
            return True
        return self.manual_tasks_this_month < 5


class Course(Base):
    """
    Course model for Canvas course information.
    
    This model optimizes the manual task creation flow by storing
    course names locally, avoiding repeated Canvas API calls.
    """
    __tablename__ = 'courses'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Canvas course information
    canvas_course_id = Column(String(20), nullable=False, index=True)
    course_name = Column(String(255), nullable=False)
    course_code = Column(String(50), nullable=True)  # e.g., "CS101"
    
    # Course status
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="courses")
    tasks = relationship(
        "Task", 
        back_populates="course", 
        cascade="all, delete-orphan",
        lazy="dynamic"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'canvas_course_id', name='uq_user_canvas_course'),
        Index('idx_course_user_active', 'user_id', 'is_active'),
    )
    
    def __repr__(self) -> str:
        return f"<Course(id={self.id}, name='{self.course_name}', canvas_id='{self.canvas_course_id}')>"


class Task(Base):
    """
    Task model for assignments and events.
    
    This is the central operational table storing both Canvas assignments
    and manually created tasks. It supports Easely's core functionality
    of tracking and reminding users about their academic obligations.
    """
    __tablename__ = 'tasks'
    
    # Primary key
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Foreign key to user
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False, index=True)
    
    # Optional foreign key to course (null for personal tasks)
    course_id = Column(Integer, ForeignKey('courses.id'), nullable=True, index=True)
    
    # Canvas integration IDs (mutually exclusive based on source)
    canvas_assignment_id = Column(String(20), nullable=True, index=True)
    canvas_event_id = Column(String(20), nullable=True, index=True)
    
    # Task information
    title = Column(String(500), nullable=False)
    description = Column(Text, nullable=True)
    
    # Timing information (stored in UTC)
    due_date = Column(DateTime(timezone=True), nullable=False, index=True)
    
    # Task metadata
    source = Column(
        Enum(TaskSource), 
        nullable=False, 
        index=True,
        default=TaskSource.MANUAL_ENTRY
    )
    
    # Task status tracking
    is_completed = Column(Boolean, default=False, nullable=False)
    is_deleted = Column(Boolean, default=False, nullable=False)  # Soft delete
    
    # Reminder tracking for premium users
    reminder_1_week_sent = Column(Boolean, default=False, nullable=False)
    reminder_3_days_sent = Column(Boolean, default=False, nullable=False)
    reminder_1_day_sent = Column(Boolean, default=False, nullable=False)
    reminder_8_hours_sent = Column(Boolean, default=False, nullable=False)
    reminder_2_hours_sent = Column(Boolean, default=False, nullable=False)
    reminder_1_hour_sent = Column(Boolean, default=False, nullable=False)
    
    # Canvas-specific fields
    assignment_type = Column(String(50), nullable=True)  # e.g., "assignment", "quiz", "discussion"
    points_possible = Column(Integer, nullable=True)
    submission_types = Column(String(255), nullable=True)  # JSON string of allowed types
    
    # Audit fields
    created_at = Column(DateTime(timezone=True), default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=func.now(), onupdate=func.now(), nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="tasks")
    course = relationship("Course", back_populates="tasks")
    
    # Indexes for efficient querying
    __table_args__ = (
        # Composite indexes for common query patterns
        Index('idx_task_user_due_date', 'user_id', 'due_date'),
        Index('idx_task_user_source', 'user_id', 'source'),
        Index('idx_task_user_active', 'user_id', 'is_deleted', 'is_completed'),
        Index('idx_task_due_date_active', 'due_date', 'is_deleted'),
        
        # Unique constraints for Canvas items
        UniqueConstraint('user_id', 'canvas_assignment_id', name='uq_user_canvas_assignment'),
        UniqueConstraint('user_id', 'canvas_event_id', name='uq_user_canvas_event'),
    )
    
    def __repr__(self) -> str:
        return f"<Task(id={self.id}, title='{self.title[:30]}...', due='{self.due_date}', source={self.source.value})>"
    
    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        return datetime.now(timezone.utc) > self.due_date and not self.is_completed
    
    @property
    def canvas_id(self) -> Optional[str]:
        """Get the relevant Canvas ID based on source"""
        if self.source == TaskSource.CANVAS_ASSIGNMENT:
            return self.canvas_assignment_id
        elif self.source == TaskSource.CANVAS_EVENT:
            return self.canvas_event_id
        return None
    
    @property
    def is_canvas_task(self) -> bool:
        """Check if task originates from Canvas"""
        return self.source in [TaskSource.CANVAS_ASSIGNMENT, TaskSource.CANVAS_EVENT]
    
    def get_reminder_status(self) -> dict:
        """Get the status of all reminders for this task"""
        return {
            '1_week': self.reminder_1_week_sent,
            '3_days': self.reminder_3_days_sent,
            '1_day': self.reminder_1_day_sent,
            '8_hours': self.reminder_8_hours_sent,
            '2_hours': self.reminder_2_hours_sent,
            '1_hour': self.reminder_1_hour_sent,
        }
    
    def mark_reminder_sent(self, reminder_type: str) -> None:
        """Mark a specific reminder as sent"""
        reminder_mapping = {
            '1_week': 'reminder_1_week_sent',
            '3_days': 'reminder_3_days_sent',
            '1_day': 'reminder_1_day_sent',
            '8_hours': 'reminder_8_hours_sent',
            '2_hours': 'reminder_2_hours_sent',
            '1_hour': 'reminder_1_hour_sent',
        }
        
        if reminder_type in reminder_mapping:
            setattr(self, reminder_mapping[reminder_type], True)


# Optional: Create all tables (useful for testing)
def create_all_tables(engine):
    """
    Create all tables in the database.
    
    Note: In production, use Alembic migrations instead.
    """
    Base.metadata.create_all(bind=engine)


def drop_all_tables(engine):
    """
    Drop all tables from the database.
    
    Warning: This will permanently delete all data!
    """
    Base.metadata.drop_all(bind=engine)