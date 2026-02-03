"""Contact schemas for API validation."""
from typing import Optional, List
from pydantic import BaseModel


# Contact type constants
CONTACT_TYPE_SHIPPER = 1
CONTACT_TYPE_CONSIGNEE = 2
CONTACT_TYPE_AGENT = 3
CONTACT_TYPE_NOTIFY = 4
CONTACT_TYPE_FORWARDER = 5

CONTACT_TYPE_NAMES = {
    CONTACT_TYPE_SHIPPER: "Shipper",
    CONTACT_TYPE_CONSIGNEE: "Consignee",
    CONTACT_TYPE_AGENT: "Agent",
    CONTACT_TYPE_NOTIFY: "Notify Party",
    CONTACT_TYPE_FORWARDER: "Freight Forwarder",
}


class ContactBase(BaseModel):
    """Base contact schema."""
    contact_type: int
    display_name: Optional[str] = None
    account_number: Optional[str] = None


class ContactResponse(ContactBase):
    """Full contact response."""
    id: int
    station_id: int
    contact_type_name: Optional[str] = None
    
    class Config:
        from_attributes = True
    
    @classmethod
    def from_orm_with_type(cls, obj):
        """Create response with contact type name."""
        data = {
            "id": obj.id,
            "station_id": obj.station_id,
            "contact_type": obj.contact_type,
            "display_name": obj.display_name,
            "account_number": obj.account_number,
            "contact_type_name": CONTACT_TYPE_NAMES.get(obj.contact_type, "Unknown")
        }
        return cls(**data)


class ContactListItem(BaseModel):
    """Simplified contact for list views."""
    id: int
    contact_type: int
    contact_type_name: str
    display_name: Optional[str] = None
    account_number: Optional[str] = None
    
    class Config:
        from_attributes = True


class ContactListResponse(BaseModel):
    """Paginated contact list response."""
    items: List[ContactListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ContactSearchParams(BaseModel):
    """Contact search parameters."""
    display_name: Optional[str] = None
    account_number: Optional[str] = None
    contact_type: Optional[int] = None
    station_id: Optional[int] = None


class ContactStats(BaseModel):
    """Contact statistics by type."""
    total: int
    by_type: dict

