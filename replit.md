# Face Attendance System

## Overview

This is a modern, production-ready face recognition attendance system designed for small offices (≤50 employees). The system uses computer vision to automatically detect and recognize faces through a webcam, marking attendance in real-time. It features a web-based dashboard for employee management and attendance monitoring, with optional SMS notifications for unknown faces.

## System Architecture

### Backend Architecture
- **Framework**: Flask with SQLAlchemy ORM
- **Database**: SQLite (with PostgreSQL compatibility)
- **Computer Vision**: OpenCV for video capture and face detection
- **Face Recognition**: `face_recognition` library (based on dlib) for facial embeddings and matching
- **Configuration**: Environment-based configuration using python-dotenv
- **Logging**: Python's built-in logging module with structured logging

### Frontend Architecture
- **UI Framework**: Bootstrap 5 with dark theme
- **Icons**: Feather Icons for consistent iconography
- **Charts**: Chart.js for data visualization
- **Responsive Design**: Mobile-first approach with responsive layouts
- **Real-time Updates**: JavaScript-based status checking and dashboard updates

### Database Schema
- **Employee**: Stores employee information, face embeddings (JSON), and photo paths
- **Attendance**: Records attendance events with timestamps, confidence scores, and image paths
- **UnknownFace**: Tracks unrecognized faces for security monitoring

## Key Components

### Face Recognition System (`recognition.py`)
- Real-time face detection and recognition using webcam
- Multi-threading for optimized performance (15+ FPS)
- Configurable recognition threshold (default 0.6)
- Duplicate prevention with cooldown periods
- Unknown face tracking and alerting

### Employee Management
- Web-based employee enrollment with photo upload
- CLI tool for batch employee addition
- Face embedding generation and storage
- Support for multiple reference photos per employee

### Attendance Logging
- Automatic attendance marking on face recognition
- Duplicate prevention with configurable cooldown (default 2 minutes)
- Image capture and storage for audit trails
- Optional face blurring for privacy compliance

### Notification System (`notifier.py`)
- SMS alerts via Twilio integration
- Unknown face detection notifications
- Configurable alert thresholds

### Web Dashboard
- Real-time attendance monitoring
- Employee management interface
- CSV export functionality
- Recognition system controls

## Data Flow

1. **Employee Enrollment**: Photos uploaded → Face embeddings generated → Stored in database
2. **Real-time Recognition**: Webcam feed → Face detection → Embedding comparison → Attendance logging
3. **Dashboard Updates**: Database queries → JSON API responses → Frontend updates
4. **Notifications**: Unknown face detected → SMS alert sent → Admin notification

## External Dependencies

### Required Libraries
- Flask and Flask-SQLAlchemy for web framework
- OpenCV-Python for computer vision
- face_recognition for facial recognition
- Pillow for image processing
- NumPy for numerical operations

### Optional Services
- **Twilio**: SMS notification service for unknown face alerts
- **PostgreSQL**: Optional database upgrade from SQLite

### Environment Variables
- Database configuration (DATABASE_URL)
- Camera settings (CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT)
- Recognition parameters (RECOGNITION_THRESHOLD, PROCESS_EVERY_N_FRAMES)
- Notification settings (Twilio credentials)
- Privacy settings (BLUR_FACES)

## Deployment Strategy

### Local Development
- SQLite database for lightweight development
- Local webcam for testing
- Environment variable configuration via `.env` file

### Production Considerations
- PostgreSQL upgrade path available
- IP camera support for remote installations
- Multi-threading enabled for performance
- Configurable file upload limits (16MB default)
- ProxyFix middleware for reverse proxy deployments

### Security Features
- Optional face blurring for privacy compliance
- Secure file upload handling
- SQL injection prevention via SQLAlchemy ORM
- Session management with configurable secret keys

## Changelog
- July 05, 2025. Initial setup
- July 05, 2025. Created minimal version of app without CV dependencies
- July 05, 2025. Fixed JavaScript errors in dashboard
- July 05, 2025. Prepared project for GitHub push with comprehensive documentation

## User Preferences

Preferred communication style: Simple, everyday language.