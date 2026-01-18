from flask import Blueprint, request, jsonify
from utils.db import get_db
from bson import ObjectId
from datetime import datetime
import jwt
import os

kanban_bp = Blueprint('kanban', __name__)

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

@kanban_bp.route('/<workspace_id>', methods=['GET'])
def get_kanban(workspace_id):
    """Get kanban board for workspace"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        # Get all tasks for this workspace
        tasks = list(db.tasks.find({
            'workspace_id': workspace_id
        }).sort('created_at', -1))
        
        # Convert ObjectId to string
        for task in tasks:
            task['_id'] = str(task['_id'])
            if 'created_at' in task:
                task['created_at'] = task['created_at'].isoformat()
            if 'due_date' in task and task['due_date']:
                task['due_date'] = task['due_date'].isoformat()
        
        # Define board columns
        boards = [
            {'id': 'todo', 'title': 'To Do', 'color': 'bg-gray-100'},
            {'id': 'in_progress', 'title': 'In Progress', 'color': 'bg-blue-100'},
            {'id': 'review', 'title': 'Review', 'color': 'bg-yellow-100'},
            {'id': 'done', 'title': 'Done', 'color': 'bg-green-100'}
        ]
        
        return jsonify({
            'boards': boards,
            'tasks': tasks
        }), 200
        
    except Exception as e:
        print(f"Error getting kanban: {e}")
        return jsonify({'error': 'Failed to get kanban board'}), 500

@kanban_bp.route('/task', methods=['POST'])
def create_task():
    """Create a new task"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        if not data.get('title') or not data.get('workspace_id'):
            return jsonify({'error': 'Title and workspace_id are required'}), 400
        
        task = {
            'title': data['title'],
            'description': data.get('description', ''),
            'status': data.get('status', 'todo'),
            'priority': data.get('priority', 'medium'),
            'workspace_id': data['workspace_id'],
            'project_id': data.get('project_id'),
            'assigned_to': data.get('assigned_to', []),
            'created_by': user_id,
            'created_at': datetime.now(),
            'due_date': datetime.fromisoformat(data['due_date']) if data.get('due_date') else None
        }
        
        result = db.tasks.insert_one(task)
        task['_id'] = str(result.inserted_id)
        task['created_at'] = task['created_at'].isoformat()
        if task.get('due_date'):
            task['due_date'] = task['due_date'].isoformat()
        
        return jsonify(task), 201
        
    except Exception as e:
        print(f"Error creating task: {e}")
        return jsonify({'error': 'Failed to create task'}), 500

@kanban_bp.route('/task/<task_id>', methods=['PUT'])
def update_task(task_id):
    """Update a task"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        update_data = {}
        if 'title' in data:
            update_data['title'] = data['title']
        if 'description' in data:
            update_data['description'] = data['description']
        if 'status' in data:
            update_data['status'] = data['status']
        if 'priority' in data:
            update_data['priority'] = data['priority']
        if 'assigned_to' in data:
            update_data['assigned_to'] = data['assigned_to']
        if 'due_date' in data:
            update_data['due_date'] = datetime.fromisoformat(data['due_date']) if data['due_date'] else None
        
        if update_data:
            db.tasks.update_one(
                {'_id': ObjectId(task_id)},
                {'$set': update_data}
            )
        
        return jsonify({'message': 'Task updated successfully'}), 200
        
    except Exception as e:
        print(f"Error updating task: {e}")
        return jsonify({'error': 'Failed to update task'}), 500

@kanban_bp.route('/task/<task_id>/move', methods=['PUT'])
def move_task(task_id):
    """Move task to different column"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        if not data.get('status'):
            return jsonify({'error': 'Status is required'}), 400
        
        db.tasks.update_one(
            {'_id': ObjectId(task_id)},
            {'$set': {'status': data['status']}}
        )
        
        return jsonify({'message': 'Task moved successfully'}), 200
        
    except Exception as e:
        print(f"Error moving task: {e}")
        return jsonify({'error': 'Failed to move task'}), 500

@kanban_bp.route('/task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    """Delete a task"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        db.tasks.delete_one({'_id': ObjectId(task_id)})
        
        return jsonify({'message': 'Task deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting task: {e}")
        return jsonify({'error': 'Failed to delete task'}), 500

@kanban_bp.route('/my-tasks', methods=['GET'])
def get_my_tasks():
    """Get all tasks assigned to current user"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        # Get all tasks where user is assigned
        tasks = list(db.tasks.find({
            '$or': [
                {'assigned_to': user_id},
                {'assigned_to': {'$elemMatch': {'$eq': user_id}}}
            ]
        }).sort('created_at', -1).limit(50))
        
        # Convert ObjectId to string
        for task in tasks:
            task['_id'] = str(task['_id'])
            if 'workspace_id' in task:
                task['workspace_id'] = str(task['workspace_id'])
            if 'created_at' in task:
                task['created_at'] = task['created_at'].isoformat()
            if 'due_date' in task and task.get('due_date'):
                task['due_date'] = task['due_date'].isoformat()
        
        return jsonify({'tasks': tasks}), 200
        
    except Exception as e:
        print(f"Error getting my tasks: {e}")
        return jsonify({'error': 'Failed to get tasks'}), 500
