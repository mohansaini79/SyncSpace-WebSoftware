# Use eventlet for better WebSocket support


from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from dotenv import load_dotenv
import os
from datetime import datetime
from bson import ObjectId
import cloudinary
import cloudinary.uploader

# Load environment variables FIRST
load_dotenv()

# Initialize database connection
from utils.db import init_db, get_db

MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/syncspace')

# Try to initialize database (will work even if already initialized)
try:
    init_db(MONGO_URI)
    db = get_db()
    print("✓ Database ready")
except RuntimeError:
    db = get_db()
    print("✓ Database already initialized")
except Exception as e:
    print(f"✗ Database error: {e}")
    db = None

# Import routes after DB init
from routes.auth_routes import auth_bp
from routes.workspace_routes import workspace_bp
from routes.project_routes import project_bp
from routes.kanban_routes import kanban_bp
from routes.document_routes import document_bp
from routes.chat_routes import chat_bp
from routes.file_routes import file_bp
from routes.notification_routes import notification_bp

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'your-secret-key-change-this')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Configure Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME', ''),
    api_key=os.getenv('CLOUDINARY_API_KEY', ''),
    api_secret=os.getenv('CLOUDINARY_API_SECRET', '')
)

# Initialize extensions
CORS(app, resources={r"/*": {"origins": "*"}})

# Initialize Socket.IO with eventlet (FIXED)
socketio = SocketIO(
    app, 
    cors_allowed_origins="*",
    async_mode='threading',
    logger=False,
    engineio_logger=False,
    ping_timeout=60,
    ping_interval=25
)

# Register ALL blueprints
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(workspace_bp, url_prefix='/api/workspace')
app.register_blueprint(project_bp, url_prefix='/api/project')
app.register_blueprint(kanban_bp, url_prefix='/api/kanban')
app.register_blueprint(document_bp, url_prefix='/api/document')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(file_bp, url_prefix='/api/files')
app.register_blueprint(notification_bp, url_prefix='/api/notifications')

# Store active users
active_users = {}

# ==================== HTML ROUTES ====================

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/workspace/<workspace_id>')
def workspace(workspace_id):
    return render_template('workspace.html', workspace_id=workspace_id)

@app.route('/document/<document_id>')
def document_page(document_id):
    return render_template('document_editor.html', document_id=document_id)

@app.route('/login')
def login():
    return render_template('login.html')

@app.route('/register')
def register():
    return render_template('register.html')

# ==================== SOCKET.IO EVENTS ====================

@socketio.on('connect')
def handle_connect():
    '''Handle client connection'''
    print(f'✓ Client connected: {request.sid}')
    emit('connected', {'data': 'Connected to SyncSpace', 'sid': request.sid})

@socketio.on('disconnect')
def handle_disconnect():
    '''Handle client disconnection'''
    print(f'✗ Client disconnected: {request.sid}')
    
    for workspace_id, users in list(active_users.items()):
        if request.sid in users:
            user_info = users.pop(request.sid)
            emit('user_left', {
                'username': user_info.get('username'),
                'workspace_id': workspace_id
            }, room=workspace_id)
            
            emit('user_presence', {
                'online_count': len(users),
                'users': list(users.values())
            }, room=workspace_id)

@socketio.on('user_online')
def handle_user_online(data):
    '''User came online'''
    user_id = data.get('user_id')
    username = data.get('username')
    
    if user_id:
        try:
            db = get_db()
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'status': 'online', 'last_seen': datetime.now()}}
            )
        except Exception as e:
            print(f"Error updating user status: {e}")
    
    print(f'✓ User online: {username}')

@socketio.on('user_offline')
def handle_user_offline(data):
    '''User went offline'''
    user_id = data.get('user_id')
    
    if user_id:
        try:
            db = get_db()
            db.users.update_one(
                {'_id': ObjectId(user_id)},
                {'$set': {'status': 'offline', 'last_seen': datetime.now()}}
            )
        except Exception as e:
            print(f"Error updating user status: {e}")

