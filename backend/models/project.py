# models/project.py
import uuid
import json
from datetime import datetime
from database_manager import get_db
from typing import Optional, Dict, Any, List




class Project:
    """Project model compatible with DatabaseManager"""
    
    def __init__(self, project_data: Dict[str, Any]):
        self.id = project_data.get('id')
        self.title = project_data.get('title')
        self.description = project_data.get('description')
        self.status = project_data.get('status', 'processing')
        self.progress = project_data.get('progress', 0)
        self.status_message = project_data.get('status_message')
        self.files_json = project_data.get('files_json', '[]')
        self.documentation = project_data.get('documentation')
        self.generation_metadata = project_data.get('generation_metadata')
        self.diagrams_json = project_data.get('diagrams_json', '{}')
        self.diagrams_generated_at = project_data.get('diagrams_generated_at')
        self.created_by = project_data.get('created_by')
        self.tags = project_data.get('tags', '[]')
        self.is_public = project_data.get('is_public', False)
        self.version = project_data.get('version', '1.0.0')
        self.error_message = project_data.get('error_message')
        self.created_at = project_data.get('created_at')
        self.updated_at = project_data.get('updated_at')
    
    @property
    def files(self):
        """Get files as Python list"""
        try:
            return json.loads(self.files_json) if self.files_json else []
        except json.JSONDecodeError:
            return []
    
    @files.setter
    def files(self, value):
        """Set files from Python list"""
        self.files_json = json.dumps(value) if value else '[]'
    
    # NEW: Diagrams property
    @property
    def diagrams(self):
        """Get diagrams as Python dict"""
        try:
            return json.loads(self.diagrams_json) if self.diagrams_json else {}
        except json.JSONDecodeError:
            return {}

    @diagrams.setter
    def diagrams(self, value):
        self.diagrams_json = json.dumps(value or {})
    
    def update_progress(self, progress: int, status_message: str = None):
        """Update project progress"""
        updates = {'progress': progress}
        if status_message:
            updates['status_message'] = status_message
        
        with get_db() as db:
            success = db.update_project(self.id, updates)
            if success:
                self.progress = progress
                if status_message:
                    self.status_message = status_message
                self.updated_at = datetime.utcnow().isoformat()
    
    def mark_completed(self, documentation: str, metadata: Dict = None, diagrams: Dict = None):
        """Mark project as completed"""
        updates = {
            'status': 'completed',
            'documentation': documentation,
            'progress': 100,
            'status_message': 'Documentation generated successfully',
            'error_message': None
        }
        
        if metadata:
            updates['generation_metadata'] = json.dumps(metadata)
        if diagrams:
            updates['diagrams_json'] = json.dumps(diagrams)
            updates['diagrams_generated_at'] = datetime.utcnow().isoformat()
        
        with get_db() as db:
            success = db.update_project(self.id, updates)
            if success:
                self.status = 'completed'
                self.documentation = documentation
                self.progress = 100
                self.status_message = 'Documentation generated successfully'
                self.error_message = None
                if metadata:
                    self.generation_metadata = json.dumps(metadata)
                if diagrams:
                    self.diagrams_json = json.dumps(diagrams)
                    self.diagrams_generated_at = datetime.utcnow().isoformat()
                self.updated_at = datetime.utcnow().isoformat()
    
    def mark_error(self, error_message: str):
        """Mark project as error"""
        updates = {
            'status': 'error',
            'error_message': error_message,
            'progress': 0,
            'status_message': 'Documentation generation failed'
        }
        
        with get_db() as db:
            success = db.update_project(self.id, updates)
            if success:
                self.status = 'error'
                self.error_message = error_message
                self.progress = 0
                self.status_message = 'Documentation generation failed'
                self.updated_at = datetime.utcnow().isoformat()
    
    # NEW: Diagram helper methods
    @property
    def diagrams_count(self):
        d = self.diagrams
        return len(d.get('diagrams', {})) + len(d.get('existing', []))
    
    def has_diagrams(self):
        """Check if project has any diagrams"""
        return self.diagrams_count > 0
    
    def to_dict(self, include_files_content=False):
        """Convert project to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status,
            'progress': self.progress,
            'error': self.error_message,
            'documentation': self.documentation,
            'generation_metadata': self.generation_metadata,  # ADD THIS LINE
            'diagrams': self.diagrams,
            'files_count': len(self.files) if self.files else 0,
            'file_names': [f.get('name') for f in self.files] if self.files else [],
            'created_by': self.created_by,
            'is_public': self.is_public,
            'created_at': self.created_at,  # Already a string, no .isoformat() needed
            'updated_at': self.updated_at,  # Already a string, no .isoformat() needed
            'statusMessage': self.status_message
        }
        
        if include_files_content:
            data['files'] = self.files
        
        return data
    
    @staticmethod
    def get_user_projects(user_id: str) -> List['Project']:
        """Get all projects for a user"""
        with get_db() as db:
            project_data_list = db.get_user_projects(user_id)
            return [Project(data) for data in project_data_list]
    
    @staticmethod
    def get_by_id(project_id: str, user_id: str = None) -> Optional['Project']:
        """Get project by ID"""
        with get_db() as db:
            project_data = db.get_project_by_id(project_id, user_id)
            return Project(project_data) if project_data else None
    
    @staticmethod
    def create_project(title: str, description: str, files: List[Dict], created_by: str) -> 'Project':
        """Create a new project"""
        project_data = {
            'title': title,
            'description': description,
            'files': files,
            'created_by': created_by
        }
        
        with get_db() as db:
            project_id = db.create_project(project_data)
            project_data['id'] = project_id
            project_data['files_json'] = json.dumps(files)
            project_data['created_at'] = datetime.utcnow().isoformat()
            project_data['updated_at'] = datetime.utcnow().isoformat()
        
        return Project(project_data)
    
    def __repr__(self):
        return f'<Project {self.title}>'
    
    # In models/project.py - Add this method to the Project class
    def get_embedded_images(self):
        """Get all embedded images from project files"""
        images = []
        for file_data in self.files:
            if 'embedded_images' in file_data:
                images.extend(file_data['embedded_images'])
            elif 'images' in file_data:
                images.extend(file_data['images'])
        return images


    def add_embedded_images(self, images_data):
        """Add embedded images to project"""
        files = self.files
        if not files:
            files = []
        
        # Add images data to first file or create images file
        if files:
            files[0]['embedded_images'] = images_data
        else:
            files.append({
                'name': 'embedded_images.json',
                'type': 'image_data',
                'embedded_images': images_data
            })
        
        self.files = files