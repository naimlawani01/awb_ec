"""User service for authentication and user management."""
from datetime import datetime, timedelta
from typing import Optional, List, Tuple
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.models.internal_models import PlatformUser, AuditLog
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash, verify_password, create_access_token
from app.core.config import settings


class UserService:
    """Service for user operations."""
    
    def __init__(self, db: Session):
        self.db = db
    
    def create_user(self, user_data: UserCreate) -> PlatformUser:
        """Create a new platform user."""
        hashed_password = get_password_hash(user_data.password)
        
        user = PlatformUser(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            first_name=user_data.first_name,
            last_name=user_data.last_name,
            role=user_data.role,
            station_id=user_data.station_id,
            is_active=True,
        )
        
        self.db.add(user)
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def authenticate_user(
        self,
        username: str,
        password: str
    ) -> Optional[PlatformUser]:
        """Authenticate user and return user object if valid."""
        user = self.get_user_by_username(username)
        
        if not user:
            return None
        
        if not user.is_active:
            return None
        
        if not verify_password(password, user.hashed_password):
            return None
        
        # Update last login
        user.last_login = datetime.utcnow()
        self.db.commit()
        
        return user
    
    def create_token_for_user(self, user: PlatformUser) -> Tuple[str, int]:
        """Create access token for authenticated user."""
        expires_delta = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        
        token_data = {
            "sub": str(user.id),
            "username": user.username,
            "role": user.role,
            "user_id": user.id,
        }
        
        token = create_access_token(token_data, expires_delta)
        
        return token, settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    
    def get_user_by_id(self, user_id: int) -> Optional[PlatformUser]:
        """Get user by ID."""
        query = select(PlatformUser).where(PlatformUser.id == user_id)
        return self.db.execute(query).scalar_one_or_none()
    
    def get_user_by_username(self, username: str) -> Optional[PlatformUser]:
        """Get user by username."""
        query = select(PlatformUser).where(PlatformUser.username == username)
        return self.db.execute(query).scalar_one_or_none()
    
    def get_user_by_email(self, email: str) -> Optional[PlatformUser]:
        """Get user by email."""
        query = select(PlatformUser).where(PlatformUser.email == email)
        return self.db.execute(query).scalar_one_or_none()
    
    def get_users(
        self,
        page: int = 1,
        page_size: int = 25
    ) -> Tuple[List[PlatformUser], int]:
        """Get paginated list of users."""
        query = select(PlatformUser).order_by(PlatformUser.created_at.desc())
        
        # Get total count
        count_query = select(func.count(PlatformUser.id))
        total = self.db.execute(count_query).scalar() or 0
        
        # Apply pagination
        query = query.offset((page - 1) * page_size).limit(page_size)
        users = self.db.execute(query).scalars().all()
        
        return users, total
    
    def update_user(
        self,
        user_id: int,
        user_data: UserUpdate
    ) -> Optional[PlatformUser]:
        """Update user details."""
        user = self.get_user_by_id(user_id)
        
        if not user:
            return None
        
        update_data = user_data.model_dump(exclude_unset=True)
        
        # Hash password if provided
        if "password" in update_data and update_data["password"]:
            update_data["hashed_password"] = get_password_hash(
                update_data.pop("password")
            )
        
        for field, value in update_data.items():
            setattr(user, field, value)
        
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def delete_user(self, user_id: int) -> bool:
        """Delete a user."""
        user = self.get_user_by_id(user_id)
        
        if not user:
            return False
        
        self.db.delete(user)
        self.db.commit()
        
        return True
    
    def deactivate_user(self, user_id: int) -> Optional[PlatformUser]:
        """Deactivate a user account."""
        user = self.get_user_by_id(user_id)
        
        if not user:
            return None
        
        user.is_active = False
        user.updated_at = datetime.utcnow()
        self.db.commit()
        self.db.refresh(user)
        
        return user
    
    def log_action(
        self,
        user_id: int,
        username: str,
        action: str,
        resource_type: str = None,
        resource_id: int = None,
        details: str = None,
        ip_address: str = None,
        user_agent: str = None
    ) -> AuditLog:
        """Log user action for audit trail."""
        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            details=details,
            ip_address=ip_address,
            user_agent=user_agent,
        )
        
        self.db.add(log)
        self.db.commit()
        
        return log
    
    def get_audit_logs(
        self,
        user_id: Optional[int] = None,
        action: Optional[str] = None,
        page: int = 1,
        page_size: int = 50
    ) -> Tuple[List[AuditLog], int]:
        """Get paginated audit logs with optional filters."""
        query = select(AuditLog)
        
        if user_id:
            query = query.where(AuditLog.user_id == user_id)
        
        if action:
            query = query.where(AuditLog.action == action)
        
        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total = self.db.execute(count_query).scalar() or 0
        
        # Apply pagination and ordering
        query = query.order_by(AuditLog.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        
        logs = self.db.execute(query).scalars().all()
        
        return logs, total
    
    def create_default_admin(self) -> Optional[PlatformUser]:
        """Create default admin user if none exists."""
        # Check if any admin exists
        query = select(PlatformUser).where(PlatformUser.role == "admin")
        existing_admin = self.db.execute(query).scalar_one_or_none()
        
        if existing_admin:
            return None
        
        admin_data = UserCreate(
            username="admin",
            email="admin@awbplatform.com",
            password="admin123!",  # Should be changed on first login
            first_name="System",
            last_name="Administrator",
            role="admin"
        )
        
        return self.create_user(admin_data)

