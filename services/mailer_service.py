import os
import random
import smtplib
import requests
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

class MailerService:
    def __init__(self):
        load_dotenv()
        self.resend_api_key = os.getenv("RESEND_API_KEY")
        self.resend_from = os.getenv("RESEND_FROM_EMAIL") or os.getenv("SMTP_USER") or "no-reply@pegasus.com"
        self.smtp_user = os.getenv("SMTP_USER")
        self.smtp_pass = os.getenv("SMTP_PASS")
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.gmail.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", 465))

    def _generar_html(self, asunto, mensaje_texto, otp):
        """Plantilla centralizada para todos los correos de Pegasus."""
        return f"""
        <html>
        <body style="background-color: #121212; color: #ffffff; font-family: sans-serif; padding: 20px;">
            <div style="max-width: 500px; margin: auto; background-color: #1e1e1e; padding: 30px; border-radius: 10px; border: 1px solid #333;">
                <h1 style="color: #00E5FF; text-align: center; margin-bottom: 20px;">PEGASUS</h1>
                <div style="border-bottom: 1px solid #333; margin-bottom: 20px;"></div>
                <p style="font-size: 16px; color: #00E5FF; font-weight: bold;">{asunto}</p>
                <p style="font-size: 14px; color: #cccccc; line-height: 1.6;">{mensaje_texto}</p>
                <div style="text-align: center; margin: 30px 0;">
                    <span style="font-size: 32px; font-weight: bold; color: #00E5FF; letter-spacing: 5px; background: #252525; padding: 15px 25px; border-radius: 8px; border: 1px solid #00E5FF;">
                        {otp}
                    </span>
                </div>
                <p style="font-size: 11px; color: #666666; text-align: center; margin-top: 40px;">
                    Este es un mensaje automático de seguridad. Si no solicitaste este código, por favor ignora este correo.<br>
                    <br>© 2026 Pegasus Bot System - Venezuela.
                </p>
            </div>
        </body>
        </html>
        """

    def _send_via_resend(self, email_dest, subject, html_content):
        if not self.resend_api_key:
            return False

        payload = {
            "from": self.resend_from,
            "to": email_dest,
            "subject": subject,
            "html": html_content,
        }
        headers = {
            "Authorization": f"Bearer {self.resend_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(
                "https://api.resend.com/emails",
                json=payload,
                headers=headers,
                timeout=15,
            )
            if response.status_code in (200, 202):
                return True
            print(f"Resend API error {response.status_code}: {response.text}")
            return False
        except Exception as e:
            print(f"Error en MailerService Resend: {e}")
            return False

    def _send_via_smtp(self, email_dest, subject, html_content):
        if not self.smtp_user or not self.smtp_pass:
            print("MailerService: credenciales SMTP incompletas.")
            return False

        msg = MIMEMultipart("alternative")
        msg["Subject"] = f"Pegasus: {subject}"
        msg["From"] = f"Pegasus System <{self.smtp_user}>"
        msg["To"] = email_dest
        msg.attach(MIMEText(html_content, "html"))

        try:
            with smtplib.SMTP_SSL(self.smtp_server, self.smtp_port) as server:
                server.login(self.smtp_user, self.smtp_pass)
                server.send_message(msg)
            return True
        except Exception as e:
            print(f"Error en MailerService SMTP: {e}")
            return False

    def enviar_otp(self, email_dest, asunto_corto, mensaje_cuerpo):
        """Envía un OTP y devuelve el código generado o None si falla."""
        otp = str(random.randint(100000, 999999))
        subject = f"Pegasus: {asunto_corto}"
        html_content = self._generar_html(asunto_corto, mensaje_cuerpo, otp)

        if self.resend_api_key:
            enviado = self._send_via_resend(email_dest, subject, html_content)
        else:
            enviado = self._send_via_smtp(email_dest, subject, html_content)

        return otp if enviado else None