"""Reference data API endpoints (airlines, airports, rates)."""
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.core.database import get_awb_db
from app.core.security import require_viewer
from app.models.awb_models import UserAirline, UserAirport, RateAirCharges, RateAirWeight

router = APIRouter()


@router.get("/airlines")
async def list_airlines(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    List airlines with optional search.
    """
    query = select(UserAirline)
    
    if search:
        query = query.where(
            func.or_(
                UserAirline.name.ilike(f"%{search}%"),
                UserAirline.prefix.ilike(f"%{search}%"),
                UserAirline.designator.ilike(f"%{search}%"),
            )
        )
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0
    
    # Paginate
    query = query.order_by(UserAirline.name)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    airlines = db.execute(query).scalars().all()
    
    return {
        "items": [
            {
                "id": a.id,
                "prefix": a.prefix,
                "designator": a.designator,
                "name": a.name,
            }
            for a in airlines
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/airlines/{airline_id}")
async def get_airline(
    airline_id: int,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get airline by ID.
    """
    query = select(UserAirline).where(UserAirline.id == airline_id)
    airline = db.execute(query).scalar_one_or_none()
    
    if not airline:
        raise HTTPException(status_code=404, detail="Airline not found")
    
    return {
        "id": airline.id,
        "prefix": airline.prefix,
        "designator": airline.designator,
        "name": airline.name,
        "text": airline.text,
    }


@router.get("/airlines/by-prefix/{prefix}")
async def get_airline_by_prefix(
    prefix: str,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get airline by prefix code.
    """
    query = select(UserAirline).where(UserAirline.prefix == prefix)
    airline = db.execute(query).scalar_one_or_none()
    
    if not airline:
        raise HTTPException(status_code=404, detail="Airline not found")
    
    return {
        "id": airline.id,
        "prefix": airline.prefix,
        "designator": airline.designator,
        "name": airline.name,
    }


@router.get("/airports")
async def list_airports(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    search: Optional[str] = None,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    List airports with optional search.
    """
    query = select(UserAirport)
    
    if search:
        query = query.where(
            func.or_(
                UserAirport.name.ilike(f"%{search}%"),
                UserAirport.code.ilike(f"%{search}%"),
            )
        )
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0
    
    # Paginate
    query = query.order_by(UserAirport.name)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    airports = db.execute(query).scalars().all()
    
    return {
        "items": [
            {
                "id": a.id,
                "code": a.code,
                "name": a.name,
            }
            for a in airports
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/airports/{airport_id}")
async def get_airport(
    airport_id: int,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get airport by ID.
    """
    query = select(UserAirport).where(UserAirport.id == airport_id)
    airport = db.execute(query).scalar_one_or_none()
    
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")
    
    return {
        "id": airport.id,
        "code": airport.code,
        "name": airport.name,
    }


@router.get("/airports/by-code/{code}")
async def get_airport_by_code(
    code: str,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    Get airport by IATA code.
    """
    query = select(UserAirport).where(UserAirport.code == code.upper())
    airport = db.execute(query).scalar_one_or_none()
    
    if not airport:
        raise HTTPException(status_code=404, detail="Airport not found")
    
    return {
        "id": airport.id,
        "code": airport.code,
        "name": airport.name,
    }


@router.get("/rates/charges")
async def list_rate_charges(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    airline: Optional[str] = None,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    List air freight charge rates.
    """
    query = select(RateAirCharges)
    
    if airline:
        query = query.where(RateAirCharges.airline == airline)
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0
    
    # Paginate
    query = query.order_by(RateAirCharges.airline, RateAirCharges.code)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    rates = db.execute(query).scalars().all()
    
    return {
        "items": [
            {
                "id": r.id,
                "airline": r.airline,
                "code": r.code,
                "rate_info": r.rate_info,
            }
            for r in rates
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }


@router.get("/rates/weight")
async def list_rate_weight(
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=200),
    from_airport: Optional[str] = None,
    to_airport: Optional[str] = None,
    current_user: dict = Depends(require_viewer),
    db: Session = Depends(get_awb_db),
):
    """
    List air freight weight-based rates.
    """
    query = select(RateAirWeight)
    
    if from_airport:
        query = query.where(RateAirWeight.from_airport == from_airport)
    
    if to_airport:
        query = query.where(RateAirWeight.to_airport == to_airport)
    
    # Count
    count_query = select(func.count()).select_from(query.subquery())
    total = db.execute(count_query).scalar() or 0
    
    # Paginate
    query = query.order_by(RateAirWeight.from_airport, RateAirWeight.to_airport)
    query = query.offset((page - 1) * page_size).limit(page_size)
    
    rates = db.execute(query).scalars().all()
    
    return {
        "items": [
            {
                "id": r.id,
                "rate_type": r.rate_type,
                "airline_prefix": r.airline_prefix,
                "from_airport": r.from_airport,
                "to_airport": r.to_airport,
                "valid_from": str(r.valid_from_date) if r.valid_from_date else None,
                "valid_to": str(r.valid_to_date) if r.valid_to_date else None,
                "rates": r.rates,
            }
            for r in rates
        ],
        "total": total,
        "page": page,
        "page_size": page_size,
    }

