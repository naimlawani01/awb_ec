"""
Internal platform models for users, audit logs, and settings.
These tables are created and managed by this platform, separate from AWB Editor.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, Boolean, JSON
from app.core.database import InternalBase


class PlatformUser(InternalBase):
    """Platform user accounts (separate from AWB Editor users)."""
    __tablename__ = "platform_users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    first_name = Column(String(50))
    last_name = Column(String(50))
    role = Column(String(20), nullable=False, default="viewer")  # admin, staff, viewer
    is_active = Column(Boolean, default=True)
    station_id = Column(Integer)  # Optional: link to AWB station
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    
    def __repr__(self):
        return f"<PlatformUser {self.username} ({self.role})>"


class AuditLog(InternalBase):
    """Audit trail for platform actions."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, index=True)
    username = Column(String(50))
    action = Column(String(50), nullable=False)  # VIEW, EXPORT, SEARCH, LOGIN, etc.
    resource_type = Column(String(50))  # document, shipment, contact, etc.
    resource_id = Column(Integer)
    details = Column(Text)
    ip_address = Column(String(45))
    user_agent = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    def __repr__(self):
        return f"<AuditLog {self.action} by {self.username}>"


class PlatformSettings(InternalBase):
    """Platform configuration settings."""
    __tablename__ = "platform_settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String(100), unique=True, nullable=False)
    value = Column(Text)
    value_type = Column(String(20), default="string")  # string, int, bool, json
    description = Column(String(255))
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    updated_by = Column(Integer)
    
    def __repr__(self):
        return f"<PlatformSettings {self.key}>"


class SavedFilter(InternalBase):
    """User-saved filters for quick access."""
    __tablename__ = "saved_filters"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    filter_type = Column(String(50), nullable=False)  # awb, shipment, contact
    filter_data = Column(JSON)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<SavedFilter {self.name}>"


class ExportHistory(InternalBase):
    """Track export operations."""
    __tablename__ = "export_history"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False, index=True)
    export_type = Column(String(20), nullable=False)  # excel, pdf
    resource_type = Column(String(50), nullable=False)
    record_count = Column(Integer)
    filter_criteria = Column(JSON)
    file_name = Column(String(255))
    created_at = Column(DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f"<ExportHistory {self.export_type} - {self.resource_type}>"

