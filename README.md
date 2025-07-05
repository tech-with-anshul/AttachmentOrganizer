# Face Attendance System

A modern, production-ready face recognition attendance system built with Flask, OpenCV, and face_recognition for small offices (≤50 employees).

## Features

- **Real-time Face Recognition**: Automatic attendance marking using webcam
- **Employee Management**: Easy enrollment with photo upload
- **Smart Attendance Logging**: Duplicate prevention with cooldown periods
- **Web Dashboard**: Beautiful, responsive interface for attendance monitoring
- **CSV Export**: Download attendance records for analysis
- **Privacy Compliance**: Optional face blurring for stored images
- **Admin Notifications**: SMS alerts for unknown faces (via Twilio)
- **Multi-threading**: Optimized for 15+ FPS performance

## Tech Stack

- **Backend**: Flask, OpenCV, face_recognition, SQLAlchemy
- **Frontend**: Bootstrap 5, Chart.js, Feather Icons
- **Database**: SQLite (PostgreSQL ready)
- **Notifications**: Twilio SMS API
- **Computer Vision**: OpenCV, dlib

## Quick Start

### Prerequisites

- Python 3.11+
- Webcam or IP camera (for face recognition)
- (Optional) Twilio account for notifications

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd face-attendance-system
   ```

2. **Install basic dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **For face recognition features, install computer vision dependencies**
   ```bash
   pip install opencv-python face-recognition pillow numpy
   ```

4. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

5. **Initialize the database**
   ```bash
   python app.py
   ```

6. **Run the application**
   ```bash
   python main.py
   ```

7. **Access the web interface**
   - Open http://localhost:5000 in your browser

## Usage

### Employee Enrollment

#### Via Web Interface
1. Navigate to the "Employees" page
2. Click "Add Employee"
3. Enter employee details
4. Upload 3+ reference photos
5. The system will automatically process face embeddings (if CV dependencies are installed)

#### Via Command Line
```bash
# Add employee with photos (requires face recognition dependencies)
python cli.py add "John Doe" "john@company.com" photo1.jpg photo2.jpg photo3.jpg

# List all employees
python cli.py list

# Show attendance summary
python cli.py summary

# Delete employee
python cli.py delete 1
```

### Face Recognition System

The system can run in two modes:

1. **Basic Mode** (without computer vision dependencies):
   - Employee management
   - Manual attendance tracking
   - Dashboard and reporting

2. **Full Mode** (with computer vision dependencies):
   - Automatic face recognition
   - Real-time attendance marking
   - Unknown face detection and alerts

To enable full face recognition features:
```bash
pip install opencv-python face-recognition pillow numpy
```

### Configuration

Key configuration options in `.env`:

```bash
# Database
DATABASE_URL=sqlite:///attendance.db

# Camera settings (for face recognition)
CAMERA_INDEX=0
CAMERA_WIDTH=640
CAMERA_HEIGHT=480

# Recognition settings
RECOGNITION_THRESHOLD=0.6
ATTENDANCE_COOLDOWN_MINUTES=2

# Notifications (optional)
TWILIO_ACCOUNT_SID=your-account-sid
TWILIO_AUTH_TOKEN=your-auth-token
TWILIO_PHONE_NUMBER=your-twilio-number
ADMIN_PHONE_NUMBER=admin-number

# Privacy
BLUR_FACES=false
```

## API Endpoints

### Employees
- `GET /api/employees` - List all employees
- `POST /api/employees` - Add new employee
- `POST /api/employees/{id}/upload-photos` - Upload reference photos

### Attendance
- `GET /api/attendance` - Get attendance records
- `GET /api/attendance/export` - Export attendance as CSV

### Recognition System
- `GET /api/recognition/status` - Get system status
- `POST /api/recognition/start` - Start face recognition
- `POST /api/recognition/stop` - Stop face recognition

## Testing

Run the test suite:
```bash
pytest test_recognition.py -v
```

## Deployment

### Using Gunicorn
```bash
gunicorn --bind 0.0.0.0:5000 main:app
```

### Using Docker
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

# Install CV dependencies if needed
RUN pip install opencv-python face-recognition pillow numpy

COPY . .
EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "main:app"]
```

## Architecture

### File Structure
```
face-attendance-system/
├── app.py                 # Main Flask application
├── app_minimal.py         # Minimal version without CV dependencies
├── main.py               # Application entry point
├── models.py             # Database models
├── recognition.py        # Face recognition system
├── notifier.py          # SMS notification service
├── config.py            # Configuration management
├── cli.py               # Command-line interface
├── utils.py             # Utility functions
├── test_recognition.py  # Test suite
├── templates/           # HTML templates
├── static/             # CSS, JS, images
└── uploads/            # Uploaded files
```

### Database Schema
- **Employee**: Stores employee info and face embeddings
- **Attendance**: Records attendance events with timestamps
- **UnknownFace**: Tracks unrecognized faces for security

## Troubleshooting

### Common Issues

1. **Face recognition not working**
   - Ensure computer vision dependencies are installed
   - Check camera permissions and connectivity
   - Verify photo quality (clear, well-lit faces)

2. **Database errors**
   - Check database permissions
   - Ensure SQLite file is writable
   - For PostgreSQL, verify connection string

3. **SMS notifications not working**
   - Verify Twilio credentials in `.env`
   - Check phone number formats
   - Ensure Twilio account has sufficient credits

### Performance Optimization

- Adjust `PROCESS_EVERY_N_FRAMES` to balance accuracy vs performance
- Use smaller camera resolution for better FPS
- Enable threading with `ENABLE_THREADING=true`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Support

For support and questions:
- Check the troubleshooting section
- Review the test suite for examples
- Open an issue on GitHub

---

**Note**: This system is designed for small offices (≤50 employees). For larger deployments, consider additional optimizations and infrastructure scaling.