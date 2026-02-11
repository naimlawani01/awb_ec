"""Export API endpoints for Excel and PDF generation."""
from datetime import datetime, date
from typing import Optional
from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.core.database import get_awb_db, get_internal_db
from app.core.security import require_staff
from app.services.document_service import DocumentService
from app.services.shipment_service import ShipmentService
from app.services.contact_service import ContactService
from app.services.statistics_service import StatisticsService
from app.services.export_service import ExportService
from app.services.user_service import UserService
from app.schemas.document import DocumentSearchParams
from app.schemas.shipment import ShipmentSearchParams

router = APIRouter()


@router.get("/documents/excel")
async def export_documents_to_excel(
    request: Request,
    awb_number: Optional[str] = None,
    shipper: Optional[str] = None,
    consignee: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[int] = None,
    limit: int = Query(1000, ge=1, le=10000),
    current_user: dict = Depends(require_staff),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Export documents to Excel format.
    """
    search_params = DocumentSearchParams(
        awb_number=awb_number,
        shipper=shipper,
        consignee=consignee,
        origin=origin,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    
    doc_service = DocumentService(awb_db)
    documents, _ = doc_service.get_documents(1, limit, search_params)
    
    export_service = ExportService()
    buffer = export_service.export_documents_to_excel(
        documents,
        title="AWB Documents Export"
    )
    
    # Log export action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="EXPORT",
        resource_type="document",
        details=f"Excel export: {len(documents)} records",
        ip_address=request.client.host if request.client else None,
    )
    
    filename = f"awb_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/documents/pdf")
async def export_documents_to_pdf(
    request: Request,
    awb_number: Optional[str] = None,
    shipper: Optional[str] = None,
    consignee: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[int] = None,
    limit: int = Query(500, ge=1, le=2000),
    current_user: dict = Depends(require_staff),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Export documents to PDF format.
    """
    search_params = DocumentSearchParams(
        awb_number=awb_number,
        shipper=shipper,
        consignee=consignee,
        origin=origin,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    
    doc_service = DocumentService(awb_db)
    documents, _ = doc_service.get_documents(1, limit, search_params)
    
    export_service = ExportService()
    buffer = export_service.export_documents_to_pdf(
        documents,
        title="AWB Documents Report"
    )
    
    # Log export action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="EXPORT",
        resource_type="document",
        details=f"PDF export: {len(documents)} records",
        ip_address=request.client.host if request.client else None,
    )
    
    filename = f"awb_documents_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/shipments/excel")
async def export_shipments_to_excel(
    request: Request,
    master_number: Optional[str] = None,
    shipper: Optional[str] = None,
    consignee: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(1000, ge=1, le=10000),
    current_user: dict = Depends(require_staff),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Export shipments to Excel format.
    """
    search_params = ShipmentSearchParams(
        master_number=master_number,
        shipper=shipper,
        consignee=consignee,
        origin=origin,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
    )
    
    ship_service = ShipmentService(awb_db)
    shipments, _ = ship_service.get_shipments(1, limit, search_params)
    
    export_service = ExportService()
    buffer = export_service.export_shipments_to_excel(
        shipments,
        title="Shipments Export"
    )
    
    # Log export action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="EXPORT",
        resource_type="shipment",
        details=f"Excel export: {len(shipments)} records",
        ip_address=request.client.host if request.client else None,
    )
    
    filename = f"shipments_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/contacts/excel")
async def export_contacts_to_excel(
    request: Request,
    contact_type: Optional[int] = None,
    limit: int = Query(5000, ge=1, le=20000),
    current_user: dict = Depends(require_staff),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Export contacts to Excel format.
    """
    from app.schemas.contact import ContactSearchParams
    
    search_params = ContactSearchParams(contact_type=contact_type)
    
    contact_service = ContactService(awb_db)
    contacts, _ = contact_service.get_contacts(1, limit, search_params)
    
    export_service = ExportService()
    buffer = export_service.export_contacts_to_excel(
        contacts,
        title="Contacts Export"
    )
    
    # Log export action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="EXPORT",
        resource_type="contact",
        details=f"Excel export: {len(contacts)} records",
        ip_address=request.client.host if request.client else None,
    )
    
    filename = f"contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/statistics/pdf")
