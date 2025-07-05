from datetime import datetime
from app import db

class Employee(db.Model):
    """Employee model for storing employee information and face embeddings"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    face_embeddings = db.Column(db.Text)  # JSON string of face embeddings
    photo_paths = db.Column(db.Text)  # JSON string of photo file paths
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship
    attendance_records = db.relationship('Attendance', backref='employee', lazy=True)
    
    def __repr__(self):
        return f'<Employee {self.name}>'

class Attendance(db.Model):
    """Attendance model for storing attendance records"""
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employee.id'), nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255))  # Path to captured image
    confidence = db.Column(db.Float)  # Recognition confidence score
    
    def __repr__(self):
        return f'<Attendance {self.employee.name} at {self.timestamp}>'

class UnknownFace(db.Model):
    """Model for storing unknown face detections"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255))  # Path to captured image
    notified = db.Column(db.Boolean, default=False)  # Whether admin was notified
    
    def __repr__(self):
        return f'<UnknownFace at {self.timestamp}>'
