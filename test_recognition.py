#!/usr/bin/env python3
"""
Test suite for Face Recognition System
Tests the core face recognition functionality with mock camera streams
"""

import pytest
import os
import sys
import tempfile
import shutil
import json
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta

# Add the parent directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app
from models import db, Employee, Attendance, UnknownFace
from config import Config

# Try to import face recognition modules
try:
    import cv2
    import face_recognition
    from PIL import Image
    from recognition import FaceRecognitionSystem
    from notifier import NotificationService
    from utils import blur_face, validate_image_file, resize_image
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: Face recognition modules not available. Some tests will be skipped.")

class TestFaceRecognitionSystem:
    """Test suite for the FaceRecognitionSystem class"""
    
    @pytest.fixture
    def app_context(self):
        """Create application context for testing"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for test files"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def mock_config(self):
        """Mock configuration for testing"""
        config = Config()
        config.update({
            'CAMERA_INDEX': 0,
            'RECOGNITION_THRESHOLD': 0.6,
            'ATTENDANCE_COOLDOWN_MINUTES': 2,
            'UNKNOWN_FACE_MAX_ATTEMPTS': 3,
            'BLUR_FACES': False,
            'PROCESS_EVERY_N_FRAMES': 1,
            'TARGET_FPS': 15
        })
        return config
    
    @pytest.fixture
    def mock_notification_service(self):
        """Mock notification service for testing"""
        if FACE_RECOGNITION_AVAILABLE:
            return Mock(spec=NotificationService)
        else:
            return Mock()
    
    @pytest.fixture
    def recognition_system(self, app_context, mock_config, mock_notification_service):
        """Create FaceRecognitionSystem instance for testing"""
        if not FACE_RECOGNITION_AVAILABLE:
            pytest.skip("Face recognition modules not available")
        return FaceRecognitionSystem(db, mock_notification_service, mock_config)
    
    def create_test_employee(self, name="John Doe", email="john@test.com"):
        """Create a test employee with face embeddings"""
        # Create a simple test face embedding
        test_embedding = np.random.rand(128).tolist()
        
        employee = Employee(
            name=name,
            email=email,
            face_embeddings=json.dumps([test_embedding]),
            photo_paths=json.dumps(["/test/path/photo1.jpg"])
        )
        
        db.session.add(employee)
        db.session.commit()
        return employee
    
    def create_test_image(self, width=640, height=480):
        """Create a test image array"""
        if not FACE_RECOGNITION_AVAILABLE:
            pytest.skip("Face recognition modules not available")
        
        # Create a simple test image with a face-like pattern
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add a simple face-like pattern
        cv2.circle(image, (width//2, height//2), 100, (255, 255, 255), -1)  # Face
        cv2.circle(image, (width//2 - 30, height//2 - 30), 10, (0, 0, 0), -1)  # Left eye
        cv2.circle(image, (width//2 + 30, height//2 - 30), 10, (0, 0, 0), -1)  # Right eye
        cv2.ellipse(image, (width//2, height//2 + 20), (20, 10), 0, 0, 180, (0, 0, 0), 2)  # Mouth
        
        return image
    
    @pytest.mark.skipif(not FACE_RECOGNITION_AVAILABLE, reason="Face recognition modules not available")
    def test_initialization(self, recognition_system):
        """Test FaceRecognitionSystem initialization"""
        assert recognition_system.db is not None
        assert recognition_system.notification_service is not None
        assert recognition_system.config is not None
        assert recognition_system.is_running is False
        assert recognition_system.camera is None
        assert isinstance(recognition_system.known_face_encodings, list)
        assert isinstance(recognition_system.known_face_names, list)
        assert isinstance(recognition_system.employee_ids, list)
    
    @pytest.mark.skipif(not FACE_RECOGNITION_AVAILABLE, reason="Face recognition modules not available")
    def test_load_known_faces_empty(self, recognition_system):
        """Test loading known faces when no employees exist"""
        recognition_system.load_known_faces()
        
        assert len(recognition_system.known_face_encodings) == 0
        assert len(recognition_system.known_face_names) == 0
        assert len(recognition_system.employee_ids) == 0

class TestUtilityFunctions:
    """Test suite for utility functions"""
    
    @pytest.mark.skipif(not FACE_RECOGNITION_AVAILABLE, reason="Face recognition modules not available")
    def test_blur_face(self):
        """Test face blurring function"""
        # Create test image
        test_image = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        
        # Test with positive blur intensity
        blurred = blur_face(test_image, 15)
        assert blurred.shape == test_image.shape
        assert not np.array_equal(blurred, test_image)
        
        # Test with zero blur intensity
        no_blur = blur_face(test_image, 0)
        assert np.array_equal(no_blur, test_image)
    
    @pytest.mark.skipif(not FACE_RECOGNITION_AVAILABLE, reason="Face recognition modules not available")
    def test_resize_image(self):
        """Test image resizing function"""
        # Create large test image
        large_image = np.random.randint(0, 255, (1000, 1200, 3), dtype=np.uint8)
        
        resized = resize_image(large_image, max_width=800, max_height=600)
        
        assert resized.shape[0] <= 600  # height
        assert resized.shape[1] <= 800  # width
        assert resized.shape[2] == 3    # channels
    
    def test_validate_image_file_nonexistent(self):
        """Test validation of non-existent image file"""
        if not FACE_RECOGNITION_AVAILABLE:
            pytest.skip("Face recognition modules not available")
        
        valid, message = validate_image_file('/nonexistent/path.jpg')
        assert valid is False
        assert 'does not exist' in message

class TestDatabaseModels:
    """Test suite for database models"""
    
    @pytest.fixture
    def app_context(self):
        """Create application context for testing"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        
        with app.app_context():
            db.create_all()
            yield app
            db.drop_all()
    
    def test_employee_model(self, app_context):
        """Test Employee model"""
        employee = Employee(
            name="John Doe",
            email="john@test.com",
            face_embeddings=json.dumps([[0.1, 0.2, 0.3]]),
            photo_paths=json.dumps(["/path/to/photo.jpg"])
        )
        
        db.session.add(employee)
        db.session.commit()
        
        retrieved = Employee.query.filter_by(email="john@test.com").first()
        assert retrieved is not None
        assert retrieved.name == "John Doe"
        assert retrieved.face_embeddings is not None
        assert retrieved.photo_paths is not None
    
    def test_attendance_model(self, app_context):
        """Test Attendance model"""
        # Create employee first
        employee = Employee(name="John Doe", email="john@test.com")
        db.session.add(employee)
        db.session.commit()
        
        # Create attendance record
        attendance = Attendance(
            employee_id=employee.id,
            timestamp=datetime.now(),
            image_path="/path/to/image.jpg",
            confidence=0.85
        )
        
        db.session.add(attendance)
        db.session.commit()
        
        retrieved = Attendance.query.filter_by(employee_id=employee.id).first()
        assert retrieved is not None
        assert retrieved.confidence == 0.85
        assert retrieved.employee.name == "John Doe"

