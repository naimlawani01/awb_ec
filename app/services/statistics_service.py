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
    StatisticsResponse, StatusDistribution, DailyTrend,
    RouteStats, RoutesResponse, AirlineStats, AirlinesResponse
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
        
        # Shipments by month (shipment_date is also stored as timestamp in ms)
        ship_date_as_ts = func.to_timestamp(Shipment.shipment_date / 1000)
        ship_query = select(
            extract('year', ship_date_as_ts).label('year'),
            extract('month', ship_date_as_ts).label('month'),
            func.count(Shipment.id).label('count')
        ).where(
            and_(
                Shipment.shipment_date >= start_ts,
                Shipment.shipment_date <= end_ts
            )
        ).group_by(
            extract('year', ship_date_as_ts),
            extract('month', ship_date_as_ts)
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
    
    # Mapping des préfixes AWB vers les compagnies aériennes
    AIRLINE_PREFIXES = {
        "001": "American Airlines",
        "006": "Delta Air Lines",
        "014": "Air Canada",
        "016": "United Airlines",
        "020": "Lufthansa",
        "027": "Air India",
        "045": "Aeroméxico",
        "055": "Air France",
        "057": "Air France",
        "071": "Ethiopian Airlines",
        "074": "KLM Royal Dutch",
        "077": "TAP Air Portugal",
        "079": "TAM Airlines",
        "081": "Qantas",
        "083": "South African Airways",
        "098": "Asiana Airlines",
        "105": "British Airways",
        "114": "Japan Airlines",
        "117": "SAS Scandinavian",
        "118": "Singapore Airlines",
        "125": "Emirates",
        "131": "Japan Airlines",
        "139": "China Eastern",
        "147": "Air France Cargo",
        "157": "Qatar Airways",
        "160": "Cathay Pacific",
        "172": "EVA Air",
        "176": "Emirates",
        "180": "Korean Air",
        "205": "All Nippon Airways",
        "217": "Thai Airways",
        "220": "Lufthansa Cargo",
        "235": "Turkish Airlines",
        "258": "Air Algérie",
        "279": "Royal Air Maroc",
        "297": "ASKY Airlines",
        "302": "Air Austral",
        "369": "Air China",
        "580": "China Southern",
        "618": "Air China Cargo",
        "695": "China Cargo Airlines",
        "706": "Wamos Air",
        "729": "LATAM Cargo",
        "781": "TAAG Angola",
        "837": "Saudia Cargo",
        "932": "Kenya Airways",
    }
    
    def get_routes_stats(self, limit: int = 20) -> RoutesResponse:
        """Get route statistics (origin -> destination)."""
        total = self._count_table(Document)
        
        # Get routes with counts
        query = select(
            Document.origin,
            Document.destination,
            func.count(Document.id).label('count')
        ).where(
            and_(
                Document.origin.isnot(None),
                Document.destination.isnot(None),
                Document.origin != '',
                Document.destination != ''
            )
        ).group_by(
            Document.origin,
            Document.destination
        ).order_by(
            func.count(Document.id).desc()
        ).limit(limit)
        
        results = self.db.execute(query).all()
        
        routes = []
        for origin, dest, count in results:
            # Normalize destination (extract airport code)
            dest_code = self._extract_airport_code(dest)
            origin_code = origin.strip().upper() if origin else ""
            
            routes.append(RouteStats(
                origin=origin_code,
                origin_name=self._get_airport_name(origin_code),
                destination=dest_code,
                destination_name=self._get_airport_name(dest_code) or dest.strip(),
                count=count,
                percentage=round((count / total * 100) if total > 0 else 0, 2)
            ))
        
        # Find main hub (most common origin)
        main_hub = None
        if routes:
            origins = {}
            for r in routes:
                origins[r.origin] = origins.get(r.origin, 0) + r.count
            main_hub = max(origins, key=origins.get) if origins else None
        
        return RoutesResponse(
            routes=routes,
            total_routes=len(results),
            main_hub=main_hub
        )
    
    def get_airlines_stats(self, limit: int = 10) -> AirlinesResponse:
        """Get airline statistics based on AWB prefixes."""
        # Extract prefix from document_number (first 3 chars using LEFT function)
        prefix_expr = func.left(Document.document_number, 3)
        
        query = select(
            prefix_expr.label('prefix'),
            func.count(Document.id).label('count')
        ).where(
            Document.document_number.isnot(None)
        ).group_by(
            prefix_expr
        ).order_by(
            func.count(Document.id).desc()
        ).limit(limit)
        
        results = self.db.execute(query).all()
        total = sum(count for _, count in results)
        
        airlines = []
        for prefix, count in results:
            if prefix:
                airline_name = self.AIRLINE_PREFIXES.get(
                    prefix, 
                    f"Airline ({prefix})"
                )
                airlines.append(AirlineStats(
                    prefix=prefix,
                    airline_name=airline_name,
                    count=count,
                    percentage=round((count / total * 100) if total > 0 else 0, 2)
                ))
        
        return AirlinesResponse(
            airlines=airlines,
            total_awbs=total
        )
    
    def _extract_airport_code(self, destination: str) -> str:
        """Extract airport code from destination string."""
        if not destination:
            return ""
        
        dest = destination.strip().upper()
        
        # Common patterns: "MONTREAL YUL", "CAIRO   CAI", "KUWAIT  KWI"
        parts = dest.split()
        
        # If last part is 3 letters, it's likely the code
        if len(parts) > 1 and len(parts[-1]) == 3 and parts[-1].isalpha():
            return parts[-1]
        
        # Known mappings for inconsistent data
        code_mapping = {
            "MONTREAL": "YUL",
            "KUWAIT": "KWI",
            "LAGOS": "LOS",
            "BAGDAD": "BGW",
            "MALDIVES": "MLE",
            "KINSHASA": "FIH",
            "KINSHASHA": "FIH",
        }
        
        for city, code in code_mapping.items():
            if city in dest:
                return code
        
        # Return first 3 chars as fallback
        return dest[:3] if len(dest) >= 3 else dest

