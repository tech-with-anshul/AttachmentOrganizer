import cv2
import os
import numpy as np
from PIL import Image
import logging

logger = logging.getLogger(__name__)

def blur_face(image, blur_intensity=15):
    """Apply blur effect to a face image for privacy"""
    try:
        if blur_intensity <= 0:
            return image
        
        # Apply Gaussian blur
        blurred = cv2.GaussianBlur(image, (blur_intensity, blur_intensity), 0)
        return blurred
    
    except Exception as e:
        logger.error(f"Error blurring face: {str(e)}")
        return image

def save_employee_images(employee_name, images, upload_folder):
    """Save employee reference images"""
    try:
        employee_folder = os.path.join(upload_folder, "employees")
        os.makedirs(employee_folder, exist_ok=True)
        
        saved_paths = []
        
        for i, image in enumerate(images):
            filename = f"{employee_name.replace(' ', '_')}_{i+1}.jpg"
            filepath = os.path.join(employee_folder, filename)
            
            # Save image
            cv2.imwrite(filepath, image)
            saved_paths.append(filepath)
        
        return saved_paths
    
    except Exception as e:
        logger.error(f"Error saving employee images: {str(e)}")
        return []

def resize_image(image, max_width=800, max_height=600):
    """Resize image while maintaining aspect ratio"""
    try:
        height, width = image.shape[:2]
        
        # Calculate scaling factor
        scale_width = max_width / width
        scale_height = max_height / height
        scale = min(scale_width, scale_height)
        
        if scale < 1:
            new_width = int(width * scale)
            new_height = int(height * scale)
            resized = cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_AREA)
            return resized
        
        return image
    
    except Exception as e:
        logger.error(f"Error resizing image: {str(e)}")
        return image

def validate_image_file(filepath):
    """Validate if file is a valid image"""
    try:
        # Check if file exists
        if not os.path.exists(filepath):
            return False, "File does not exist"
        
        # Check file extension
        valid_extensions = ['.jpg', '.jpeg', '.png', '.bmp', '.tiff']
        _, ext = os.path.splitext(filepath.lower())
        if ext not in valid_extensions:
            return False, f"Invalid file extension. Supported: {', '.join(valid_extensions)}"
        
        # Try to open with OpenCV
        image = cv2.imread(filepath)
        if image is None:
            return False, "Cannot read image file"
        
        # Check image dimensions
        height, width = image.shape[:2]
        if width < 100 or height < 100:
            return False, "Image too small (minimum 100x100 pixels)"
        
        return True, "Valid image"
    
    except Exception as e:
        return False, f"Error validating image: {str(e)}"

def create_thumbnail(image_path, thumbnail_path, size=(150, 150)):
    """Create thumbnail of an image"""
    try:
        with Image.open(image_path) as img:
            img.thumbnail(size, Image.Resampling.LANCZOS)
            img.save(thumbnail_path, "JPEG", quality=85)
        return True
    
    except Exception as e:
        logger.error(f"Error creating thumbnail: {str(e)}")
        return False

def get_file_size(filepath):
    """Get file size in bytes"""
    try:
        return os.path.getsize(filepath)
    except Exception as e:
        logger.error(f"Error getting file size: {str(e)}")
        return 0

def cleanup_old_files(directory, days_old=30):
    """Clean up files older than specified days"""
    try:
        import time
        from datetime import datetime, timedelta
        
        cutoff_time = time.time() - (days_old * 24 * 60 * 60)
        deleted_count = 0
        
        for filename in os.listdir(directory):
            filepath = os.path.join(directory, filename)
            if os.path.isfile(filepath):
                file_time = os.path.getmtime(filepath)
                if file_time < cutoff_time:
                    os.remove(filepath)
                    deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old files from {directory}")
        return deleted_count
    
    except Exception as e:
        logger.error(f"Error cleaning up old files: {str(e)}")
        return 0

def ensure_directory_exists(directory):
    """Ensure directory exists, create if not"""
    try:
        os.makedirs(directory, exist_ok=True)
        return True
    except Exception as e:
        logger.error(f"Error creating directory {directory}: {str(e)}")
        return False

def get_face_landmarks(image_path):
    """Get face landmarks from image"""
    try:
        import face_recognition
        
        image = face_recognition.load_image_file(image_path)
        face_landmarks = face_recognition.face_landmarks(image)
        
        return face_landmarks
    
    except Exception as e:
        logger.error(f"Error getting face landmarks: {str(e)}")
        return []

def calculate_face_distance(encoding1, encoding2):
    """Calculate distance between two face encodings"""
    try:
        import face_recognition
        
        distance = face_recognition.face_distance([encoding1], encoding2)[0]
        return distance
    
    except Exception as e:
        logger.error(f"Error calculating face distance: {str(e)}")
        return 1.0
