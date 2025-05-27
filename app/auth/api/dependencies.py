from fastapi import Depends
from sqlmodel import Session
from app.auth.infra.email_service import EmailService
from app.auth.infra.password_service import PasswordService
from app.auth.domain.repositories import UserRepository
from app.auth.infra.db.repositories import SQLModelUserRepository
from app.shared.infra.db.session import get_db
import bcrypt
from app.core.config import settings
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

class BcryptPasswordService(PasswordService):
    def hash_password(self, password: str) -> str:
        salt = bcrypt.gensalt()
        return bcrypt.hashpw(password.encode(), salt).decode()

    def verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return bcrypt.checkpw(
            plain_password.encode(),
            hashed_password.encode()
        )

class SMTPEmailService(EmailService):
    async def send_otp_email(self, email: str, otp_code: str) -> None:
        msg = MIMEMultipart()
        msg['From'] = settings.EMAIL_USER
        msg['To'] = email
        msg['Subject'] = 'Código de verificación'

        body = f'''
            <h1>Código de verificación</h1>
            <p>Tu código de verificación es: <strong>{otp_code}</strong></p>
            <p>Este código expirará en 15 minutos.</p>
        '''
        msg.attach(MIMEText(body, 'html'))

        try:
            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(settings.EMAIL_USER, settings.EMAIL_PASSWORD)
            server.send_message(msg)
            server.quit()
        except Exception as e:
            raise Exception(f"Error al enviar email: {str(e)}")

def get_email_service() -> EmailService:
    return SMTPEmailService()

def get_password_service() -> PasswordService:
    return BcryptPasswordService()

def get_user_repository(db: Session = Depends(get_db)) -> UserRepository:
    return SQLModelUserRepository(db) 