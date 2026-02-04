"""
SQLAlchemy models for AWB Editor database tables.
These models map to the existing PostgreSQL tables (read-only).
"""
from datetime import date, datetime
from sqlalchemy import (
    Column, Integer, BigInteger, String, SmallInteger, Date, DateTime,
    ForeignKey, LargeBinary, Text, CHAR
)
from sqlalchemy.orm import declarative_base, relationship

AWBBase = declarative_base()


class AWBAutofill(AWBBase):
    """AWB autofill configuration for quick data entry."""
    __tablename__ = "awb_autofill"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer)
    airline_prefixes = Column(String(50))
    iata_agent_codes = Column(String(80))
    sph_codes = Column(String(50))
    destination_airport_codes = Column(String(50))
    destination_country_codes = Column(String(50))
    signature_names = Column(String(200))
    actions = Column(String(5000))
    signature_image = Column(LargeBinary)


class AWBStockNumber(AWBBase):
    """AWB stock number management."""
    __tablename__ = "awb_stock_number"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    stock_status = Column(SmallInteger, nullable=False)
    airline_prefix = Column(Integer, nullable=False)
    serial_number = Column(Integer, nullable=False)
    block = Column(Integer, nullable=False, default=1)
    numbers_available = Column(Integer, nullable=False, default=1)
    agent_iata_code = Column(Integer)
    origin = Column(String(5))
    date_created = Column(DateTime, nullable=False)


class Contact(AWBBase):
    """Contact information (shippers, consignees, agents)."""
    __tablename__ = "contact"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    contact_type = Column(SmallInteger, nullable=False)
    display_name = Column(String(100))
    account_number = Column(String(30))
    contact_data = Column(LargeBinary)


class Document(AWBBase):
    """AWB and other document records."""
    __tablename__ = "document"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    shipment_id = Column(Integer)
    status = Column(SmallInteger, nullable=False)
    document_type = Column(SmallInteger)
    document_number = Column(String(50))
    master_document_number = Column(String(50))
    reference_number = Column(String(50))
    date_created = Column(DateTime)
    date_modified = Column(DateTime)
    document_date = Column(DateTime)
    created_by = Column(Integer)
    modified_by = Column(Integer)
    owner = Column(Integer)
    tags = Column(CHAR(8), default='--------')
    shipper = Column(String(200))
    consignee = Column(String(200))
    route = Column(String(100))
    origin = Column(String(20))
    destination = Column(String(20))
    search_text = Column(String(5000))
    short_info = Column(LargeBinary)
    document_data = Column(LargeBinary)
    
    # Relationships
    logs = relationship("DocumentLog", back_populates="document")


class DocumentLog(AWBBase):
    """Document activity logs."""
    __tablename__ = "document_log"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    document_id = Column(Integer, ForeignKey("document.id"), nullable=False)
    user_id = Column(Integer, nullable=False)
    log_type = Column(SmallInteger, nullable=False)
    log_date = Column(DateTime, nullable=False)
    log_data = Column(LargeBinary)
    
    # Relationships
    document = relationship("Document", back_populates="logs")


class InventoryLocation(AWBBase):
    """Inventory storage locations."""
    __tablename__ = "inventory_location"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    name = Column(String(100), nullable=False)
    
    # Relationships
    item_locations = relationship("InventoryItemLocation", back_populates="location")


class InventoryItem(AWBBase):
    """Inventory items with barcodes."""
    __tablename__ = "inventory_item"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    current_item_location_id = Column(Integer, ForeignKey("inventory_item_location.id"))
    barcode = Column(String(50))
    document_type = Column(SmallInteger)
    document_number = Column(String(50))
    date_created = Column(DateTime)
    additional_info = Column(String(5000))
    
    # Relationships
    current_location = relationship("InventoryItemLocation", foreign_keys=[current_item_location_id])
    locations = relationship("InventoryItemLocation", back_populates="item", foreign_keys="InventoryItemLocation.item_id")


class InventoryItemLocation(AWBBase):
    """Inventory item location history."""
    __tablename__ = "inventory_item_location"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    location_id = Column(Integer, ForeignKey("inventory_location.id", ondelete="CASCADE"))
    location_type = Column(SmallInteger, nullable=False)
    item_id = Column(Integer, ForeignKey("inventory_item.id", ondelete="CASCADE"), nullable=False)
    date_created = Column(DateTime)
    
    # Relationships
    location = relationship("InventoryLocation", back_populates="item_locations")
    item = relationship("InventoryItem", back_populates="locations", foreign_keys=[item_id])


