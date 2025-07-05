import cv2
import face_recognition
import numpy as np
import os
import json
import threading
import time
from datetime import datetime, timedelta
from models import Employee, Attendance, UnknownFace
from utils import blur_face
import logging

logger = logging.getLogger(__name__)

class FaceRecognitionSystem:
    """Real-time face recognition system for attendance tracking"""
    
    def __init__(self, db, notification_service, config):
        self.db = db
        self.notification_service = notification_service
        self.config = config
        self.is_running = False
        self.camera = None
        self.known_face_encodings = []
        self.known_face_names = []
        self.employee_ids = []
        self.attendance_cooldown = {}  # Track recent attendance to prevent duplicates
        self.unknown_face_attempts = {}  # Track unknown face attempts
        self.load_known_faces()
        
    def load_known_faces(self):
        """Load known faces from the database"""
        try:
            with self.db.session.begin():
                employees = Employee.query.all()
                
                self.known_face_encodings = []
                self.known_face_names = []
                self.employee_ids = []
                
                for employee in employees:
                    if employee.face_embeddings:
                        embeddings = json.loads(employee.face_embeddings)
                        for embedding in embeddings:
                            self.known_face_encodings.append(np.array(embedding))
                            self.known_face_names.append(employee.name)
                            self.employee_ids.append(employee.id)
                
                logger.info(f"Loaded {len(self.known_face_encodings)} face encodings for {len(employees)} employees")
                
        except Exception as e:
            logger.error(f"Error loading known faces: {str(e)}")
    
    def initialize_camera(self):
        """Initialize the camera"""
        try:
            camera_index = self.config.get('CAMERA_INDEX', 0)
            self.camera = cv2.VideoCapture(camera_index)
            
            if not self.camera.isOpened():
                raise Exception(f"Cannot open camera {camera_index}")
            
            # Set camera properties for better performance
            self.camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
            self.camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
            self.camera.set(cv2.CAP_PROP_FPS, 30)
            
            logger.info(f"Camera initialized successfully on index {camera_index}")
            return True
            
        except Exception as e:
            logger.error(f"Error initializing camera: {str(e)}")
            return False
    
    def process_frame(self, frame):
        """Process a single frame for face recognition"""
        try:
            # Resize frame for faster processing
            small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
            rgb_small_frame = small_frame[:, :, ::-1]
            
            # Find faces in the frame
            face_locations = face_recognition.face_locations(rgb_small_frame)
            face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
            
            # Process each face
            for face_encoding, face_location in zip(face_encodings, face_locations):
                # Compare with known faces
                matches = face_recognition.compare_faces(
                    self.known_face_encodings, 
                    face_encoding,
                    tolerance=self.config.get('RECOGNITION_THRESHOLD', 0.6)
                )
                
                face_distances = face_recognition.face_distance(
                    self.known_face_encodings, 
                    face_encoding
                )
                
                best_match_index = np.argmin(face_distances)
                
                if matches[best_match_index]:
                    # Face recognized
                    employee_id = self.employee_ids[best_match_index]
                    employee_name = self.known_face_names[best_match_index]
                    confidence = 1 - face_distances[best_match_index]
                    
                    self.handle_recognized_face(employee_id, employee_name, confidence, frame, face_location)
                else:
                    # Unknown face
                    self.handle_unknown_face(frame, face_location)
                    
        except Exception as e:
            logger.error(f"Error processing frame: {str(e)}")
    
    def handle_recognized_face(self, employee_id, employee_name, confidence, frame, face_location):
        """Handle a recognized face"""
        try:
            current_time = datetime.now()
            
            # Check if this employee already marked attendance recently (cooldown)
            cooldown_minutes = self.config.get('ATTENDANCE_COOLDOWN_MINUTES', 2)
            if employee_id in self.attendance_cooldown:
                time_diff = current_time - self.attendance_cooldown[employee_id]
                if time_diff < timedelta(minutes=cooldown_minutes):
                    return  # Skip marking attendance due to cooldown
            
            # Check if already marked attendance today
            today = current_time.date()
            with self.db.session.begin():
                existing_attendance = Attendance.query.filter(
                    Attendance.employee_id == employee_id,
                    Attendance.timestamp >= today,
                    Attendance.timestamp < today + timedelta(days=1)
                ).first()
                
                if existing_attendance:
                    # Update cooldown but don't mark attendance again
                    self.attendance_cooldown[employee_id] = current_time
                    return
                
                # Mark attendance
                # Save attendance image
                image_filename = f"attendance_{employee_id}_{current_time.strftime('%Y%m%d_%H%M%S')}.jpg"
                image_path = os.path.join("uploads", "attendance", image_filename)
                
                # Extract and save face image
                top, right, bottom, left = face_location
                # Scale back up face locations since frame was scaled down
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                # Extract face from frame
                face_image = frame[top:bottom, left:right]
                
                # Apply blur if configured
                if self.config.get('BLUR_FACES', False):
                    face_image = blur_face(face_image)
                
                # Save the image
                cv2.imwrite(image_path, face_image)
                
                # Create attendance record
                attendance = Attendance(
                    employee_id=employee_id,
                    timestamp=current_time,
                    image_path=image_path,
                    confidence=confidence
                )
                
                self.db.session.add(attendance)
                self.db.session.commit()
                
                # Update cooldown
                self.attendance_cooldown[employee_id] = current_time
                
                logger.info(f"Attendance marked for {employee_name} (ID: {employee_id}) with confidence {confidence:.2f}")
                
        except Exception as e:
            logger.error(f"Error handling recognized face: {str(e)}")
    
    def handle_unknown_face(self, frame, face_location):
        """Handle an unknown face"""
        try:
            current_time = datetime.now()
            
            # Track unknown face attempts
            face_key = f"{face_location[0]}_{face_location[1]}"  # Simple key based on location
            
            if face_key not in self.unknown_face_attempts:
                self.unknown_face_attempts[face_key] = {'count': 1, 'first_seen': current_time}
            else:
                self.unknown_face_attempts[face_key]['count'] += 1
            
            attempt_data = self.unknown_face_attempts[face_key]
            
            # Send notification after multiple attempts
            max_attempts = self.config.get('UNKNOWN_FACE_MAX_ATTEMPTS', 3)
            if attempt_data['count'] >= max_attempts:
                # Save unknown face image
                image_filename = f"unknown_{current_time.strftime('%Y%m%d_%H%M%S')}.jpg"
                image_path = os.path.join("uploads", "attendance", image_filename)
                
                # Extract face from frame
                top, right, bottom, left = face_location
                # Scale back up face locations since frame was scaled down
                top *= 4
                right *= 4
                bottom *= 4
                left *= 4
                
                face_image = frame[top:bottom, left:right]
                
                # Apply blur if configured
                if self.config.get('BLUR_FACES', False):
                    face_image = blur_face(face_image)
                
                cv2.imwrite(image_path, face_image)
                
                # Record unknown face
                with self.db.session.begin():
                    unknown_face = UnknownFace(
                        timestamp=current_time,
                        image_path=image_path
                    )
                    self.db.session.add(unknown_face)
                    self.db.session.commit()
                
                # Send notification
                self.notification_service.send_unknown_face_alert(image_path)
                
                # Reset attempts for this face
                del self.unknown_face_attempts[face_key]
                
                logger.warning(f"Unknown face detected after {max_attempts} attempts")
                
        except Exception as e:
            logger.error(f"Error handling unknown face: {str(e)}")
    
    def cleanup_old_attempts(self):
        """Clean up old unknown face attempts"""
        try:
            current_time = datetime.now()
            cleanup_threshold = timedelta(minutes=5)
            
            keys_to_remove = []
            for key, data in self.unknown_face_attempts.items():
                if current_time - data['first_seen'] > cleanup_threshold:
                    keys_to_remove.append(key)
            
            for key in keys_to_remove:
                del self.unknown_face_attempts[key]
                
        except Exception as e:
            logger.error(f"Error cleaning up attempts: {str(e)}")
    
    def run(self):
        """Main recognition loop"""
        try:
            if not self.initialize_camera():
                logger.error("Failed to initialize camera")
                return
            
            self.is_running = True
            logger.info("Face recognition system started")
            
            frame_count = 0
            last_cleanup = datetime.now()
            
            while self.is_running:
                ret, frame = self.camera.read()
                if not ret:
                    logger.error("Failed to read frame from camera")
                    break
                
                # Process every nth frame to maintain performance
                process_every_n_frames = self.config.get('PROCESS_EVERY_N_FRAMES', 3)
                if frame_count % process_every_n_frames == 0:
                    self.process_frame(frame)
                
                frame_count += 1
                
                # Cleanup old attempts periodically
                if datetime.now() - last_cleanup > timedelta(minutes=1):
                    self.cleanup_old_attempts()
                    last_cleanup = datetime.now()
                
                # Small delay to prevent excessive CPU usage
                time.sleep(0.03)  # ~30 FPS
                
        except Exception as e:
            logger.error(f"Error in recognition loop: {str(e)}")
        finally:
            self.cleanup()
    
    def stop(self):
        """Stop the recognition system"""
        self.is_running = False
        logger.info("Face recognition system stopped")
    
    def cleanup(self):
        """Clean up resources"""
        try:
            if self.camera:
                self.camera.release()
                self.camera = None
            cv2.destroyAllWindows()
            logger.info("Recognition system cleaned up")
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
