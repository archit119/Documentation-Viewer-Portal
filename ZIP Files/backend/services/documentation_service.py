import os
import logging
import datetime
from dotenv import load_dotenv
from services.multi_agent_documentation_service import multi_agent_service
from services.file_processing_service import enhanced_file_processor
# services/documentation_service.py
from models.project import Project

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

os.environ['no_proxy'] = '*'

class DocumentationService:
    """Main documentation service class that can be used anywhere"""
    
    def __init__(self):
        """Initialize the documentation service"""
        self.multi_agent_service = multi_agent_service
        self.file_processor = enhanced_file_processor
        logger.debug("✅ Documentation service initialized successfully")
    
    def create_project(self, title, description="", files=None, user_id=None):
        """Create a new documentation project"""
        try:
            if not title or len(title.strip()) < 2:
                raise ValueError('Project title is required and must be at least 2 characters')
            
            if not files:
                raise ValueError('At least one file is required')
            
            # Process uploaded files
            processed_files = self.file_processor.process_uploaded_files(files)
            
            if not processed_files:
                raise ValueError('No valid files could be processed')
            
            # Create project in database using the new model
            project = Project.create_project(
                title=title.strip(),
                description=description.strip(),
                files=processed_files,
                created_by=user_id
            )
            
            logger.info(f"📝 Project created: {project.title} (ID: {project.id})")
            logger.info(f"📄 Files uploaded: {len(processed_files)}")
            
            return project
            
        except Exception as e:
            logger.error(f"⚠️ Error creating project: {e}")
            raise e
    
    def generate_documentation(self, project, async_mode=True):
        """Generate documentation for a project"""
        try:
            project_data = {
                'title': project.title,
                'description': project.description,
                'files': project.files,
            }
            
            if async_mode:
                # For async processing (existing behavior)
                return self._generate_documentation_async(project, project_data)
            else:
                # For synchronous processing
                return self._generate_documentation_sync(project, project_data)
                
        except Exception as e:
            logger.error(f"❌ Error generating documentation: {e}")
            project.mark_error(f"Documentation generation failed: {str(e)}")
            raise e
    
    def _generate_documentation_sync(self, project, project_data):
        """Generate documentation synchronously"""
        project.update_progress(10, "Initializing multi-agent documentation system...")
        project.update_progress(25, "Analyzing uploaded files...")
        project.update_progress(50, "Deploying specialized AI agents...")
        
        result = self.multi_agent_service.generate_documentation(project_data, project)
        
        project.update_progress(75, "Finalizing documentation...")
        project.update_progress(90, "Saving comprehensive documentation...")
        
        project.mark_completed(
            documentation=result['content'],
            metadata=result
        )
        
        logger.info("✅ Documentation generated successfully")
        return result
    
    def _generate_documentation_async(self, project, project_data):
        """Generate documentation asynchronously (existing behavior)"""
        import threading
        from flask import current_app
        
        def generate_docs_async(app_instance):
            with app_instance.app_context():
                try:
                    proj = Project.get_by_id(project.id)
                    if proj:
                        self._generate_documentation_sync(proj, project_data)
                except Exception as e:
                    logger.error(f"⚠️ Async documentation generation failed: {e}")
                    proj = Project.get_by_id(project.id)
                    if proj:
                        proj.mark_error(f"System error: {str(e)}")
        
        doc_thread = threading.Thread(
            target=generate_docs_async, 
            args=(current_app._get_current_object(),), 
            daemon=True
        )
        doc_thread.start()
        
        return {"status": "started", "message": "Documentation generation started"}
    
    def get_project(self, project_id, user_id=None):
        """Get a specific project"""
        try:
            project = Project.get_by_id(project_id, user_id)
            
            if not project:
                raise ValueError('Project not found')
            
            return project
            
        except Exception as e:
            logger.error(f"⚠️ Error getting project: {e}")
            raise e
    
    def get_all_projects(self, user_id=None):
        """Get all projects for a user or all public projects"""
        try:
            if user_id:
                projects = Project.get_user_projects(user_id)
            else:
                # Get all projects for public access
                from database_manager import get_db
                with get_db() as db:
                    project_data_list = db.retrieve_data("projects", "1=1 ORDER BY updated_at DESC")
                    projects = [Project(data) for data in project_data_list]
            
            return projects
            
        except Exception as e:
            logger.error(f"⚠️ Error getting projects: {e}")
            raise e
    
    def update_project(self, project_id, user_id, **kwargs):
        """Update project details"""
        try:
            from database_manager import get_db
            
            # Update allowed fields
            updates = {}
            for key, value in kwargs.items():
                if key in ['title', 'description']:
                    updates[key] = value
            
            if updates:
                with get_db() as db:
                    success = db.update_project(project_id, updates)
                    if not success:
                        raise ValueError('Project not found')
            
            # Return updated project
            project = Project.get_by_id(project_id, user_id)
            return project
            
        except Exception as e:
            logger.error(f"⌚ Error updating project: {e}")
            raise e
    
    def delete_project(self, project_id, user_id):
        """Delete a project"""
        try:
            from database_manager import get_db
            
            with get_db() as db:
                success = db.delete_project(project_id, user_id)
                
                if not success:
                    raise ValueError('Project not found')
            
            logger.info(f"🗑️ Project deleted successfully")
            return True
            
        except Exception as e:
            logger.error(f"⌚ Error deleting project: {e}")
            raise e


def main():
    """Main function to test the documentation service locally"""
    print("🚀 Documentation Service Test")
    print("=" * 40)
    
    # Initialize service
    doc_service = DocumentationService()
    
    # Example usage would go here
    print("Documentation service initialized successfully!")
    print("Use this service in your Flask routes or other applications.")


if __name__ == "__main__":
    main()