#!/usr/bin/env python
"""Envoi planifié du rapport d'activité par email (à brancher sur un cron).

Usage (depuis n'importe où) :
    python scripts/send_activity_report.py weekly    # semaine précédente (lun→dim)
    python scripts/send_activity_report.py monthly   # mois civil précédent

Prérequis : variables SMTP renseignées dans backend/.env
(SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, REPORT_FROM_EMAIL, REPORT_TO_EMAILS).
"""
import os
import sys
import logging

# Permet `import app...` quel que soit le répertoire courant
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.core.database import AWBSessionLocal
from app.services.activity_report import generate_activity_report, resolve_period
from app.services.email_service import send_email_with_pdf

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("send_activity_report")

PRESETS = {"weekly": "last_week", "monthly": "last_month"}


def main() -> int:
    arg = sys.argv[1] if len(sys.argv) > 1 else "weekly"
    preset = PRESETS.get(arg, arg)
    try:
        start, end = resolve_period(preset)
    except ValueError as exc:
        log.error("Période invalide : %s", exc)
        return 2

    db = AWBSessionLocal()
    try:
        report = generate_activity_report(db, start, end)
    finally:
        db.close()

    try:
        sent = send_email_with_pdf(
            subject=report["subject"],
            html_body=report["html_body"],
            pdf_bytes=report["pdf_bytes"],
            filename=report["filename"],
        )
    except Exception as exc:
        log.error("Échec de l'envoi : %s", exc)
        return 1

    log.info("Rapport %s (%s LTA) envoyé à %s",
             report["period_label"], report["total"], ", ".join(sent))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
