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
import cv2
import face_recognition
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
from PIL import Image

# Add the parent directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import Employee, Attendance, UnknownFace
from recognition import FaceRecognitionSystem
from notifier import NotificationService
from config import Config
from utils import blur_face, validate_image_file, resize_image

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
        return Mock(spec=NotificationService)
    
    @pytest.fixture
    def recognition_system(self, app_context, mock_config, mock_notification_service):
        """Create FaceRecognitionSystem instance for testing"""
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
        # Create a simple test image with a face-like pattern
        image = np.zeros((height, width, 3), dtype=np.uint8)
        
        # Add a simple face-like pattern
        cv2.circle(image, (width//2, height//2), 100, (255, 255, 255), -1)  # Face
        cv2.circle(image, (width//2 - 30, height//2 - 30), 10, (0, 0, 0), -1)  # Left eye
        cv2.circle(image, (width//2 + 30, height//2 - 30), 10, (0, 0, 0), -1)  # Right eye
        cv2.ellipse(image, (width//2, height//2 + 20), (20, 10), 0, 0, 180, (0, 0, 0), 2)  # Mouth
        
        return image
    
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
    
    def test_load_known_faces_empty(self, recognition_system):
        """Test loading known faces when no employees exist"""
        recognition_system.load_known_faces()
        
        assert len(recognition_system.known_face_encodings) == 0
        assert len(recognition_system.known_face_names) == 0
        assert len(recognition_system.employee_ids) == 0
    
    def test_load_known_faces_with_employees(self, app_context, recognition_system):
        """Test loading known faces with existing employees"""
        # Create test employees
        employee1 = self.create_test_employee("John Doe", "john@test.com")
        employee2 = self.create_test_employee("Jane Smith", "jane@test.com")
        
        recognition_system.load_known_faces()
        
        assert len(recognition_system.known_face_encodings) == 2
        assert len(recognition_system.known_face_names) == 2
        assert len(recognition_system.employee_ids) == 2
        assert "John Doe" in recognition_system.known_face_names
        assert "Jane Smith" in recognition_system.known_face_names
    
    @patch('cv2.VideoCapture')
    def test_initialize_camera_success(self, mock_video_capture, recognition_system):
        """Test successful camera initialization"""
        mock_camera = Mock()
        mock_camera.isOpened.return_value = True
        mock_video_capture.return_value = mock_camera
        
        result = recognition_system.initialize_camera()
        
        assert result is True
        assert recognition_system.camera is mock_camera
        mock_video_capture.assert_called_once_with(0)
        mock_camera.set.assert_called()
    
    @patch('cv2.VideoCapture')
    def test_initialize_camera_failure(self, mock_video_capture, recognition_system):
        """Test camera initialization failure"""
        mock_camera = Mock()
        mock_camera.isOpened.return_value = False
        mock_video_capture.return_value = mock_camera
        
        result = recognition_system.initialize_camera()
        
        assert result is False
        assert recognition_system.camera is mock_camera
    
    def test_process_frame_no_faces(self, recognition_system):
        """Test processing frame with no faces detected"""
        test_image = self.create_test_image()
        
        with patch('face_recognition.face_locations') as mock_locations:
            mock_locations.return_value = []
            
            # Should not raise any exceptions
            recognition_system.process_frame(test_image)
    
    @patch('face_recognition.face_locations')
    @patch('face_recognition.face_encodings')
    @patch('face_recognition.compare_faces')
    @patch('face_recognition.face_distance')
    def test_process_frame_recognized_face(self, mock_distance, mock_compare, mock_encodings, mock_locations, 
                                         app_context, recognition_system):
        """Test processing frame with recognized face"""
        # Create test employee
        employee = self.create_test_employee()
        recognition_system.load_known_faces()
        
        # Mock face detection
        mock_locations.return_value = [(100, 200, 300, 400)]
        mock_encodings.return_value = [np.random.rand(128)]
        mock_compare.return_value = [True]
        mock_distance.return_value = np.array([0.4])
        
        test_image = self.create_test_image()
        
        with patch.object(recognition_system, 'handle_recognized_face') as mock_handle:
            recognition_system.process_frame(test_image)
            mock_handle.assert_called_once()
    
    def test_handle_recognized_face_first_time_today(self, app_context, recognition_system, temp_dir):
        """Test handling recognized face for first time today"""
        employee = self.create_test_employee()
        test_image = self.create_test_image()
        face_location = (100, 200, 300, 400)
        
        # Mock the uploads directory
        with patch('os.path.join', return_value=os.path.join(temp_dir, 'test.jpg')):
            with patch('cv2.imwrite') as mock_imwrite:
                recognition_system.handle_recognized_face(
                    employee.id, employee.name, 0.8, test_image, face_location
                )
                
                # Check that attendance was recorded
                attendance = Attendance.query.filter_by(employee_id=employee.id).first()
                assert attendance is not None
                assert attendance.confidence == 0.8
                mock_imwrite.assert_called_once()
    
    def test_handle_recognized_face_with_cooldown(self, app_context, recognition_system):
        """Test handling recognized face within cooldown period"""
        employee = self.create_test_employee()
        test_image = self.create_test_image()
        face_location = (100, 200, 300, 400)
        
        # Set cooldown
        recognition_system.attendance_cooldown[employee.id] = datetime.now()
        
        initial_count = Attendance.query.count()
        
        recognition_system.handle_recognized_face(
            employee.id, employee.name, 0.8, test_image, face_location
        )
        
        # Should not create new attendance record
        assert Attendance.query.count() == initial_count
    
    def test_handle_unknown_face(self, app_context, recognition_system, temp_dir):
        """Test handling unknown face detection"""
        test_image = self.create_test_image()
        face_location = (100, 200, 300, 400)
        
        # Mock the uploads directory
        with patch('os.path.join', return_value=os.path.join(temp_dir, 'unknown.jpg')):
            with patch('cv2.imwrite') as mock_imwrite:
                # Simulate multiple attempts
                for i in range(3):
                    recognition_system.handle_unknown_face(test_image, face_location)
                
                # Check that unknown face was recorded
                unknown_face = UnknownFace.query.first()
                assert unknown_face is not None
                mock_imwrite.assert_called()
    
    def test_cleanup_old_attempts(self, recognition_system):
        """Test cleanup of old unknown face attempts"""
        face_key = "100_200"
        old_time = datetime.now() - timedelta(minutes=10)
        
        recognition_system.unknown_face_attempts[face_key] = {
            'count': 2,
            'first_seen': old_time
        }
        
        recognition_system.cleanup_old_attempts()
        
        assert face_key not in recognition_system.unknown_face_attempts
    
    def test_stop_and_cleanup(self, recognition_system):
        """Test stopping and cleanup of recognition system"""
        # Mock camera
        mock_camera = Mock()
        recognition_system.camera = mock_camera
        recognition_system.is_running = True
        
        with patch('cv2.destroyAllWindows') as mock_destroy:
            recognition_system.stop()
            recognition_system.cleanup()
            
            assert recognition_system.is_running is False
            mock_camera.release.assert_called_once()
            mock_destroy.assert_called_once()
            assert recognition_system.camera is None

class TestNotificationService:
    """Test suite for the NotificationService class"""
    
    @pytest.fixture
    def notification_service(self):
        """Create NotificationService instance for testing"""
        return NotificationService()
    
    @patch('twilio.rest.Client')
    def test_setup_twilio_success(self, mock_client_class):
        """Test successful Twilio setup"""
        mock_client = Mock()
        mock_client_class.return_value = mock_client
        
        with patch.dict(os.environ, {
            'TWILIO_ACCOUNT_SID': 'test_sid',
            'TWILIO_AUTH_TOKEN': 'test_token'
        }):
            service = NotificationService()
            assert service.twilio_client is mock_client
    
    def test_setup_twilio_no_credentials(self, notification_service):
        """Test Twilio setup without credentials"""
        with patch.dict(os.environ, {}, clear=True):
            service = NotificationService()
            assert service.twilio_client is None
    
    @patch('twilio.rest.Client')
    def test_send_unknown_face_alert(self, mock_client_class, notification_service):
        """Test sending unknown face alert"""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.sid = 'test_message_id'
        mock_client.messages.create.return_value = mock_message
        
        notification_service.twilio_client = mock_client
        
        with patch.dict(os.environ, {
            'TWILIO_PHONE_NUMBER': '+1234567890',
            'ADMIN_PHONE_NUMBER': '+0987654321'
        }):
            notification_service.send_unknown_face_alert('/path/to/image.jpg')
            mock_client.messages.create.assert_called_once()
    
    def test_send_system_alert(self, notification_service):
        """Test sending system alert"""
        with patch.object(notification_service, 'send_sms_notification') as mock_send:
            notification_service.send_system_alert('ERROR', 'Test message')
            mock_send.assert_called_once()

class TestUtilityFunctions:
    """Test suite for utility functions"""
    
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
        valid, message = validate_image_file('/nonexistent/path.jpg')
        assert valid is False
        assert 'does not exist' in message
    
    def test_validate_image_file_invalid_extension(self, tmp_path):
        """Test validation of file with invalid extension"""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")
        
        valid, message = validate_image_file(str(test_file))
        assert valid is False
        assert 'Invalid file extension' in message
    
    def test_validate_image_file_valid(self, tmp_path):
        """Test validation of valid image file"""
        # Create a simple test image
        test_image = Image.new('RGB', (200, 200), color='red')
        test_file = tmp_path / "test.jpg"
        test_image.save(str(test_file))
        
        valid, message = validate_image_file(str(test_file))
        assert valid is True
        assert message == "Valid image"

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
    
    def test_unknown_face_model(self, app_context):
        """Test UnknownFace model"""
        unknown_face = UnknownFace(
            timestamp=datetime.now(),
            image_path="/path/to/unknown.jpg",
            notified=False
        )
        
        db.session.add(unknown_face)
        db.session.commit()
        
        retrieved = UnknownFace.query.first()
        assert retrieved is not None
        assert retrieved.notified is False
        assert retrieved.image_path == "/path/to/unknown.jpg"

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
    
    def test_config_validation(self):
        """Test configuration validation"""
        config = Config()
        
        # Test valid configuration
        errors = config.validate()
        assert len(errors) == 0
        
        # Test invalid threshold
        config.set('RECOGNITION_THRESHOLD', 1.5)
        errors = config.validate()
        assert len(errors) > 0
        assert any('RECOGNITION_THRESHOLD' in error for error in errors)

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
    
    def test_get_employees_api(self, app_client):
        """Test get employees API endpoint"""
        # First add an employee
        employee_data = {
            'name': 'John Doe',
            'email': 'john@test.com'
        }
        
        app_client.post('/api/employees', 
                       json=employee_data,
                       content_type='application/json')
        
        # Then get all employees
        response = app_client.get('/api/employees')
        assert response.status_code == 200
        
        data = response.get_json()
        assert len(data) == 1
        assert data[0]['name'] == 'John Doe'
    
    def test_recognition_system_api(self, app_client):
        """Test recognition system control API"""
        # Test getting status
        response = app_client.get('/api/recognition/status')
        assert response.status_code == 200
        
        data = response.get_json()
        assert 'is_running' in data
        assert data['is_running'] is False
        
        # Test starting (will fail without camera, but should return proper error)
        response = app_client.post('/api/recognition/start')
        # Should return error or success depending on camera availability
        assert response.status_code in [200, 500]
    
    def test_attendance_export_api(self, app_client):
        """Test attendance export API"""
        response = app_client.get('/api/attendance/export')
        assert response.status_code == 200
        assert response.headers['Content-Type'] == 'text/csv; charset=utf-8'

if __name__ == '__main__':
    # Run tests with pytest
    pytest.main([__file__, '-v'])
