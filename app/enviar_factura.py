import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.application import MIMEApplication
from email.mime.text import MIMEText
from dotenv import load_dotenv

load_dotenv()

def enviar_factura_email(destinatario: str, archivo_pdf: str):
    remitente = os.getenv("GMAIL_USER")
    clave = os.getenv("GMAIL_PASSWORD")
    smtp = os.getenv("GMAIL_SMTP", "smtp.gmail.com")
    puerto = int(os.getenv("GMAIL_PORT", 587))

    # Crear mensaje
    msg = MIMEMultipart()
    msg['From'] = remitente
    msg['To'] = destinatario
    msg['Subject'] = 'Tu factura digital - Bizyvel'

    msg.attach(MIMEText("Adjunto encontrarás tu factura. Puedes enviarsela a su cliente"))

    # Adjuntar PDF
    with open(archivo_pdf, "rb") as f:
        parte = MIMEApplication(f.read(), _subtype="pdf")
        parte.add_header('Content-Disposition', 'attachment', filename="factura.pdf")
        msg.attach(parte)

    # Enviar usando STARTTLS (puerto 587)
    with smtplib.SMTP(smtp, puerto) as servidor:
        servidor.ehlo()
        servidor.starttls()
        servidor.login(remitente, clave)
        servidor.send_message(msg)

def enviar_promocion_email(destinatario: str, mensaje: str, asunto: str = "Promoción especial de Bizyvel"):
    remitente = os.getenv("GMAIL_USER")
    clave = os.getenv("GMAIL_PASSWORD")
    smtp = os.getenv("GMAIL_SMTP", "smtp.gmail.com")
    puerto = int(os.getenv("GMAIL_PORT", 587))

    msg = MIMEMultipart()
    msg["From"] = remitente
    msg["To"] = destinatario
    msg["Subject"] = asunto

    msg.attach(MIMEText(mensaje, "html"))

    try:
        with smtplib.SMTP(smtp, puerto) as servidor:
            servidor.ehlo()
            servidor.starttls()
            servidor.login(remitente, clave)
            servidor.send_message(msg)
            print(f"✅ Correo enviado a {destinatario}")
    except Exception as e:
        print(f"❌ Error al enviar a {destinatario}: {e}")
