"""Authentication API endpoints."""
from datetime import datetime
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app.core.database import get_internal_db
from app.core.security import require_admin, require_staff, decode_token, oauth2_scheme
from app.services.user_service import UserService
from app.schemas.user import (
    UserCreate, UserUpdate, UserResponse, UserLogin, Token, UserListResponse,
    PasswordChange
)

router = APIRouter()


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_internal_db)
):
    """
    Authenticate user and return JWT token.
    """
    service = UserService(db)
    user = service.authenticate_user(form_data.username, form_data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token, expires_in = service.create_token_for_user(user)
    
    # Log login action
    service.log_action(
        user_id=user.id,
        username=user.username,
        action="LOGIN",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    
    return Token(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user)
    )


@router.post("/login/json", response_model=Token)
async def login_json(
    request: Request,
    credentials: UserLogin,
    db: Session = Depends(get_internal_db)
):
    """
    Authenticate user with JSON body and return JWT token.
    """
    service = UserService(db)
    user = service.authenticate_user(credentials.username, credentials.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    token, expires_in = service.create_token_for_user(user)
    
    # Log login action
    service.log_action(
        user_id=user.id,
        username=user.username,
        action="LOGIN",
        ip_address=request.client.host if request.client else None,
        user_agent=request.headers.get("User-Agent"),
    )
    
    return Token(
        access_token=token,
        expires_in=expires_in,
        user=UserResponse.model_validate(user)
    )


@router.get("/me", response_model=UserResponse)
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_internal_db)
):
    """
    Get current authenticated user details.
    """
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    service = UserService(db)
    user = service.get_user_by_id(payload.get("user_id"))
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user)


@router.post("/change-password")
async def change_password(
    password_data: PasswordChange,
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_internal_db)
):
    """
    Change current user's password.
    """
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )
    
    service = UserService(db)
    user = service.authenticate_user(
        payload.get("username"),
        password_data.current_password
    )
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    
    update_data = UserUpdate(password=password_data.new_password)
    service.update_user(user.id, update_data)
    
    return {"message": "Password changed successfully"}


# Admin routes for user management

@router.get("/users", response_model=UserListResponse)
async def list_users(
    page: int = 1,
    page_size: int = 25,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_internal_db)
):
    """
    List all users (admin only).
    """
    service = UserService(db)
    users, total = service.get_users(page, page_size)
    
    return UserListResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total
    )


@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(
    user_data: UserCreate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_internal_db)
):
    """
    Create a new user (admin only).
    """
    service = UserService(db)
    
    # Check for existing user
    if service.get_user_by_username(user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already exists",
        )
    
    if service.get_user_by_email(user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already exists",
        )
    
    user = service.create_user(user_data)
    
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_internal_db)
):
    """
    Get user by ID (admin only).
    """
    service = UserService(db)
    user = service.get_user_by_id(user_id)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user)


@router.put("/users/{user_id}", response_model=UserResponse)
async def update_user(
    user_id: int,
    user_data: UserUpdate,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_internal_db)
):
    """
    Update user (admin only).
    """
    service = UserService(db)
    user = service.update_user(user_id, user_data)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return UserResponse.model_validate(user)


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(require_admin),
    db: Session = Depends(get_internal_db)
):
    """
    Delete user (admin only).
    """
    service = UserService(db)
    
    if not service.delete_user(user_id):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    return {"message": "User deleted successfully"}

