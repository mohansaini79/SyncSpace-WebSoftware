from flask import Blueprint, request, jsonify
from utils.db import get_db
from bson import ObjectId
from datetime import datetime
import jwt
import os
import cloudinary.uploader

file_bp = Blueprint('file', __name__)

def verify_token():
    """Verify JWT token from request headers"""
    token = request.headers.get('Authorization', '').replace('Bearer ', '')
    
    if not token:
        return None
    
    try:
        payload = jwt.decode(token, os.getenv('SECRET_KEY', 'your-secret-key'), algorithms=['HS256'])
        return payload['user_id']
    except:
        return None

@file_bp.route('/upload', methods=['POST'])
def upload_file():
    """Upload file to Cloudinary and save metadata"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        # Check if file is present
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        workspace_id = request.form.get('workspace_id')
        
        if not workspace_id:
            return jsonify({'error': 'workspace_id is required'}), 400
        
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Upload to Cloudinary
        upload_result = cloudinary.uploader.upload(
            file,
            folder=f"syncspace/{workspace_id}",
            resource_type="auto"
        )
        
        # Save file metadata to database
        db = get_db()
        file_data = {
            'name': file.filename,
            'url': upload_result['secure_url'],
            'public_id': upload_result['public_id'],
            'size': upload_result.get('bytes', 0),
            'format': upload_result.get('format', ''),
            'resource_type': upload_result.get('resource_type', ''),
            'workspace_id': workspace_id,
            'uploaded_by': user_id,
            'uploaded_at': datetime.now()
        }
        
        result = db.files.insert_one(file_data)
        file_data['_id'] = str(result.inserted_id)
        file_data['uploaded_at'] = file_data['uploaded_at'].isoformat()
        
        return jsonify(file_data), 201
        
    except Exception as e:
        print(f"Error uploading file: {e}")
        return jsonify({'error': 'Failed to upload file', 'details': str(e)}), 500

@file_bp.route('/<workspace_id>', methods=['GET'])
def get_files(workspace_id):
    """Get all files in a workspace"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        files = list(db.files.find({
            'workspace_id': workspace_id
        }).sort('uploaded_at', -1))
        
        # Convert ObjectId to string
        for file in files:
            file['_id'] = str(file['_id'])
            if 'uploaded_at' in file:
                file['uploaded_at'] = file['uploaded_at'].isoformat()
        
        return jsonify(files), 200
        
    except Exception as e:
        print(f"Error getting files: {e}")
        return jsonify({'error': 'Failed to get files'}), 500

@file_bp.route('/<file_id>', methods=['DELETE'])
def delete_file(file_id):
    """Delete a file"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        # Get file data
        file = db.files.find_one({'_id': ObjectId(file_id)})
        
        if not file:
            return jsonify({'error': 'File not found'}), 404
        
        # Delete from Cloudinary
        cloudinary.uploader.destroy(file['public_id'])
        
        # Delete from database
        db.files.delete_one({'_id': ObjectId(file_id)})
        
        return jsonify({'message': 'File deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting file: {e}")
        return jsonify({'error': 'Failed to delete file'}), 500
