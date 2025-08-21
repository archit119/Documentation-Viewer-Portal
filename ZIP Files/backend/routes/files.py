from flask import Blueprint, request, jsonify, send_file
from middleware.auth import auth_required
import os

files_bp = Blueprint('files', __name__, url_prefix='/api/files')

@files_bp.route('/health', methods=['GET'])
def health_check():
    """File service health check"""
    return jsonify({'status': 'File service OK'})

@files_bp.route('/upload', methods=['POST'])
@auth_required
def upload_files():
    """Upload files endpoint"""
    try:
        files = request.files.getlist('files')
        
        if not files:
            return jsonify({'error': 'No files provided'}), 400
        
        uploaded_files = []
        for file in files:
            if file.filename:
                # In a real app, you'd save files to disk/cloud storage
                # For now, we'll just return file info
                uploaded_files.append({
                    'name': file.filename,
                    'size': len(file.read()),
                    'type': file.content_type
                })
                file.seek(0)  # Reset file pointer
        
        return jsonify({
            'success': True,
            'files': uploaded_files
        })
    except Exception as e:
        return jsonify({'error': f'Upload failed: {str(e)}'}), 500