@socketio.on('join_workspace')
def handle_join_workspace(data):
    '''User joins a workspace room'''
    workspace_id = data.get('workspace_id')
    username = data.get('username')
    user_id = data.get('user_id', request.sid)
    
    join_room(workspace_id)
    
    if workspace_id not in active_users:
        active_users[workspace_id] = {}
    
    active_users[workspace_id][request.sid] = {
        'user_id': user_id,
        'username': username,
        'joined_at': datetime.now().isoformat()
    }
    
    emit('user_joined', {
        'username': username,
        'message': f'{username} joined the workspace'
    }, room=workspace_id)
    
    emit('user_presence', {
        'online_count': len(active_users[workspace_id]),
        'users': list(active_users[workspace_id].values())
    }, room=workspace_id)
    
    print(f'✓ {username} joined workspace {workspace_id}')

@socketio.on('leave_workspace')
def handle_leave_workspace(data):
    '''User leaves a workspace room'''
    workspace_id = data.get('workspace_id')
    username = data.get('username')
    
    leave_room(workspace_id)
    
    if workspace_id in active_users and request.sid in active_users[workspace_id]:
        active_users[workspace_id].pop(request.sid)
    
    emit('user_left', {
        'username': username
    }, room=workspace_id)
    
    if workspace_id in active_users:
        emit('user_presence', {
            'online_count': len(active_users[workspace_id]),
            'users': list(active_users[workspace_id].values())
        }, room=workspace_id)

@socketio.on('join_document')
def handle_join_document(data):
    '''User joins a document editing session'''
    document_id = data.get('document_id')
    user_id = data.get('user_id')
    username = data.get('username')
    
    join_room(document_id)
    
    try:
        db = get_db()
        db.documents.update_one(
            {'_id': ObjectId(document_id)},
            {'$addToSet': {'active_users': {'user_id': user_id, 'username': username}}}
        )
    except Exception as e:
        print(f"Error updating document: {e}")
    
    emit('user_joined_document', {
        'username': username
    }, room=document_id)
    
    print(f'✓ {username} joined document {document_id}')

@socketio.on('leave_document')
def handle_leave_document(data):
    '''User leaves document editing session'''
    document_id = data.get('document_id')
    user_id = data.get('user_id')
    username = data.get('username')
    
    leave_room(document_id)
    
    try:
        db = get_db()
        db.documents.update_one(
            {'_id': ObjectId(document_id)},
            {'$pull': {'active_users': {'user_id': user_id}}}
        )
    except Exception as e:
        print(f"Error updating document: {e}")
    
    emit('user_left_document', {
        'username': username
    }, room=document_id)

@socketio.on('document_typing')
def handle_document_typing(data):
    '''Handle typing indicator in document'''
    document_id = data.get('document_id')
    username = data.get('username')
    
    emit('user_typing_document', {
        'username': username,
        'typing': True
    }, room=document_id, include_self=False)

@socketio.on('document_stop_typing')
def handle_document_stop_typing(data):
    '''Handle stop typing in document'''
    document_id = data.get('document_id')
    username = data.get('username')
    
    emit('user_typing_document', {
        'username': username,
        'typing': False
    }, room=document_id, include_self=False)

@socketio.on('document_content_change')
def handle_document_content_change(data):
    '''Handle real-time document content changes'''
    document_id = data.get('document_id')
    content = data.get('content')
    username = data.get('username')
    user_id = data.get('user_id')
    
    emit('document_updated', {
        'content': content,
        'username': username,
        'user_id': user_id,
        'timestamp': datetime.now().isoformat()
    }, room=document_id, include_self=False)

@socketio.on('document_cursor_position')
def handle_document_cursor_position(data):
    '''Handle cursor position in collaborative editing'''
    document_id = data.get('document_id')
    user_id = data.get('user_id')
    username = data.get('username')
    position = data.get('position')
    
    emit('cursor_position_update', {
        'user_id': user_id,
        'username': username,
        'position': position
    }, room=document_id, include_self=False)

@socketio.on('kanban_update')
def handle_kanban_update(data):
    '''Handle kanban board updates'''
    workspace_id = data.get('workspace_id')
    
    emit('kanban_changed', {
        'workspace_id': workspace_id,
        'timestamp': datetime.now().isoformat()
    }, room=workspace_id, include_self=False)