class TestConfiguration:
    """Test suite for configuration management"""
    
    def test_config_initialization(self):
        """Test Configuration initialization"""
        config = Config()
        assert config.get('RECOGNITION_THRESHOLD') == 0.6
        assert config.get('ATTENDANCE_COOLDOWN_MINUTES') == 2
        assert config.get('UNKNOWN_FACE_MAX_ATTEMPTS') == 3
    
    def test_config_get_set(self):
        """Test getting and setting configuration values"""
        config = Config()
        
        # Test getting existing value
        assert config.get('RECOGNITION_THRESHOLD') == 0.6
        
        # Test getting non-existent value with default
        assert config.get('NON_EXISTENT', 'default') == 'default'
        
        # Test setting value
        config.set('TEST_VALUE', 'test')
        assert config.get('TEST_VALUE') == 'test'

class TestIntegration:
    """Integration tests for the complete system"""
    
    @pytest.fixture
    def app_client(self):
        """Create Flask test client"""
        app.config['TESTING'] = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['WTF_CSRF_ENABLED'] = False
        
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                yield client
                db.drop_all()
    
    def test_dashboard_endpoint(self, app_client):
        """Test dashboard endpoint"""
        response = app_client.get('/')
        assert response.status_code == 302  # Redirect to dashboard
        
        response = app_client.get('/dashboard')
        assert response.status_code == 200
    
    def test_employees_endpoint(self, app_client):
        """Test employees endpoint"""
        response = app_client.get('/employees')
        assert response.status_code == 200
    
    def test_add_employee_api(self, app_client):
        """Test add employee API endpoint"""
        employee_data = {
            'name': 'John Doe',
            'email': 'john@test.com'
        }
        
        response = app_client.post('/api/employees', 
                                 json=employee_data,
                                 content_type='application/json')
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['name'] == 'John Doe'
        assert data['email'] == 'john@test.com'
    
    def test_recognition_system_api(self, app_client):
        """Test recognition system control API"""
        # Test getting status
        response = app_client.get('/api/recognition/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'is_running' in data

if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])