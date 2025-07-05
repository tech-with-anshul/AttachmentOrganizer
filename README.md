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
- Webcam or IP camera
- (Optional) Twilio account for notifications

### Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd face-attendance-system
   ```

2. **Install dependencies**
   ```bash
   pip install flask opencv-python face-recognition sqlalchemy flask-sqlalchemy python-dotenv twilio pillow numpy
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Initialize the database**
   ```bash
   python app.py
   ```

5. **Run the application**
   ```bash
   python main.py
   ```

6. **Access the web interface**
   - Open http://localhost:5000 in your browser

## Usage

### Employee Enrollment

#### Via Web Interface
1. Navigate to the "Employees" page
2. Click "Add Employee"
3. Enter employee details
4. Upload 3+ reference photos
5. The system will automatically process face embeddings

#### Via Command Line
```bash
# Add employee with photos
python cli.py add "John Doe" "john@company.com" photo1.jpg photo2.jpg photo3.jpg

# List all employees
python cli.py list

# Show attendance summary
python cli.py summary

# Delete employee
python cli.py delete 1
