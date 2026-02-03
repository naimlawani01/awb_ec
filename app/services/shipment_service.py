"""Shipment service for cargo tracking operations."""
from datetime import date, datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session

from app.models.awb_models import Shipment, ShipmentAttachedFile
from app.schemas.shipment import ShipmentSearchParams


class ShipmentService:
    """Service for shipment operations."""
    
    # Import/Export types
    IMPORT_EXPORT_TYPES = {
        1: "Import",
        2: "Export",
        3: "Transit",
    }
    
    # Shipment types
    SHIPMENT_TYPES = {
        1: "Air Freight",
        2: "Sea Freight",
        3: "Ground",
        4: "Multimodal",
    }
    
    # Event status codes
    EVENT_STATUS = {
        "RCS": "Received from Shipper",
        "DEP": "Departed",
        "ARR": "Arrived",
        "NFD": "Notified for Delivery",
        "DLV": "Delivered",
        "RCF": "Received from Flight",
        "AWR": "Documents Received",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_shipments(
        self,
        page: int = 1,
        page_size: int = 25,
        search_params: Optional[ShipmentSearchParams] = None
    ) -> Tuple[List[Shipment], int]:
        """Get paginated list of shipments with optional filters."""
        query = select(Shipment)
        
        # Apply filters
        if search_params:
            filters = []
            
            if search_params.master_number:
                filters.append(
                    Shipment.master_number.ilike(f"%{search_params.master_number}%")
                )
            
            if search_params.house_number:
                filters.append(
                    Shipment.house_number.ilike(f"%{search_params.house_number}%")
                )
            
            if search_params.shipper:
                filters.append(Shipment.shipper.ilike(f"%{search_params.shipper}%"))
            
            if search_params.consignee:
                filters.append(Shipment.consignee.ilike(f"%{search_params.consignee}%"))
            
            if search_params.origin:
                filters.append(Shipment.origin.ilike(f"%{search_params.origin}%"))
            
            if search_params.destination:
                filters.append(Shipment.destination.ilike(f"%{search_params.destination}%"))
            
            if search_params.start_date:
                filters.append(Shipment.shipment_date >= search_params.start_date)
            
            if search_params.end_date:
                filters.append(Shipment.shipment_date <= search_params.end_date)
            
            if search_params.import_export is not None:
                filters.append(Shipment.import_export == search_params.import_export)
            
            if search_params.event_status:
                filters.append(Shipment.event_status == search_params.event_status)
            
            if search_params.station_id:
                filters.append(Shipment.station_id == search_params.station_id)
            
            if filters:
                query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0
        
        # Apply pagination and ordering
        query = query.order_by(Shipment.shipment_date.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        shipments = self.db.execute(query).scalars().all()
        
        return shipments, total
    
    def get_shipment_by_id(self, shipment_id: int) -> Optional[Shipment]:
        """Get single shipment by ID."""
        query = select(Shipment).where(Shipment.id == shipment_id)
        return self.db.execute(query).scalar_one_or_none()
    
    def get_shipment_by_number(self, number: str) -> Optional[Shipment]:
        """Get shipment by master or house number."""
        query = select(Shipment).where(
            or_(
                Shipment.master_number == number,
                Shipment.house_number == number
            )
        )
        return self.db.execute(query).scalar_one_or_none()
    
    def get_shipment_attached_files(self, shipment_id: int) -> List[ShipmentAttachedFile]:
        """Get files attached to a shipment."""
        query = select(ShipmentAttachedFile).where(
            ShipmentAttachedFile.shipment_id == shipment_id
        ).order_by(ShipmentAttachedFile.file_date.desc())
        
        return self.db.execute(query).scalars().all()
    
    def get_shipments_by_client(
        self,
        client_name: str,
        client_type: str = "shipper",
        limit: int = 100
    ) -> List[Shipment]:
        """Get shipments for a specific client."""
        if client_type == "shipper":
            query = select(Shipment).where(
                Shipment.shipper.ilike(f"%{client_name}%")
            )
        else:
            query = select(Shipment).where(
                Shipment.consignee.ilike(f"%{client_name}%")
            )
        
        query = query.order_by(Shipment.shipment_date.desc()).limit(limit)
        return self.db.execute(query).scalars().all()
    
    def get_shipment_count(self) -> int:
        """Get total shipment count."""
        query = select(func.count(Shipment.id))
        return self.db.execute(query).scalar() or 0
    
    def get_shipments_by_date_range(
        self,
        start_date: date,
        end_date: date
    ) -> List[Shipment]:
        """Get shipments within a date range."""
        query = select(Shipment).where(
            and_(
                Shipment.shipment_date >= start_date,
                Shipment.shipment_date <= end_date
            )
        ).order_by(Shipment.shipment_date.desc())
        
        return self.db.execute(query).scalars().all()
    
    def get_recent_shipments(self, days: int = 7, limit: int = 50) -> List[Shipment]:
        """Get recently created shipments."""
        cutoff_date = date.today() - timedelta(days=days)
        query = select(Shipment).where(
            Shipment.shipment_date >= cutoff_date
        ).order_by(Shipment.shipment_date.desc()).limit(limit)
        
        return self.db.execute(query).scalars().all()
    
    def get_shipments_by_status(self, event_status: str) -> List[Shipment]:
        """Get shipments by event status."""
        query = select(Shipment).where(
            Shipment.event_status == event_status
        ).order_by(Shipment.shipment_date.desc())
        
        return self.db.execute(query).scalars().all()
    
    def get_pending_shipments(self) -> List[Shipment]:
        """Get shipments that are not yet delivered."""
        delivered_statuses = ["DLV"]
        query = select(Shipment).where(
            or_(
                Shipment.event_status.notin_(delivered_statuses),
                Shipment.event_status.is_(None)
            )
        ).order_by(Shipment.shipment_date.desc())
        
        return self.db.execute(query).scalars().all()
    
    @classmethod
    def get_import_export_name(cls, type_id: int) -> str:
        """Get import/export type display name."""
        return cls.IMPORT_EXPORT_TYPES.get(type_id, f"Unknown ({type_id})")
    
    @classmethod
    def get_shipment_type_name(cls, type_id: int) -> str:
        """Get shipment type display name."""
        return cls.SHIPMENT_TYPES.get(type_id, f"Unknown ({type_id})")
    
    @classmethod
    def get_event_status_name(cls, status_code: str) -> str:
        """Get event status display name."""
        return cls.EVENT_STATUS.get(status_code, status_code or "Unknown")

