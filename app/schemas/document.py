"""Document (AWB) schemas for API validation."""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class DocumentBase(BaseModel):
    """Base document schema."""
    document_number: Optional[str] = None
    master_document_number: Optional[str] = None
    reference_number: Optional[str] = None
    document_type: Optional[int] = None
    status: int
    shipper: Optional[str] = None
    consignee: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    route: Optional[str] = None


class DocumentResponse(DocumentBase):
    """Document response schema with all fields."""
    id: int
    station_id: int
    shipment_id: Optional[int] = None
    date_created: Optional[datetime] = None
    date_modified: Optional[datetime] = None
    document_date: Optional[datetime] = None
    created_by: Optional[int] = None
    modified_by: Optional[int] = None
    owner: Optional[int] = None
    tags: Optional[str] = None
    
    class Config:
        from_attributes = True


class DocumentListItem(BaseModel):
    """Simplified document for list views."""
    id: int
    document_number: Optional[str] = None
    document_type: Optional[int] = None
    status: int
    shipper: Optional[str] = None
    consignee: Optional[str] = None
    origin: Optional[str] = None
    destination: Optional[str] = None
    document_date: Optional[datetime] = None
    date_created: Optional[datetime] = None
    
    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    """Paginated document list response."""
    items: List[DocumentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class DocumentSearchParams(BaseModel):
    """Document search parameters."""
    awb_number: Optional[str] = Field(None, description="AWB number to search")
    shipper: Optional[str] = Field(None, description="Shipper name")
    consignee: Optional[str] = Field(None, description="Consignee name")
    origin: Optional[str] = Field(None, description="Origin airport code")
    destination: Optional[str] = Field(None, description="Destination airport code")
    start_date: Optional[datetime] = Field(None, description="Start date filter")
    end_date: Optional[datetime] = Field(None, description="End date filter")
    status: Optional[int] = Field(None, description="Document status")
    station_id: Optional[int] = Field(None, description="Station ID")


class DocumentTypeCount(BaseModel):
    """Document type statistics."""
    document_type: int
    type_name: str
    count: int


class DocumentStatusCount(BaseModel):
    """Document status statistics."""
    status: int
    status_name: str
    count: int

