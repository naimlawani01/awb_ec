"""Statistics schemas for dashboard and reports."""
from datetime import date
from typing import Optional, List, Dict, Any
from pydantic import BaseModel


class MonthlyVolumeItem(BaseModel):
    """Monthly volume data point."""
    year: int
    month: int
    month_name: str
    document_count: int
    shipment_count: int


class MonthlyVolumeResponse(BaseModel):
    """Monthly volume statistics response."""
    data: List[MonthlyVolumeItem]
    total_documents: int
    total_shipments: int
    period_start: date
    period_end: date


class TopClient(BaseModel):
    """Top client data."""
    name: str
    contact_type: str
    document_count: int
    shipment_count: int
    percentage: float


class TopClientsResponse(BaseModel):
    """Top clients statistics response."""
    shippers: List[TopClient]
    consignees: List[TopClient]
    total_clients: int


class DestinationStats(BaseModel):
    """Destination statistics."""
    airport_code: str
    airport_name: Optional[str] = None
    country: Optional[str] = None
    count: int
    percentage: float


class DestinationStatsResponse(BaseModel):
    """Destination statistics response."""
    destinations: List[DestinationStats]
    origins: List[DestinationStats]
    total_routes: int


class StatusDistribution(BaseModel):
    """Status distribution data."""
    status: int
    status_name: str
    count: int
    percentage: float


class DailyTrend(BaseModel):
    """Daily trend data point."""
    date: date
    count: int


class StatisticsResponse(BaseModel):
    """Comprehensive statistics response for dashboard."""
    # Counts
    total_documents: int
    total_shipments: int
    total_contacts: int
    total_airlines: int
    total_airports: int
    
    # Today's stats
    documents_today: int
    documents_this_week: int
    documents_this_month: int
    
    # Status distribution
    document_status_distribution: List[StatusDistribution]
    
    # Recent trends (last 30 days)
    daily_trends: List[DailyTrend]
    
    # Top data
    top_destinations: List[DestinationStats]
    top_origins: List[DestinationStats]
    
    # Growth metrics
    mom_growth: Optional[float] = None  # Month over month
    yoy_growth: Optional[float] = None  # Year over year


class RevenueStats(BaseModel):
    """Revenue statistics (if charge data available)."""
    total_revenue: float
    currency: str
    by_airline: Dict[str, float]
    by_destination: Dict[str, float]
    monthly_revenue: List[Dict[str, Any]]


class KPIResponse(BaseModel):
    """Key Performance Indicators."""
    avg_processing_time_hours: Optional[float] = None
    on_time_delivery_rate: Optional[float] = None
    documents_per_day_avg: float
    peak_day: Optional[str] = None
    peak_hour: Optional[int] = None
    busiest_route: Optional[str] = None


class RouteStats(BaseModel):
    """Route statistics (origin -> destination)."""
    origin: str
    origin_name: Optional[str] = None
    destination: str
    destination_name: Optional[str] = None
    count: int
    percentage: float


class AirlineStats(BaseModel):
    """Airline statistics based on AWB prefix."""
    prefix: str
    airline_name: str
    count: int
    percentage: float


class RoutesResponse(BaseModel):
    """Routes statistics response."""
    routes: List[RouteStats]
    total_routes: int
    main_hub: Optional[str] = None


class AirlinesResponse(BaseModel):
    """Airlines statistics response."""
    airlines: List[AirlineStats]
    total_awbs: int

