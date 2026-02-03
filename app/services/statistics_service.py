"""Statistics service for dashboard and reports."""
import time
from datetime import date, datetime, timedelta
from typing import List, Dict, Optional
from calendar import month_name
from sqlalchemy import select, func, and_, extract, cast, Date
from sqlalchemy.orm import Session

from app.models.awb_models import (
    Document, Shipment, Contact, UserAirline, UserAirport
)
from app.schemas.statistics import (
    MonthlyVolumeItem, MonthlyVolumeResponse,
    TopClient, TopClientsResponse,
    DestinationStats, DestinationStatsResponse,
    StatisticsResponse, StatusDistribution, DailyTrend
)
from app.services.document_service import DocumentService


class StatisticsService:
    """Service for generating statistics and reports."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def get_dashboard_stats(self) -> StatisticsResponse:
        """Get comprehensive dashboard statistics."""
        today = date.today()
        week_ago = today - timedelta(days=7)
        month_ago = today - timedelta(days=30)
        
        # Total counts
        total_documents = self._count_table(Document)
        total_shipments = self._count_table(Shipment)
        total_contacts = self._count_table(Contact)
        total_airlines = self._count_table(UserAirline)
        total_airports = self._count_table(UserAirport)
        
        # Today's documents
        documents_today = self._count_documents_since(today)
        documents_this_week = self._count_documents_since(week_ago)
        documents_this_month = self._count_documents_since(month_ago)
        
        # Status distribution
        status_distribution = self._get_status_distribution()
        
        # Daily trends
        daily_trends = self._get_daily_trends(30)
        
        # Top destinations/origins
        top_destinations = self._get_top_destinations(10)
        top_origins = self._get_top_origins(10)
        
        # Growth metrics
        mom_growth = self._calculate_mom_growth()
        yoy_growth = self._calculate_yoy_growth()
        
        return StatisticsResponse(
            total_documents=total_documents,
            total_shipments=total_shipments,
            total_contacts=total_contacts,
            total_airlines=total_airlines,
            total_airports=total_airports,
            documents_today=documents_today,
            documents_this_week=documents_this_week,
            documents_this_month=documents_this_month,
            document_status_distribution=status_distribution,
            daily_trends=daily_trends,
            top_destinations=top_destinations,
            top_origins=top_origins,
            mom_growth=mom_growth,
            yoy_growth=yoy_growth,
        )
    
    def get_monthly_volume(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> MonthlyVolumeResponse:
        """Get monthly volume statistics."""
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=365)
        
        start_ts = self._date_to_timestamp(start_date)
        end_ts = self._date_to_timestamp(end_date + timedelta(days=1)) - 1
        
        # Convert timestamp to date for extraction
        # Use to_timestamp() to convert bigint (in milliseconds) to timestamp
        # Divide by 1000 since timestamps are stored in milliseconds
        doc_date_as_ts = func.to_timestamp(Document.document_date / 1000)
        
        # Documents by month
        doc_query = select(
            extract('year', doc_date_as_ts).label('year'),
            extract('month', doc_date_as_ts).label('month'),
            func.count(Document.id).label('count')
        ).where(
            and_(
                Document.document_date >= start_ts,
                Document.document_date <= end_ts
            )
        ).group_by(
            extract('year', doc_date_as_ts),
            extract('month', doc_date_as_ts)
        ).order_by('year', 'month')
        
        doc_results = self.db.execute(doc_query).all()
        
        # Shipments by month
        ship_query = select(
            extract('year', Shipment.shipment_date).label('year'),
            extract('month', Shipment.shipment_date).label('month'),
            func.count(Shipment.id).label('count')
        ).where(
            and_(
                Shipment.shipment_date >= start_date,
                Shipment.shipment_date <= end_date
            )
        ).group_by(
            extract('year', Shipment.shipment_date),
            extract('month', Shipment.shipment_date)
        ).order_by('year', 'month')
        
        ship_results = self.db.execute(ship_query).all()
        
        # Combine results
        monthly_data = {}
        for year, month, count in doc_results:
            key = (int(year), int(month))
            if key not in monthly_data:
                monthly_data[key] = {"doc_count": 0, "ship_count": 0}
            monthly_data[key]["doc_count"] = count
        
        for year, month, count in ship_results:
            key = (int(year), int(month))
            if key not in monthly_data:
                monthly_data[key] = {"doc_count": 0, "ship_count": 0}
            monthly_data[key]["ship_count"] = count
        
        items = []
        total_docs = 0
        total_ships = 0
        
        for (year, month), data in sorted(monthly_data.items()):
            items.append(MonthlyVolumeItem(
                year=year,
                month=month,
                month_name=month_name[month],
                document_count=data["doc_count"],
                shipment_count=data["ship_count"]
            ))
            total_docs += data["doc_count"]
            total_ships += data["ship_count"]
        
        return MonthlyVolumeResponse(
            data=items,
            total_documents=total_docs,
            total_shipments=total_ships,
            period_start=start_date,
            period_end=end_date
        )
    
    def get_top_clients(self, limit: int = 10) -> TopClientsResponse:
        """Get top shippers and consignees."""
        # Top shippers
        shipper_query = select(
            Document.shipper,
            func.count(Document.id).label('count')
        ).where(
            Document.shipper.isnot(None)
        ).group_by(Document.shipper).order_by(
            func.count(Document.id).desc()
        ).limit(limit)
        
        shipper_results = self.db.execute(shipper_query).all()
        total_docs = self._count_table(Document)
        
        shippers = []
        for name, count in shipper_results:
            if name and name.strip():
                shippers.append(TopClient(
                    name=name.strip(),
                    contact_type="Shipper",
                    document_count=count,
                    shipment_count=0,
                    percentage=round((count / total_docs * 100) if total_docs > 0 else 0, 2)
                ))
        
        # Top consignees
        consignee_query = select(
            Document.consignee,
            func.count(Document.id).label('count')
        ).where(
            Document.consignee.isnot(None)
        ).group_by(Document.consignee).order_by(
            func.count(Document.id).desc()
        ).limit(limit)
        
        consignee_results = self.db.execute(consignee_query).all()
        
        consignees = []
        for name, count in consignee_results:
            if name and name.strip():
                consignees.append(TopClient(
                    name=name.strip(),
                    contact_type="Consignee",
                    document_count=count,
                    shipment_count=0,
                    percentage=round((count / total_docs * 100) if total_docs > 0 else 0, 2)
                ))
        
        # Count unique clients
        total_clients = self._count_table(Contact)
        
        return TopClientsResponse(
            shippers=shippers,
            consignees=consignees,
            total_clients=total_clients
        )
    
    def get_destination_stats(self, limit: int = 10) -> DestinationStatsResponse:
        """Get destination and origin statistics."""
        total = self._count_table(Document)
        
        destinations = self._get_top_destinations(limit)
        origins = self._get_top_origins(limit)
        
        # Count unique routes
        route_query = select(
            func.count(func.distinct(
                func.concat(Document.origin, '-', Document.destination)
            ))
        )
        total_routes = self.db.execute(route_query).scalar() or 0
        
        return DestinationStatsResponse(
            destinations=destinations,
            origins=origins,
            total_routes=total_routes
        )
    
    def _count_table(self, model) -> int:
        """Count rows in a table."""
        query = select(func.count(model.id))
        return self.db.execute(query).scalar() or 0
    
    def _date_to_timestamp(self, d: date) -> int:
        """Convert a date to Unix timestamp in milliseconds."""
        return int(datetime.combine(d, datetime.min.time()).timestamp() * 1000)
    
    def _count_documents_since(self, since_date: date) -> int:
        """Count documents created since a date."""
        timestamp = self._date_to_timestamp(since_date)
        query = select(func.count(Document.id)).where(
            Document.document_date >= timestamp
        )
        return self.db.execute(query).scalar() or 0
    
    def _get_status_distribution(self) -> List[StatusDistribution]:
        """Get document status distribution."""
        query = select(
            Document.status,
            func.count(Document.id).label('count')
        ).group_by(Document.status)
        
        results = self.db.execute(query).all()
        total = sum(count for _, count in results)
        
        distribution = []
        for status, count in results:
            distribution.append(StatusDistribution(
                status=status,
                status_name=DocumentService.get_document_status_name(status),
                count=count,
                percentage=round((count / total * 100) if total > 0 else 0, 2)
            ))
        
        return sorted(distribution, key=lambda x: x.count, reverse=True)
    
    def _get_daily_trends(self, days: int) -> List[DailyTrend]:
        """Get daily document creation trends."""
        start_date = date.today() - timedelta(days=days)
        start_ts = self._date_to_timestamp(start_date)
        
        # Convert bigint timestamp (in milliseconds) to date for grouping
        doc_date_as_date = cast(func.to_timestamp(Document.document_date / 1000), Date)
        
        query = select(
            doc_date_as_date.label('day'),
            func.count(Document.id).label('count')
        ).where(
            Document.document_date >= start_ts
        ).group_by(
            doc_date_as_date
        ).order_by('day')
        
        results = self.db.execute(query).all()
        
        return [
            DailyTrend(date=day, count=count)
            for day, count in results if day
        ]
    
    def _get_top_destinations(self, limit: int) -> List[DestinationStats]:
        """Get top destination airports."""
        total = self._count_table(Document)
        
        query = select(
            Document.destination,
            func.count(Document.id).label('count')
        ).where(
            Document.destination.isnot(None)
        ).group_by(Document.destination).order_by(
            func.count(Document.id).desc()
        ).limit(limit)
        
        results = self.db.execute(query).all()
        
        destinations = []
        for dest, count in results:
            if dest and dest.strip():
                # Try to get airport name
                airport_name = self._get_airport_name(dest.strip())
                destinations.append(DestinationStats(
                    airport_code=dest.strip(),
                    airport_name=airport_name,
                    count=count,
                    percentage=round((count / total * 100) if total > 0 else 0, 2)
                ))
        
        return destinations
    
    def _get_top_origins(self, limit: int) -> List[DestinationStats]:
        """Get top origin airports."""
        total = self._count_table(Document)
        
        query = select(
            Document.origin,
            func.count(Document.id).label('count')
        ).where(
            Document.origin.isnot(None)
        ).group_by(Document.origin).order_by(
            func.count(Document.id).desc()
        ).limit(limit)
        
        results = self.db.execute(query).all()
        
        origins = []
        for origin, count in results:
            if origin and origin.strip():
                airport_name = self._get_airport_name(origin.strip())
                origins.append(DestinationStats(
                    airport_code=origin.strip(),
                    airport_name=airport_name,
                    count=count,
                    percentage=round((count / total * 100) if total > 0 else 0, 2)
                ))
        
        return origins
    
    def _get_airport_name(self, code: str) -> Optional[str]:
        """Get airport name from code."""
        query = select(UserAirport.name).where(
            UserAirport.code == code
        )
        result = self.db.execute(query).scalar()
        return result
    
    def _calculate_mom_growth(self) -> Optional[float]:
        """Calculate month-over-month growth."""
        today = date.today()
        this_month_start = today.replace(day=1)
        last_month_end = this_month_start - timedelta(days=1)
        last_month_start = last_month_end.replace(day=1)
        
        this_month_count = self._count_documents_in_range(
            this_month_start, today
        )
        last_month_count = self._count_documents_in_range(
            last_month_start, last_month_end
        )
        
        if last_month_count == 0:
            return None
        
        return round(
            ((this_month_count - last_month_count) / last_month_count) * 100,
            2
        )
    
    def _calculate_yoy_growth(self) -> Optional[float]:
        """Calculate year-over-year growth."""
        today = date.today()
        year_start = today.replace(month=1, day=1)
        last_year_start = year_start.replace(year=year_start.year - 1)
        last_year_same_day = today.replace(year=today.year - 1)
        
        this_year_count = self._count_documents_in_range(year_start, today)
        last_year_count = self._count_documents_in_range(
            last_year_start, last_year_same_day
        )
        
        if last_year_count == 0:
            return None
        
        return round(
            ((this_year_count - last_year_count) / last_year_count) * 100,
            2
        )
    
    def _count_documents_in_range(self, start: date, end: date) -> int:
        """Count documents in a date range."""
        start_ts = self._date_to_timestamp(start)
        # End of day for end date
        end_ts = self._date_to_timestamp(end + timedelta(days=1)) - 1
        query = select(func.count(Document.id)).where(
            and_(
                Document.document_date >= start_ts,
                Document.document_date <= end_ts
            )
        )
        return self.db.execute(query).scalar() or 0

