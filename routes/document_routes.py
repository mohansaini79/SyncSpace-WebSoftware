from flask import Blueprint, request, jsonify
from utils.db import get_db
from bson import ObjectId
from datetime import datetime
import jwt
import os

document_bp = Blueprint('document', __name__)

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

@document_bp.route('/create', methods=['POST'])
def create_document():
    """Create a new document"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        if not data.get('title') or not data.get('workspace_id'):
            return jsonify({'error': 'Title and workspace_id are required'}), 400
        
        document = {
            'title': data['title'],
            'content': data.get('content', ''),
            'workspace_id': data['workspace_id'],
            'created_by': user_id,
            'created_at': datetime.now(),
            'updated_at': datetime.now(),
            'active_users': []
        }
        
        result = db.documents.insert_one(document)
        document['_id'] = str(result.inserted_id)
        document['created_at'] = document['created_at'].isoformat()
        document['updated_at'] = document['updated_at'].isoformat()
        
        return jsonify(document), 201
        
    except Exception as e:
        print(f"Error creating document: {e}")
        return jsonify({'error': 'Failed to create document'}), 500

@document_bp.route('/<document_id>', methods=['GET'])
def get_document(document_id):
    """Get document by ID"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        document = db.documents.find_one({'_id': ObjectId(document_id)})
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        document['_id'] = str(document['_id'])
        if 'created_at' in document:
            document['created_at'] = document['created_at'].isoformat()
        if 'updated_at' in document:
            document['updated_at'] = document['updated_at'].isoformat()
        
        return jsonify(document), 200
        
    except Exception as e:
        print(f"Error getting document: {e}")
        return jsonify({'error': 'Failed to get document'}), 500

@document_bp.route('/<document_id>', methods=['PUT'])
def update_document(document_id):
    """Update document content"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        update_data = {'updated_at': datetime.now()}
        
        if 'title' in data:
            update_data['title'] = data['title']
        if 'content' in data:
            update_data['content'] = data['content']
        
        db.documents.update_one(
            {'_id': ObjectId(document_id)},
            {'$set': update_data}
        )
        
        return jsonify({'message': 'Document updated successfully'}), 200
        
    except Exception as e:
        print(f"Error updating document: {e}")
        return jsonify({'error': 'Failed to update document'}), 500

@document_bp.route('/<document_id>', methods=['DELETE'])
def delete_document(document_id):
    """Delete document"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        document = db.documents.find_one({'_id': ObjectId(document_id)})
        
        if not document:
            return jsonify({'error': 'Document not found'}), 404
        
        # Check if user is the creator
        if document.get('created_by') != user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        db.documents.delete_one({'_id': ObjectId(document_id)})
        
        return jsonify({'message': 'Document deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting document: {e}")
        return jsonify({'error': 'Failed to delete document'}), 500

@document_bp.route('/workspace/<workspace_id>', methods=['GET'])
def get_workspace_documents(workspace_id):
    """Get all documents in a workspace"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        documents = list(db.documents.find({
            'workspace_id': workspace_id
        }).sort('updated_at', -1))
        
        # Convert ObjectId to string
        for doc in documents:
            doc['_id'] = str(doc['_id'])
            if 'created_at' in doc:
                doc['created_at'] = doc['created_at'].isoformat()
            if 'updated_at' in doc:
                doc['updated_at'] = doc['updated_at'].isoformat()
        
        return jsonify(documents), 200
        
    except Exception as e:
        print(f"Error getting documents: {e}")
        return jsonify({'error': 'Failed to get documents'}), 500
