from flask import Blueprint, request, jsonify
from utils.db import get_db
from bson import ObjectId
from datetime import datetime
import jwt
import os

project_bp = Blueprint('project', __name__)

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

@project_bp.route('/list', methods=['GET'])
def list_projects():
    """Get all projects for current user"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        # Get workspaces where user is a member
        workspaces = list(db.workspaces.find({
            'members.user_id': user_id
        }))
        
        workspace_ids = [str(ws['_id']) for ws in workspaces]
        
        # Get projects from these workspaces
        projects = list(db.projects.find({
            'workspace_id': {'$in': workspace_ids}
        }).sort('created_at', -1))
        
        # Convert ObjectId to string and add task count
        for project in projects:
            project['_id'] = str(project['_id'])
            project['workspace_id'] = str(project['workspace_id'])
            
            # Count tasks in this project
            tasks_count = db.tasks.count_documents({
                'project_id': str(project['_id'])
            })
            project['tasks_count'] = tasks_count
            
            # Calculate progress
            completed_tasks = db.tasks.count_documents({
                'project_id': str(project['_id']),
                'status': 'done'
            })
            project['progress'] = int((completed_tasks / tasks_count * 100) if tasks_count > 0 else 0)
            
            if 'created_at' in project:
                project['created_at'] = project['created_at'].isoformat()
        
        return jsonify({'projects': projects}), 200
        
    except Exception as e:
        print(f"Error listing projects: {e}")
        return jsonify({'error': str(e)}), 500

@project_bp.route('/create', methods=['POST'])
def create_project():
    """Create a new project"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        # Validate required fields
        if not data.get('name') or not data.get('workspace_id'):
            return jsonify({'error': 'Name and workspace_id are required'}), 400
        
        project = {
            'name': data['name'],
            'description': data.get('description', ''),
            'workspace_id': data['workspace_id'],
            'created_by': user_id,
            'created_at': datetime.now(),
            'status': 'active'
        }
        
        result = db.projects.insert_one(project)
        project['_id'] = str(result.inserted_id)
        project['created_at'] = project['created_at'].isoformat()
        
        return jsonify(project), 201
        
    except Exception as e:
        print(f"Error creating project: {e}")
        return jsonify({'error': 'Failed to create project'}), 500

@project_bp.route('/<project_id>', methods=['GET'])
def get_project(project_id):
    """Get project details"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        project = db.projects.find_one({'_id': ObjectId(project_id)})
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        project['_id'] = str(project['_id'])
        project['workspace_id'] = str(project['workspace_id'])
        
        if 'created_at' in project:
            project['created_at'] = project['created_at'].isoformat()
        
        return jsonify(project), 200
        
    except Exception as e:
        print(f"Error getting project: {e}")
        return jsonify({'error': 'Failed to get project'}), 500

@project_bp.route('/<project_id>', methods=['PUT'])
def update_project(project_id):
    """Update project"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        update_data = {}
        if 'name' in data:
            update_data['name'] = data['name']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'status' in data:
            update_data['status'] = data['status']
        
        if update_data:
            db.projects.update_one(
                {'_id': ObjectId(project_id)},
                {'$set': update_data}
            )
        
        return jsonify({'message': 'Project updated successfully'}), 200
        
    except Exception as e:
        print(f"Error updating project: {e}")
        return jsonify({'error': 'Failed to update project'}), 500

@project_bp.route('/<project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete project"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        project = db.projects.find_one({'_id': ObjectId(project_id)})
        
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        db.projects.delete_one({'_id': ObjectId(project_id)})
        
        return jsonify({'message': 'Project deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting project: {e}")
        return jsonify({'error': 'Failed to delete project'}), 500
