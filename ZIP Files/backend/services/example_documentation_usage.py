#!/usr/bin/env python3
"""
Example usage of the DocumentationService class
"""

from documentation_service import DocumentationService
from models.database import db
from app import create_app

def main():
    print("🚀 DocumentationService Usage Examples")
    print("=" * 40)
    
    # Initialize Flask app context for database operations
    app = create_app()
    
    with app.app_context():
        # Create the documentation service
        doc_service = DocumentationService()
        
        # Example 1: Get all projects
        print("\n1. Get All Projects:")
        print("-" * 20)
        projects = doc_service.get_all_projects()
        print(f"Found {len(projects)} projects")
        
        for project in projects[:3]:  # Show first 3
            print(f"- {project.title} ({project.status})")
        
        # Example 2: Get specific project
        if projects:
            print("\n2. Get Specific Project:")
            print("-" * 20)
            first_project = projects[0]
            project = doc_service.get_project(first_project.id)
            print(f"Project: {project.title}")
            print(f"Status: {project.status}")
            print(f"Files: {len(project.files)}")
        
        # Example 3: Service info
        print("\n3. Service Information:")
        print("-" * 20)
        print("Documentation service ready for:")
        print("- Creating new projects")
        print("- Generating AI documentation")
        print("- Managing project lifecycle")
        print("- Multi-agent processing")

if __name__ == "__main__":
    main()