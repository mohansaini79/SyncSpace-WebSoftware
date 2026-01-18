from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError, ConnectionFailure, ConfigurationError
import os
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Global database connection
_db = None
_client = None


def init_db(mongo_uri=None, max_retries=3, retry_delay=2):
    """
    Initialize database connection with retry logic
    """
    global _db, _client
    
    if _db is not None:
        return _db
    
    # Get MongoDB URI from environment or parameter
    if mongo_uri is None:
        mongo_uri = os.getenv('MONGO_URI', 'mongodb://localhost:27017/syncspace')
    
    # SIMPLIFIED FIX: Just use 'syncspace' as database name
    # Don't try to parse it from URI - it's unreliable
    db_name = 'syncspace'
    
    print(f"📂 Using database: {db_name}")
    
    # Connection with retry logic
    for attempt in range(max_retries):
        try:
            print(f"🔄 Connecting to MongoDB (Attempt {attempt + 1}/{max_retries})...")
            
            # Create MongoDB client with production-ready settings
            _client = MongoClient(
                mongo_uri,
                serverSelectionTimeoutMS=10000,
                connectTimeoutMS=10000,
                socketTimeoutMS=10000,
                maxPoolSize=50,
                minPoolSize=10,
                retryWrites=True,
                retryReads=True,
                w='majority',
                journal=True
            )
            
            # Test connection
            _client.admin.command('ping')
            
            # Get database instance - ALWAYS use 'syncspace'
            _db = _client[db_name]
            
            print(f"✅ MongoDB connected successfully!")
            print(f"📂 Database: {db_name}")
            print(f"🌍 Server: MongoDB Atlas")
            
            # Create indexes for performance
            try:
                create_indexes()
            except Exception as idx_error:
                print(f"⚠️ Index creation warning: {idx_error}")
            
            return _db
            
        except (ServerSelectionTimeoutError, ConnectionFailure) as e:
            if attempt < max_retries - 1:
                print(f"⚠️ Connection attempt {attempt + 1} failed. Retrying in {retry_delay}s...")
                time.sleep(retry_delay)
            else:
                print(f"❌ Failed to connect to MongoDB after {max_retries} attempts")
                print(f"❌ Error: {str(e)}")
                raise ConnectionError(f"Could not connect to MongoDB: {str(e)}")
        
        except ConfigurationError as e:
            print(f"❌ MongoDB configuration error: {str(e)}")
            raise ConfigurationError(f"Invalid MongoDB URI or configuration: {str(e)}")
        
        except Exception as e:
            print(f"❌ Unexpected database error: {str(e)}")
            raise RuntimeError(f"Database initialization failed: {str(e)}")
    
    return None


def get_db():
    """Get database instance (lazy initialization)"""
    global _db
    
    if _db is None:
        try:
            return init_db()
        except Exception as e:
            print(f"❌ Error getting database: {str(e)}")
            raise RuntimeError(f"Database not initialized. Error: {str(e)}")
    
    return _db


def close_db():
    """Close database connection gracefully"""
    global _db, _client
    
    if _client is not None:
        try:
            _client.close()
            _db = None
            _client = None
            print("✅ Database connection closed successfully")
        except Exception as e:
            print(f"⚠️ Error closing database: {str(e)}")


def check_connection():
    """Check if database connection is alive"""
    global _client
    
    if _client is None:
        return False
    
    try:
        _client.admin.command('ping')
        return True
    except Exception:
        return False


def reconnect():
    """Reconnect to database"""
    global _db, _client
    
    print("🔄 Reconnecting to database...")
    close_db()
    _db = None
    _client = None
    return init_db()


def create_indexes():
    """Create database indexes for performance optimization"""
    global _db
    
    if _db is None:
        return
    
    try:
        # Users collection indexes
        _db.users.create_index('email', unique=True)
        _db.users.create_index('created_at')
        
        # Workspaces collection indexes
        _db.workspaces.create_index('created_by')
        _db.workspaces.create_index('members.user_id')
        _db.workspaces.create_index('created_at')
        
        # Tasks collection indexes
        _db.tasks.create_index('workspace_id')
        _db.tasks.create_index('project_id')
        _db.tasks.create_index('assigned_to')
        _db.tasks.create_index([('workspace_id', 1), ('status', 1)])
        
        # Documents collection indexes
        _db.documents.create_index('workspace_id')
        _db.documents.create_index('created_by')
        _db.documents.create_index('updated_at')
        
        # Messages collection indexes
        _db.messages.create_index('workspace_id')
        _db.messages.create_index([('workspace_id', 1), ('created_at', -1)])
        
        # Files collection indexes
        _db.files.create_index('workspace_id')
        _db.files.create_index('uploaded_by')
        _db.files.create_index('created_at')
        
        # Notifications collection indexes
        _db.notifications.create_index('user_id')
        _db.notifications.create_index([('user_id', 1), ('read', 1)])
        _db.notifications.create_index('created_at')
        
        print("✅ Database indexes created successfully")
        
    except Exception as e:
        print(f"⚠️ Index creation warning: {str(e)}")


def get_stats():
    """Get database statistics"""
    global _db, _client
    
    if _db is None or _client is None:
        return {"error": "Database not connected"}
    
    try:
        stats = {
            "connected": check_connection(),
            "database": _db.name,
            "collections": _db.list_collection_names(),
            "server_info": _client.server_info()
        }
        return stats
    except Exception as e:
        return {"error": str(e)}
