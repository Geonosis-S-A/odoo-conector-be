from typing import Protocol
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings

class EmailService(Protocol):
    async def send_otp_email(self, email: str, otp_code: str) -> None:
        """Envía un email con el código OTP al usuario usando SMTP"""
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