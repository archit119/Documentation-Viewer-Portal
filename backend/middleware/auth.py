from functools import wraps
from flask import jsonify, request
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from models.user import User

def auth_required(f):
    """Decorator to require authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Verify JWT token in request
            verify_jwt_in_request()
            
            # Get user ID from token
            user_id = get_jwt_identity()
            
            # Find user in database
            # Find user in database using your custom User class
            user = User.get_by_id(user_id)

            if not user:
                return jsonify({
                    'success': False,
                    'error': 'User not found'
                }), 401

            # Note: Your User class doesn't have is_active property, so remove this check
            # or add it to your User class if needed
            
            # Add user to request context
            request.current_user = user
            
            # Call the original function
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
    
    return decorated_function

def admin_required(f):
    """Decorator to require admin role"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # First check authentication
            verify_jwt_in_request()
            user_id = get_jwt_identity()
            user = User.get_by_id(user_id)

            if not user:
                return jsonify({
                    'success': False,
                    'error': 'Authentication required'
                }), 401
            
            # Check admin role
            if user.role != 'admin':
                return jsonify({
                    'success': False,
                    'error': 'Admin access required'
                }), 403
            
            # Add user to request context
            request.current_user = user
            
            return f(*args, **kwargs)
            
        except Exception as e:
            return jsonify({
                'success': False,
                'error': 'Authentication required'
            }), 401
    
    return decorated_function

def optional_auth(f):
    """Decorator for optional authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        try:
            # Try to verify JWT token
            verify_jwt_in_request(optional=True)
            user_id = get_jwt_identity()
            
            if user_id:
                user = User.get_by_id(user_id)
                if user:
                    request.current_user = user
                else:
                    request.current_user = None
            else:
                request.current_user = None
                
        except:
            # If token verification fails, continue without user
            request.current_user = None
        
        return f(*args, **kwargs)
    
    return decorated_function