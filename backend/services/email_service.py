import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import uuid
from sqlalchemy.orm import Session
from .. import models

class EmailService:
    def __init__(self):
        self.smtp_host = os.environ.get("SMTP_HOST")
        self.smtp_port = int(os.environ.get("SMTP_PORT", "587"))
        self.smtp_user = os.environ.get("SMTP_USER")
        self.smtp_pass = os.environ.get("SMTP_PASS")
        self.sender_email = os.environ.get("SMTP_SENDER_EMAIL", self.smtp_user)

    def is_configured(self) -> bool:
        return bool(self.smtp_host and self.smtp_user and self.smtp_pass)

    def send_email(self, db: Session, to_email: str, subject: str, body_text: str, body_html: str = None, email_type: str = "General", user_id: str = None) -> bool:
        """Sends an email and records it in the database."""
        
        # Create history record
        history_id = f"EMAIL-{uuid.uuid4().hex[:8].upper()}"
        history = models.EmailHistory(
            id=history_id,
            recipient_email=to_email,
            subject=subject,
            email_type=email_type,
            status="Pending",
            sent_at=datetime.utcnow()
        )
        db.add(history)
        db.commit()

        if not self.is_configured():
            history.status = "Failed"
            history.error_message = "SMTP not configured"
            db.commit()
            return False

        try:
            self.send_raw_email(to_email, subject, body_text, body_html)
            
            history.status = "Sent"
            db.commit()
            return True

        except Exception as e:
            history.status = "Failed"
            history.error_message = str(e)
            db.commit()
            return False

    def send_raw_email(self, to_email: str, subject: str, body_text: str, body_html: str = None):
        """Sends an email without recording it in the database."""
        if not self.is_configured():
            raise Exception("SMTP not configured")
            
        test_email = os.environ.get("AUTOMATION_TEST_EMAIL")
        if test_email:
            print(f"[TEST MODE] Routing email originally destined for {to_email} to {test_email}")
            to_email = test_email
            
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = self.sender_email
        msg["To"] = to_email

        part1 = MIMEText(body_text, "plain")
        msg.attach(part1)
        
        if body_html:
            part2 = MIMEText(body_html, "html")
            msg.attach(part2)

        with smtplib.SMTP(self.smtp_host, self.smtp_port) as server:
            server.starttls()
            server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(self.sender_email, to_email, msg.as_string())
