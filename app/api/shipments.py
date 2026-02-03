"""Shipment API endpoints."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.database import get_awb_db, get_internal_db
from app.core.security import require_viewer
from app.services.shipment_service import ShipmentService
from app.services.user_service import UserService
from app.schemas.shipment import (
    ShipmentResponse, ShipmentListResponse, ShipmentSearchParams,
    ShipmentListItem, AttachedFileResponse
)

router = APIRouter()


@router.get("", response_model=ShipmentListResponse)
async def list_shipments(
    request: Request,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    master_number: Optional[str] = None,
    house_number: Optional[str] = None,
    shipper: Optional[str] = None,
    consignee: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    import_export: Optional[int] = None,
    event_status: Optional[str] = None,
    station_id: Optional[int] = None,
    current_user: dict = Depends(require_viewer),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    List shipments with optional filters and pagination.
    """
    search_params = ShipmentSearchParams(
        master_number=master_number,
        house_number=house_number,
        shipper=shipper,
        consignee=consignee,
        origin=origin,
        destination=destination,
        start_date=start_date,
        end_date=end_date,
        import_export=import_export,
        event_status=event_status,
        station_id=station_id,
    )
    
    service = ShipmentService(awb_db)
    shipments, total = service.get_shipments(page, page_size, search_params)
    
    # Log search action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="SEARCH",
        resource_type="shipment",
        details=f"Search: {search_params.model_dump_json()}",
        ip_address=request.client.host if request.client else None,
    )
    
    total_pages = (total + page_size - 1) // page_size
    
    items = [
        ShipmentListItem(
            id=ship.id,
            master_number=ship.master_number,
            house_number=ship.house_number,
            shipper=ship.shipper,
            consignee=ship.consignee,
            origin=ship.origin,
            destination=ship.destination,
            shipment_date=ship.shipment_date,
            event_status=ship.event_status,
            import_export=ship.import_export,
        )
        for ship in shipments
    ]
    
    return ShipmentListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/recent")
async def get_recent_shipments(
    days: int = Query(7, ge=1, le=90),
    limit: int = Query(50, ge=1, le=100),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get recently created shipments.
    """
    service = ShipmentService(db)
    shipments = service.get_recent_shipments(days, limit)
    
    return {
        "period_days": days,
        "count": len(shipments),
        "shipments": [
            ShipmentListItem(
                id=ship.id,
                master_number=ship.master_number,
                house_number=ship.house_number,
                shipper=ship.shipper,
                consignee=ship.consignee,
                origin=ship.origin,
                destination=ship.destination,
                shipment_date=ship.shipment_date,
                event_status=ship.event_status,
                import_export=ship.import_export,
            )
            for ship in shipments
        ]
    }


@router.get("/pending")
async def get_pending_shipments(
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get shipments that are not yet delivered.
    """
    service = ShipmentService(db)
    shipments = service.get_pending_shipments()
    
    return {
        "count": len(shipments),
        "shipments": [
            ShipmentListItem(
                id=ship.id,
                master_number=ship.master_number,
                house_number=ship.house_number,
                shipper=ship.shipper,
                consignee=ship.consignee,
                origin=ship.origin,
                destination=ship.destination,
                shipment_date=ship.shipment_date,
                event_status=ship.event_status,
                import_export=ship.import_export,
            )
            for ship in shipments
        ]
    }


@router.get("/by-number/{number}", response_model=ShipmentResponse)
async def get_shipment_by_number(
    number: str,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get shipment by master or house number.
    """
    service = ShipmentService(db)
    shipment = service.get_shipment_by_number(number)
    
    if not shipment:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment with number {number} not found"
        )
    
    return ShipmentResponse.model_validate(shipment)


@router.get("/client/{client_name}")
async def get_shipments_by_client(
    client_name: str,
    client_type: str = Query("shipper", pattern="^(shipper|consignee)$"),
    limit: int = Query(100, ge=1, le=500),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get shipments for a specific client.
    """
    service = ShipmentService(db)
    shipments = service.get_shipments_by_client(client_name, client_type, limit)
    
    return {
        "client_name": client_name,
        "client_type": client_type,
        "count": len(shipments),
        "shipments": [
            ShipmentListItem(
                id=ship.id,
                master_number=ship.master_number,
                house_number=ship.house_number,
                shipper=ship.shipper,
                consignee=ship.consignee,
                origin=ship.origin,
                destination=ship.destination,
                shipment_date=ship.shipment_date,
                event_status=ship.event_status,
                import_export=ship.import_export,
            )
            for ship in shipments
        ]
    }


@router.get("/status/{event_status}")
async def get_shipments_by_status(
    event_status: str,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get shipments by event status.
    """
    service = ShipmentService(db)
    shipments = service.get_shipments_by_status(event_status)
    
    status_name = ShipmentService.get_event_status_name(event_status)
    
    return {
        "event_status": event_status,
        "status_name": status_name,
        "count": len(shipments),
        "shipments": [
            ShipmentListItem(
                id=ship.id,
                master_number=ship.master_number,
                house_number=ship.house_number,
                shipper=ship.shipper,
                consignee=ship.consignee,
                origin=ship.origin,
                destination=ship.destination,
                shipment_date=ship.shipment_date,
                event_status=ship.event_status,
                import_export=ship.import_export,
            )
            for ship in shipments
        ]
    }


@router.get("/{shipment_id}", response_model=ShipmentResponse)
async def get_shipment(
    shipment_id: int,
    request: Request,
    current_user: dict = Depends(require_viewer),
    awb_db: Session = Depends(get_awb_db),
    internal_db: Session = Depends(get_internal_db),
):
    """
    Get shipment by ID.
    """
    service = ShipmentService(awb_db)
    shipment = service.get_shipment_by_id(shipment_id)
    
    if not shipment:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment with ID {shipment_id} not found"
        )
    
    # Log view action
    user_service = UserService(internal_db)
    user_service.log_action(
        user_id=current_user.get("user_id", 0),
        username=current_user.get("username", "unknown"),
        action="VIEW",
        resource_type="shipment",
        resource_id=shipment_id,
        ip_address=request.client.host if request.client else None,
    )
    
    return ShipmentResponse.model_validate(shipment)


@router.get("/{shipment_id}/files")
async def get_shipment_files(
    shipment_id: int,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get files attached to a shipment.
    """
    service = ShipmentService(db)
    
    # Verify shipment exists
    shipment = service.get_shipment_by_id(shipment_id)
    if not shipment:
        raise HTTPException(
            status_code=404,
            detail=f"Shipment with ID {shipment_id} not found"
        )
    
    files = service.get_shipment_attached_files(shipment_id)
    
    return {
        "shipment_id": shipment_id,
        "file_count": len(files),
        "files": [
            AttachedFileResponse.model_validate(f)
            for f in files
        ]
    }

