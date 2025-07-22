"""
Authentication and authorization module for the disaster response system.
Implements JWT token-based authentication with role-based access control.
"""

import jwt
import bcrypt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from fastapi import HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import os
import redis
from dataclasses import dataclass

# JWT Configuration
SECRET_KEY = os.getenv("JWT_SECRET_KEY", "disaster-response-secret-key-change-in-production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7

# Initialize Redis for token blacklist
redis_client = redis.Redis(
    host=os.getenv("REDIS_HOST", "localhost"),
    port=int(os.getenv("REDIS_PORT", 6379)),
    decode_responses=True
)

security = HTTPBearer()


@dataclass
class User:
    """User data class"""
    user_id: str
    username: str
    email: str
    role: str
    permissions: List[str]
    is_active: bool = True


class AuthManager:
    """Authentication and authorization manager"""
    
    # Define user roles and their permissions
    ROLES_PERMISSIONS = {
        "admin": [
            "read:all", "write:all", "delete:all", "manage:users",
            "predict:disasters", "search:events", "view:stats"
        ],
        "emergency_responder": [
            "read:events", "predict:disasters", "search:events", 
            "view:stats", "create:alerts", "update:events"
        ],
        "analyst": [
            "read:events", "search:events", "view:stats", 
            "predict:disasters", "export:data"
        ],
        "public": [
            "read:public_events", "view:public_stats"
        ]
    }
    
    # Mock user database (in production, use proper database)
    USERS_DB = {
        "admin": {
            "user_id": "admin_001",
            "username": "admin",
            "email": "admin@disaster-response.com",
            "password_hash": bcrypt.hashpw("admin123".encode(), bcrypt.gensalt()).decode(),
            "role": "admin",
            "is_active": True
        },
        "responder1": {
            "user_id": "resp_001", 
            "username": "responder1",
            "email": "responder1@emergency.gov",
            "password_hash": bcrypt.hashpw("responder123".encode(), bcrypt.gensalt()).decode(),
            "role": "emergency_responder",
            "is_active": True
        },
        "analyst1": {
            "user_id": "anal_001",
            "username": "analyst1", 
            "email": "analyst1@disaster-response.com",
            "password_hash": bcrypt.hashpw("analyst123".encode(), bcrypt.gensalt()).decode(),
            "role": "analyst",
            "is_active": True
        }
    }
    
    @classmethod
    def hash_password(cls, password: str) -> str:
        """Hash a password using bcrypt"""
        return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
    
    @classmethod
    def verify_password(cls, password: str, hashed: str) -> bool:
        """Verify a password against its hash"""
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    @classmethod
    def get_user(cls, username: str) -> Optional[User]:
        """Get user by username"""
        user_data = cls.USERS_DB.get(username)
        if not user_data:
            return None
        
        return User(
            user_id=user_data["user_id"],
            username=user_data["username"],
            email=user_data["email"],
            role=user_data["role"],
            permissions=cls.ROLES_PERMISSIONS.get(user_data["role"], []),
            is_active=user_data["is_active"]
        )
    
    @classmethod
    def authenticate_user(cls, username: str, password: str) -> Optional[User]:
        """Authenticate user with username and password"""
        user_data = cls.USERS_DB.get(username)
        if not user_data:
            return None
        
        if not cls.verify_password(password, user_data["password_hash"]):
            return None
        
        if not user_data["is_active"]:
            return None
        
        return cls.get_user(username)
    
    @classmethod
    def create_access_token(cls, data: Dict[str, Any]) -> str:
        """Create JWT access token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire, "type": "access"})
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @classmethod
    def create_refresh_token(cls, data: Dict[str, Any]) -> str:
        """Create JWT refresh token"""
        to_encode = data.copy()
        expire = datetime.utcnow() + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
        to_encode.update({"exp": expire, "type": "refresh"})
        
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    
    @classmethod
    def verify_token(cls, token: str) -> Optional[Dict[str, Any]]:
        """Verify and decode JWT token"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            
            # Check if token is blacklisted
            if cls.is_token_blacklisted(token):
                return None
            
            return payload
        
        except jwt.ExpiredSignatureError:
            return None
        except jwt.JWTError:
            return None
    
    @classmethod
    def blacklist_token(cls, token: str):
        """Add token to blacklist (for logout)"""
        try:
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            exp_time = payload.get("exp")
            
            if exp_time:
                # Store token in Redis with expiration
                ttl = exp_time - int(datetime.utcnow().timestamp())
                if ttl > 0:
                    redis_client.setex(f"blacklist:{token}", ttl, "1")
        
        except jwt.JWTError:
            pass
    
    @classmethod
    def is_token_blacklisted(cls, token: str) -> bool:
        """Check if token is blacklisted"""
        try:
            return redis_client.exists(f"blacklist:{token}") == 1
        except:
            return False
    
    @classmethod
    def has_permission(cls, user: User, permission: str) -> bool:
        """Check if user has specific permission"""
        return permission in user.permissions


# FastAPI dependency functions
async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)) -> User:
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    
    payload = AuthManager.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    username = payload.get("sub")
    if not username:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    user = AuthManager.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
            headers={"WWW-Authenticate": "Bearer"}
        )
    
    return user


def require_permission(permission: str):
    """Dependency factory for permission-based access control"""
    def permission_checker(current_user: User = Depends(get_current_user)) -> User:
        if not AuthManager.has_permission(current_user, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Insufficient permissions. Required: {permission}"
            )
        return current_user
    
    return permission_checker


def require_role(role: str):
    """Dependency factory for role-based access control"""
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role != role:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {role}"
            )
        return current_user
    
    return role_checker


# Authentication endpoints
def login(username: str, password: str) -> Dict[str, Any]:
    """Login endpoint logic"""
    user = AuthManager.authenticate_user(username, password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password"
        )
    
    # Create tokens
    access_token = AuthManager.create_access_token({"sub": user.username})
    refresh_token = AuthManager.create_refresh_token({"sub": user.username})
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        "user": {
            "user_id": user.user_id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "permissions": user.permissions
        }
    }


def logout(token: str) -> Dict[str, str]:
    """Logout endpoint logic"""
    AuthManager.blacklist_token(token)
    return {"message": "Successfully logged out"}


def refresh_access_token(refresh_token: str) -> Dict[str, Any]:
    """Refresh access token using refresh token"""
    payload = AuthManager.verify_token(refresh_token)
    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    username = payload.get("sub")
    user = AuthManager.get_user(username)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    # Create new access token
    access_token = AuthManager.create_access_token({"sub": user.username})
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60
    }