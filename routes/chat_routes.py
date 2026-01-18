from flask import Blueprint, request, jsonify
from utils.db import get_db
from bson import ObjectId
from datetime import datetime
import jwt
import os

chat_bp = Blueprint('chat', __name__)

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

@chat_bp.route('/<workspace_id>/messages', methods=['GET'])
def get_messages(workspace_id):
    """Get chat messages for a workspace"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        # Get last 100 messages
        messages = list(db.chat_messages.find({
            'workspace_id': workspace_id
        }).sort('timestamp', -1).limit(100))
        
        # Reverse to show oldest first
        messages.reverse()
        
        # Convert ObjectId to string
        for msg in messages:
            msg['_id'] = str(msg['_id'])
            if 'timestamp' in msg:
                msg['timestamp'] = msg['timestamp'].isoformat()
        
        return jsonify(messages), 200
        
    except Exception as e:
        print(f"Error getting messages: {e}")
        return jsonify({'error': 'Failed to get messages'}), 500

@chat_bp.route('/message', methods=['POST'])
def send_message():
    """Send a chat message"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        if not data.get('workspace_id') or not data.get('message'):
            return jsonify({'error': 'workspace_id and message are required'}), 400
        
        message = {
            'workspace_id': data['workspace_id'],
            'user_id': user_id,
            'username': data.get('username', 'Unknown'),
            'message': data['message'],
            'timestamp': datetime.now()
        }
        
        result = db.chat_messages.insert_one(message)
        message['_id'] = str(result.inserted_id)
        message['timestamp'] = message['timestamp'].isoformat()
        
        return jsonify(message), 201
        
    except Exception as e:
        print(f"Error sending message: {e}")
        return jsonify({'error': 'Failed to send message'}), 500

@chat_bp.route('/message/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    """Delete a chat message"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        message = db.chat_messages.find_one({'_id': ObjectId(message_id)})
        
        if not message:
            return jsonify({'error': 'Message not found'}), 404
        
        # Check if user is the sender
        if message.get('user_id') != user_id:
            return jsonify({'error': 'Permission denied'}), 403
        
        db.chat_messages.delete_one({'_id': ObjectId(message_id)})
        
        return jsonify({'message': 'Message deleted successfully'}), 200
        
    except Exception as e:
        print(f"Error deleting message: {e}")
        return jsonify({'error': 'Failed to delete message'}), 500
