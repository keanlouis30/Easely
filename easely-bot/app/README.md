# Easely Bot - Application Directory

## Overview

The `app/` directory contains the core application logic for Easely, a smart conversational assistant that operates within Facebook Messenger to help students manage their Canvas LMS assignments and academic tasks. This directory implements a modular, scalable architecture following Flask best practices.

## 🏗️ Architecture

```
app/
├── __init__.py          # Flask app factory and initialization
├── api/                 # External API integrations
├── core/                # Core business logic and event handling
├── database/            # Data models and database operations
├── features/            # Premium features and specialized tools
├── jobs/                # Background job processing
└── static/              # Static HTML files (privacy, terms)
```

## 📁 Directory Structure

### 1. **`__init__.py`** - Application Factory
- **Purpose**: Main Flask application initialization and configuration
- **Key Features**:
  - Application factory pattern for better testing and deployment
  - SQLAlchemy database integration
  - CORS support for cross-origin requests
  - Blueprint registration for all modules
  - Error handling and database session management
- **Usage**: Creates and configures the Flask app instance

### 2. **`api/`** - External Service Integrations
- **`canvas_api.py`**: Canvas LMS API integration for assignments and courses
- **`messenger_api.py`**: Facebook Messenger API for sending messages and templates
- **`payment_api.py`**: Payment processing and subscription management
- **Purpose**: Bridge between Easely and external services

#### Key Features:
- **Canvas Integration**: Fetch assignments, courses, and calendar events
- **Messenger Integration**: Rich message templates, buttons, and quick replies
- **Payment Processing**: Premium subscription management via Ko-fi

### 3. **`core/`** - Business Logic Engine
- **`event_handler.py`**: Main event processing and conversation flow
- **Purpose**: Orchestrates user interactions and routes to appropriate handlers

#### Responsibilities:
- Message processing and routing
- User state management
- Feature access control
- Conversation flow orchestration

### 4. **`database/`** - Data Layer
- **`models.py`**: SQLAlchemy ORM models (User, Task, Course, etc.)
- **`queries.py`**: Database query functions and operations
- **`session.py`**: Database connection management
- **Purpose**: Persistent data storage and retrieval

#### Models:
- **User**: User profiles, preferences, and subscription status
- **Task**: Academic tasks and assignments
- **Course**: Canvas course information
- **Calendar**: Event and deadline tracking

### 5. **`features/`** - Premium Functionality
- **`ai_tools.py`**: AI-powered assignment outline generation
- **`calendar_generator.py`**: Excel calendar file creation and cloud delivery
- **Purpose**: Advanced features for premium subscribers

#### Premium Features:
- **AI Assignment Outlines**: Generate structured assignment plans using OpenAI
- **Calendar Export**: Downloadable Excel files with all academic tasks
- **Cloud Storage**: Secure file delivery via AWS S3

### 6. **`jobs/`** - Background Processing
- **`send_reminders.py`**: Hourly reminder notifications
- **`check_expiries.py`**: Daily subscription expiration checks
- **`refresh_data.py`**: Periodic Canvas data synchronization
- **Purpose**: Automated background tasks and maintenance

#### Job Types:
- **Reminders**: Proactive task notifications
- **Maintenance**: Data cleanup and synchronization
- **Billing**: Subscription management and renewal

### 7. **`static/`** - Static Content
- **`privacy.html`**: Privacy policy page
- **`terms.html`**: Terms of service page
- **Purpose**: Legal and informational content

## 🚀 Getting Started

### Prerequisites
- Python 3.8+
- PostgreSQL database
- Facebook Developer Account
- Canvas LMS API access
- OpenAI API key (for AI features)
- AWS S3 credentials (for file storage)

### Installation
```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export FLASK_APP=app
export DATABASE_URL=postgresql://...
export FACEBOOK_ACCESS_TOKEN=...
export CANVAS_API_TOKEN=...
export OPENAI_API_KEY=...
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...

# Run the application
python -m app
```

### Configuration
The application uses a configuration system located in `config/settings.py`:
- Database connection settings
- API credentials and endpoints
- Feature flags and limits
- Environment-specific configurations

## 🔧 Development

### Project Structure Philosophy
- **Modular Design**: Each directory has a specific responsibility
- **Blueprint Pattern**: Flask blueprints for organized routing
- **Dependency Injection**: Clean separation of concerns
- **Error Handling**: Comprehensive error management and logging

### Testing
```bash
# Run tests
python -m pytest tests/

# Test specific modules
python -m pytest tests/test_canvas_api.py
python -m pytest tests/test_event_handler.py
```

### Code Style
- Follow PEP 8 Python style guidelines
- Use type hints where appropriate
- Document all public functions and classes
- Maintain consistent error handling patterns

## 📊 Data Flow

### User Interaction Flow
1. **User sends message** → Facebook Messenger API
2. **Message received** → `core/event_handler.py`
3. **Intent identified** → Route to appropriate handler
4. **Business logic** → Process request using relevant modules
5. **Response generated** → Send via `api/messenger_api.py`

### Data Synchronization
1. **Background jobs** → Fetch data from Canvas LMS
2. **Data processed** → Store in local PostgreSQL database
3. **User requests** → Serve from local database for speed
4. **Periodic sync** → Keep local data fresh and accurate

## 🔒 Security Features

- **Token Encryption**: Secure storage of API credentials
- **Input Validation**: Sanitize all user inputs
- **Rate Limiting**: Prevent API abuse
- **Error Handling**: Secure error messages without information leakage
- **CORS Configuration**: Controlled cross-origin access

## 🚀 Deployment

### Render Deployment
The application is configured for deployment on Render:
- **Web Service**: Main Flask application
- **Cron Jobs**: Background task processing
- **PostgreSQL**: Managed database service

### Environment Variables
```bash
# Required for production
DATABASE_URL=postgresql://...
FACEBOOK_ACCESS_TOKEN=...
CANVAS_API_TOKEN=...
OPENAI_API_KEY=...
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_S3_BUCKET=...
```

## 📈 Monitoring and Maintenance

### Health Checks
- Database connection monitoring
- API endpoint availability
- Background job execution status
- Error rate tracking

### Logging
- Structured logging for all operations
- Error tracking and alerting
- Performance metrics collection
- User activity monitoring

## 🤝 Contributing

### Development Workflow
1. Create feature branch from `main`
2. Implement changes with tests
3. Update documentation
4. Submit pull request
5. Code review and testing
6. Merge to main branch

### Code Standards
- Write clear, documented code
- Include unit tests for new features
- Follow existing architectural patterns
- Update relevant documentation

## 📚 Additional Resources

- **API Documentation**: See individual module README files
- **Database Schema**: Check `database/models.py` for data structure
- **Configuration**: Review `config/settings.py` for all options
- **Testing**: Use `tests/` directory for examples and test cases

## 🆘 Support

For technical issues or questions:
- Check the individual module README files
- Review error logs and debugging information
- Consult the test files for usage examples
- Refer to Flask and SQLAlchemy documentation

---

**Easely Bot** - Making academic life easier, one conversation at a time. 