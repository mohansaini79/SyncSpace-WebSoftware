from flask import Blueprint, request, jsonify
from bson import ObjectId
from datetime import datetime
from utils.db import get_db
from functools import wraps
import jwt
import os

workspace_bp = Blueprint('workspace', __name__)

def verify_token():
    """Verify JWT token from request"""
    token = request.headers.get('Authorization')
    if not token:
        return None
    
    try:
        token = token.replace('Bearer ', '')
        decoded = jwt.decode(token, os.getenv('SECRET_KEY'), algorithms=['HS256'])
        return decoded['user_id']
    except:
        return None

@workspace_bp.route('/list', methods=['GET'])
def list_workspaces():
    """Get all workspaces for current user"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        # Find workspaces where user is a member
        workspaces = list(db.workspaces.find({
            'members.user_id': current_user_id
        }))
        
        # Convert ObjectId to string
        for workspace in workspaces:
            workspace['_id'] = str(workspace['_id'])
        
        return jsonify({'workspaces': workspaces}), 200
        
    except Exception as e:
        print(f"Error listing workspaces: {e}")
        return jsonify({'error': 'Failed to list workspaces'}), 500

@workspace_bp.route('/create', methods=['POST'])
def create_workspace():
    """Create new workspace"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        name = data.get('name')
        description = data.get('description', '')
        
        if not name:
            return jsonify({'error': 'Workspace name is required'}), 400
        
        db = get_db()
        
        # Get user info
        user = db.users.find_one({'_id': ObjectId(current_user_id)})
        
        workspace = {
            'name': name,
            'description': description,
            'created_by': current_user_id,
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow(),
            'members': [
                {
                    'user_id': current_user_id,
                    'email': user.get('email', ''),
                    'name': user.get('name', ''),
                    'role': 'owner',
                    'joined_at': datetime.utcnow()
                }
            ]
        }
        
        result = db.workspaces.insert_one(workspace)
        workspace['_id'] = str(result.inserted_id)
        
        return jsonify(workspace), 201
        
    except Exception as e:
        print(f"Error creating workspace: {e}")
        return jsonify({'error': 'Failed to create workspace'}), 500

@workspace_bp.route('/<workspace_id>', methods=['GET'])
def get_workspace(workspace_id):
    """Get workspace details"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'members.user_id': current_user_id
        })
        
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        workspace['_id'] = str(workspace['_id'])
        
        return jsonify(workspace), 200
        
    except Exception as e:
        print(f"Error getting workspace: {e}")
        return jsonify({'error': 'Failed to get workspace'}), 500

@workspace_bp.route('/<workspace_id>', methods=['PUT'])
def update_workspace(workspace_id):
    """Update workspace details"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        # Check if user has permission (owner or admin)
        workspace = db.workspaces.find_one({'_id': ObjectId(workspace_id)})
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        user_role = None
        for member in workspace.get('members', []):
            if member['user_id'] == current_user_id:
                user_role = member['role']
                break
        
        if user_role not in ['owner', 'admin']:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Update workspace
        update_data = {
            'updated_at': datetime.utcnow()
        }
        
        if 'name' in data:
            update_data['name'] = data['name']
        if 'description' in data:
            update_data['description'] = data['description']
        
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {'$set': update_data}
        )
        
        return jsonify({'message': 'Workspace updated successfully'}), 200
        
    except Exception as e:
        print(f"Error updating workspace: {e}")
        return jsonify({'error': 'Failed to update workspace'}), 500

