"""Service d'envoi d'emails (SMTP) avec pièce jointe.

Utilisé pour l'envoi du rapport d'activité à la direction et à la comptabilité.
La configuration vient des variables d'environnement (voir app/core/config.py).
"""
import ssl
import smtplib
import logging
from email.message import EmailMessage
from typing import List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailNotConfigured(RuntimeError):
    """Levée quand aucun serveur SMTP n'est configuré."""


def send_email_with_pdf(
    subject: str,
    html_body: str,
    pdf_bytes: bytes,
    filename: str,
    to_emails: Optional[List[str]] = None,
    text_body: Optional[str] = None,
) -> List[str]:
    """Envoie un email HTML avec un PDF en pièce jointe.

    Retourne la liste des destinataires. Lève EmailNotConfigured si SMTP absent.
    """
    recipients = [e.strip() for e in (to_emails or settings.REPORT_TO_EMAILS) if e and e.strip()]
    if not settings.smtp_configured:
        raise EmailNotConfigured(
            "SMTP non configuré : renseignez SMTP_HOST (et SMTP_USER/SMTP_PASSWORD) dans .env"
        )
    if not recipients:
        raise ValueError("Aucun destinataire fourni.")

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
