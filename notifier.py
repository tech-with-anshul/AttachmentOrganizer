import os
import logging
from datetime import datetime
from twilio.rest import Client

logger = logging.getLogger(__name__)

class NotificationService:
    """Service for sending notifications about unknown faces and system events"""
    
    def __init__(self):
        self.twilio_client = None
        self.setup_twilio()
        
    def setup_twilio(self):
        """Setup Twilio client for SMS notifications"""
        try:
            account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
            auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
            
            if account_sid and auth_token:
                self.twilio_client = Client(account_sid, auth_token)
                logger.info("Twilio client initialized successfully")
            else:
                logger.warning("Twilio credentials not found. SMS notifications disabled.")
                
        except Exception as e:
            logger.error(f"Error setting up Twilio: {str(e)}")
    
    def send_unknown_face_alert(self, image_path):
        """Send alert when unknown face is detected"""
        try:
            message = f"Unknown face detected at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}. Please check the dashboard for details."
            
            # Send SMS notification
            if self.twilio_client:
                self.send_sms_notification(message)
            
            # Log the event
            logger.warning(f"Unknown face alert sent. Image saved to: {image_path}")
            
        except Exception as e:
            logger.error(f"Error sending unknown face alert: {str(e)}")
    
    def send_sms_notification(self, message):
        """Send SMS notification using Twilio"""
        try:
            if not self.twilio_client:
                logger.warning("Twilio client not available. Cannot send SMS.")
                return
            
            from_number = os.environ.get("TWILIO_PHONE_NUMBER")
            to_number = os.environ.get("ADMIN_PHONE_NUMBER")
            
            if not from_number or not to_number:
                logger.warning("Twilio phone numbers not configured. Cannot send SMS.")
                return
            
            message = self.twilio_client.messages.create(
                body=message,
                from_=from_number,
                to=to_number
            )
            
            logger.info(f"SMS notification sent successfully. Message SID: {message.sid}")
            
        except Exception as e:
            logger.error(f"Error sending SMS notification: {str(e)}")
    
    def send_system_alert(self, alert_type, message):
        """Send system alert notifications"""
        try:
            full_message = f"Face Attendance System Alert [{alert_type}]: {message}"
            
            if self.twilio_client:
                self.send_sms_notification(full_message)
            
            logger.info(f"System alert sent: {alert_type} - {message}")
            
        except Exception as e:
            logger.error(f"Error sending system alert: {str(e)}")
    
    def send_daily_summary(self, attendance_count, total_employees):
        """Send daily attendance summary"""
        try:
            message = f"Daily Attendance Summary: {attendance_count}/{total_employees} employees marked attendance today."
            
            if self.twilio_client:
                self.send_sms_notification(message)
            
            logger.info(f"Daily summary sent: {message}")
            
        except Exception as e:
            logger.error(f"Error sending daily summary: {str(e)}")
