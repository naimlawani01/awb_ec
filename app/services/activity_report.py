"""Génération du rapport d'activité (PDF) pour une période donnée, réutilisable
hors du contexte d'une requête HTTP (endpoint d'envoi + script planifié).
"""
from datetime import date, datetime, timedelta
from typing import Optional, Tuple

from sqlalchemy.orm import Session

from app.schemas.document import DocumentSearchParams
from app.services.document_service import DocumentService
from app.services.statistics_service import StatisticsService
from app.services.export_service import ExportService


VALID_PRESETS = ("last_week", "this_week", "last_month", "this_month", "custom")


def resolve_period(
    preset: str,
    start: Optional[date] = None,
    end: Optional[date] = None,
) -> Tuple[date, date]:
    """Calcule (début, fin) à partir d'un préréglage ou de dates explicites."""
    today = date.today()
    if preset == "last_week":
        # Semaine précédente complète (lundi → dimanche)
        last_monday = today - timedelta(days=today.weekday() + 7)
        return last_monday, last_monday + timedelta(days=6)
    if preset == "this_week":
        monday = today - timedelta(days=today.weekday())
        return monday, today
    if preset == "last_month":
        first_this = today.replace(day=1)
        last_prev = first_this - timedelta(days=1)
        return last_prev.replace(day=1), last_prev
    if preset == "this_month":
        return today.replace(day=1), today
    if preset == "custom":
        if not start or not end:
            raise ValueError("Période 'custom' : start et end requis.")
        return start, end
    raise ValueError(f"Préréglage inconnu : {preset} (attendus : {', '.join(VALID_PRESETS)})")


def _fr(v) -> str:
    try:
        return f"{int(round(float(v))):,}".replace(",", " ")
    except Exception:
        return "0"


def generate_activity_report(
    awb_db: Session,
    start: date,
    end: date,
    limit: int = 2000,
) -> dict:
    """Construit le rapport PDF + le sujet et le corps HTML de l'email.

    Retourne un dict : pdf_bytes, filename, subject, html_body, stats.
    """
    start_dt = datetime.combine(start, datetime.min.time())
    end_dt = datetime.combine(end, datetime.min.time())

    search = DocumentSearchParams(start_date=start_dt, end_date=end_dt)
    doc_service = DocumentService(awb_db)
    documents, total = doc_service.get_documents(1, limit, search)

    stats = StatisticsService(awb_db).get_dashboard_stats(start, end).model_dump()

    buffer = ExportService().export_detailed_awb_report_pdf(
        documents,
        stats,
        title="Rapport d'activité",
        total_count=total,
        period_start=start,
        period_end=end,
    )
    pdf_bytes = buffer.getvalue()

    period_lbl = f"du {start.strftime('%d/%m/%Y')} au {end.strftime('%d/%m/%Y')}"
    filename = f"rapport_activite_{start.strftime('%Y%m%d')}_{end.strftime('%Y%m%d')}.pdf"
    subject = f"Elite Cargo — Rapport d'activité ({period_lbl})"

    cur = stats.get("main_currency") or "USD"
    ca = _fr(stats.get("total_prepaid", 0))
    nb = _fr(total)
    poids = f"{(stats.get('total_weight') or 0) / 1000:.1f}".replace(".", ",")
    pieces = _fr(stats.get("total_pieces", 0))

    html_body = f"""\
<div style="font-family:Arial,Helvetica,sans-serif;color:#13273b;max-width:560px">
  <div style="background:#0c6d61;color:#fff;padding:16px 20px;border-radius:8px 8px 0 0">
    <div style="font-size:18px;font-weight:bold">ELITE CARGO</div>
    <div style="font-size:12px;color:#d5ece7">Rapport d'activité</div>
  </div>
  <div style="border:1px solid #e2e8f0;border-top:none;padding:20px;border-radius:0 0 8px 8px">
    <p>Bonjour,</p>
    <p>Veuillez trouver ci-joint le <strong>rapport d'activité</strong> pour la période
       <strong>{period_lbl}</strong>.</p>
    <table style="border-collapse:collapse;margin:14px 0;font-size:14px">
      <tr>
        <td style="padding:6px 14px 6px 0;color:#5b6b7f">Chiffre d'affaires</td>
        <td style="padding:6px 0;font-weight:bold">{ca} {cur}</td>
      </tr>
      <tr>
        <td style="padding:6px 14px 6px 0;color:#5b6b7f">LTA (documents)</td>
        <td style="padding:6px 0;font-weight:bold">{nb}</td>
      </tr>
      <tr>
        <td style="padding:6px 14px 6px 0;color:#5b6b7f">Poids total</td>
        <td style="padding:6px 0;font-weight:bold">{poids} t</td>
      </tr>
      <tr>
        <td style="padding:6px 14px 6px 0;color:#5b6b7f">Pièces</td>
        <td style="padding:6px 0;font-weight:bold">{pieces}</td>
      </tr>
    </table>
    <p style="color:#5b6b7f;font-size:13px">Le détail complet (compagnies, destinations, clients, LTA)
       figure dans le PDF joint.</p>
    <p style="margin-top:18px">Cordialement,<br/><strong>Elite Cargo</strong></p>
  </div>
</div>
"""

    return {
        "pdf_bytes": pdf_bytes,
        "filename": filename,
        "subject": subject,
        "html_body": html_body,
        "stats": stats,
        "total": total,
        "period_label": period_lbl,
    }
