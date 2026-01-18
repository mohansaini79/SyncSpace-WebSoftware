import jwt
import os
from functools import wraps
from flask import request, jsonify
from bson import ObjectId
from utils.db import get_db

SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-change-this')

def token_required(f):
    '''Decorator to protect routes that require authentication'''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        # Get token from Authorization header
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]  # Bearer <token>
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401
        
        try:
            # Decode token
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            
            # Get user from database
            db = get_db()
            user = db.users.find_one({'_id': ObjectId(payload['user_id'])})
            
            if not user:
                return jsonify({'error': 'User not found'}), 401
            
            # Add user info to request
            request.user_id = str(user['_id'])
            request.user_email = user['email']
            request.user_role = user['role']
            request.user_name = user['name']
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            print(f"Token validation error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function

def generate_token(user_id, email, role, expiry_days=7):
    '''Generate JWT token for user'''
    from datetime import datetime, timedelta
    
    payload = {
        'user_id': str(user_id),
        'email': email,
        'role': role,
        'exp': datetime.now() + timedelta(days=expiry_days)
    }
    
    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')
    return token

def decode_token(token):
    '''Decode JWT token'''
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None

def admin_required(f):
    '''Decorator to protect routes that require admin access'''
    @wraps(f)
    def decorated_function(*args, **kwargs):
        token = None
        
        if 'Authorization' in request.headers:
            auth_header = request.headers['Authorization']
            try:
                token = auth_header.split(' ')[1]
            except IndexError:
                return jsonify({'error': 'Invalid token format'}), 401
        
        if not token:
            return jsonify({'error': 'Authentication token is missing'}), 401
        
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=['HS256'])
            
            db = get_db()
            user = db.users.find_one({'_id': ObjectId(payload['user_id'])})
            
            if not user:
                return jsonify({'error': 'User not found'}), 401
            
            if user['role'] != 'admin':
                return jsonify({'error': 'Admin access required'}), 403
            
            request.user_id = str(user['_id'])
            request.user_email = user['email']
            request.user_role = user['role']
            request.user_name = user['name']
            
        except jwt.ExpiredSignatureError:
            return jsonify({'error': 'Token has expired'}), 401
        except jwt.InvalidTokenError:
            return jsonify({'error': 'Invalid token'}), 401
        except Exception as e:
            print(f"Token validation error: {e}")
            return jsonify({'error': 'Authentication failed'}), 401
        
        return f(*args, **kwargs)
    
    return decorated_function