@socketio.on('chat_message')
def handle_chat_message(data):
    '''Handle chat messages'''
    workspace_id = data.get('workspace_id')
    user_id = data.get('user_id')
    username = data.get('username')
    message = data.get('message')
    
    timestamp = datetime.now()
    
    try:
        db = get_db()
        db.chat_messages.insert_one({
            'workspace_id': workspace_id,
            'user_id': user_id,
            'username': username,
            'message': message,
            'timestamp': timestamp
        })
    except Exception as e:
        print(f"Error saving message: {e}")
    
    emit('new_message', {
        'username': username,
        'user_id': user_id,
        'message': message,
        'timestamp': timestamp.isoformat()
    }, room=workspace_id)
    
    if '@' in message:
        words = message.split()
        for word in words:
            if word.startswith('@'):
                mentioned_username = word[1:]
                try:
                    db = get_db()
                    mentioned_user = db.users.find_one({'name': mentioned_username})
                    if mentioned_user:
                        db.notifications.insert_one({
                            'user_id': str(mentioned_user['_id']),
                            'message': f'{username} mentioned you in chat',
                            'type': 'mention',
                            'workspace_id': workspace_id,
                            'read': False,
                            'created_at': datetime.now()
                        })
                        
                        emit('live_notification', {
                            'message': f'{username} mentioned you in chat',
                            'type': 'mention'
                        }, room=f"user_{str(mentioned_user['_id'])}")
                except Exception as e:
                    print(f"Error handling mention: {e}")

@socketio.on('typing_start')
def handle_typing_start(data):
    '''Handle typing indicator start'''
    workspace_id = data.get('workspace_id')
    username = data.get('username')
    
    emit('user_typing', {
        'username': username,
        'typing': True
    }, room=workspace_id, include_self=False)

@socketio.on('typing_stop')
def handle_typing_stop(data):
    '''Handle typing indicator stop'''
    workspace_id = data.get('workspace_id')
    username = data.get('username')
    
    emit('user_typing', {
        'username': username,
        'typing': False
    }, room=workspace_id, include_self=False)

@socketio.on('task_assigned')
def handle_task_assigned(data):
    '''Handle task assignment notifications'''
    assigned_to = data.get('assigned_to')
    task_title = data.get('task_title')
    assigned_by = data.get('assigned_by')
    
    if not assigned_to:
        return
    
    try:
        db = get_db()
        db.notifications.insert_one({
            'user_id': assigned_to,
            'message': f'{assigned_by} assigned you to task: {task_title}',
            'type': 'task_assignment',
            'read': False,
            'created_at': datetime.now()
        })
    except Exception as e:
        print(f"Error creating notification: {e}")
    
    emit('live_notification', {
        'message': f'{assigned_by} assigned you to task: {task_title}',
        'type': 'task_assignment',
        'timestamp': datetime.now().isoformat()
    }, room=f'user_{assigned_to}')
    
    print(f'✓ Task assigned: {task_title} → {assigned_to}')

@socketio.on('subscribe_notifications')
def handle_subscribe_notifications(data):
    '''Subscribe user to their notification room'''
    user_id = data.get('user_id')
    if user_id:
        join_room(f'user_{user_id}')
        print(f'✓ User {user_id} subscribed to notifications')
        emit('notifications_subscribed', {'status': 'success'})

@socketio.on('unsubscribe_notifications')
def handle_unsubscribe_notifications(data):
    '''Unsubscribe user from notification room'''
    user_id = data.get('user_id')
    if user_id:
        leave_room(f'user_{user_id}')
        print(f'✗ User {user_id} unsubscribed from notifications')

# ==================== ERROR HANDLERS ====================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({'error': 'File size exceeds 16MB limit'}), 413

# ==================== HEALTH CHECK ====================

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat()
    }), 200

# ==================== MAIN ====================

if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    
    # Check if running in production (Render sets RENDER env variable)
    is_production = os.getenv('RENDER') is not None
    debug_mode = not is_production
    
    print(f"\n{'='*60}")
    print(f"🚀 SyncSpace Server Starting...")
    print(f"{'='*60}")
    print(f"📍 Port: {port}")
    print(f"🔌 Socket.IO: Enabled (threading mode)")  # Changed from eventlet
    print(f"☁️  Cloudinary: Configured")
    print(f"🗄️  MongoDB Atlas: Connected")
    print(f"🐍 Python Version: 3.13")
    print(f"🌍 Environment: {'Production' if is_production else 'Development'}")
    print(f"🐛 Debug Mode: {'OFF' if is_production else 'ON'}")
    print(f"{'='*60}\n")
    
    socketio.run(
        app, 
        host='0.0.0.0', 
        port=port, 
        debug=debug_mode,
        use_reloader=False,  # Important for production
        log_output=True
    )
