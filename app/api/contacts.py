"""Contact API endpoints."""
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_awb_db, get_internal_db
from app.core.security import require_viewer
from app.services.contact_service import ContactService
from app.services.user_service import UserService
from app.schemas.contact import (
    ContactResponse, ContactListResponse, ContactSearchParams,
    ContactListItem, CONTACT_TYPE_NAMES
)


def timestamp_to_datetime(ts) -> Optional[datetime]:
    """Convert Unix timestamp in milliseconds to datetime."""
    if ts is None:
        return None
    if isinstance(ts, datetime):
        return ts
    try:
        return datetime.fromtimestamp(ts / 1000)
    except (ValueError, OSError, TypeError):
        return None

router = APIRouter()


@router.get("", response_model=ContactListResponse)
async def list_contacts(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    display_name: Optional[str] = None,
    account_number: Optional[str] = None,
    contact_type: Optional[int] = None,
    station_id: Optional[int] = None,
    current_user: dict = Depends(require_viewer),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    List contacts with optional filters and pagination.
    """
    search_params = ContactSearchParams(
        display_name=display_name,
        account_number=account_number,
        contact_type=contact_type,
        station_id=station_id,
    )
    
    service = ContactService(awb_db)
    contacts, total = service.get_contacts(page, page_size, search_params)
    
    # Log search action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="SEARCH",
        resource_type="contact",
        details=f"Search: {search_params.model_dump_json()}",
        ip_address=request.client.host if request.client else None,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    items = [
        ContactListItem(
            id=contact.id,
            contact_type=contact.contact_type,
            contact_type_name=CONTACT_TYPE_NAMES.get(contact.contact_type, "Unknown"),
            display_name=contact.display_name,
            account_number=contact.account_number,
        )
        for contact in contacts
    ]
    
    return ContactListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/search")
async def search_contacts(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Search contacts by name or account number.
    """
    service = ContactService(db)
    contacts = service.search_contacts(q, limit)
    
    return {
        "query": q,
        "count": len(contacts),
        "results": [
            ContactListItem(
                id=contact.id,
                contact_type=contact.contact_type,
                contact_type_name=CONTACT_TYPE_NAMES.get(contact.contact_type, "Unknown"),
                display_name=contact.display_name,
                account_number=contact.account_number,
            )
            for contact in contacts
        ]
    }


@router.get("/stats")
async def get_contact_stats(
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get contact statistics by type.
    """
    service = ContactService(db)
    stats = service.get_contact_stats()
    
    return stats


@router.get("/types")
async def get_contact_types():
    """
    Get list of contact types.
    """
    return {
        "types": [
            {"id": type_id, "name": name}
            for type_id, name in CONTACT_TYPE_NAMES.items()
        ]
    }


@router.get("/type/{contact_type}")
async def get_contacts_by_type(
    contact_type: int,
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get contacts by type.
    """
    service = ContactService(db)
    contacts = service.get_contacts_by_type(contact_type, limit)
    
    type_name = CONTACT_TYPE_NAMES.get(contact_type, f"Type {contact_type}")
    
    return {
        "contact_type": contact_type,
        "type_name": type_name,
        "count": len(contacts),
        "contacts": [
            ContactListItem(
                id=contact.id,
                contact_type=contact.contact_type,
                contact_type_name=type_name,
                display_name=contact.display_name,
                account_number=contact.account_number,
            )
            for contact in contacts
        ]
    }


@router.get("/top-shippers")
async def get_top_shippers(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get top shippers by document count.
    """
    service = ContactService(db)
    shippers = service.get_top_shippers(limit)
    
    return {
        "count": len(shippers),
        "shippers": shippers
    }


@router.get("/top-consignees")
async def get_top_consignees(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get top consignees by document count.
    """
    service = ContactService(db)
    consignees = service.get_top_consignees(limit)
    
    return {
        "count": len(consignees),
        "consignees": consignees
    }


@router.get("/{contact_id}", response_model=ContactResponse)
async def get_contact(
    contact_id: int,
    request: Request,
    current_user: dict = Depends(require_viewer),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Get contact by ID.
    """
    service = ContactService(awb_db)
    contact = service.get_contact_by_id(contact_id)
    
    if not contact:
        raise HTTPException(
            status_code=404,
            detail=f"Contact with ID {contact_id} not found"
        )
    
    # Log view action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="VIEW",
        resource_type="contact",
        resource_id=contact_id,
        ip_address=request.client.host if request.client else None,
    )
    
    return ContactResponse.from_orm_with_type(contact)


@router.get("/{contact_id}/documents")
async def get_contact_documents(
    contact_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get documents associated with a contact.
    """
    service = ContactService(db)
    
    # Verify contact exists
    contact = service.get_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(
            status_code=404,
            detail=f"Contact with ID {contact_id} not found"
        )
    
    documents = service.get_contact_documents(contact_id, limit)
    
    return {
        "contact_id": contact_id,
        "contact_name": contact.display_name,
        "document_count": len(documents),
        "documents": [
            {
                "id": doc.id,
                "document_number": doc.document_number,
                "shipper": doc.shipper,
                "consignee": doc.consignee,
                "origin": doc.origin,
                "destination": doc.destination,
                "document_date": timestamp_to_datetime(doc.document_date),
            }
            for doc in documents
        ]
    }


@router.get("/{contact_id}/shipments")
async def get_contact_shipments(
    contact_id: int,
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get shipments associated with a contact.
    """
    service = ContactService(db)
    
    # Verify contact exists
    contact = service.get_contact_by_id(contact_id)
    if not contact:
        raise HTTPException(
            status_code=404,
            detail=f"Contact with ID {contact_id} not found"
        )
    
    shipments = service.get_contact_shipments(contact_id, limit)
    
    return {
        "contact_id": contact_id,
        "contact_name": contact.display_name,
        "shipment_count": len(shipments),
        "shipments": [
            {
                "id": ship.id,
                "master_number": ship.master_number,
                "house_number": ship.house_number,
                "shipper": ship.shipper,
                "consignee": ship.consignee,
                "origin": ship.origin,
                "destination": ship.destination,
                "shipment_date": ship.shipment_date,
            }
            for ship in shipments
        ]
    }

