"""Document (AWB) API endpoints."""
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session

from app.core.database import get_awb_db, get_internal_db
from app.core.security import require_viewer, oauth2_scheme, decode_token
from app.services.document_service import DocumentService
from app.services.user_service import UserService
from app.services.awb_parser import AWBParser
from app.services.invoice_service import generate_invoice_word, generate_invoice_pdf
from app.schemas.document import (
    DocumentResponse, DocumentListResponse, DocumentSearchParams,
    DocumentListItem
)

router = APIRouter()


def get_current_user_info(token: str = Depends(oauth2_scheme)):
    """Extract user info from token."""
    payload = decode_token(token)
    if not payload:
        return {"user_id": 0, "username": "anonymous"}
    return payload


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    awb_number: Optional[str] = None,
    shipper: Optional[str] = None,
    consignee: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
    status: Optional[int] = None,
    station_id: Optional[int] = None,
    order_by: Optional[str] = Query("date_created", description="Column to sort by"),
    order_dir: Optional[str] = Query("desc", pattern="^(asc|desc)$", description="Sort direction"),
    current_user: dict = Depends(require_viewer),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    List documents with optional filters, pagination and sorting.
    
    Sortable columns: document_number, reference_number, shipper, consignee, 
    origin, destination, document_date, date_created, status
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
        station_id=station_id,
    )
    
    service = DocumentService(awb_db)
    documents, total = service.get_documents(
        page, page_size, search_params, 
        order_by=order_by, 
        order_dir=order_dir
    )
    
    # Log search action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="SEARCH",
        resource_type="document",
        details=f"Search: {search_params.model_dump_json()}",
        ip_address=request.client.host if request.client else None,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    items = [
        DocumentListItem(
            id=doc.id,
            document_number=doc.document_number,
            reference_number=doc.reference_number,
            document_type=doc.document_type,
            status=doc.status,
            shipper=doc.shipper,
            consignee=doc.consignee,
            origin=doc.origin,
            destination=doc.destination,
            document_date=doc.document_date,
            date_created=doc.date_created,
        )
        for doc in documents
    ]
    
    return DocumentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/search")
