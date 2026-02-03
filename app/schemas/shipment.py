"""Shipment schemas for API validation."""
from datetime import date, datetime
from typing import Optional, List
from pydantic import BaseModel


class ShipmentBase(BaseModel):
    """Base shipment schema."""
    master_number: Optional[str] = None
    house_number: Optional[str] = None
    reference_number: Optional[str] = None
    shipper: Optional[str] = None
    consignee: Optional[str] = None
    agent: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    shipment_date: date
    import_export: Optional[int] = None
    shipment_type: Optional[int] = None


class ShipmentResponse(ShipmentBase):
    """Full shipment response."""
    id: int
    station_id: int
    master_shipment_id: Optional[int] = None
    shipper_contact_id: Optional[int] = None
    consignee_contact_id: Optional[int] = None
    also_notify_contact_id: Optional[int] = None
    freight_forwarder_contact_id: Optional[int] = None
    event_status: Optional[str] = None
    customs_status: Optional[int] = None
    transport: Optional[int] = None
    scheduled_carrier_arrival_datetime: Optional[datetime] = None
    actual_carrier_arrival_datetime: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class ShipmentListItem(BaseModel):
    """Simplified shipment for list views."""
    id: int
    master_number: Optional[str] = None
    house_number: Optional[str] = None
    shipper: Optional[str] = None
    consignee: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    shipment_date: date
    event_status: Optional[str] = None
    import_export: Optional[int] = None
    
    class Config:
        from_attributes = True


class ShipmentListResponse(BaseModel):
    """Paginated shipment list response."""
    items: List[ShipmentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ShipmentSearchParams(BaseModel):
    """Shipment search parameters."""
    master_number: Optional[str] = None
    house_number: Optional[str] = None
    shipper: Optional[str] = None
    consignee: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    import_export: Optional[int] = None
    event_status: Optional[str] = None
    station_id: Optional[int] = None


class AttachedFileResponse(BaseModel):
    """Attached file response."""
    id: int
    shipment_id: int
    file_date: Optional[date] = None
    file_size: Optional[int] = None
    original_file_name: Optional[str] = None
    description: Optional[str] = None
    status: int
    
    class Config:
        from_attributes = True

