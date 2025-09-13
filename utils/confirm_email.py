import os
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from typing import Optional
from itsdangerous import URLSafeTimedSerializer
from itsdangerous.exc import SignatureExpired




load_dotenv()

SECRET_KEY = os.getenv('SECRET_KEY')

SECURITY_PASSWORD_SALT = os.getenv('SECURITY_PASSWORD_SALT')
SMTP_SERVER = os.getenv('SMTP_SERVER')
SMTP_PORT = int(os.getenv('SMTP_PORT'))
SMTP_USERNAME = os.getenv('SMTP_USERNAME')
SMTP_PASSWORD = os.getenv('SMTP_PASSWORD')

serializer = URLSafeTimedSerializer(SECRET_KEY)



def generate_email_token(email: str) -> str:
    return serializer.dumps(email, salt=SECURITY_PASSWORD_SALT)


def confirm_email_token(token: str, expiration=3600) -> Optional[str]:
    try:
        email = serializer.loads(
            token,
            salt=SECURITY_PASSWORD_SALT,
            max_age=expiration
        )
        return email
    except SignatureExpired:
        return None
    except:
        return False


def send_confirmation_email(email: str, token: str):
    subject = "Подтвердите почту"
    body = f"Чтобы подтвержить почту перейдите по ссылке: http://127.0.0.1:8000/auth/confirm/token={token}/email={email}"
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = SMTP_USERNAME
    msg['To'] = email
    
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
        server.starttls()
        server.login(SMTP_USERNAME, SMTP_PASSWORD)
        server.sendmail(SMTP_USERNAME, [email], msg.as_string())