async def search_documents(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Full-text search in documents.
    """
    service = DocumentService(db)
    documents = service.search_documents(q, limit)
    
    return {
        "query": q,
        "count": len(documents),
        "results": [
            DocumentListItem(
                id=doc.id,
                document_number=doc.document_number,
                reference_number=doc.reference_number,
                document_type=doc.document_type,
                status=doc.status,
                shipper=doc.shipper,
                consignee=doc.consignee,
                origin=doc.origin,
                destination=doc.destination,
                document_date=doc.document_date,
                date_created=doc.date_created,
            )
            for doc in documents
        ]
    }


@router.get("/recent")
async def get_recent_documents(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get recently created documents.
    """
    service = DocumentService(db)
    documents = service.get_recent_documents(days, limit)
    
    return {
        "period_days": days,
        "count": len(documents),
        "documents": [
            DocumentListItem(
                id=doc.id,
                document_number=doc.document_number,
                reference_number=doc.reference_number,
                document_type=doc.document_type,
                status=doc.status,
                shipper=doc.shipper,
                consignee=doc.consignee,
                origin=doc.origin,
                destination=doc.destination,
                document_date=doc.document_date,
                date_created=doc.date_created,
            )
            for doc in documents
        ]
    }


@router.get("/by-awb/{awb_number}", response_model=DocumentResponse)
async def get_document_by_awb(
    awb_number: str,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get document by AWB number.
    """
    service = DocumentService(db)
    document = service.get_document_by_number(awb_number)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document with AWB number {awb_number} not found"
        )
    
    return DocumentResponse.model_validate(document)


@router.get("/client/{client_name}")
async def get_documents_by_client(
    client_name: str,
    client_type: str = Query("shipper", pattern="^(shipper|consignee)$"),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get documents for a specific client.
    """
    service = DocumentService(db)
    documents = service.get_documents_by_client(client_name, client_type, limit)
    
    return {
        "client_name": client_name,
        "client_type": client_type,
        "count": len(documents),
        "documents": [
            DocumentListItem(
                id=doc.id,
                document_number=doc.document_number,
                reference_number=doc.reference_number,
                document_type=doc.document_type,
                status=doc.status,
                shipper=doc.shipper,
                consignee=doc.consignee,
                origin=doc.origin,
                destination=doc.destination,
                document_date=doc.document_date,
                date_created=doc.date_created,
            )
            for doc in documents
        ]
    }


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: int,
    request: Request,
    current_user: dict = Depends(require_viewer),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Get document by ID.
    """
    service = DocumentService(awb_db)
    document = service.get_document_by_id(document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID {document_id} not found"
        )
    
    # Log view action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="VIEW",
        resource_type="document",
        resource_id=document_id,
        ip_address=request.client.host if request.client else None,
    )
    
    return DocumentResponse.model_validate(document)


@router.get("/{document_id}/details")
async def get_document_details(
    document_id: int,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get detailed AWB information parsed from document_data XML.
    
    Returns rate description (pieces, weights, charges), routing,
    other charges, and all AWB fields.
    """
    service = DocumentService(db)
    document = service.get_document_by_id(document_id)
    
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID {document_id} not found"
        )
    
    # Parse the XML document_data
    awb_details = AWBParser.parse(document.document_data)
    
    if not awb_details:
        raise HTTPException(
            status_code=404,
            detail="Document data could not be parsed or is empty"
        )
    
    return {
        "document_id": document_id,
        "document_number": document.document_number,
        "awb_details": AWBParser.to_dict(awb_details),
    }


@router.post("/{document_id}/invoice/word")
async def download_invoice_word(
    document_id: int,
    request: Request,
    current_user: dict = Depends(require_viewer),
    awb_db: Session = Depends(get_awb_db),
):
    """
    Generate and download invoice as Word document (Delphinus format).
    Request body: { "amount_usd": float, "usd_to_gnf": int (default 8960) }
    """
    try:
        body = await request.json()
        amount_usd = float(body.get("amount_usd", 0))
        usd_to_gnf = int(body.get("usd_to_gnf", 8960))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid amount_usd or usd_to_gnf")

    service = DocumentService(awb_db)
    document = service.get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_data = document.document_data
    if doc_data and isinstance(doc_data, str):
        doc_data = doc_data.encode("utf-8")
    awb_details = AWBParser.parse(doc_data) if doc_data else None
    awb_dict = AWBParser.to_dict(awb_details) if awb_details else {}

    docx_bytes = generate_invoice_word(document, awb_dict, amount_usd, usd_to_gnf)

    filename = f"facture_{document.document_number or document_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.docx"
    return Response(
        content=docx_bytes,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/{document_id}/invoice/pdf")
async def download_invoice_pdf(
    document_id: int,
    request: Request,
    current_user: dict = Depends(require_viewer),
    awb_db: Session = Depends(get_awb_db),
):
    """
    Generate and download invoice as PDF (Word converted to PDF, same format).
    Request body: { "amount_usd": float, "usd_to_gnf": int (default 8960) }
    """
    try:
        body = await request.json()
        amount_usd = float(body.get("amount_usd", 0))
        usd_to_gnf = int(body.get("usd_to_gnf", 8960))
    except (ValueError, TypeError):
        raise HTTPException(status_code=400, detail="Invalid amount_usd or usd_to_gnf")

    service = DocumentService(awb_db)
    document = service.get_document_by_id(document_id)
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    doc_data = document.document_data
    if doc_data and isinstance(doc_data, str):
        doc_data = doc_data.encode("utf-8")
    awb_details = AWBParser.parse(doc_data) if doc_data else None
    awb_dict = AWBParser.to_dict(awb_details) if awb_details else {}

    try:
        pdf_bytes = generate_invoice_pdf(document, awb_dict, amount_usd, usd_to_gnf)
    except Exception as e:
        import logging
        log = logging.getLogger(__name__)
        log.exception("Invoice PDF generation failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))

    filename = f"facture_{document.document_number or document_id}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{document_id}/logs")
async def get_document_logs(
    document_id: int,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get activity logs for a document.
    """
    service = DocumentService(db)
    
    # Verify document exists
    document = service.get_document_by_id(document_id)
    if not document:
        raise HTTPException(
            status_code=404,
            detail=f"Document with ID {document_id} not found"
        )
    
    logs = service.get_document_logs(document_id)
    
    return {
        "document_id": document_id,
        "log_count": len(logs),
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "log_type": log.log_type,
                "log_date": log.log_date,
            }
            for log in logs
        ]
    }

