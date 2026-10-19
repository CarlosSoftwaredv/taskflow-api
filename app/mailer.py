import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import quote

from fastapi import HTTPException


def is_configured() -> bool:
    configured = all(os.getenv(key) for key in ("SMTP_HOST", "SMTP_USER", "SMTP_PASSWORD", "SMTP_FROM"))
    https_url = os.getenv("PUBLIC_BASE_URL", "").startswith("https://")
    return configured and (os.getenv("APP_ENV", "development").lower() != "production" or https_url)


def _send(email: str, subject: str, body: str) -> None:
    host = os.getenv("SMTP_HOST")
    username = os.getenv("SMTP_USER")
    password = os.getenv("SMTP_PASSWORD")
    sender = os.getenv("SMTP_FROM")
    if not all((host, username, password, sender)):
        raise HTTPException(status_code=503, detail="O envio de e-mail ainda não está configurado.")
    if os.getenv("APP_ENV", "development").lower() == "production" and not os.getenv("PUBLIC_BASE_URL", "").startswith("https://"):
        raise HTTPException(status_code=503, detail="PUBLIC_BASE_URL precisa usar HTTPS em produção.")
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = email
    message.set_content(body)
    try:
        with smtplib.SMTP(host, int(os.getenv("SMTP_PORT", "587")), timeout=15) as server:
            server.starttls(context=ssl.create_default_context())
            server.login(username, password)
            server.send_message(message)
    except (OSError, smtplib.SMTPException) as exc:
        raise HTTPException(status_code=503, detail="Não foi possível enviar o e-mail. Tente novamente mais tarde.") from exc


def send_verification(email: str, token: str) -> None:
    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    url = f"{base_url}/?verify={quote(token)}"
    _send(email, "Confirme seu e-mail do TaskFlow", f"Olá! Confirme seu e-mail do TaskFlow abrindo este link (válido por 30 minutos):\n\n{url}\n\nSe você não criou uma conta, ignore esta mensagem.")


def send_password_reset(email: str, token: str) -> None:
    base_url = os.getenv("PUBLIC_BASE_URL", "http://localhost:8000").rstrip("/")
    url = f"{base_url}/?reset={quote(token)}"
    _send(email, "Redefina sua senha do TaskFlow", f"Recebemos um pedido para redefinir sua senha. Use este link em até 30 minutos:\n\n{url}\n\nSe você não solicitou a alteração, ignore esta mensagem. Sua senha atual continuará funcionando.")
