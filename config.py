import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Configuration class for the Face Attendance System"""
    
    def __init__(self):
        self.config = {
            # Database settings
            'DATABASE_URL': os.getenv('DATABASE_URL', 'sqlite:///attendance.db'),
            
            # Camera settings
            'CAMERA_INDEX': int(os.getenv('CAMERA_INDEX', '0')),
            'CAMERA_WIDTH': int(os.getenv('CAMERA_WIDTH', '640')),
            'CAMERA_HEIGHT': int(os.getenv('CAMERA_HEIGHT', '480')),
            
            # Recognition settings
            'RECOGNITION_THRESHOLD': float(os.getenv('RECOGNITION_THRESHOLD', '0.6')),
            'PROCESS_EVERY_N_FRAMES': int(os.getenv('PROCESS_EVERY_N_FRAMES', '3')),
            
            # Attendance settings
            'ATTENDANCE_COOLDOWN_MINUTES': int(os.getenv('ATTENDANCE_COOLDOWN_MINUTES', '2')),
            'WORK_START_TIME': os.getenv('WORK_START_TIME', '09:00'),
            
            # Unknown face settings
            'UNKNOWN_FACE_MAX_ATTEMPTS': int(os.getenv('UNKNOWN_FACE_MAX_ATTEMPTS', '3')),
            
            # Privacy settings
            'BLUR_FACES': os.getenv('BLUR_FACES', 'false').lower() == 'true',
            
            # Notification settings
            'TWILIO_ACCOUNT_SID': os.getenv('TWILIO_ACCOUNT_SID'),
            'TWILIO_AUTH_TOKEN': os.getenv('TWILIO_AUTH_TOKEN'),
            'TWILIO_PHONE_NUMBER': os.getenv('TWILIO_PHONE_NUMBER'),
            'ADMIN_PHONE_NUMBER': os.getenv('ADMIN_PHONE_NUMBER'),
            
            # Flask settings
            'SECRET_KEY': os.getenv('SECRET_KEY', 'fallback-secret-key'),
            'SESSION_SECRET': os.getenv('SESSION_SECRET', 'fallback-session-secret'),
            'DEBUG': os.getenv('DEBUG', 'true').lower() == 'true',
            
            # File upload settings
            'UPLOAD_FOLDER': os.getenv('UPLOAD_FOLDER', 'uploads'),
            'MAX_CONTENT_LENGTH': int(os.getenv('MAX_CONTENT_LENGTH', str(16 * 1024 * 1024))),
            
            # Performance settings
            'ENABLE_THREADING': os.getenv('ENABLE_THREADING', 'true').lower() == 'true',
            'TARGET_FPS': int(os.getenv('TARGET_FPS', '15')),
        }
    
    def get(self, key, default=None):
        """Get configuration value"""
        return self.config.get(key, default)
    
    def set(self, key, value):
        """Set configuration value"""
        self.config[key] = value
    
    def update(self, updates):
        """Update multiple configuration values"""
        self.config.update(updates)
    
    def to_dict(self):
        """Return configuration as dictionary"""
        return self.config.copy()
    
    def validate(self):
        """Validate configuration values"""
        errors = []
        
        # Validate numeric values
        if self.config['RECOGNITION_THRESHOLD'] < 0 or self.config['RECOGNITION_THRESHOLD'] > 1:
            errors.append("RECOGNITION_THRESHOLD must be between 0 and 1")
        
        if self.config['ATTENDANCE_COOLDOWN_MINUTES'] < 0:
            errors.append("ATTENDANCE_COOLDOWN_MINUTES must be positive")
        
        if self.config['CAMERA_INDEX'] < 0:
            errors.append("CAMERA_INDEX must be non-negative")
        
        # Validate required directories
        upload_folder = self.config['UPLOAD_FOLDER']
        if not os.path.exists(upload_folder):
            try:
                os.makedirs(upload_folder, exist_ok=True)
            except Exception as e:
                errors.append(f"Cannot create upload folder {upload_folder}: {str(e)}")
        
        return errors
