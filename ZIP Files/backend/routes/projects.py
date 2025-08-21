# routes/projects.py
from datetime import datetime
from flask import Blueprint, request, jsonify, current_app
from models.project import Project
from middleware.auth import auth_required, optional_auth
from services.documentation_service import DocumentationService
from database_manager import get_db
import threading
import time
import json

doc_service = DocumentationService()

projects_bp = Blueprint('projects', __name__, url_prefix='/api/projects')

# ADD near other imports
from flask import send_file, abort
from io import BytesIO
import base64

@projects_bp.route('/<project_id>/files', methods=['GET'])
@optional_auth
def list_project_files(project_id):
    """List project files (name/size/type only)."""
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404
    files = project.files or []
    return jsonify({
        'success': True,
        'data': [{'name': f.get('name'), 'size': f.get('size'), 'type': f.get('type')} for f in files]
    })

@projects_bp.route('/<project_id>/files/<path:filename>', methods=['GET'])
@optional_auth
def get_project_file(project_id, filename):
    """Return full text content of a single file."""
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'error': 'Project not found'}), 404

    files = project.files or []
    import os
    candidates = [f for f in files if f.get('name') == filename or os.path.basename(f.get('name','')) == filename]
    file_obj = candidates[0] if candidates else None
    if not file_obj:
        return jsonify({'error': 'File not found'}), 404

    content = file_obj.get('content', '')
    return jsonify({'success': True, 'name': filename, 'content': content})


@projects_bp.route('', methods=['GET'])
@optional_auth 
def get_all_projects():
    """Get all projects - public access for viewing, user-specific for authenticated users"""
    try:
        # Get projects using documentation service
        user_id = request.current_user.id if request.current_user else None
        projects = doc_service.get_all_projects(user_id)
        
        return jsonify({
            'success': True,
            'data': [project.to_dict() for project in projects],
            'total': len(projects)
        })
    except Exception as e:
        return jsonify({'error': f'Failed to fetch projects: {str(e)}'}), 500

@projects_bp.route('', methods=['POST'])
@auth_required
def create_project():
    """Create new project with file upload"""
    try:
        # Get form data
        title = request.form.get('title')
        description = request.form.get('description', '')
        files = request.files.getlist('files')
        
        # Validation
        if not title or len(title.strip()) < 2:
            return jsonify({'error': 'Project title is required and must be at least 2 characters'}), 400
        
        if not files or not any(f.filename for f in files):
            return jsonify({'error': 'At least one file is required'}), 400
        
        # Create project using documentation service
        project = doc_service.create_project(
            title=title,
            description=description,
            files=files,
            user_id=request.current_user.id
        )
        
        # Start async documentation generation using the service
        doc_service.generate_documentation(project, async_mode=True)
        
        return jsonify({
            'success': True,
            'message': 'Project created successfully. Multi-agent documentation generation started.',
            'data': project.to_dict()
        }), 201
        
    except Exception as e:
        print(f"⚠️ Project creation failed: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'Failed to create project: {str(e)}'}), 500

@projects_bp.route('/<project_id>', methods=['GET'])
@optional_auth
def get_project(project_id):
    """Get specific project details"""
    try:
        # Get project using documentation service
        user_id = request.current_user.id if request.current_user else None
        project = doc_service.get_project(project_id, user_id)
        
        return jsonify({
            'success': True,
            'data': project.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to fetch project: {str(e)}'}), 500

@projects_bp.route('/<project_id>', methods=['PUT'])
@auth_required
def update_project(project_id):
    """Update project details"""
    try:
        project = Project.get_by_id(project_id, request.current_user.id)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        
        # Update allowed fields
        updates = {}
        if 'title' in data:
            updates['title'] = data['title']
        if 'description' in data:
            updates['description'] = data['description']
        
        if updates:
            with get_db() as db:
                success = db.update_project(project_id, updates)
                if success:
                    # Update local object
                    for key, value in updates.items():
                        setattr(project, key, value)
                    project.updated_at = datetime.utcnow().isoformat()
        
        return jsonify({
            'success': True,
            'message': 'Project updated successfully',
            'data': project.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to update project: {str(e)}'}), 500

@projects_bp.route('/<project_id>', methods=['DELETE'])
@auth_required
def delete_project(project_id):
    """Delete a project"""
    try:
        with get_db() as db:
            success = db.delete_project(project_id, request.current_user.id)
            
            if not success:
                return jsonify({'error': 'Project not found'}), 404
        
        return jsonify({
            'success': True,
            'message': 'Project deleted successfully'
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to delete project: {str(e)}'}), 500
    
    
@projects_bp.route('/<project_id>/documentation/section', methods=['PUT'])
@auth_required
def update_documentation_section(project_id):
    """Update a specific section of project documentation"""
    try:
        project = Project.get_by_id(project_id, request.current_user.id)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        section_id = data.get('section_id')
        section_content = data.get('section_content')
        
        if not section_id or not section_content:
            return jsonify({'error': 'Section ID and content are required'}), 400
        
        # Store section updates in metadata (we don't modify the main documentation)
        current_metadata = json.loads(project.generation_metadata or '{}')
        if 'section_updates' not in current_metadata:
            current_metadata['section_updates'] = {}
        
        current_metadata['section_updates'][section_id] = {
            'content': section_content,
            'updated_at': datetime.utcnow().isoformat()
        }
        
        # Update project with new metadata
        updates = {
            'generation_metadata': json.dumps(current_metadata)
        }
        
        with get_db() as db:
            success = db.update_project(project_id, updates)
            if success:
                project.generation_metadata = json.dumps(current_metadata)
        
        return jsonify({
            'success': True,
            'message': 'Section updated successfully',
            'data': {
                'section_id': section_id,
                'section_content': section_content
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to update section: {str(e)}'}), 500

@projects_bp.route('/<project_id>/documentation', methods=['PUT'])
@auth_required
def update_documentation(project_id):
    """Update project documentation"""
    try:
        project = Project.get_by_id(project_id, request.current_user.id)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        documentation = data.get('documentation')
        
        if not documentation:
            return jsonify({'error': 'Documentation content is required'}), 400
        
        # Update project documentation
        updates = {
            'documentation': documentation
        }
        
        with get_db() as db:
            success = db.update_project(project_id, updates)
            if success:
                project.documentation = documentation
        
        return jsonify({
            'success': True,
            'message': 'Documentation updated successfully',
            'data': {
                'documentation': project.documentation
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to update documentation: {str(e)}'}), 500

@projects_bp.route('/<project_id>/regenerate', methods=['POST'])
@auth_required
def regenerate_documentation(project_id):
    """Regenerate documentation for existing project using multi-agent system"""
    try:
        project = Project.get_by_id(project_id, request.current_user.id)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Start regeneration using documentation service
        doc_service.generate_documentation(project, async_mode=True)
        
        return jsonify({
            'success': True,
            'message': 'Documentation regeneration started',
            'data': project.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to start regeneration: {str(e)}'}), 500

@projects_bp.route('/<project_id>/status', methods=['GET'])
@optional_auth
def get_project_status(project_id):
    """Get project processing status"""
    try:
        # Check access permissions
        if request.current_user:
            project = Project.get_by_id(project_id, request.current_user.id)
        else:
            # Guest access
            project = Project.get_by_id(project_id)
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        return jsonify({
            'success': True,
            'data': {
                'status': project.status,
                'progress': project.progress,
                'status_message': project.status_message,
                'error_message': project.error_message,
                'updated_at': project.updated_at
            }
        })
        
    except Exception as e:
        return jsonify({'error': f'Failed to get status: {str(e)}'}), 500