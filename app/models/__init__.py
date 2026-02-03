"""
Database models module.
Contains both AWB Editor models (reflected) and internal platform models.
"""
from app.models.awb_models import (
    Document,
    DocumentLog,
    Shipment,
    ShipmentAttachedFile,
    Contact,
    AWBStockNumber,
    AWBAutofill,
    InventoryItem,
    InventoryItemLocation,
    InventoryLocation,
    RateAirCharges,
    RateAirWeight,
    StationConfiguration,
    Template,
    UserAccount,
    UserAirline,
    UserAirport,
)
from app.models.internal_models import (
    PlatformUser,
    AuditLog,
    PlatformSettings,
)

__all__ = [
    # AWB Models
    "Document",
    "DocumentLog", 
    "Shipment",
    "ShipmentAttachedFile",
    "Contact",
    "AWBStockNumber",
    "AWBAutofill",
    "InventoryItem",
    "InventoryItemLocation",
    "InventoryLocation",
    "RateAirCharges",
    "RateAirWeight",
    "StationConfiguration",
    "Template",
    "UserAccount",
    "UserAirline",
    "UserAirport",
    # Internal Models
    "PlatformUser",
    "AuditLog",
    "PlatformSettings",
]

