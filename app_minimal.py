import os
import logging
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, send_file, flash, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
import csv
import io
import json

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Create the app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "fallback-secret-key")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Configure the database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///attendance.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["UPLOAD_FOLDER"] = "uploads"
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size

# Initialize extensions
db.init_app(app)

# Create uploads directory
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "employees"), exist_ok=True)
os.makedirs(os.path.join(app.config["UPLOAD_FOLDER"], "attendance"), exist_ok=True)

# Database Models
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
        return f'<Attendance for employee {self.employee_id} at {self.timestamp}>'

class UnknownFace(db.Model):
    """Model for storing unknown face detections"""
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    image_path = db.Column(db.String(255))  # Path to captured image
    notified = db.Column(db.Boolean, default=False)  # Whether admin was notified
    
    def __repr__(self):
        return f'<UnknownFace at {self.timestamp}>'

with app.app_context():
    db.create_all()

@app.route('/')
def index():
    """Home page redirect to dashboard"""
    return redirect(url_for('dashboard'))

@app.route('/dashboard')
def dashboard():
    """Main dashboard showing attendance overview"""
    today = datetime.now().date()
    
    # Get all employees
    employees = Employee.query.all()
    
    # Get today's attendance
    today_attendance = Attendance.query.filter(
        Attendance.timestamp >= today,
        Attendance.timestamp < today + timedelta(days=1)
    ).all()
    
    # Create attendance summary
    attendance_summary = []
    for employee in employees:
        attended_today = any(att.employee_id == employee.id for att in today_attendance)
        attendance_record = next((att for att in today_attendance if att.employee_id == employee.id), None)
        
        status = "Present" if attended_today else "Absent"
        time_in = attendance_record.timestamp.strftime("%H:%M") if attendance_record else "N/A"
        
        # Determine if late (assuming 9 AM is the cutoff)
        if attendance_record and attendance_record.timestamp.time() > datetime.strptime("09:00", "%H:%M").time():
            status = "Late"
        
        attendance_summary.append({
            'employee': employee,
            'status': status,
            'time_in': time_in,
            'attendance_record': attendance_record
        })
    
    return render_template('dashboard.html', 
                         attendance_summary=attendance_summary,
                         today=today,
                         total_employees=len(employees),
                         present_count=len([a for a in attendance_summary if a['status'] in ['Present', 'Late']]))

@app.route('/employees')
def employees():
    """Employee management page"""
    employees = Employee.query.all()
    return render_template('employees.html', employees=employees)

@app.route('/api/employees', methods=['GET'])
def get_employees():
    """API endpoint to get all employees"""
    employees = Employee.query.all()
    return jsonify([{
        'id': emp.id,
        'name': emp.name,
        'email': emp.email,
        'created_at': emp.created_at.isoformat()
    } for emp in employees])

@app.route('/api/employees', methods=['POST'])
def add_employee():
    """API endpoint to add new employee"""
    try:
        data = request.get_json()
        if not data or 'name' not in data or 'email' not in data:
            return jsonify({'error': 'Name and email are required'}), 400
        
        # Check if employee already exists
        existing = Employee.query.filter_by(email=data['email']).first()
        if existing:
            return jsonify({'error': 'Employee with this email already exists'}), 400
        
        employee = Employee(
            name=data['name'],
            email=data['email']
        )
        db.session.add(employee)
        db.session.commit()
        
        return jsonify({
            'id': employee.id,
            'name': employee.name,
            'email': employee.email,
            'created_at': employee.created_at.isoformat()
        }), 201
    except Exception as e:
        logger.error(f"Error adding employee: {str(e)}")
        return jsonify({'error': 'Failed to add employee'}), 500

