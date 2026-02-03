"""Contact service for shipper/consignee management."""
from typing import Optional, List, Tuple, Dict
from sqlalchemy import select, func, and_
from sqlalchemy.orm import Session

from app.models.awb_models import Contact, Document, Shipment
from app.schemas.contact import ContactSearchParams, CONTACT_TYPE_NAMES


class ContactService:
    """Service for contact operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_contacts(
        self,
        page: int = 1,
        page_size: int = 25,
        search_params: Optional[ContactSearchParams] = None
    ) -> Tuple[List[Contact], int]:
        """Get paginated list of contacts with optional filters."""
        query = select(Contact)
        
        # Apply filters
        if search_params:
            filters = []
            
            if search_params.display_name:
                filters.append(
                    Contact.display_name.ilike(f"%{search_params.display_name}%")
                )
            
            if search_params.account_number:
                filters.append(
                    Contact.account_number.ilike(f"%{search_params.account_number}%")
                )
            
            if search_params.contact_type is not None:
                filters.append(Contact.contact_type == search_params.contact_type)
            
            if search_params.station_id:
                filters.append(Contact.station_id == search_params.station_id)
            
            if filters:
                query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0
        
        # Apply pagination and ordering
        query = query.order_by(Contact.display_name)
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        contacts = self.db.execute(query).scalars().all()
        
        return contacts, total
    
    def get_contact_by_id(self, contact_id: int) -> Optional[Contact]:
        """Get single contact by ID."""
        query = select(Contact).where(Contact.id == contact_id)
        return self.db.execute(query).scalar_one_or_none()
    
    def get_contacts_by_type(self, contact_type: int, limit: int = 100) -> List[Contact]:
        """Get contacts by type."""
        query = select(Contact).where(
            Contact.contact_type == contact_type
        ).order_by(Contact.display_name).limit(limit)
        
        return self.db.execute(query).scalars().all()
    
    def search_contacts(self, search_text: str, limit: int = 50) -> List[Contact]:
        """Search contacts by name or account number."""
        query = select(Contact).where(
            func.or_(
                Contact.display_name.ilike(f"%{search_text}%"),
                Contact.account_number.ilike(f"%{search_text}%")
            )
        ).order_by(Contact.display_name).limit(limit)
        
        return self.db.execute(query).scalars().all()
    
    def get_contact_count(self) -> int:
        """Get total contact count."""
        query = select(func.count(Contact.id))
        return self.db.execute(query).scalar() or 0
    
    def get_contact_stats(self) -> Dict[str, int]:
        """Get contact statistics by type."""
        query = select(
            Contact.contact_type,
            func.count(Contact.id).label("count")
        ).group_by(Contact.contact_type)
        
        results = self.db.execute(query).all()
        
        stats = {"total": 0}
        for contact_type, count in results:
            type_name = CONTACT_TYPE_NAMES.get(contact_type, f"Type {contact_type}")
            stats[type_name] = count
            stats["total"] += count
        
        return stats
    
    def get_contact_documents(self, contact_id: int, limit: int = 50) -> List[Document]:
        """Get documents associated with a contact."""
        contact = self.get_contact_by_id(contact_id)
        if not contact:
            return []
        
        # Search by contact name in documents
        query = select(Document).where(
            func.or_(
                Document.shipper.ilike(f"%{contact.display_name}%"),
                Document.consignee.ilike(f"%{contact.display_name}%")
            )
        ).order_by(Document.document_date.desc()).limit(limit)
        
        return self.db.execute(query).scalars().all()
    
    def get_contact_shipments(self, contact_id: int, limit: int = 50) -> List[Shipment]:
        """Get shipments associated with a contact."""
        contact = self.get_contact_by_id(contact_id)
        if not contact:
            return []
        
        # Get shipments by contact ID relationships
        query = select(Shipment).where(
            func.or_(
                Shipment.shipper_contact_id == contact_id,
                Shipment.consignee_contact_id == contact_id,
                Shipment.also_notify_contact_id == contact_id,
                Shipment.freight_forwarder_contact_id == contact_id
            )
        ).order_by(Shipment.shipment_date.desc()).limit(limit)
        
        return self.db.execute(query).scalars().all()
    
    def get_top_shippers(self, limit: int = 10) -> List[Dict]:
        """Get top shippers by document count."""
        query = select(
            Document.shipper,
            func.count(Document.id).label("count")
        ).where(
            Document.shipper.isnot(None)
        ).group_by(
            Document.shipper
        ).order_by(
            func.count(Document.id).desc()
        ).limit(limit)
        
        results = self.db.execute(query).all()
        return [{"name": name, "count": count} for name, count in results if name]
    
    def get_top_consignees(self, limit: int = 10) -> List[Dict]:
        """Get top consignees by document count."""
        query = select(
            Document.consignee,
            func.count(Document.id).label("count")
        ).where(
            Document.consignee.isnot(None)
        ).group_by(
            Document.consignee
        ).order_by(
            func.count(Document.id).desc()
        ).limit(limit)
        
        results = self.db.execute(query).all()
        return [{"name": name, "count": count} for name, count in results if name]
    
    @staticmethod
    def get_contact_type_name(contact_type: int) -> str:
        """Get contact type display name."""
        return CONTACT_TYPE_NAMES.get(contact_type, f"Unknown ({contact_type})")

