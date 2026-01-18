from flask import Blueprint, request, jsonify
from utils.db import get_db
from bson import ObjectId
from datetime import datetime
import jwt
import os

notification_bp = Blueprint('notification', __name__)

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

@notification_bp.route('/', methods=['GET'])
def get_notifications():
    """Get user notifications"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        # Get all notifications for user
        notifications = list(db.notifications.find(
            {'user_id': user_id}
        ).sort('created_at', -1).limit(50))
        
        # Count unread notifications
        unread_count = db.notifications.count_documents({
            'user_id': user_id,
            'read': False
        })
        
        # Convert ObjectId to string
        for notif in notifications:
            notif['_id'] = str(notif['_id'])
            if 'created_at' in notif:
                notif['created_at'] = notif['created_at'].isoformat()
        
        return jsonify({
            'notifications': notifications,
            'unread_count': unread_count
        }), 200
        
    except Exception as e:
        print(f"Error getting notifications: {e}")
        return jsonify({'error': 'Failed to get notifications'}), 500

@notification_bp.route('/read', methods=['PUT'])
def mark_notifications_read():
    """Mark all notifications as read"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        db.notifications.update_many(
            {'user_id': user_id, 'read': False},
            {'$set': {'read': True}}
        )
        
        return jsonify({'message': 'Notifications marked as read'}), 200
        
    except Exception as e:
        print(f"Error marking notifications as read: {e}")
        return jsonify({'error': 'Failed to mark notifications as read'}), 500

@notification_bp.route('/', methods=['DELETE'])
def clear_notifications():
    """Clear all notifications"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        db = get_db()
        
        db.notifications.delete_many({'user_id': user_id})
        
        return jsonify({'message': 'Notifications cleared'}), 200
        
    except Exception as e:
        print(f"Error clearing notifications: {e}")
        return jsonify({'error': 'Failed to clear notifications'}), 500

@notification_bp.route('/create', methods=['POST'])
def create_notification():
    """Create a new notification"""
    user_id = verify_token()
    if not user_id:
        return jsonify({'error': 'Unauthorized'}), 401
    
    try:
        data = request.get_json()
        db = get_db()
        
        notification = {
            'user_id': data.get('target_user_id'),
            'message': data.get('message'),
            'type': data.get('type', 'info'),
            'read': False,
            'created_at': datetime.now()
        }
        
        if data.get('workspace_id'):
            notification['workspace_id'] = data.get('workspace_id')
        
        result = db.notifications.insert_one(notification)
        
        return jsonify({
            'message': 'Notification created',
            'notification_id': str(result.inserted_id)
        }), 201
        
    except Exception as e:
        print(f"Error creating notification: {e}")
        return jsonify({'error': 'Failed to create notification'}), 500
