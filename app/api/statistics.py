"""Statistics API endpoints."""
from datetime import date
from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_awb_db
from app.core.security import require_viewer
from app.services.statistics_service import StatisticsService
from app.schemas.statistics import (
    StatisticsResponse, MonthlyVolumeResponse,
    TopClientsResponse, DestinationStatsResponse
)

router = APIRouter()


@router.get("/dashboard", response_model=StatisticsResponse)
async def get_dashboard_statistics(
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get comprehensive dashboard statistics.
    """
    service = StatisticsService(db)
    return service.get_dashboard_stats()


@router.get("/monthly-volume", response_model=MonthlyVolumeResponse)
async def get_monthly_volume(
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get monthly document and shipment volume statistics.
    """
    service = StatisticsService(db)
    return service.get_monthly_volume(start_date, end_date)


@router.get("/top-clients", response_model=TopClientsResponse)
async def get_top_clients(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get top shippers and consignees.
    """
    service = StatisticsService(db)
    return service.get_top_clients(limit)


@router.get("/destinations", response_model=DestinationStatsResponse)
async def get_destination_statistics(
    limit: int = Query(10, ge=1, le=50),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get destination and origin statistics.
    """
    service = StatisticsService(db)
    return service.get_destination_stats(limit)


@router.get("/summary")
async def get_summary_statistics(
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get quick summary statistics for widgets.
    """
    service = StatisticsService(db)
    stats = service.get_dashboard_stats()
    
    return {
        "totals": {
            "documents": stats.total_documents,
            "shipments": stats.total_shipments,
            "contacts": stats.total_contacts,
            "airlines": stats.total_airlines,
            "airports": stats.total_airports,
        },
        "recent": {
            "today": stats.documents_today,
            "this_week": stats.documents_this_week,
            "this_month": stats.documents_this_month,
        },
        "growth": {
            "mom": stats.mom_growth,
            "yoy": stats.yoy_growth,
        }
    }


@router.get("/trends")
async def get_trend_data(
    days: int = Query(30, ge=7, le=365),
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get trend data for charts.
    """
    service = StatisticsService(db)
    stats = service.get_dashboard_stats()
    
    return {
        "period_days": days,
        "daily_trends": [
            {"date": str(t.date), "count": t.count}
            for t in stats.daily_trends
        ],
        "status_distribution": [
            {
                "status": s.status,
                "name": s.status_name,
                "count": s.count,
                "percentage": s.percentage
            }
            for s in stats.document_status_distribution
        ],
        "top_destinations": [
            {
                "code": d.airport_code,
                "name": d.airport_name,
                "count": d.count,
                "percentage": d.percentage
            }
            for d in stats.top_destinations
        ],
        "top_origins": [
            {
                "code": o.airport_code,
                "name": o.airport_name,
                "count": o.count,
                "percentage": o.percentage
            }
            for o in stats.top_origins
        ],
    }