@workspace_bp.route('/<workspace_id>', methods=['DELETE'])
def delete_workspace(workspace_id):
    """Delete workspace"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        workspace = db.workspaces.find_one({'_id': ObjectId(workspace_id)})
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        # Only owner can delete
        if workspace['created_by'] != current_user_id:
            return jsonify({'error': 'Only workspace owner can delete'}), 403
        
        # Delete workspace and all related data
        db.workspaces.delete_one({'_id': ObjectId(workspace_id)})
        db.projects.delete_many({'workspace_id': workspace_id})
        db.tasks.delete_many({'workspace_id': workspace_id})
        db.documents.delete_many({'workspace_id': workspace_id})
        db.messages.delete_many({'workspace_id': workspace_id})
        db.files.delete_many({'workspace_id': workspace_id})
        
        return jsonify({'message': 'Workspace deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting workspace: {e}")
        return jsonify({'error': 'Failed to delete workspace'}), 500

# ==================== MEMBER MANAGEMENT ====================

@workspace_bp.route('/<workspace_id>/members', methods=['POST'])
def add_member(workspace_id):
    """Add member to workspace"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        email = data.get('email')
        role = data.get('role', 'member')
        
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        
        if role not in ['member', 'admin']:
            return jsonify({'error': 'Invalid role'}), 400
        
        db = get_db()
        
        # Check if workspace exists and user has permission
        workspace = db.workspaces.find_one({'_id': ObjectId(workspace_id)})
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        # Check if current user is owner or admin
        user_role = None
        for member in workspace.get('members', []):
            if member['user_id'] == current_user_id:
                user_role = member['role']
                break
        
        if user_role not in ['owner', 'admin']:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Find user by email
        new_user = db.users.find_one({'email': email})
        if not new_user:
            return jsonify({'error': 'User not found with this email'}), 404
        
        new_user_id = str(new_user['_id'])
        
        # Check if user is already a member
        for member in workspace.get('members', []):
            if member['user_id'] == new_user_id:
                return jsonify({'error': 'User is already a member'}), 400
        
        # Add member
        new_member = {
            'user_id': new_user_id,
            'email': email,
            'name': new_user.get('name', ''),
            'role': role,
            'joined_at': datetime.utcnow()
        }
        
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {
                '$push': {'members': new_member},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        return jsonify({
            'message': 'Member added successfully',
            'member': new_member
        }), 200
        
    except Exception as e:
        print(f"Error adding member: {e}")
        return jsonify({'error': 'Failed to add member'}), 500

@workspace_bp.route('/<workspace_id>/members/<user_id>', methods=['DELETE'])
def remove_member(workspace_id, user_id):
    """Remove member from workspace"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        workspace = db.workspaces.find_one({'_id': ObjectId(workspace_id)})
        
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        # Check if user has permission
        user_role = None
        for member in workspace.get('members', []):
            if member['user_id'] == current_user_id:
                user_role = member['role']
                break
        
        if user_role not in ['owner', 'admin']:
            return jsonify({'error': 'Permission denied'}), 403
        
        # Cannot remove owner
        target_member = None
        for member in workspace.get('members', []):
            if member['user_id'] == user_id:
                target_member = member
                break
        
        if not target_member:
            return jsonify({'error': 'Member not found'}), 404
        
        if target_member['role'] == 'owner':
            return jsonify({'error': 'Cannot remove workspace owner'}), 400
        
        # Admins cannot remove other admins unless they are owner
        if target_member['role'] == 'admin' and user_role != 'owner':
            return jsonify({'error': 'Only owner can remove admins'}), 403
        
        # Remove member
        db.workspaces.update_one(
            {'_id': ObjectId(workspace_id)},
            {
                '$pull': {'members': {'user_id': user_id}},
                '$set': {'updated_at': datetime.utcnow()}
            }
        )
        
        return jsonify({'message': 'Member removed successfully'}), 200
        
    except Exception as e:
        print(f"Error removing member: {e}")
        return jsonify({'error': 'Failed to remove member'}), 500

@workspace_bp.route('/<workspace_id>/members/<user_id>/role', methods=['PUT'])
def update_member_role(workspace_id, user_id):
    """Update member role"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        new_role = data.get('role')
        
        if new_role not in ['member', 'admin']:
            return jsonify({'error': 'Invalid role'}), 400
        
        db = get_db()
        
        workspace = db.workspaces.find_one({'_id': ObjectId(workspace_id)})
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        # Only owner can change roles
        if workspace['created_by'] != current_user_id:
            return jsonify({'error': 'Only workspace owner can change roles'}), 403
        
        # Cannot change owner role
        for member in workspace.get('members', []):
            if member['user_id'] == user_id and member['role'] == 'owner':
                return jsonify({'error': 'Cannot change owner role'}), 400
        
        # Update role
        db.workspaces.update_one(
            {
                '_id': ObjectId(workspace_id),
                'members.user_id': user_id
            },
            {
                '$set': {
                    'members.$.role': new_role,
                    'updated_at': datetime.utcnow()
                }
            }
        )
        
        return jsonify({'message': 'Member role updated successfully'}), 200
        
    except Exception as e:
        print(f"Error updating member role: {e}")
        return jsonify({'error': 'Failed to update member role'}), 500

@workspace_bp.route('/<workspace_id>/members', methods=['GET'])
def get_members(workspace_id):
    """Get all workspace members"""
    current_user_id = verify_token()
    if not current_user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        workspace = db.workspaces.find_one({
            '_id': ObjectId(workspace_id),
            'members.user_id': current_user_id
        })
        
        if not workspace:
            return jsonify({'error': 'Workspace not found'}), 404
        
        members = workspace.get('members', [])
        
        return jsonify({'members': members}), 200
        
    except Exception as e:
        print(f"Error getting members: {e}")
        return jsonify({'error': 'Failed to get members'}), 500
