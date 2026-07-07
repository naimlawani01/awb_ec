"""Endpoints de rapports (envoi par email du rapport d'activité).

Deux déclencheurs :
- POST /reports/activity/send  : manuel/test, protégé par JWT admin.
- POST /reports/cron/send      : automatique, protégé par un jeton secret
  (header X-Cron-Token) — destiné à être appelé par un cron externe / Railway Function.
"""
import secrets
from datetime import date
from typing import Optional

from fastapi import APIRouter, Depends, Query, Header, HTTPException
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


def _generate_and_send(
    awb_db: Session,
    internal_db: Session,
    period: str,
    start_date: Optional[date],
    end_date: Optional[date],
    to: Optional[str],
    triggered_by: str,
) -> dict:
    """Génère le rapport pour la période et l'envoie par email. Logique partagée."""
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

    try:
        UserService(internal_db).log_action(
            user_id=0,
            username=triggered_by,
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
    """Déclenchement MANUEL (admin) : génère et envoie le rapport d'activité."""
    return _generate_and_send(
        awb_db, internal_db, period, start_date, end_date, to,
        triggered_by=current_user.get("username", "admin"),
    )


@router.post("/cron/send")
async def cron_send_activity_report(
    period: str = Query("last_week", description=f"Préréglage : {', '.join(VALID_PRESETS)}"),
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    to: Optional[str] = None,
    x_cron_token: Optional[str] = Header(None, alias="X-Cron-Token"),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """Déclenchement AUTOMATIQUE : appelé par un cron externe (Railway Function).

    Authentification par jeton secret (header `X-Cron-Token`) — pas de JWT.
    """
    expected = settings.REPORT_CRON_TOKEN
    if not expected:
        raise HTTPException(status_code=503, detail="REPORT_CRON_TOKEN non configuré côté serveur.")
    if not x_cron_token or not secrets.compare_digest(x_cron_token, expected):
        raise HTTPException(status_code=401, detail="Jeton cron invalide.")

    return _generate_and_send(
        awb_db, internal_db, period, start_date, end_date, to,
        triggered_by="cron",
    )


@router.get("/config")
async def report_email_config(current_user: dict = Depends(require_admin)):
    """État de la configuration email (sans exposer les secrets)."""
    return {
        "smtp_configured": settings.smtp_configured,
        "smtp_host": settings.SMTP_HOST,
        "smtp_port": settings.SMTP_PORT,
        "from": settings.REPORT_FROM_EMAIL,
        "default_recipients": settings.REPORT_TO_EMAILS,
        "cron_token_set": bool(settings.REPORT_CRON_TOKEN),
    }
