from app.auth.application.services.crypt_service import BcryptPasswordService
from app.auth.infra.email_service import EmailService
from app.auth.infra.password_service import PasswordService
from app.core.config import settings
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


class SMTPEmailService(EmailService):
    async def send_otp_email(self, email: str, otp_code: str) -> None:
        msg = MIMEMultipart()
        msg["From"] = settings.EMAIL_USER
        msg["To"] = email
        msg["Subject"] = "Código de verificación - Geonosis"

        body = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
            </head>
            <body style="margin:0;padding:0;font-family:Arial,sans-serif;background-color:#fafbfc;">
                <table width="100%" cellpadding="0" cellspacing="0" border="0" style="background-color:#fafbfc;">
                    <tr>
                        <td align="center" style="padding:40px 20px;">
                            <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;background-color:#ffffff;border-radius:12px;box-shadow:0 2px 8px rgba(0,0,0,0.1);">
                                
                                <!-- Header -->
                                <tr>
                                    <td align="center" style="padding:40px 40px 20px 40px;">
                                        <div style="background-color:#3b82f6;color:#ffffff;border-radius:8px;padding:12px 20px;display:inline-block;">
                                            <h1 style="margin:0;font-size:20px;font-weight:bold;">Geonosis</h1>
                                        </div>
                                    </td>
                                </tr>
                                
                                <!-- Title -->
                                <tr>
                                    <td align="center" style="padding:0 40px 30px 40px;">
                                        <h2 style="margin:0;font-size:28px;color:#1f2937;font-weight:600;">Código de Verificación</h2>
                                        <p style="margin:16px 0 0 0;font-size:16px;color:#6b7280;line-height:1.5;">Hemos recibido una solicitud para acceder a tu cuenta</p>
                                    </td>
                                </tr>
                                
                                <!-- OTP Code -->
                                <tr>
                                    <td align="center" style="padding:0 40px 30px 40px;">
                                        <p style="margin:0 0 16px 0;font-size:12px;color:#6b7280;text-transform:uppercase;letter-spacing:1px;">Tu código de verificación</p>
                                        <div style="background-color:#dbeafe;border:2px solid #3b82f6;border-radius:12px;padding:24px;margin:0 auto;max-width:250px;">
                                            <div style="font-size:36px;font-weight:bold;color:#3b82f6;letter-spacing:4px;font-family:monospace;">{otp_code}</div>
                                        </div>
                                        <div style="margin-top:16px;padding:12px;background-color:#fef3c7;border-radius:8px;display:inline-block;">
                                            <p style="margin:0;font-size:12px;color:#92400e;font-weight:600;">⏱️ Expira en 15 minutos</p>
                                        </div>
                                    </td>
                                </tr>
                                
                                <!-- Security Note -->
                                <tr>
                                    <td style="padding:0 40px 30px 40px;">
                                        <div style="background-color:#f3f4f6;border-left:4px solid #3b82f6;border-radius:6px;padding:16px;">
                                            <h4 style="margin:0 0 8px 0;font-size:14px;color:#1f2937;font-weight:600;">Nota de Seguridad</h4>
                                            <p style="margin:0;font-size:13px;color:#6b7280;line-height:1.4;">Nunca compartas este código con nadie. Nuestro equipo nunca te pedirá este código por teléfono o email.</p>
                                        </div>
                                    </td>
                                </tr>
                                
                                <!-- Support -->
                                <tr>
                                    <td align="center" style="padding:0 40px 40px 40px;border-top:1px solid #e5e7eb;">
                                        <p style="margin:20px 0 0 0;font-size:13px;color:#6b7280;">¿Necesitas ayuda? Contacta con nuestro equipo de soporte</p>
                                    </td>
                                </tr>
                                
                            </table>
                            
                            <!-- Footer -->
                            <table width="600" cellpadding="0" cellspacing="0" border="0" style="max-width:600px;margin-top:20px;">
                                <tr>
                                    <td align="center" style="padding:20px;">
                                        <p style="margin:0 0 8px 0;font-size:14px;color:#1f2937;font-weight:600;">Geonosis</p>
                                        <p style="margin:0;font-size:11px;color:#6b7280;">© 2025 Geonosis. Todos los derechos reservados.</p>
                                    </td>
                                </tr>
                            </table>
                            
                        </td>
                    </tr>
                </table>
            </body>
            </html>
        """
        msg.attach(MIMEText(body, "html"))

        try:
            server = smtplib.SMTP("smtp.gmail.com", 587)
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
