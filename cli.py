#!/usr/bin/env python3
"""
Command Line Interface for Face Attendance System
Allows adding employees and managing the system from command line
"""

import os
import sys
import argparse
import json
import cv2
import numpy as np

# Add the parent directory to the path to import our modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app
from models import db, Employee, Attendance

# Try to import face recognition modules
try:
    import face_recognition
    from PIL import Image
    FACE_RECOGNITION_AVAILABLE = True
except ImportError:
    FACE_RECOGNITION_AVAILABLE = False
    print("Warning: Face recognition modules not available. Some features will be limited.")

def add_employee(name, email, photo_paths):
    """Add a new employee with face recognition data"""
    try:
        with app.app_context():
            # Check if employee already exists
            existing = Employee.query.filter_by(email=email).first()
            if existing:
                print(f"Error: Employee with email {email} already exists")
                return False
            
            if not FACE_RECOGNITION_AVAILABLE:
                # Create employee without face recognition
                employee = Employee(
                    name=name,
                    email=email,
                    photo_paths=json.dumps(photo_paths)
                )
                db.session.add(employee)
                db.session.commit()
                print(f"✓ Employee {name} added successfully (without face recognition)")
                return True
            
            # Process photos and generate embeddings
            embeddings = []
            saved_files = []
            
            print(f"Processing {len(photo_paths)} photos for {name}...")
            
            for i, photo_path in enumerate(photo_paths):
                if not os.path.exists(photo_path):
                    print(f"Error: Photo {photo_path} not found")
                    return False
                
                # Load and process image
                try:
                    image = face_recognition.load_image_file(photo_path)
                    face_encodings = face_recognition.face_encodings(image)
                    
                    if not face_encodings:
                        print(f"Error: No face found in photo {photo_path}")
                        return False
                    
                    if len(face_encodings) > 1:
                        print(f"Warning: Multiple faces found in photo {photo_path}, using the first one")
                    
                    embeddings.append(face_encodings[0].tolist())
                    
                    # Save photo to uploads directory
                    uploads_dir = os.path.join("uploads", "employees")
                    os.makedirs(uploads_dir, exist_ok=True)
                    
                    filename = f"{name.replace(' ', '_')}_{i+1}.jpg"
                    save_path = os.path.join(uploads_dir, filename)
                    
                    # Convert and save image
                    cv2_image = cv2.cvtColor(image, cv2.COLOR_RGB2BGR)
                    cv2.imwrite(save_path, cv2_image)
                    saved_files.append(save_path)
                    
                    print(f"  ✓ Processed photo {i+1}: {os.path.basename(photo_path)}")
                    
                except Exception as e:
                    print(f"Error processing photo {photo_path}: {str(e)}")
                    return False
            
            # Create employee record
            employee = Employee(
                name=name,
                email=email,
                face_embeddings=json.dumps(embeddings),
                photo_paths=json.dumps(saved_files)
            )
            
            db.session.add(employee)
            db.session.commit()
            
            print(f"✓ Employee {name} added successfully with {len(embeddings)} face encodings")
            return True
            
    except Exception as e:
        print(f"Error adding employee: {str(e)}")
        return False

def list_employees():
    """List all employees"""
    try:
        with app.app_context():
            employees = Employee.query.all()
            
            if not employees:
                print("No employees found")
                return
            
            print(f"\nFound {len(employees)} employees:")
            print("-" * 60)
            print(f"{'ID':<5} {'Name':<25} {'Email':<30}")
            print("-" * 60)
            
            for emp in employees:
                print(f"{emp.id:<5} {emp.name:<25} {emp.email:<30}")
            
    except Exception as e:
        print(f"Error listing employees: {str(e)}")

def delete_employee(employee_id):
    """Delete an employee"""
    try:
        with app.app_context():
            employee = Employee.query.get(employee_id)
            if not employee:
                print(f"Error: Employee with ID {employee_id} not found")
                return False
            
            # Delete associated files
            if employee.photo_paths:
                photo_paths = json.loads(employee.photo_paths)
                for photo_path in photo_paths:
                    if os.path.exists(photo_path):
                        os.remove(photo_path)
            
            # Delete from database
            db.session.delete(employee)
            db.session.commit()
            
            print(f"✓ Employee {employee.name} deleted successfully")
            return True
            
    except Exception as e:
        print(f"Error deleting employee: {str(e)}")
        return False

def show_attendance_summary():
    """Show attendance summary"""
    try:
        with app.app_context():
            from datetime import datetime, timedelta
            
            today = datetime.now().date()
            
            # Get today's attendance
            today_attendance = Attendance.query.filter(
                Attendance.timestamp >= today,
                Attendance.timestamp < today + timedelta(days=1)
            ).all()
            
            # Get all employees
            employees = Employee.query.all()
            
            print(f"\nAttendance Summary for {today}")
            print("-" * 60)
            print(f"{'Name':<25} {'Status':<15} {'Time':<15}")
            print("-" * 60)
            
            for employee in employees:
                attendance = next((att for att in today_attendance if att.employee_id == employee.id), None)
                if attendance:
                    status = "Present"
                    time_str = attendance.timestamp.strftime("%H:%M")
                    if attendance.timestamp.time() > datetime.strptime("09:00", "%H:%M").time():
                        status = "Late"
                else:
                    status = "Absent"
                    time_str = "N/A"
                
                print(f"{employee.name:<25} {status:<15} {time_str:<15}")
            
            print(f"\nTotal: {len(today_attendance)}/{len(employees)} employees present")
            
    except Exception as e:
        print(f"Error showing attendance summary: {str(e)}")

def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='Face Attendance System CLI')
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Add employee command
    add_parser = subparsers.add_parser('add', help='Add a new employee')
    add_parser.add_argument('name', help='Employee name')
    add_parser.add_argument('email', help='Employee email')
    add_parser.add_argument('photos', nargs='+', help='Paths to employee photos (minimum 3)')
    
    # List employees command
    list_parser = subparsers.add_parser('list', help='List all employees')
    
    # Delete employee command
    delete_parser = subparsers.add_parser('delete', help='Delete an employee')
    delete_parser.add_argument('employee_id', type=int, help='Employee ID to delete')
    
    # Attendance summary command
    summary_parser = subparsers.add_parser('summary', help='Show attendance summary')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    if args.command == 'add':
        if len(args.photos) < 3:
            print("Error: At least 3 photos are required for face recognition")
            return
        
        add_employee(args.name, args.email, args.photos)
    
    elif args.command == 'list':
        list_employees()
    
    elif args.command == 'delete':
        delete_employee(args.employee_id)
    
    elif args.command == 'summary':
        show_attendance_summary()

if __name__ == '__main__':
    main()