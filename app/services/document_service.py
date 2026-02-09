"""Document service for AWB operations."""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import select, func, and_, or_
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.awb_models import Document, DocumentLog
from app.schemas.document import DocumentSearchParams


# No longer needed - using proper DateTime types


class DocumentService:
    """Service for document (AWB) operations."""
    
    # Document type names mapping
    DOCUMENT_TYPES = {
        1: "Air Waybill (AWB)",
        2: "House Waybill (HAWB)",
        3: "Master Waybill (MAWB)",
        4: "Commercial Invoice",
        5: "Packing List",
        6: "Certificate of Origin",
    }
    
    # Document status names mapping
    DOCUMENT_STATUS = {
        0: "Draft",
        1: "Active",
        2: "Completed",
        3: "Cancelled",
        4: "Archived",
    }
    
    def __init__(self, db: Session):
        self.db = db
    
    # Allowed columns for sorting
    SORTABLE_COLUMNS = {
        'document_number': Document.document_number,
        'reference_number': Document.reference_number,
        'shipper': Document.shipper,
        'consignee': Document.consignee,
        'origin': Document.origin,
        'destination': Document.destination,
        'document_date': Document.document_date,
        'date_created': Document.date_created,
        'status': Document.status,
    }
    
    def get_documents(
        self,
        page: int = 1,
        page_size: int = 25,
        search_params: Optional[DocumentSearchParams] = None,
        order_by: str = "date_created",
        order_dir: str = "desc"
    ) -> Tuple[List[Document], int]:
        """Get paginated list of documents with optional filters and sorting."""
        query = select(Document)
        
        # Apply filters
        if search_params:
            filters = []
            
            if search_params.awb_number:
                filters.append(
                    or_(
                        Document.document_number.ilike(f"%{search_params.awb_number}%"),
                        Document.master_document_number.ilike(f"%{search_params.awb_number}%")
                    )
                )
            
            if search_params.shipper:
                filters.append(Document.shipper.ilike(f"%{search_params.shipper}%"))
            
            if search_params.consignee:
                filters.append(Document.consignee.ilike(f"%{search_params.consignee}%"))
            
            if search_params.origin:
                filters.append(Document.origin.ilike(f"%{search_params.origin}%"))
            
            if search_params.destination:
                filters.append(Document.destination.ilike(f"%{search_params.destination}%"))
            
            if search_params.start_date:
                filters.append(Document.document_date >= search_params.start_date)
            
            if search_params.end_date:
                filters.append(Document.document_date <= search_params.end_date)
            
            if search_params.status is not None:
                filters.append(Document.status == search_params.status)
            
            if search_params.station_id:
                filters.append(Document.station_id == search_params.station_id)
            
            if filters:
                query = query.where(and_(*filters))
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0
        
        # Apply sorting
        sort_column = self.SORTABLE_COLUMNS.get(order_by, Document.date_created)
        if order_dir.lower() == "asc":
            query = query.order_by(sort_column.asc().nulls_last())
        else:
            query = query.order_by(sort_column.desc().nulls_last())
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        documents = self.db.execute(query).scalars().all()
        
        return documents, total
    
    def get_document_by_id(self, document_id: int) -> Optional[Document]:
        """Get single document by ID."""
        query = select(Document).where(Document.id == document_id)
        return self.db.execute(query).scalar_one_or_none()
    
    def get_document_by_number(self, document_number: str) -> Optional[Document]:
        """Get document by AWB number."""
        query = select(Document).where(
            or_(
                Document.document_number == document_number,
                Document.master_document_number == document_number
            )
        )
        return self.db.execute(query).scalar_one_or_none()
    
    def search_documents(self, search_text: str, limit: int = 50) -> List[Document]:
        """Full-text search in documents."""
        query = select(Document).where(
            or_(
                Document.document_number.ilike(f"%{search_text}%"),
                Document.master_document_number.ilike(f"%{search_text}%"),
                Document.shipper.ilike(f"%{search_text}%"),
                Document.consignee.ilike(f"%{search_text}%"),
                Document.search_text.ilike(f"%{search_text}%")
            )
        ).order_by(Document.date_created.desc()).limit(limit)
        
        return self.db.execute(query).scalars().all()
    
    def get_document_logs(self, document_id: int) -> List[DocumentLog]:
        """Get activity logs for a document."""
        query = select(DocumentLog).where(
            DocumentLog.document_id == document_id
        ).order_by(DocumentLog.log_date.desc())
        
        return self.db.execute(query).scalars().all()
    
    def get_documents_by_client(
        self,
        client_name: str,
        client_type: str = "shipper",
        limit: int = 100
    ) -> List[Document]:
        """Get documents for a specific client."""
        if client_type == "shipper":
            query = select(Document).where(
                Document.shipper.ilike(f"%{client_name}%")
            )
        else:
            query = select(Document).where(
                Document.consignee.ilike(f"%{client_name}%")
            )
        
        query = query.order_by(Document.document_date.desc()).limit(limit)
        return self.db.execute(query).scalars().all()
    
    def get_document_count(self) -> int:
        """Get total document count."""
        query = select(func.count(Document.id))
        return self.db.execute(query).scalar() or 0
    
    def get_documents_by_date_range(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> List[Document]:
        """Get documents within a date range."""
        query = select(Document).where(
            and_(
                Document.document_date >= start_date,
                Document.document_date <= end_date
            )
        ).order_by(Document.document_date.desc())
        
        return self.db.execute(query).scalars().all()
    
    def get_recent_documents(self, days: int = 7, limit: int = 50) -> List[Document]:
        """Get recently created documents."""
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        query = select(Document).where(
            Document.date_created >= cutoff_date
        ).order_by(Document.date_created.desc()).limit(limit)
        
        return self.db.execute(query).scalars().all()
    
    @classmethod
    def get_document_type_name(cls, type_id: int) -> str:
        """Get document type display name."""
        return cls.DOCUMENT_TYPES.get(type_id, f"Unknown ({type_id})")
    
    @classmethod
    def get_document_status_name(cls, status_id: int) -> str:
        """Get document status display name."""
        return cls.DOCUMENT_STATUS.get(status_id, f"Unknown ({status_id})")

