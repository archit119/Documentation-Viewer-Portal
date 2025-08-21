# models/user.py
import uuid
import bcrypt
from datetime import datetime
from database_manager import get_db
from typing import Optional, Dict, Any

class User:
    """User model compatible with DatabaseManager"""
    
    def __init__(self, user_data: Dict[str, Any]):
        self.id = user_data.get('id')
        self.name = user_data.get('name')
        self.email = user_data.get('email')
        self.password_hash = user_data.get('password_hash')
        self.role = user_data.get('role', 'user')
        self.created_at = user_data.get('created_at')
        self.updated_at = user_data.get('updated_at')
    
    def set_password(self, password: str):
        """Hash and set password"""
        salt = bcrypt.gensalt()
        self.password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
    
    def check_password(self, password: str) -> bool:
        """Check password against hash"""
        return bcrypt.checkpw(password.encode('utf-8'), self.password_hash.encode('utf-8'))
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'role': self.role,
            'created_at': self.created_at,
            'updated_at': self.updated_at
        }
    
    @staticmethod
    def create_user(name: str, email: str, password: str, role: str = 'user') -> 'User':
        """Create new user"""
        # Hash password
        salt = bcrypt.gensalt()
        password_hash = bcrypt.hashpw(password.encode('utf-8'), salt).decode('utf-8')
        
        user_data = {
            'name': name,
            'email': email,
            'password_hash': password_hash,
            'role': role
        }
        
        with get_db() as db:
            user_id = db.create_user(user_data)
            user_data['id'] = user_id
            user_data['created_at'] = datetime.utcnow().isoformat()
            user_data['updated_at'] = datetime.utcnow().isoformat()
        
        return User(user_data)
    
    @staticmethod
    def get_by_email(email: str) -> Optional['User']:
        """Get user by email"""
        with get_db() as db:
            user_data = db.get_user_by_email(email)
            return User(user_data) if user_data else None
    
    @staticmethod
    def get_by_id(user_id: str) -> Optional['User']:
        """Get user by ID"""
        with get_db() as db:
            user_data = db.get_user_by_id(user_id)
            return User(user_data) if user_data else None
    
    @property
    def is_active(self):
        """User is always active (you can add logic here later)"""
        return True

    def __repr__(self):
        return f'<User {self.email}>'