class RateAirCharges(AWBBase):
    """Air freight charge rates."""
    __tablename__ = "rate_air_charges"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    airline = Column(String(3), nullable=False)
    code = Column(String(20), nullable=False)
    rate_info = Column(String(5000), nullable=False)


class RateAirWeight(AWBBase):
    """Air freight weight-based rates."""
    __tablename__ = "rate_air_weight"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    rate_type = Column(SmallInteger, nullable=False)
    airline_prefix = Column(String(3))
    spot = Column(SmallInteger, nullable=False, default=0)
    from_airport = Column(String(10))
    to_airport = Column(String(10))
    valid_from_date = Column(Date)
    valid_to_date = Column(Date)
    commodity = Column(Integer)
    rates = Column(String(5000))
    notes = Column(String(5000))


class Shipment(AWBBase):
    """Shipment records linking contacts and tracking info."""
    __tablename__ = "shipment"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    master_shipment_id = Column(Integer)
    shipper_contact_id = Column(Integer)
    consignee_contact_id = Column(Integer)
    also_notify_contact_id = Column(Integer)
    freight_forwarder_contact_id = Column(Integer)
    shipment_date = Column(DateTime, nullable=False)
    import_export = Column(SmallInteger)
    shipment_type = Column(SmallInteger)
    master_number = Column(String(20))
    house_number = Column(String(20))
    reference_number = Column(String(30))
    shipper = Column(String(35))
    consignee = Column(String(35))
    agent = Column(String(35))
    origin = Column(String(4))
    destination = Column(String(4))
    event_status = Column(String(4))
    customs_status = Column(SmallInteger, default=0)
    transport = Column(SmallInteger, default=1)
    scheduled_carrier_arrival_datetime = Column(DateTime)
    actual_carrier_arrival_datetime = Column(DateTime)
    summary = Column(LargeBinary)
    shipment_additional_info = Column(LargeBinary)
    
    # Relationships
    attached_files = relationship("ShipmentAttachedFile", back_populates="shipment")


class ShipmentAttachedFile(AWBBase):
    """Files attached to shipments."""
    __tablename__ = "shipment_attached_file"
    
    id = Column(Integer, primary_key=True)
    shipment_id = Column(Integer, ForeignKey("shipment.id", ondelete="CASCADE"), nullable=False)
    file_date = Column(Date)
    file_size = Column(Integer)
    compression = Column(SmallInteger, nullable=False, default=0)
    status = Column(SmallInteger, nullable=False, default=2)
    original_file_name = Column(String(200))
    saved_file_name = Column(String(200))
    description = Column(String(2000))
    
    # Relationships
    shipment = relationship("Shipment", back_populates="attached_files")


class StationConfiguration(AWBBase):
    """Station-specific configuration."""
    __tablename__ = "station_configuration"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    configuration_type = Column(SmallInteger, nullable=False)
    reference = Column(Integer)
    details = Column(String(1000))
    configuration_data = Column(LargeBinary)


class Template(AWBBase):
    """Document templates for quick AWB creation."""
    __tablename__ = "template"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    shipper_contact_id = Column(Integer)
    consignee_contact_id = Column(Integer)
    also_notify_contact_id = Column(Integer)
    freight_forwarder_contact_id = Column(Integer)
    name = Column(String(255))
    document_type = Column(Integer)
    template_data = Column(LargeBinary)


class UserAccount(AWBBase):
    """AWB Editor user accounts."""
    __tablename__ = "user_account"
    
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, nullable=False)
    station_id = Column(Integer, nullable=False)
    username = Column(String(50), nullable=False)
    password = Column(String(150), nullable=False)
    user_type = Column(SmallInteger, nullable=False)
    user_status = Column(SmallInteger, nullable=False)
    first_name = Column(String(50))
    roles = Column(String(75))


class UserAirline(AWBBase):
    """Airline reference data."""
    __tablename__ = "user_airline"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    prefix = Column(CHAR(3))
    designator = Column(CHAR(2))
    name = Column(String(100))
    text = Column(String(1000))


class UserAirport(AWBBase):
    """Airport reference data."""
    __tablename__ = "user_airport"
    
    id = Column(Integer, primary_key=True)
    station_id = Column(Integer, nullable=False)
    code = Column(String(10), nullable=False)
    name = Column(String(250), nullable=False)

