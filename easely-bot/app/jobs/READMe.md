# Easely: Complete Development Guide

*A Comprehensive Technical Documentation for the Canvas Assistant*

---

## Table of Contents

1. [Project Overview](#project-overview)
2. [Architecture & Philosophy](#architecture--philosophy)
3. [Project Structure](#project-structure)
4. [Core Features & User Journey](#core-features--user-journey)
5. [Database Design](#database-design)
6. [Background Jobs System](#background-jobs-system)
7. [API Integration](#api-integration)
8. [Monetization System](#monetization-system)
9. [Deployment Architecture](#deployment-architecture)
10. [Implementation Details](#implementation-details)
11. [Development Roadmap](#development-roadmap)

---

## Project Overview

### The Vision
Easely is a smart, conversational assistant operating entirely within Facebook Messenger, designed to transform the static, overwhelming nature of the Canvas Learning Management System (LMS) into a dynamic, proactive, and manageable experience.

### Core Philosophy
- **Reduce Cognitive Load**: Offload the mental burden of tracking academic tasks
- **Single Source of Truth**: Unified calendar visible in both Messenger and Canvas
- **Two-Way Synchronization**: Not just notifications, but active task management

### The Name
"Easely" = "Easel" (support for academic work) + "Easily" (simplifying student life)

---

## Architecture & Philosophy

### Design Principles

1. **Asynchronous Processing**: Background jobs handle heavy lifting separately from user interactions
2. **Mirror Principle**: Local database mirrors Canvas data for speed and reliability
3. **Tiered Value Delivery**: Free tier provides genuine value, premium feels indispensable
4. **Proactive Intelligence**: System works silently in the background, not just on-demand

### Technical Stack

- **Backend**: Python with Flask/FastAPI
- **Database**: PostgreSQL (managed on Render)
- **Hosting**: Render (Web Service + Cron Jobs)
- **Integrations**: Facebook Messenger API, Canvas LMS API
- **Payment**: Ko-fi Memberships (GCash via Stripe)

---

## Project Structure

```
easely/
├── app/
│   ├── __init__.py                 # Main app package exports
│   ├── database/
│   │   ├── __init__.py            # Database package exports
│   │   ├── session.py             # PostgreSQL connection management
│   │   ├── models.py              # SQLAlchemy models (User, Task, Course)
│   │   └── queries.py             # Database query functions
│   ├── api/
│   │   ├── __init__.py            # API package exports
│   │   ├── messenger_api.py       # Facebook Messenger integration
│   │   └── canvas_api.py          # Canvas LMS integration
│   ├── handlers/
│   │   ├── __init__.py            # Handlers package exports
│   │   ├── message_handler.py     # Text message processing
│   │   ├── postback_handler.py    # Button click handling
│   │   ├── quick_reply_handler.py # Quick reply processing
│   │   ├── onboarding_handler.py  # New user onboarding
│   │   └── task_handler.py        # Task management flows
│   ├── utils/
│   │   ├── __init__.py            # Utils package exports
│   │   ├── validators.py          # Input validation
│   │   ├── formatters.py          # Message formatting
│   │   ├── date_helpers.py        # Date/time utilities
│   │   └── encryption.py          # Token encryption
│   └── jobs/
│       ├── __init__.py            # Jobs package with shared utilities
│       ├── send_reminders.py      # Hourly reminder service
│       ├── check_expiries.py      # Daily subscription management
│       └── refresh_data.py        # Periodic Canvas sync
├── config/
│   ├── __init__.py               # Config package exports
│   └── settings.py               # Environment configuration
├── main.py                       # Flask/FastAPI application entry
├── requirements.txt              # Python dependencies
└── render.yaml                   # Render deployment configuration
```

---

## Core Features & User Journey

### Onboarding Experience (First 5 Minutes)

1. **First Contact**
   - User initiates conversation
   - Bot introduces itself with clear value proposition
   - Consent request with tappable buttons: ✅ I Agree, 📜 Privacy Policy, ⚖ Terms of Use

2. **Guided Token Request**
   - "Do you have your Canvas Access Token ready?"
   - Technical users: Direct input
   - Others: "Show me how" tutorial link

3. **Tutorial Requirement**
   - Clear, concise video tutorial
   - Emphasizes necessary API permissions for two-way sync

4. **Verification & Magic Moment**
   - User pastes token
   - Backend validates against Canvas API
   - **Success**: Immediate sync + display of user's actual assignments
   - This reflection of personal data builds instant trust

5. **Contextual Upsell**
   - After delivering initial value
   - Introduce premium tier as natural extension

### Daily Interaction: Returning Users

#### On-Demand Task Management Menu

When user says "Hi" or "Menu":

**"Welcome back to Easely! What would you like to see?"**

Quick Reply Options:
- 🔥 **Due Today**: Tasks due in next 24 hours
- ⏰ **Due This Week**: Tasks due in next 7 days  
- ❗ **Show Overdue**: Past due tasks
- 🗓 **View All Upcoming**: All future tasks (paginated)
- ➕ **Add New Task**: Start manual task creation

---

## Database Design

### PostgreSQL Schema

#### Users Table
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    messenger_id VARCHAR(50) UNIQUE NOT NULL,
    canvas_token TEXT ENCRYPTED,
    canvas_user_id VARCHAR(50),
    subscription_tier VARCHAR(20) DEFAULT 'free', -- 'free' or 'premium'
    subscription_expiry_date TIMESTAMP,
    token_valid BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Tasks Table (Central Operational Table)
```sql
CREATE TABLE tasks (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    canvas_assignment_id VARCHAR(50), -- NULL for manual entries
    canvas_event_id VARCHAR(50),      -- For manual entries synced to Canvas
    title VARCHAR(255) NOT NULL,
    due_date TIMESTAMP WITH TIME ZONE,
    course_id VARCHAR(50),
    source VARCHAR(20) NOT NULL,      -- 'canvas_sync' or 'manual_entry'
    last_reminder_sent TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);
```

#### Courses Table (Optimization Table)
```sql
CREATE TABLE courses (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    canvas_course_id VARCHAR(50) NOT NULL,
    course_name VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(user_id, canvas_course_id)
);
```

### Data Flow Patterns

1. **Initial Sync**: Heavy lifting during onboarding, populates all tables
2. **Manual Task Creation**: API call to Canvas → store returned event_id
3. **Reminder Processing**: Fast local queries, zero Canvas API calls
4. **Data Refresh**: Periodic sync to maintain mirror accuracy

---

## Background Jobs System

### The "Automated Workforce"

Three independent scripts running on Render Cron Jobs:

#### 1. send_reminders.py - "The Town Crier"
- **Schedule**: Every hour (`0 * * * *`)
- **Purpose**: Send proactive assignment reminders
- **Logic**: 
  - Query tasks due within reminder windows
  - Apply subscription-tier specific reminder cascade
  - Send personalized messages via Messenger API
  - Update reminder timestamps to prevent duplicates

**Free Tier Reminders**:
- 24 hours before due date

**Premium Tier Reminders**:
- 1 week, 3 days, 24 hours, 8 hours, 2 hours, 1 hour before due date

#### 2. check_expiries.py - "The Subscription Manager"  
- **Schedule**: Daily at midnight (`0 0 * * *`)
- **Purpose**: Manage subscription expiration
- **Logic**:
  - Find users with expired premium subscriptions
  - Revert to free tier (update subscription_tier, clear expiry_date)
  - Send polite expiration notification
  - Log activity for audit trail

#### 3. refresh_data.py - "The Data Auditor"
- **Schedule**: Every 4 hours (`0 */4 * * *`)  
- **Purpose**: Keep local database synchronized with Canvas
- **Logic**:
  - For each active user: fetch fresh assignments from Canvas
  - Compare with local database
  - **Create**: New assignments not in local DB
  - **Update**: Changed due dates or details
  - **Delete**: Assignments removed from Canvas
  - Handle revoked tokens gracefully
  - Rate limiting protection (2-second delays between users)

### Job Architecture Features

- **Independent Execution**: Each job is a complete Python script
- **Shared Utilities**: Common logging, error handling, statistics
- **Robust Error Handling**: Individual failures don't stop entire job
- **Comprehensive Logging**: Detailed execution statistics and timing
- **Rate Limit Respect**: Staggered API calls to avoid throttling

---

## API Integration

### Canvas LMS API Integration

#### Required Endpoints:
- `GET /api/v1/courses` - Fetch user's courses
- `GET /api/v1/assignments` - Fetch assignments
- `POST /api/v1/calendar_events` - Create manual tasks (two-way sync)
- Token validation and error handling

#### Key Features:
- **Token Validation**: Detect and handle revoked tokens
- **Rate Limiting**: Respect Canvas API limits
- **Error Handling**: Distinguish between token issues and API problems
- **Data Transformation**: Convert Canvas format to internal models

### Facebook Messenger API Integration

#### Core Functions:
- `send_text_message()` - Basic text responses
- `send_quick_replies()` - Menu-style interactions
- `send_buttons()` - Structured button templates
- `handle_webhook()` - Process incoming messages
- `send_typing_indicator()` - UX improvement

#### Message Types:
- **Text Messages**: Basic responses and reminders
- **Quick Replies**: Menu navigation and filtering
- **Button Templates**: Onboarding consent, upgrade flows
- **Generic Templates**: Rich assignment displays

---

## Monetization System

### Two-Tier Model

#### Easely (Free Tier) - "The Hook"
- ✅ Full Canvas synchronization
- ✅ 24-hour reminder notifications  
- ✅ 5 manual tasks per month (two-way sync)
- ✅ On-demand task filtering (Due Today, This Week, Overdue, All)
- ✅ Basic task management

#### Easely Premium - "The Proactive Partner"
- ✅ Complete reminder cascade (6 reminder points)
- ✅ Unlimited manual tasks with two-way sync
- ✅ AI-powered assignment outline generation
- ✅ Personalized weekly digest (Monday briefings)
- ✅ Calendar export to Excel
- ✅ Priority support

### Payment System

**Model**: 30-day "Access Pass" (manual renewal)
- **Platform**: Ko-fi Memberships
- **Payment Methods**: GCash via Stripe (no business registration required)
- **Process**: 
  1. User initiates upgrade in chat
  2. Redirects to Ko-fi guest checkout (Messenger WebView)
  3. Returns to chat, types "ACTIVATE" for instant access
  4. Developer receives email notification from Ko-fi
  5. Periodic audit to cross-reference payments with activations

---

## Deployment Architecture

### Render Platform Services

1. **PostgreSQL Database**
   - Managed database service
   - Automatic backups and scaling
   - Internal connection URL for security

2. **Web Service** 
   - Main Python application
   - Handles Messenger webhooks
   - Real-time user interactions
   - Environment variables for secrets

3. **Cron Jobs** (3 separate services)
   - `send_reminders`: Hourly execution
   - `check_expiries`: Daily execution  
   - `refresh_data`: Every 4 hours
   - Shared environment variables
   - Independent scaling and monitoring

### Environment Variables
```
DATABASE_URL=postgresql://...
MESSENGER_ACCESS_TOKEN=your_token
MESSENGER_VERIFY_TOKEN=your_verify_token  
CANVAS_API_BASE_URL=https://your-institution.instructure.com
ENCRYPTION_KEY=your_encryption_key
KO_FI_WEBHOOK_SECRET=your_kofi_secret
```

---

## Implementation Details

### Critical Technical Considerations

#### 1. Canvas Token Management
- **Challenge**: Users can revoke tokens anytime
- **Solution**: Robust error handling with automatic token invalidation
- **Implementation**: Try-catch around all Canvas API calls, flag invalid tokens

#### 2. API Rate Limiting
- **Challenge**: Canvas enforces request limits
- **Solution**: Staggered refresh job with batched processing
- **Implementation**: Process users in small batches with delays

#### 3. Date/Time Input Handling
- **Challenge**: Natural language parsing is error-prone
- **Solution**: Structured conversational flow with Quick Replies
- **Implementation**: 
  ```
  "What day?" → [Today] [Tomorrow] [Next Week] [Choose Date]
  "What time?" → [9:00 AM] [12:00 PM] [5:00 PM] [Custom Time]
  ```

#### 4. Duplicate Reminder Prevention
- **Challenge**: Hourly job could send same reminder multiple times
- **Solution**: Track last reminder timestamps per reminder type
- **Implementation**: Database fields for each reminder window

#### 5. Data Consistency
- **Challenge**: Local mirror could become stale
- **Solution**: Regular refresh job with intelligent diff detection
- **Implementation**: Compare Canvas data with local, sync differences

### Security Measures

1. **Token Encryption**: Canvas tokens encrypted at rest
2. **Environment Variables**: All secrets in environment, never in code
3. **Input Validation**: All user inputs validated and sanitized  
4. **Error Handling**: No sensitive information in error messages
5. **API Security**: Webhook verification, rate limiting

---

## Development Roadmap

### Phase 1: Core Foundation (Weeks 1-4)
- [ ] Database setup and models
- [ ] Basic Messenger integration
- [ ] Canvas API integration
- [ ] User onboarding flow
- [ ] Token management system

### Phase 2: Task Management (Weeks 5-8)
- [ ] Canvas synchronization logic
- [ ] Manual task creation
- [ ] Two-way sync implementation
- [ ] On-demand task filtering
- [ ] Basic reminder system

### Phase 3: Background Jobs (Weeks 9-12)
- [ ] Reminder service implementation
- [ ] Subscription management
- [ ] Data refresh service  
- [ ] Job monitoring and logging
- [ ] Error handling and recovery

### Phase 4: Premium Features (Weeks 13-16)
- [ ] Advanced reminder cascade
- [ ] AI outline generation
- [ ] Weekly digest system
- [ ] Calendar export functionality
- [ ] Payment integration

### Phase 5: Polish & Launch (Weeks 17-20)
- [ ] Comprehensive testing
- [ ] Performance optimization
- [ ] User documentation
- [ ] Deployment automation
- [ ] Monitoring and analytics

---

## Key Success Metrics

### Technical Metrics
- **Uptime**: >99.5% availability
- **Response Time**: <2 seconds for user interactions
- **Job Success Rate**: >95% for background jobs
- **API Rate Limit Adherence**: Zero throttling incidents

### Business Metrics  
- **Onboarding Completion**: >60% complete token setup
- **Daily Active Users**: Track engagement
- **Premium Conversion**: Target 15-20% conversion rate
- **User Retention**: 7-day and 30-day retention rates

### User Experience Metrics
- **Magic Moment**: Time to first value delivery <5 minutes
- **Feature Usage**: Track most-used menu options
- **Support Tickets**: Minimize user confusion and errors
- **User Satisfaction**: Regular feedback collection

---

## Conclusion

Easely represents a comprehensive solution to student academic management, built on solid technical foundations with clear business objectives. The architecture prioritizes reliability, scalability, and user experience while maintaining the simplicity that makes it valuable.

The two-tier monetization model provides genuine free value while creating clear upgrade incentives. The background jobs system ensures proactive functionality without impacting real-time user experience.

Success depends on flawless onboarding, reliable reminder delivery, and seamless Canvas integration - all of which this architecture is designed to deliver.

---

*This document serves as the definitive technical specification for Easely development. It should be updated as the project evolves and new requirements emerge.*