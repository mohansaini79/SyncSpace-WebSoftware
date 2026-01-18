import cloudinary
import cloudinary.uploader
import os
from werkzeug.utils import secure_filename

def upload_to_cloudinary(file):
    '''Upload a file to Cloudinary and return the result'''
    try:
        # Secure the filename
        filename = secure_filename(file.filename)
        
        # Upload to Cloudinary
        result = cloudinary.uploader.upload(
            file,
            folder='syncspace',
            resource_type='auto',
            use_filename=True,
            unique_filename=True
        )
        
        return result
        
    except Exception as e:
        print(f"Cloudinary upload error: {e}")
        raise Exception(f"Failed to upload to Cloudinary: {str(e)}")

def delete_from_cloudinary(public_id):
    '''Delete a file from Cloudinary'''
    try:
        result = cloudinary.uploader.destroy(public_id)
        return result
    except Exception as e:
        print(f"Cloudinary delete error: {e}")
        raise Exception(f"Failed to delete from Cloudinary: {str(e)}")

def upload_image(file, folder='syncspace/images'):
    '''Upload an image file to Cloudinary'''
    try:
        filename = secure_filename(file.filename)
        
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type='image',
            use_filename=True,
            unique_filename=True,
            transformation=[
                {'width': 1000, 'height': 1000, 'crop': 'limit'},
                {'quality': 'auto'},
                {'fetch_format': 'auto'}
            ]
        )
        
        return result
        
    except Exception as e:
        print(f"Image upload error: {e}")
        raise Exception(f"Failed to upload image: {str(e)}")

def upload_document(file, folder='syncspace/documents'):
    '''Upload a document file to Cloudinary'''
    try:
        filename = secure_filename(file.filename)
        
        result = cloudinary.uploader.upload(
            file,
            folder=folder,
            resource_type='raw',
            use_filename=True,
            unique_filename=True
        )
        
        return result
        
    except Exception as e:
        print(f"Document upload error: {e}")
        raise Exception(f"Failed to upload document: {str(e)}")

def get_file_url(public_id, resource_type='auto'):
    '''Get the URL of a file from Cloudinary'''
    try:
        url = cloudinary.CloudinaryImage(public_id).build_url(resource_type=resource_type)
        return url
    except Exception as e:
        print(f"Error getting file URL: {e}")
        return None

def validate_file(file, allowed_extensions=None, max_size_mb=16):
    '''Validate file before upload'''
    if not file or file.filename == '':
        return False, 'No file selected'
    
    # Check file size
    file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.seek(0)  # Reset to beginning
    
    if file_size > max_size_mb * 1024 * 1024:
        return False, f'File size exceeds {max_size_mb}MB limit'
    
    # Check file extension if provided
    if allowed_extensions:
        filename = secure_filename(file.filename)
        ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        if ext not in allowed_extensions:
            return False, f'File type not allowed. Allowed types: {", ".join(allowed_extensions)}'
    
    return True, 'Valid file'