@app.route('/api/employees/<int:employee_id>/upload-photos', methods=['POST'])
def upload_employee_photos(employee_id):
    """Upload reference photos for an employee"""
    try:
        employee = Employee.query.get_or_404(employee_id)
        
        if 'photos' not in request.files:
            return jsonify({'error': 'No photos uploaded'}), 400
        
        photos = request.files.getlist('photos')
        if len(photos) < 3:
            return jsonify({'error': 'At least 3 photos are required'}), 400
        
        # Process and save photos (without face recognition for now)
        saved_files = []
        
        for i, photo in enumerate(photos):
            if photo.filename == '':
                continue
                
            # Save the uploaded file
            filename = secure_filename(f"{employee.name}_{i+1}_{photo.filename}")
            filepath = os.path.join(app.config["UPLOAD_FOLDER"], "employees", filename)
            photo.save(filepath)
            saved_files.append(filepath)
        
        # Store paths in database (face embeddings will be generated when opencv is available)
        employee.photo_paths = json.dumps(saved_files)
        db.session.commit()
        
        return jsonify({'message': 'Photos uploaded successfully. Face recognition will be enabled once computer vision is set up.'}), 200
        
    except Exception as e:
        logger.error(f"Error uploading photos: {str(e)}")
        return jsonify({'error': 'Failed to upload photos'}), 500

@app.route('/api/attendance')
def get_attendance():
    """Get attendance records with optional filtering"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id')
        
        # Build query
        query = Attendance.query
        
        if start_date:
            query = query.filter(Attendance.timestamp >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(Attendance.timestamp <= datetime.fromisoformat(end_date))
        if employee_id:
            query = query.filter(Attendance.employee_id == int(employee_id))
        
        attendance_records = query.order_by(Attendance.timestamp.desc()).all()
        
        return jsonify([{
            'id': record.id,
            'employee_id': record.employee_id,
            'employee_name': record.employee.name,
            'timestamp': record.timestamp.isoformat(),
            'image_path': record.image_path
        } for record in attendance_records])
        
    except Exception as e:
        logger.error(f"Error fetching attendance: {str(e)}")
        return jsonify({'error': 'Failed to fetch attendance records'}), 500

@app.route('/api/attendance/export')
def export_attendance():
    """Export attendance records as CSV"""
    try:
        # Get query parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        employee_id = request.args.get('employee_id')
        
        # Build query
        query = Attendance.query
        
        if start_date:
            query = query.filter(Attendance.timestamp >= datetime.fromisoformat(start_date))
        if end_date:
            query = query.filter(Attendance.timestamp <= datetime.fromisoformat(end_date))
        if employee_id:
            query = query.filter(Attendance.employee_id == int(employee_id))
        
        attendance_records = query.order_by(Attendance.timestamp.desc()).all()
        
        # Create CSV
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Write header
        writer.writerow(['Employee Name', 'Email', 'Date', 'Time'])
        
        # Write data
        for record in attendance_records:
            writer.writerow([
                record.employee.name,
                record.employee.email,
                record.timestamp.date(),
                record.timestamp.time()
            ])
        
        output.seek(0)
        
        # Create file-like object
        mem = io.BytesIO()
        mem.write(output.getvalue().encode('utf-8'))
        mem.seek(0)
        
        return send_file(
            mem,
            as_attachment=True,
            download_name=f'attendance_{datetime.now().strftime("%Y%m%d")}.csv',
            mimetype='text/csv'
        )
        
    except Exception as e:
        logger.error(f"Error exporting attendance: {str(e)}")
        return jsonify({'error': 'Failed to export attendance'}), 500

@app.route('/api/recognition/start', methods=['POST'])
def start_recognition():
    """Start the face recognition system"""
    return jsonify({'message': 'Face recognition system is not available. Computer vision dependencies need to be installed.'}), 200

@app.route('/api/recognition/stop', methods=['POST'])
def stop_recognition():
    """Stop the face recognition system"""
    return jsonify({'message': 'Face recognition system is not running'}), 200

@app.route('/api/recognition/status')
def recognition_status():
    """Get the status of the face recognition system"""
    return jsonify({
        'is_running': False,
        'message': 'Face recognition system is not available. Install OpenCV and face_recognition to enable.'
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)