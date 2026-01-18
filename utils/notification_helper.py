from datetime import datetime
from utils.db import get_db

def notify_workspace_members(workspace_id, message, notification_type='info', exclude_user_id=None):
    '''Send notification to all workspace members'''
    db = get_db()
    
    try:
        from bson import ObjectId
        
        # Get workspace members
        workspace = db.workspaces.find_one({'_id': ObjectId(workspace_id)})
        
        if not workspace:
            return
        
        members = workspace.get('members', [])
        
        # Create notifications for each member
        for member in members:
            user_id = member['user_id']
            
            # Skip excluded user (usually the one who triggered the action)
            if user_id == exclude_user_id:
                continue
            
            notification = {
                'user_id': user_id,
                'message': message,
                'type': notification_type,
                'workspace_id': workspace_id,
                'read': False,
                'created_at': datetime.utcnow()
            }
            
            db.notifications.insert_one(notification)
        
        return True
        
    except Exception as e:
        print(f'Error sending notifications: {e}')
        return False

def notify_user(user_id, message, notification_type='info', workspace_id=None):
    '''Send notification to a specific user'''
    db = get_db()
    
    try:
        notification = {
            'user_id': user_id,
            'message': message,
            'type': notification_type,
            'workspace_id': workspace_id,
            'read': False,
            'created_at': datetime.utcnow()
        }
        
        db.notifications.insert_one(notification)
        return True
        
    except Exception as e:
        print(f'Error sending notification: {e}')
        return False

def clear_old_notifications(days=30):
    '''Clear notifications older than specified days'''
    db = get_db()
    
    try:
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        result = db.notifications.delete_many({
            'created_at': {'$lt': cutoff_date}
        })
        
        print(f'✓ Cleared {result.deleted_count} old notifications')
        return result.deleted_count
        
    except Exception as e:
        print(f'Error clearing notifications: {e}')
        return 0
