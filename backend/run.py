import os
from app import create_app

if __name__ == '__main__':
    # Get environment
    env = os.environ.get('FLASK_ENV', 'development')
    
    # Create app
    app = create_app(env)
    
    # Run app
    debug = env == 'development'
    app.run(
        debug=debug,
        host='0.0.0.0',
        port=int(os.environ.get('PORT', 5000))
    )