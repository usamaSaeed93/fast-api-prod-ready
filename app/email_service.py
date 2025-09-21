import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional
from app.config import settings
from app.schemas import EmailRequest

logger = logging.getLogger(__name__)


class EmailService:
    """Service for sending emails"""
    
    def __init__(self):
        self.smtp_server = settings.smtp_server
        self.smtp_port = settings.smtp_port
        self.smtp_username = settings.smtp_username
        self.smtp_password = settings.smtp_password
        self.from_email = settings.smtp_from_email
    
    def send_email(self, email_request: EmailRequest) -> bool:
        """Send an email"""
        try:
            # Create message
            msg = MIMEMultipart('alternative')
            msg['Subject'] = email_request.subject
            msg['From'] = self.from_email
            msg['To'] = email_request.to_email
            
            # Add body
            if email_request.is_html:
                msg.attach(MIMEText(email_request.body, 'html'))
            else:
                msg.attach(MIMEText(email_request.body, 'plain'))
            
            # Send email
            if self.smtp_username and self.smtp_password:
                # Use authentication
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.starttls()
                server.login(self.smtp_username, self.smtp_password)
                server.send_message(msg)
                server.quit()
            else:
                # Send without authentication (for demo purposes)
                server = smtplib.SMTP(self.smtp_server, self.smtp_port)
                server.send_message(msg)
                server.quit()
            
            logger.info(f"Email sent successfully to {email_request.to_email}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False
    
    def send_welcome_email(self, to_email: str, username: str) -> bool:
        """Send a welcome email to new users"""
        subject = "Welcome to FastAPI Demo!"
        body = f"""
        <html>
        <body>
            <h2>Welcome {username}!</h2>
            <p>Thank you for registering with our FastAPI demo application.</p>
            <p>You can now access all the features including:</p>
            <ul>
                <li>User authentication</li>
                <li>Background job processing</li>
                <li>Email notifications</li>
                <li>API documentation</li>
            </ul>
            <p>Best regards,<br>The FastAPI Demo Team</p>
        </body>
        </html>
        """
        
        email_request = EmailRequest(
            to_email=to_email,
            subject=subject,
            body=body,
            is_html=True
        )
        
        return self.send_email(email_request)
    
    def send_notification_email(self, to_email: str, message: str) -> bool:
        """Send a notification email"""
        subject = "Notification from FastAPI Demo"
        body = f"""
        <html>
        <body>
            <h2>Notification</h2>
            <p>{message}</p>
            <p>Best regards,<br>The FastAPI Demo Team</p>
        </body>
        </html>
        """
        
        email_request = EmailRequest(
            to_email=to_email,
            subject=subject,
            body=body,
            is_html=True
        )
        
        return self.send_email(email_request)


# Global email service instance
email_service = EmailService()
