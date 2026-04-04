import smtplib
from email.mime.text import MIMEText
import random

def enviar_otp_migracion(email_destino, nombre):
    otp = str(random.randint(100000, 999999))
    msg = MIMEText(f"Hola {nombre}, tu código para autorizar tu nueva PC en Pegasus es: {otp}")
    msg['Subject'] = 'Autorización de nuevo dispositivo - Pegasus'
    msg['From'] = "tu-correo@gmail.com"
    msg['To'] = email_destino

    try:
        with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
            server.login("tu-correo@gmail.com", "tu-app-password")
            server.send_message(msg)
        return otp
    except:
        return None