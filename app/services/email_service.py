"""Service d'envoi d'emails (SMTP) avec pièce jointe.

Utilisé pour l'envoi du rapport d'activité à la direction et à la comptabilité.
La configuration vient des variables d'environnement (voir app/core/config.py).
"""
import ssl
import base64
import socket
import smtplib
import logging
import contextlib
from email.message import EmailMessage
from typing import List, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


@contextlib.contextmanager
def _force_ipv4():
    """Force la résolution DNS en IPv4 le temps de la connexion SMTP.

    Sur certains hébergeurs (Railway…), la sortie IPv6 n'est pas routée : la
    connexion vers le serveur mail échoue en « [Errno 101] Network is unreachable ».
    On limite temporairement getaddrinfo à AF_INET (IPv4) pour contourner ça.
    """
    original = socket.getaddrinfo

    def ipv4_only(host, port, family=0, type=0, proto=0, flags=0):
        return original(host, port, socket.AF_INET, type, proto, flags)

    socket.getaddrinfo = ipv4_only
    try:
        yield
    finally:
        socket.getaddrinfo = original


class EmailNotConfigured(RuntimeError):
    """Levée quand aucun moyen d'envoi (Resend ou SMTP) n'est configuré."""


def _send_via_resend(
    subject: str,
    html_body: str,
    pdf_bytes: bytes,
    filename: str,
    recipients: List[str],
    text_body: Optional[str],
) -> List[str]:
    """Envoi via l'API HTTPS de Resend (contourne le blocage SMTP de Railway)."""
    payload = {
        "from": f"{settings.REPORT_FROM_NAME} <{settings.REPORT_FROM_EMAIL}>",
        "to": recipients,
        "subject": subject,
        "html": html_body,
        "text": text_body or "Veuillez trouver ci-joint le rapport d'activité.",
        "attachments": [
            {
                "filename": filename,
                "content": base64.b64encode(pdf_bytes).decode("ascii"),
            }
        ],
    }
    resp = httpx.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {settings.RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json=payload,
        timeout=30,
    )
    if resp.status_code >= 300:
        raise RuntimeError(f"Resend API {resp.status_code} : {resp.text}")
    logger.info("Rapport envoyé via Resend à %s", ", ".join(recipients))
    return recipients


def send_email_with_pdf(
    subject: str,
    html_body: str,
    pdf_bytes: bytes,
    filename: str,
    to_emails: Optional[List[str]] = None,
    text_body: Optional[str] = None,
) -> List[str]:
    """Envoie un email HTML avec un PDF en pièce jointe.

    Priorité à Resend (API HTTPS) si RESEND_API_KEY est défini ; sinon SMTP.
    Retourne la liste des destinataires. Lève EmailNotConfigured si rien n'est configuré.
    """
    recipients = [e.strip() for e in (to_emails or settings.REPORT_TO_EMAILS) if e and e.strip()]
    if not recipients:
        raise ValueError("Aucun destinataire fourni.")
    if not settings.email_configured:
        raise EmailNotConfigured(
            "Aucun envoi configuré : définissez RESEND_API_KEY (recommandé) "
            "ou SMTP_HOST/SMTP_USER/SMTP_PASSWORD dans .env"
        )

    # Resend en priorité (HTTPS, non bloqué sur Railway)
    if settings.RESEND_API_KEY:
        return _send_via_resend(subject, html_body, pdf_bytes, filename, recipients, text_body)

    # Repli SMTP
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"{settings.REPORT_FROM_NAME} <{settings.REPORT_FROM_EMAIL}>"
    msg["To"] = ", ".join(recipients)
    msg.set_content(
        text_body
        or "Bonjour,\n\nVeuillez trouver ci-joint le rapport d'activité.\n\nElite Cargo"
    )
    msg.add_alternative(html_body, subtype="html")
    msg.add_attachment(
        pdf_bytes,
        maintype="application",
        subtype="pdf",
        filename=filename,
    )

    context = ssl.create_default_context()
    host, port = settings.SMTP_HOST, settings.SMTP_PORT

    with _force_ipv4():
        if port == 465:
            # SSL implicite
            with smtplib.SMTP_SSL(host, port, context=context, timeout=30) as server:
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=30) as server:
                server.ehlo()
                if settings.SMTP_USE_TLS:
                    server.starttls(context=context)
                    server.ehlo()
                if settings.SMTP_USER:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)

    logger.info("Rapport envoyé à %s", ", ".join(recipients))
    return recipients