async def export_statistics_to_pdf(
    request: Request,
    current_user: dict = Depends(require_staff),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Export statistics report to PDF format.
    """
    stats_service = StatisticsService(awb_db)
    stats = stats_service.get_dashboard_stats()
    
    export_service = ExportService()
    buffer = export_service.export_statistics_to_pdf(
        stats.model_dump(),
        title="AWB Statistics Report"
    )
    
    # Log export action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="EXPORT",
        resource_type="statistics",
        details="PDF statistics report",
        ip_address=request.client.host if request.client else None,
    )
    
    filename = f"awb_statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/report/detailed/excel")
async def export_detailed_report_excel(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    shipper: Optional[str] = None,
    consignee: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    status: Optional[int] = None,
    limit: int = Query(1000, ge=1, le=5000),
    current_user: dict = Depends(require_staff),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Export detailed AWB report to Excel with full rate description.
    Includes: pieces, weights, charges, routing, other fees.
    Multiple sheets for different data views.
    """
    search_params = DocumentSearchParams(
        shipper=shipper,
        consignee=consignee,
        origin=origin,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    
    doc_service = DocumentService(awb_db)
    documents, total = doc_service.get_documents(1, limit, search_params)
    
    export_service = ExportService()
    
    # Build title with date range
    period_info = ""
    if start_date and end_date:
        period_info = f" ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})"
    elif start_date:
        period_info = f" (depuis le {start_date.strftime('%d/%m/%Y')})"
    elif end_date:
        period_info = f" (jusqu'au {end_date.strftime('%d/%m/%Y')})"
    
    buffer = export_service.export_detailed_awb_report_excel(
        documents,
        title=f"Rapport AWB Détaillé{period_info}"
    )
    
    # Log export action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="EXPORT",
        resource_type="detailed_report",
        details=f"Detailed Excel export: {len(documents)} records",
        ip_address=request.client.host if request.client else None,
    )
    
    filename = f"rapport_awb_detaille_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx"
    
    return StreamingResponse(
        buffer,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/report/detailed/pdf")
async def export_detailed_report_pdf(
    request: Request,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    shipper: Optional[str] = None,
    consignee: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    status: Optional[int] = None,
    limit: int = Query(500, ge=1, le=2000),
    current_user: dict = Depends(require_staff),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Export detailed AWB report to PDF with summary and KPIs.
    """
    search_params = DocumentSearchParams(
        shipper=shipper,
        consignee=consignee,
        origin=origin,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        status=status,
    )
    
    doc_service = DocumentService(awb_db)
    documents, total = doc_service.get_documents(1, limit, search_params)
    
    stats_service = StatisticsService(awb_db)
    stats = stats_service.get_dashboard_stats()
    
    export_service = ExportService()
    
    # Build title with date range
    period_info = ""
    if start_date and end_date:
        period_info = f" ({start_date.strftime('%d/%m/%Y')} - {end_date.strftime('%d/%m/%Y')})"
    elif start_date:
        period_info = f" (depuis le {start_date.strftime('%d/%m/%Y')})"
    elif end_date:
        period_info = f" (jusqu'au {end_date.strftime('%d/%m/%Y')})"
    
    buffer = export_service.export_detailed_awb_report_pdf(
        documents,
        stats.model_dump(),
        title=f"Rapport AWB Détaillé{period_info}"
    )
    
    # Log export action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="EXPORT",
        resource_type="detailed_report",
        details=f"Detailed PDF export: {len(documents)} records",
        ip_address=request.client.host if request.client else None,
    )
    
    filename = f"rapport_awb_detaille_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )

