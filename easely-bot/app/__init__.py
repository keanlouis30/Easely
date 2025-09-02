from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from config.settings import Config

# Initialize SQLAlchemy
db = SQLAlchemy()

def create_app(config_class=Config):
    """
    Application factory pattern for creating Flask app instances
    """
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    db.init_app(app)
    CORS(app)
    
    # Import and register blueprints
    from app.api import canvas_api, messenger_api, payment_api
    from app.core import event_handler
    from app.features import ai_tools, calendar_generator
    from app.jobs import check_expiries, refresh_data, send_reminders
    
    # Register API blueprints
    app.register_blueprint(canvas_api.bp, url_prefix='/api/canvas')
    app.register_blueprint(messenger_api.bp, url_prefix='/api/messenger')
    app.register_blueprint(payment_api.bp, url_prefix='/api/payment')
    
    # Register core functionality
    app.register_blueprint(event_handler.bp, url_prefix='/core')
    
    # Register feature blueprints
    app.register_blueprint(ai_tools.bp, url_prefix='/features/ai')
    app.register_blueprint(calendar_generator.bp, url_prefix='/features/calendar')
    
    # Register job blueprints
    app.register_blueprint(check_expiries.bp, url_prefix='/jobs/expiries')
    app.register_blueprint(refresh_data.bp, url_prefix='/jobs/refresh')
    app.register_blueprint(send_reminders.bp, url_prefix='/jobs/reminders')
    
    # Create database tables
    with app.app_context():
        db.create_all()
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found(error):
        return {'error': 'Not found'}, 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return {'error': 'Internal server error'}, 500
    
    return app

# Create the app instance
app = create_app()

# Import models to ensure they're registered with SQLAlchemy
from app.database import models

if __name__ == '__main__':
    app.run(debug=True)
