"""Endpoints de rapports (envoi par email du rapport d'activité)."""
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_awb_db, get_internal_db
from app.core.security import require_admin
from app.core.config import settings
from app.services.activity_report import (
    generate_activity_report, resolve_period, VALID_PRESETS,
)
from app.services.email_service import send_email_with_pdf, EmailNotConfigured
from app.services.user_service import UserService

router = APIRouter()


@router.post("/activity/send")
async def send_activity_report(
    period: str = Query("last_week", description=f"Préréglage : {', '.join(VALID_PRESETS)}"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    to: Optional[str] = Query(None, description="Destinataires (séparés par des virgules) — sinon config par défaut"),
    current_user: dict = Depends(require_admin),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """Génère le rapport d'activité pour la période et l'envoie par email
    à la direction et à la comptabilité (destinataires configurés)."""
    try:
        start, end = resolve_period(period, start_date, end_date)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    report = generate_activity_report(awb_db, start, end)

    recipients = None
    if to:
        recipients = [e.strip() for e in to.split(",") if e.strip()]

    try:
        sent_to = send_email_with_pdf(
            subject=report["subject"],
            html_body=report["html_body"],
            pdf_bytes=report["pdf_bytes"],
            filename=report["filename"],
            to_emails=recipients,
        )
    except EmailNotConfigured as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:  # erreurs SMTP (auth, connexion…)
        raise HTTPException(status_code=502, detail=f"Échec de l'envoi SMTP : {exc}")

    # Journalisation
    try:
        UserService(internal_db).log_action(
            user_id=current_user.get("user_id", 0),
            username=current_user.get("username", "unknown"),
            action="send_report",
            resource_type="activity_report",
            details=f"Rapport {report['period_label']} envoyé à {', '.join(sent_to)}",
        )
    except Exception:
        pass

    return {
        "success": True,
        "period": report["period_label"],
        "recipients": sent_to,
        "documents": report["total"],
    }


@router.get("/config")
async def report_email_config(current_user: dict = Depends(require_admin)):
    """État de la configuration email (sans exposer le mot de passe)."""
    return {
        "smtp_configured": settings.smtp_configured,
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "from": settings.REPORT_FROM_EMAIL,
        "default_recipients": settings.REPORT_TO_EMAILS,
    }
