import re
import bleach

def validate_email(email):
    '''Validate email format'''
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def sanitize_input(text):
    '''Sanitize user input to prevent XSS'''
    if not text:
        return ''
    
    # Allow basic HTML tags for rich text
    allowed_tags = ['p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                    'ul', 'ol', 'li', 'a', 'span', 'div', 'blockquote', 'code', 'pre']
    allowed_attributes = {'a': ['href', 'title'], 'span': ['class'], 'div': ['class']}
    
    cleaned = bleach.clean(
        text,
        tags=allowed_tags,
        attributes=allowed_attributes,
        strip=True
    )
    
    return cleaned

def validate_password(password):
    '''Validate password strength'''
    if len(password) < 6:
        return False, 'Password must be at least 6 characters'
    
    return True, 'Password is valid'

def validate_workspace_name(name):
    '''Validate workspace name'''
    if not name or len(name.strip()) == 0:
        return False, 'Workspace name cannot be empty'
    
    if len(name) > 100:
        return False, 'Workspace name too long (max 100 characters)'
    
    return True, 'Valid'

def validate_file_size(size_bytes, max_mb=16):
    '''Validate file size'''
    max_bytes = max_mb * 1024 * 1024
    
    if size_bytes > max_bytes:
        return False, f'File size exceeds {max_mb}MB limit'
    
    return True, 'Valid'

def sanitize_filename(filename):
    '''Sanitize filename'''
    # Remove dangerous characters
    filename = re.sub(r'[^\w\s.-]', '', filename)
    filename = filename.strip()
    
    if not filename:
        return 'unnamed_file'
    
    return filename
