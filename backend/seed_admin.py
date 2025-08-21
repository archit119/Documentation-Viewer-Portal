# seed_admin.py
import os
from models.user import User
from database_manager import DATABASE_TYPE

def seed_admin():
    """Create initial admin user"""
    print(f"🚀 Seeding admin user to {DATABASE_TYPE} database...")
    
    # Check if admin already exists
    admin_email = 'admin@mashreq.com'
    existing_admin = User.get_by_email(admin_email)
    
    if existing_admin:
        print(f"✅ Admin user already exists: {admin_email}")
        print(f"👤 Name: {existing_admin.name}")
        print(f"🔐 Role: {existing_admin.role}")
        return
    
    # Create admin user
    try:
        admin_user = User.create_user(
            name='Mashreq Administrator',
            email=admin_email,
            password='admin123',  # Change this password!
            role='admin'  # Set role as admin
        )
        
        print(f"✅ Admin user created successfully!")
        print(f"📧 Email: {admin_email}")
        print(f"🔑 Password: admin123")
        print(f"👤 Role: admin")
        print(f"💾 Database: {DATABASE_TYPE}")
        print(f"⚠️  Please change the password after first login!")
        
    except Exception as e:
        print(f"❌ Failed to create admin user: {e}")

if __name__ == '__main__':
    seed_admin()