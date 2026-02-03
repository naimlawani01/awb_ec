"""Common schemas used across the application."""
from datetime import date, datetime
from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Pagination parameters."""
    page: int = Field(default=1, ge=1, description="Page number")
    page_size: int = Field(default=25, ge=1, le=100, description="Items per page")
    
    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class DateRangeParams(BaseModel):
    """Date range filter parameters."""
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Generic paginated response."""
    items: List[T]
    total: int
    page: int
    page_size: int
    total_pages: int
    
    class Config:
        from_attributes = True


class SuccessResponse(BaseModel):
    """Generic success response."""
    success: bool = True
    message: str = "Operation completed successfully"
    data: Optional[Any] = None


class ErrorResponse(BaseModel):
    """Generic error response."""
    success: bool = False
    error: str
    detail: Optional[str] = None


class TableInfo(BaseModel):
    """Database table information."""
    name: str
    row_count: int
    columns: List[str]


class DatabaseStats(BaseModel):
    """Database statistics."""
    tables: List[TableInfo]
    total_documents: int
    total_shipments: int
    total_contacts: int

