from functools import wraps
from flask import request, jsonify
import re

def validate_json(required_fields=None, optional_fields=None):
    """Decorator to validate JSON request data"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if request contains JSON
            if not request.is_json:
                return jsonify({
                    'success': False,
                    'error': 'Content-Type must be application/json'
                }), 400
            
            try:
                data = request.get_json()
            except Exception:
                return jsonify({
                    'success': False,
                    'error': 'Invalid JSON format'
                }), 400
            
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No JSON data provided'
                }), 400
            
            # Check required fields
            if required_fields:
                missing_fields = []
                for field in required_fields:
                    if field not in data or data[field] is None or (isinstance(data[field], str) and not data[field].strip()):
                        missing_fields.append(field)
                
                if missing_fields:
                    return jsonify({
                        'success': False,
                        'error': f'Missing required fields: {", ".join(missing_fields)}'
                    }), 400
            
            # Validate field types and constraints
            validation_errors = []
            
            # Email validation
            if 'email' in data:
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, data['email']):
                    validation_errors.append('Invalid email format')
            
            # Password validation
            if 'password' in data:
                password = data['password']
                if len(password) < 6:
                    validation_errors.append('Password must be at least 6 characters long')
                if len(password) > 128:
                    validation_errors.append('Password must be less than 128 characters')
            
            # Name validation
            if 'name' in data:
                name = data['name'].strip() if isinstance(data['name'], str) else str(data['name'])
                if len(name) < 2:
                    validation_errors.append('Name must be at least 2 characters long')
                if len(name) > 50:
                    validation_errors.append('Name must be less than 50 characters')
            
            # Title validation (for projects)
            if 'title' in data:
                title = data['title'].strip() if isinstance(data['title'], str) else str(data['title'])
                if len(title) < 2:
                    validation_errors.append('Title must be at least 2 characters long')
                if len(title) > 200:
                    validation_errors.append('Title must be less than 200 characters')
            
            if validation_errors:
                return jsonify({
                    'success': False,
                    'error': 'Validation failed',
                    'details': validation_errors
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def validate_file_upload(allowed_extensions=None, max_file_size=None, max_files=None):
    """Decorator to validate file uploads"""
    if allowed_extensions is None:
        allowed_extensions = {
            'txt', 'py', 'js', 'jsx', 'ts', 'tsx', 'html', 'css', 'scss',
            'json', 'xml', 'yaml', 'yml', 'md', 'java', 'cpp', 'c', 'cs',
            'php', 'rb', 'go', 'rs', 'swift', 'kt', 'scala', 'sql', 'sh'
        }
    
    if max_file_size is None:
        max_file_size = 50 * 1024 * 1024  # 50MB
    
    if max_files is None:
        max_files = 20
    
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Check if files are in request
            if 'files' not in request.files:
                return jsonify({
                    'success': False,
                    'error': 'No files provided'
                }), 400
            
            files = request.files.getlist('files')
            
            # Check if any files were selected
            if not files or all(f.filename == '' for f in files):
                return jsonify({
                    'success': False,
                    'error': 'No files selected'
                }), 400
            
            # Check number of files
            valid_files = [f for f in files if f.filename != '']
            if len(valid_files) > max_files:
                return jsonify({
                    'success': False,
                    'error': f'Too many files. Maximum allowed: {max_files}'
                }), 400
            
            # Validate each file
            validation_errors = []
            
            for file in valid_files:
                filename = file.filename
                
                # Check file extension
                if '.' not in filename:
                    validation_errors.append(f'File {filename} has no extension')
                    continue
                
                ext = filename.rsplit('.', 1)[1].lower()
                if ext not in allowed_extensions:
                    validation_errors.append(f'File type .{ext} not allowed for {filename}')
                
                # Check file size (read content to get actual size)
                file.seek(0, 2)  # Seek to end
                file_size = file.tell()
                file.seek(0)  # Reset to beginning
                
                if file_size > max_file_size:
                    size_mb = file_size / (1024 * 1024)
                    max_mb = max_file_size / (1024 * 1024)
                    validation_errors.append(f'File {filename} is too large ({size_mb:.1f}MB). Maximum: {max_mb:.1f}MB')
                
                # Check for empty files
                if file_size == 0:
                    validation_errors.append(f'File {filename} is empty')
            
            if validation_errors:
                return jsonify({
                    'success': False,
                    'error': 'File validation failed',
                    'details': validation_errors
                }), 400
            
            return f(*args, **kwargs)
        
        return decorated_function
    return decorator

def validate_pagination():
    """Decorator to validate pagination parameters"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            try:
                # Get pagination parameters
                page = request.args.get('page', 1, type=int)
                per_page = request.args.get('per_page', 10, type=int)
                
                # Validate page
                if page < 1:
                    return jsonify({
                        'success': False,
                        'error': 'Page number must be 1 or greater'
                    }), 400
                
                # Validate per_page
                if per_page < 1:
                    return jsonify({
                        'success': False,
                        'error': 'Items per page must be 1 or greater'
                    }), 400
                
                if per_page > 100:
                    return jsonify({
                        'success': False,
                        'error': 'Items per page cannot exceed 100'
                    }), 400
                
                # Add pagination info to request
                request.pagination = {
                    'page': page,
                    'per_page': per_page,
                    'offset': (page - 1) * per_page
                }
                
                return f(*args, **kwargs)
                
            except ValueError:
                return jsonify({
                    'success': False,
                    'error': 'Invalid pagination parameters'
                }), 400
        
        return decorated_function
    return decorator

def validate_project_access(f):
    """Decorator to validate project access permissions"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        project_id = kwargs.get('project_id')
        
        if not project_id:
            return jsonify({
                'success': False,
                'error': 'Project ID required'
            }), 400
        
        # This will be used in conjunction with auth_required
        # The actual project access check will be done in the route function
        return f(*args, **kwargs)
    
    return decorated_function