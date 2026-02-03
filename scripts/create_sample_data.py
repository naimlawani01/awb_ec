#!/usr/bin/env python3
"""
Create Sample Data Script

This script creates sample data for testing the AWB Management Platform
when no real AWB Editor database is available.

Usage:
    python create_sample_data.py
"""

import os
import sys
import random
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.models.awb_models import (
    AWBBase, Document, Shipment, Contact, UserAirline, UserAirport
)

# Sample data
AIRLINES = [
    ("125", "EK", "Emirates"),
    ("157", "QR", "Qatar Airways"),
    ("074", "KL", "KLM Royal Dutch Airlines"),
    ("057", "AF", "Air France"),
    ("020", "LH", "Lufthansa"),
    ("176", "EY", "Etihad Airways"),
    ("618", "SQ", "Singapore Airlines"),
    ("081", "QF", "Qantas"),
    ("006", "DL", "Delta Air Lines"),
    ("001", "AA", "American Airlines"),
]

AIRPORTS = [
    ("DXB", "Dubai International Airport"),
    ("DOH", "Hamad International Airport"),
    ("AMS", "Amsterdam Schiphol Airport"),
    ("CDG", "Paris Charles de Gaulle Airport"),
    ("FRA", "Frankfurt Airport"),
    ("AUH", "Abu Dhabi International Airport"),
    ("SIN", "Singapore Changi Airport"),
    ("SYD", "Sydney Kingsford Smith Airport"),
    ("JFK", "John F. Kennedy International Airport"),
    ("LAX", "Los Angeles International Airport"),
    ("LHR", "London Heathrow Airport"),
    ("HKG", "Hong Kong International Airport"),
    ("NRT", "Narita International Airport"),
    ("ICN", "Incheon International Airport"),
    ("BKK", "Suvarnabhumi Airport"),
]

SHIPPERS = [
    "Global Electronics Ltd.",
    "Pharma Solutions Inc.",
    "Fashion Forward Co.",
    "Auto Parts International",
    "Tech Components Ltd.",
    "Food Exporters Corp.",
    "Machinery World Inc.",
    "Chemical Industries Ltd.",
    "Textile Traders Co.",
    "Sports Equipment Int.",
]

CONSIGNEES = [
    "Import Specialists LLC",
    "Distribution Center Inc.",
    "Retail Networks Corp.",
    "Manufacturing Hub Ltd.",
    "Logistics Solutions Co.",
    "Trade Partners Inc.",
    "Supply Chain Masters",
    "Commerce Center Ltd.",
    "Wholesale Traders Co.",
    "Market Leaders Inc.",
]


def create_sample_database():
    """Create a SQLite database with sample data."""
    db_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "sample_awb_data.db"
    )
    
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    
    # Create tables
    AWBBase.metadata.create_all(engine)
    
    Session = sessionmaker(bind=engine)
    session = Session()
    
    print("Creating sample data...")
    
    # Create airlines
    for prefix, designator, name in AIRLINES:
        airline = UserAirline(
            station_id=1,
            prefix=prefix,
            designator=designator,
            name=name
        )
        session.add(airline)
    
    # Create airports
    for code, name in AIRPORTS:
        airport = UserAirport(
            station_id=1,
            code=code,
            name=name
        )
        session.add(airport)
    
    # Create contacts
    contact_ids = []
    for i, name in enumerate(SHIPPERS):
        contact = Contact(
            station_id=1,
            contact_type=1,  # Shipper
            display_name=name,
            account_number=f"SHP{i+1:04d}"
        )
        session.add(contact)
        session.flush()
        contact_ids.append(contact.id)
    
    for i, name in enumerate(CONSIGNEES):
        contact = Contact(
            station_id=1,
            contact_type=2,  # Consignee
            display_name=name,
            account_number=f"CNE{i+1:04d}"
        )
        session.add(contact)
    
    # Create documents
    for i in range(200):
        airline = random.choice(AIRLINES)
        origin, dest = random.sample(AIRPORTS, 2)
        shipper = random.choice(SHIPPERS)
        consignee = random.choice(CONSIGNEES)
        
        doc_date = datetime.now() - timedelta(days=random.randint(0, 365))
        
        document = Document(
            station_id=1,
            status=random.choice([1, 1, 1, 2, 2, 0]),  # Mostly active
            document_type=random.choice([1, 2, 3]),
            document_number=f"{airline[0]}-{random.randint(10000000, 99999999)}",
            master_document_number=f"{airline[0]}-{random.randint(10000000, 99999999)}" if random.random() > 0.5 else None,
            reference_number=f"REF{i+1:06d}" if random.random() > 0.3 else None,
            date_created=doc_date,
            date_modified=doc_date + timedelta(hours=random.randint(1, 48)),
            document_date=doc_date,
            shipper=shipper,
            consignee=consignee,
            origin=origin[0],
            destination=dest[0],
            route=f"{origin[0]}-{dest[0]}" if random.random() > 0.5 else f"{origin[0]}-{random.choice(AIRPORTS)[0]}-{dest[0]}",
            tags='--------',
        )
        session.add(document)
    
    # Create shipments
    for i in range(150):
        airline = random.choice(AIRLINES)
        origin, dest = random.sample(AIRPORTS, 2)
        shipper = random.choice(SHIPPERS)
        consignee = random.choice(CONSIGNEES)
        
        ship_date = datetime.now().date() - timedelta(days=random.randint(0, 365))
        
        shipment = Shipment(
            station_id=1,
            shipment_date=ship_date,
            import_export=random.choice([1, 2, 2]),  # Mostly export
            shipment_type=1,
            master_number=f"{airline[0]}-{random.randint(10000000, 99999999)}",
            house_number=f"H{random.randint(1000, 9999)}" if random.random() > 0.3 else None,
            shipper=shipper,
            consignee=consignee,
            origin=origin[0],
            destination=dest[0],
            event_status=random.choice(['RCS', 'DEP', 'ARR', 'DLV', 'NFD']),
            customs_status=random.choice([0, 1, 2]),
            transport=1,
        )
        session.add(shipment)
    
    session.commit()
    session.close()
    
    print(f"Sample database created at: {db_path}")
    print("\nTo use this database, set the following environment variable:")
    print(f"  AWB_DATABASE_URL=sqlite:///{db_path}")
    print("\nOr update the backend .env file.")


if __name__ == '__main__':
    create_sample_database()

