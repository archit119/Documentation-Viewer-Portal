# app.py
import os
from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from config import config
#from routes.diagrams import diagrams_bp 
from database_manager import DATABASE_TYPE

def create_app(config_name='development'):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config[config_name])

    # Load JWT secret from environment
    from dotenv import load_dotenv
    load_dotenv()
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', app.config['SECRET_KEY'])
    
    # Initialize extensions
    CORS(app, origins=[app.config['FRONTEND_URL']])
    jwt = JWTManager(app)
    
    # Initialize database
    from models.database import init_db
    # Import models so they're registered
    from models import user, project
    init_db(app)
    
    # Create upload directory
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Register blueprints
    from routes.auth import auth_bp
    from routes.projects import projects_bp
    from routes.files import files_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(files_bp)
    #app.register_blueprint(diagrams_bp)
    
    # Health check endpoint
    @app.route('/api/health', methods=['GET'])
    def health_check():
        return jsonify({
            'status': 'OK',
            'message': 'Mashreq Documentation Portal API',
            'version': '1.0.0',
            'database': DATABASE_TYPE
        })
    
    diagrams_dir = os.path.join(app.root_path, 'static', 'diagrams')
    os.makedirs(diagrams_dir, exist_ok=True)
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({'error': 'Endpoint not found'}), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        return jsonify({'error': 'Internal server error'}), 500
    
    return app

if __name__ == '__main__':
    print(f"🚀 Starting Flask app with {DATABASE_TYPE} database")
    app = create_app('development')
    app.run(debug=True, host='0.0.0.0', port=5000)