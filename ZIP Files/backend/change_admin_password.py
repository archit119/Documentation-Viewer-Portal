# change_admin_password_simple.py
from app import create_app
from models.database import db
from models.user import User

def change_admin_password():
    """Change admin password with visible input"""
    app = create_app('development')
    
    with app.app_context():
        admin_email = 'admin@mashreq.com'
        admin_user = User.find_by_email(admin_email)
        
        if not admin_user:
            print("❌ Admin user not found!")
            return
        
        print(f"Changing password for: {admin_email}")
        print("⚠️  Note: Password will be visible as you type")
        
        # Get new password with visible input
        while True:
            new_password = input("Enter new password: ").strip()
            confirm_password = input("Confirm new password: ").strip()
            
            if new_password != confirm_password:
                print("❌ Passwords don't match. Try again.")
                continue
            
            if len(new_password) < 8:
                print("❌ Password must be at least 8 characters long.")
                continue
            
            break
        
        # Update password
        admin_user.set_password(new_password)
        db.session.commit()
        
        print("✅ Password changed successfully!")
        print("🔍 Remember to clear your terminal history for security")

if __name__ == '__main__':
    change_admin_password()