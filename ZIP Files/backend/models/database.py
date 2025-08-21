# models/database.py
from database_manager import get_db, initialize_database

# Initialize database on import
try:
    initialize_database()
    print("✅ Database initialized successfully")
except Exception as e:
    print(f"⚠️ Database initialization failed: {e}")

def init_db(app):
    """Initialize database with Flask app"""
    # Database is already initialized by database_manager
    pass