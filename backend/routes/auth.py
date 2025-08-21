from flask import Blueprint, request, jsonify
from models.user import User
from middleware.validation import validate_json

auth_bp = Blueprint('auth', __name__, url_prefix='/api/auth')

@auth_bp.route('/register', methods=['POST'])
@validate_json(['name', 'email', 'password'])
def register():
    """User registration endpoint"""
    try:
        data = request.get_json()
        
        # Check if user already exists
        if User.find_by_email(data['email']):
            return jsonify({'error': 'User already exists'}), 400
        
        # Validate password length
        if len(data['password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters'}), 400
        
        # Create new user
        user = User.create_user(
    name=data['name'].strip(),
    email=data['email'].lower().strip(),
    password=data['password']
)
        
        # Generate token
        token = user.generate_token()
        
        return jsonify({
            'success': True,
            'token': token,
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        #db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@auth_bp.route('/login', methods=['POST'])
@validate_json(['email', 'password'])
def login():
    """User login endpoint"""
    try:
        data = request.get_json()
        
        # Find user by email
        user = User.get_by_email(data['email'])
        
        if not user or not user.check_password(data['password']):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 401
        
        # Update last login
        #user.update_last_login()
        
        # Generate token
        from flask_jwt_extended import create_access_token
        token = create_access_token(identity=user.id)
        
        return jsonify({
            'success': True,
            'token': token,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@auth_bp.route('/me', methods=['GET'])
def get_current_user():
    """Get current user information"""
    from middleware.auth import auth_required
    
    @auth_required
    def _get_current_user():
        return jsonify({
            'success': True,
            'user': request.current_user.to_dict()
        }), 200
    
    return _get_current_user()

@auth_bp.route('/logout', methods=['POST'])
def logout():
    """User logout endpoint"""
    # In JWT, logout is handled client-side by removing the token
    return jsonify({
        'success': True,
        'message': 'Logged out successfully'
    }), 200


@auth_bp.route('/cleanup-users', methods=['DELETE'])
def cleanup_all_users():
    """ADMIN: Delete ALL users from database - REMOVE AFTER USE"""
    try:
        # Delete ALL users regardless of authentication
        # Delete ALL users regardless of authentication
        from database_manager import get_db

        with get_db() as db_manager:
            deleted_count = db_manager.execute_update("DELETE FROM users")
        
        return jsonify({
            'success': True,
            'message': f'ADMIN: Deleted {deleted_count} users successfully'
        })
    except Exception as e:
        #db.session.rollback()
        return jsonify({'error': f'Failed to cleanup all users: {str(e)}'}), 500
    
'''
fetch('http://localhost:5000/api/auth/cleanup-users', {
    method: 'DELETE',
    headers: {
        'Content-Type': 'application/json'
    }
}).then(r => r.json()).then(console.log);
'''