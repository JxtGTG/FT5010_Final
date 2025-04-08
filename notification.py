#!/usr/bin/env python
import smtplib
from email.mime.text import MIMEText
import os
from dotenv import load_dotenv

load_dotenv()

def send_email_notification(subject, body):
    sender_email = os.getenv('sender_email')  
    receiver_email = os.getenv('receiver_email')  
    smtp_server = os.getenv('smtp_server')  
    smtp_port = int(os.getenv('smtp_port', 587))  
    smtp_username = os.getenv('smtp_username')  
    smtp_password = os.getenv('smtp_password') 

    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = receiver_email

    try:
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()  
            server.login(smtp_username, smtp_password)
            server.sendmail(sender_email, receiver_email, msg.as_string())
            print("Email notification sent.")
    except Exception as e:
        print(f"Failed to send email notification: {e}")

if __name__ == "__main__":
    
    send_email_notification("Test Subject", "Test Body")
