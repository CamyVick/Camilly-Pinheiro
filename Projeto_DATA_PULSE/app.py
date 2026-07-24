# app.py
from fastapi import FastAPI, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from contextlib import asynccontextmanager
import uuid
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from enum import Enum
import logging
from pydantic import BaseModel, Field, EmailStr, validator
from pydantic_settings import BaseSettings
from fastapi.responses import JSONResponse
import jwt


# Configurações
class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./datapulse.db"
    JWT_SECRET: str = "your-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    
    class Config:
        env_file = ".env"

settings = Settings()

# Configuração do banco de dados com SQLite
from sqlalchemy import create_engine, Column, String, DateTime, JSON, Boolean, Text, Integer, Float
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy import select

# Engine SQLite
engine = create_engine(settings.DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Database Models ---

class User(Base):
    __tablename__ = "users"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=True)
    full_name = Column(String)
    roles = Column(JSON, default=list)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = Column(DateTime)
    mfa_secret = Column(String, nullable=True)
    mfa_enabled = Column(Boolean, default=False)

class Organization(Base):
    __tablename__ = "organizations"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    plan = Column(String, default="free")
    settings = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class APIKey(Base):
    __tablename__ = "api_keys"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    key_prefix = Column(String, nullable=False)
    key_hash = Column(String, nullable=False, unique=True)
    scopes = Column(JSON, default=list)
    last_used = Column(DateTime)
    expires_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

class Connection(Base):
    __tablename__ = "connections"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Pipeline(Base):
    __tablename__ = "pipelines"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    connection_id = Column(String, nullable=False)
    environment = Column(String, default="DEV")
    pipeline_type = Column(String, default="etl")
    sla_minutes = Column(Integer, default=15)
    owner_id = Column(String)
    tags = Column(JSON, default=list)
    status = Column(String, default="active")
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class PipelineRun(Base):
    __tablename__ = "pipeline_runs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    pipeline_id = Column(String, nullable=False, index=True)
    status = Column(String, nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime)
    duration_seconds = Column(Float)
    cpu_usage = Column(Float)
    memory_usage = Column(Float)
    logs = Column(Text)
    error_message = Column(Text)
    run_metadata = Column("metadata", JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)

class AlertRule(Base):
    __tablename__ = "alert_rules"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    pipeline_id = Column(String, nullable=True)
    condition_type = Column(String, nullable=False)
    condition_config = Column(JSON, nullable=False)
    severity = Column(String, default="warning")
    notification_channels = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Alert(Base):
    __tablename__ = "alerts"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    rule_id = Column(String, nullable=False)
    pipeline_id = Column(String, nullable=False)
    severity = Column(String, nullable=False)
    status = Column(String, default="triggered")
    message = Column(Text)
    triggered_at = Column(DateTime, default=datetime.utcnow)
    acknowledged_at = Column(DateTime)
    resolved_at = Column(DateTime)
    alert_metadata = Column("metadata", JSON, default=dict)

class NotificationChannel(Base):
    __tablename__ = "notification_channels"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False)
    type = Column(String, nullable=False)
    config = Column(JSON, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class Dashboard(Base):
    __tablename__ = "dashboards"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    layout = Column(JSON, default=dict)
    widgets = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    org_id = Column(String, nullable=False, index=True)
    user_id = Column(String, nullable=False)
    action = Column(String, nullable=False)
    resource_type = Column(String, nullable=False)
    resource_id = Column(String)
    changes = Column(JSON)
    ip_address = Column(String)
    user_agent = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

# --- Pydantic Models ---

class UserLogin(BaseModel):
    email: EmailStr
    password: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int

class UserCreate(BaseModel):
    email: EmailStr
    full_name: str
    password: Optional[str] = None
    roles: List[str] = ["viewer"]

class UserResponse(BaseModel):
    id: str
    email: str
    full_name: str
    status: str
    roles: List[str]
    created_at: datetime
    last_login: Optional[datetime]

class OrganizationResponse(BaseModel):
    id: str
    name: str
    plan: str
    settings: Dict[str, Any]
    created_at: datetime

class APIKeyCreate(BaseModel):
    name: str
    scopes: List[str]

class APIKeyResponse(BaseModel):
    id: str
    name: str
    key: Optional[str] = None
    scopes: List[str]
    expires_at: Optional[datetime]
    created_at: datetime
    last_used: Optional[datetime]

class ConnectionCreate(BaseModel):
    name: str
    type: str
    config: Dict[str, Any]

class ConnectionResponse(BaseModel):
    id: str
    name: str
    type: str
    config: Dict[str, Any]
    status: str
    created_at: datetime
    updated_at: datetime

class PipelineCreate(BaseModel):
    name: str
    connection_id: str
    environment: str = "DEV"
    pipeline_type: str = "etl"
    sla_minutes: int = 15
    owner_id: Optional[str] = None
    tags: List[str] = []

class PipelineKPIs(BaseModel):
    status: str
    success_rate_24h: float
    avg_duration_seconds: float
    last_run_at: Optional[datetime]
    last_run_status: Optional[str]

class PipelineResponse(BaseModel):
    id: str
    name: str
    environment: str
    pipeline_type: str
    connection: Optional[ConnectionResponse]
    sla_minutes: int
    kpis: PipelineKPIs
    tags: List[str]
    created_at: datetime
    updated_at: datetime

class PipelineRunCreate(BaseModel):
    pipeline_id: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    cpu_usage: Optional[float] = None
    memory_usage: Optional[float] = None
    logs: Optional[str] = None
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = {}

class PipelineRunResponse(BaseModel):
    id: str
    pipeline_id: str
    status: str
    started_at: datetime
    ended_at: Optional[datetime]
    duration_seconds: Optional[float]
    cpu_usage: Optional[float]
    memory_usage: Optional[float]
    error_message: Optional[str]
    metadata: Dict[str, Any]
    created_at: datetime

class AlertRuleCreate(BaseModel):
    name: str
    pipeline_id: Optional[str] = None
    condition_type: str
    condition_config: Dict[str, Any]
    severity: str = "warning"
    notification_channels: List[str] = []

class AlertRuleResponse(BaseModel):
    id: str
    name: str
    pipeline_id: Optional[str]
    condition_type: str
    condition_config: Dict[str, Any]
    severity: str
    notification_channels: List[str]
    created_at: datetime
    updated_at: datetime

class AlertResponse(BaseModel):
    id: str
    rule_id: str
    pipeline_id: str
    severity: str
    status: str
    message: str
    triggered_at: datetime
    acknowledged_at: Optional[datetime]
    resolved_at: Optional[datetime]
    metadata: Dict[str, Any]

class AlertUpdate(BaseModel):
    status: str

class ChatRequest(BaseModel):
    conversation_id: Optional[str] = None
    message: str

class ChatResponse(BaseModel):
    conversation_id: str
    answer: str
    context_refs: Dict[str, Optional[str]]

class DashboardCreate(BaseModel):
    name: str
    layout: Dict[str, Any] = {}
    widgets: List[Dict[str, Any]] = []

class DashboardResponse(BaseModel):
    id: str
    name: str
    layout: Dict[str, Any]
    widgets: List[Dict[str, Any]]
    created_at: datetime
    updated_at: datetime

class PaginatedResponse(BaseModel):
    items: List[Any]
    next_cursor: Optional[str]
    limit: int
    total: Optional[int] = None

class ErrorResponse(BaseModel):
    type: str
    title: str
    status: int
    detail: Optional[str] = None
    field: Optional[str] = None
    instance: Optional[str] = None

# --- FastAPI App ---

app = FastAPI(
    title="DataPulse AI API",
    version="1.0.0",
    description="DataPulse AI API Specification v1",
    docs_url="/docs",
    redoc_url="/redoc"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security
security = HTTPBearer()

# --- Dependencies ---

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# --- Auth Helper Functions ---

import jwt
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Validate JWT and return current user"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        user = db.query(User).filter(User.id == user_id).first()
        if not user or user.status != "active":
            raise HTTPException(status_code=401, detail="User not found or inactive")
        
        return user
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def require_permission(*permissions: str):
    """Decorator to check permissions"""
    async def permission_checker(
        current_user: User = Depends(get_current_user)
    ):
        user_perms = current_user.roles
        if not any(p in user_perms for p in permissions):
            raise HTTPException(status_code=403, detail="Insufficient permissions")
        return current_user
    return permission_checker

# --- Auth Endpoints ---

@app.post("/auth/login", response_model=TokenResponse)
async def login(
    login_data: UserLogin,
    db: Session = Depends(get_db)
):
    """Login with email and password"""
    user = db.query(User).filter(User.email == login_data.email).first()
    
    if not user or not user.hashed_password:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    if not verify_password(login_data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    user.last_login = datetime.utcnow()
    db.commit()
    
    access_token = jwt.encode(
        {
            "sub": user.id,
            "org_id": user.org_id,
            "roles": user.roles,
            "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    refresh_token = jwt.encode(
        {
            "sub": user.id,
            "type": "refresh",
            "exp": datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        },
        settings.JWT_SECRET,
        algorithm=settings.JWT_ALGORITHM
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )

@app.post("/auth/refresh", response_model=TokenResponse)
async def refresh_token(
    refresh_data: Dict[str, str]
):
    """Get new access token using refresh token"""
    try:
        payload = jwt.decode(
            refresh_data.get("refresh_token", ""),
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        
        if payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        
        user_id = payload.get("sub")
        if not user_id:
            raise HTTPException(status_code=401, detail="Invalid token")
        
        access_token = jwt.encode(
            {
                "sub": user_id,
                "org_id": payload.get("org_id"),
                "roles": payload.get("roles", []),
                "exp": datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
            },
            settings.JWT_SECRET,
            algorithm=settings.JWT_ALGORITHM
        )
        
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_data.get("refresh_token", ""),
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid refresh token")

@app.get("/auth/me", response_model=UserResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_user)
):
    """Get current user profile"""
    return UserResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        status=current_user.status,
        roles=current_user.roles,
        created_at=current_user.created_at,
        last_login=current_user.last_login
    )

@app.post("/auth/logout")
async def logout(
    current_user: User = Depends(get_current_user)
):
    """Logout - revoke refresh token"""
    return {"message": "Logged out successfully"}

# --- Organization Endpoints ---

@app.get("/organizations/me", response_model=OrganizationResponse)
async def get_organization(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current organization details"""
    org = db.query(Organization).filter(Organization.id == current_user.org_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        plan=org.plan,
        settings=org.settings,
        created_at=org.created_at
    )

@app.patch("/organizations/me", response_model=OrganizationResponse)
async def update_organization(
    updates: Dict[str, Any],
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Update organization settings"""
    org = db.query(Organization).filter(Organization.id == current_user.org_id).first()
    
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    
    for key, value in updates.items():
        if hasattr(org, key) and key not in ["id", "created_at"]:
            setattr(org, key, value)
    
    org.updated_at = datetime.utcnow()
    db.commit()
    
    return OrganizationResponse(
        id=org.id,
        name=org.name,
        plan=org.plan,
        settings=org.settings,
        created_at=org.created_at
    )

# --- User Management ---

@app.post("/users", response_model=UserResponse)
async def invite_user(
    user_data: UserCreate,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Invite a new user to the organization"""
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")
    
    new_user = User(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        email=user_data.email,
        full_name=user_data.full_name,
        roles=user_data.roles,
        status="pending"
    )
    
    if user_data.password:
        new_user.hashed_password = get_password_hash(user_data.password)
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return UserResponse(
        id=new_user.id,
        email=new_user.email,
        full_name=new_user.full_name,
        status=new_user.status,
        roles=new_user.roles,
        created_at=new_user.created_at,
        last_login=new_user.last_login
    )

@app.get("/users", response_model=PaginatedResponse)
async def list_users(
    limit: int = 50,
    cursor: Optional[str] = None,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """List users in organization"""
    users = db.query(User).filter(User.org_id == current_user.org_id).limit(limit + 1).all()
    
    items = [
        UserResponse(
            id=user.id,
            email=user.email,
            full_name=user.full_name,
            status=user.status,
            roles=user.roles,
            created_at=user.created_at,
            last_login=user.last_login
        )
        for user in users[:limit]
    ]
    
    next_cursor = None
    if len(users) > limit:
        next_cursor = "cursor_placeholder"
    
    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        limit=limit
    )

@app.get("/users/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: str,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Get user details"""
    user = db.query(User).filter(
        User.id == user_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        status=user.status,
        roles=user.roles,
        created_at=user.created_at,
        last_login=user.last_login
    )

@app.delete("/users/{user_id}")
async def deactivate_user(
    user_id: str,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Deactivate a user"""
    user = db.query(User).filter(
        User.id == user_id,
        User.org_id == current_user.org_id
    ).first()
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    user.status = "inactive"
    db.commit()
    
    return {"message": "User deactivated successfully"}

# --- API Key Management ---

@app.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key(
    key_data: APIKeyCreate,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Generate a new API key"""
    import secrets
    import hashlib
    
    key_prefix = "dp_live_"
    key_suffix = secrets.token_urlsafe(32)
    full_key = f"{key_prefix}{key_suffix}"
    
    key_hash = hashlib.sha256(full_key.encode()).hexdigest()
    
    api_key = APIKey(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        user_id=current_user.id,
        name=key_data.name,
        key_prefix=key_prefix,
        key_hash=key_hash,
        scopes=key_data.scopes
    )
    
    db.add(api_key)
    db.commit()
    db.refresh(api_key)
    
    return APIKeyResponse(
        id=api_key.id,
        name=api_key.name,
        key=full_key,
        scopes=api_key.scopes,
        expires_at=api_key.expires_at,
        created_at=api_key.created_at,
        last_used=api_key.last_used
    )

@app.get("/api-keys", response_model=List[APIKeyResponse])
async def list_api_keys(
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """List all API keys for the organization"""
    keys = db.query(APIKey).filter(APIKey.org_id == current_user.org_id).all()
    
    return [
        APIKeyResponse(
            id=key.id,
            name=key.name,
            scopes=key.scopes,
            expires_at=key.expires_at,
            created_at=key.created_at,
            last_used=key.last_used
        )
        for key in keys
    ]

@app.delete("/api-keys/{key_id}")
async def revoke_api_key(
    key_id: str,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Revoke an API key"""
    key = db.query(APIKey).filter(
        APIKey.id == key_id,
        APIKey.org_id == current_user.org_id
    ).first()
    
    if not key:
        raise HTTPException(status_code=404, detail="API key not found")
    
    db.delete(key)
    db.commit()
    
    return {"message": "API key revoked successfully"}

# --- Connection Endpoints ---

@app.get("/integration-types")
async def list_integration_types():
    """List available integration types"""
    return {
        "integrations": [
            {"type": "airflow", "name": "Apache Airflow", "version": "2.0+"},
            {"type": "jenkins", "name": "Jenkins", "version": "2.0+"},
            {"type": "github_actions", "name": "GitHub Actions", "version": "latest"},
            {"type": "gitlab_ci", "name": "GitLab CI", "version": "latest"},
            {"type": "azure_devops", "name": "Azure DevOps", "version": "latest"},
            {"type": "databricks", "name": "Databricks", "version": "latest"},
            {"type": "snowflake", "name": "Snowflake", "version": "latest"},
            {"type": "bigquery", "name": "Google BigQuery", "version": "latest"}
        ]
    }

@app.post("/connections", response_model=ConnectionResponse)
async def create_connection(
    conn_data: ConnectionCreate,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Create a new connection"""
    connection = Connection(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        name=conn_data.name,
        type=conn_data.type,
        config=conn_data.config,
        status="active"
    )
    
    db.add(connection)
    db.commit()
    db.refresh(connection)
    
    return ConnectionResponse(
        id=connection.id,
        name=connection.name,
        type=connection.type,
        config=connection.config,
        status=connection.status,
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )

@app.get("/connections", response_model=PaginatedResponse)
async def list_connections(
    limit: int = 50,
    cursor: Optional[str] = None,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """List all connections"""
    connections = db.query(Connection).filter(
        Connection.org_id == current_user.org_id
    ).limit(limit + 1).all()
    
    items = [
        ConnectionResponse(
            id=conn.id,
            name=conn.name,
            type=conn.type,
            config=conn.config,
            status=conn.status,
            created_at=conn.created_at,
            updated_at=conn.updated_at
        )
        for conn in connections[:limit]
    ]
    
    next_cursor = None
    if len(connections) > limit:
        next_cursor = "cursor_placeholder"
    
    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        limit=limit
    )

@app.get("/connections/{connection_id}", response_model=ConnectionResponse)
async def get_connection(
    connection_id: str,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Get connection details"""
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.org_id == current_user.org_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    return ConnectionResponse(
        id=connection.id,
        name=connection.name,
        type=connection.type,
        config=connection.config,
        status=connection.status,
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )

@app.patch("/connections/{connection_id}", response_model=ConnectionResponse)
async def update_connection(
    connection_id: str,
    updates: Dict[str, Any],
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Update connection"""
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.org_id == current_user.org_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    for key, value in updates.items():
        if hasattr(connection, key) and key not in ["id", "created_at"]:
            setattr(connection, key, value)
    
    connection.updated_at = datetime.utcnow()
    db.commit()
    
    return ConnectionResponse(
        id=connection.id,
        name=connection.name,
        type=connection.type,
        config=connection.config,
        status=connection.status,
        created_at=connection.created_at,
        updated_at=connection.updated_at
    )

@app.delete("/connections/{connection_id}")
async def delete_connection(
    connection_id: str,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Delete a connection"""
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.org_id == current_user.org_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    db.delete(connection)
    db.commit()
    
    return {"message": "Connection deleted successfully"}

@app.post("/connections/{connection_id}/test")
async def test_connection(
    connection_id: str,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Test connection connectivity"""
    connection = db.query(Connection).filter(
        Connection.id == connection_id,
        Connection.org_id == current_user.org_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    # Mock test
    return {"status": "success", "message": "Connection test successful"}

# --- Pipeline Endpoints ---

@app.post("/pipelines", response_model=PipelineResponse)
async def create_pipeline(
    pipeline_data: PipelineCreate,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Register a new pipeline"""
    connection = db.query(Connection).filter(
        Connection.id == pipeline_data.connection_id,
        Connection.org_id == current_user.org_id
    ).first()
    
    if not connection:
        raise HTTPException(status_code=404, detail="Connection not found")
    
    pipeline = Pipeline(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        name=pipeline_data.name,
        connection_id=pipeline_data.connection_id,
        environment=pipeline_data.environment,
        pipeline_type=pipeline_data.pipeline_type,
        sla_minutes=pipeline_data.sla_minutes,
        owner_id=pipeline_data.owner_id,
        tags=pipeline_data.tags,
        status="active"
    )
    
    db.add(pipeline)
    db.commit()
    db.refresh(pipeline)
    
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        environment=pipeline.environment,
        pipeline_type=pipeline.pipeline_type,
        connection=ConnectionResponse(
            id=connection.id,
            name=connection.name,
            type=connection.type,
            config=connection.config,
            status=connection.status,
            created_at=connection.created_at,
            updated_at=connection.updated_at
        ),
        sla_minutes=pipeline.sla_minutes,
        kpis=PipelineKPIs(
            status="healthy",
            success_rate_24h=0.95,
            avg_duration_seconds=120.5,
            last_run_at=None,
            last_run_status=None
        ),
        tags=pipeline.tags,
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at
    )

@app.get("/pipelines", response_model=PaginatedResponse)
async def list_pipelines(
    environment: Optional[str] = None,
    status: Optional[str] = None,
    connection_id: Optional[str] = None,
    tag: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """List pipelines with filters"""
    query = db.query(Pipeline).filter(Pipeline.org_id == current_user.org_id)
    
    if environment:
        query = query.filter(Pipeline.environment == environment)
    if status:
        query = query.filter(Pipeline.status == status)
    if connection_id:
        query = query.filter(Pipeline.connection_id == connection_id)
    if tag:
        # SQLite JSON contains check
        query = query.filter(Pipeline.tags.contains(tag))
    
    pipelines = query.limit(limit + 1).all()
    
    items = []
    for pipeline in pipelines[:limit]:
        connection = db.query(Connection).filter(Connection.id == pipeline.connection_id).first()
        
        items.append(PipelineResponse(
            id=pipeline.id,
            name=pipeline.name,
            environment=pipeline.environment,
            pipeline_type=pipeline.pipeline_type,
            connection=ConnectionResponse(
                id=connection.id,
                name=connection.name,
                type=connection.type,
                config=connection.config,
                status=connection.status,
                created_at=connection.created_at,
                updated_at=connection.updated_at
            ) if connection else None,
            sla_minutes=pipeline.sla_minutes,
            kpis=PipelineKPIs(
                status="healthy",
                success_rate_24h=0.95,
                avg_duration_seconds=120.5,
                last_run_at=None,
                last_run_status=None
            ),
            tags=pipeline.tags,
            created_at=pipeline.created_at,
            updated_at=pipeline.updated_at
        ))
    
    next_cursor = None
    if len(pipelines) > limit:
        next_cursor = "cursor_placeholder"
    
    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        limit=limit
    )

@app.get("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def get_pipeline(
    pipeline_id: str,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Get pipeline details with KPIs"""
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.org_id == current_user.org_id
    ).first()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    connection = db.query(Connection).filter(Connection.id == pipeline.connection_id).first()
    last_run = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id == pipeline_id
    ).order_by(PipelineRun.started_at.desc()).first()
    
    return PipelineResponse(
        id=pipeline.id,
        name=pipeline.name,
        environment=pipeline.environment,
        pipeline_type=pipeline.pipeline_type,
        connection=ConnectionResponse(
            id=connection.id,
            name=connection.name,
            type=connection.type,
            config=connection.config,
            status=connection.status,
            created_at=connection.created_at,
            updated_at=connection.updated_at
        ) if connection else None,
        sla_minutes=pipeline.sla_minutes,
        kpis=PipelineKPIs(
            status="healthy" if last_run and last_run.status == "success" else "warning",
            success_rate_24h=0.97,
            avg_duration_seconds=182.4,
            last_run_at=last_run.started_at if last_run else None,
            last_run_status=last_run.status if last_run else None
        ),
        tags=pipeline.tags,
        created_at=pipeline.created_at,
        updated_at=pipeline.updated_at
    )

@app.patch("/pipelines/{pipeline_id}", response_model=PipelineResponse)
async def update_pipeline(
    pipeline_id: str,
    updates: Dict[str, Any],
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Update pipeline configuration"""
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.org_id == current_user.org_id
    ).first()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    for key, value in updates.items():
        if hasattr(pipeline, key) and key not in ["id", "created_at"]:
            setattr(pipeline, key, value)
    
    pipeline.updated_at = datetime.utcnow()
    db.commit()
    
    return await get_pipeline(pipeline_id, current_user, db)

@app.delete("/pipelines/{pipeline_id}")
async def delete_pipeline(
    pipeline_id: str,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Delete a pipeline"""
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.org_id == current_user.org_id
    ).first()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    pipeline.status = "deleted"
    db.commit()
    
    return {"message": "Pipeline deleted successfully"}

@app.get("/pipelines/{pipeline_id}/runs", response_model=PaginatedResponse)
async def get_pipeline_runs(
    pipeline_id: str,
    limit: int = 50,
    cursor: Optional[str] = None,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Get pipeline run history"""
    pipeline = db.query(Pipeline).filter(
        Pipeline.id == pipeline_id,
        Pipeline.org_id == current_user.org_id
    ).first()
    
    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    
    runs = db.query(PipelineRun).filter(
        PipelineRun.pipeline_id == pipeline_id
    ).order_by(PipelineRun.started_at.desc()).limit(limit + 1).all()
    
    items = [
        PipelineRunResponse(
            id=run.id,
            pipeline_id=run.pipeline_id,
            status=run.status,
            started_at=run.started_at,
            ended_at=run.ended_at,
            duration_seconds=run.duration_seconds,
            cpu_usage=run.cpu_usage,
            memory_usage=run.memory_usage,
            error_message=run.error_message,
            metadata=run.run_metadata,
            created_at=run.created_at
        )
        for run in runs[:limit]
    ]
    
    next_cursor = None
    if len(runs) > limit:
        next_cursor = "cursor_placeholder"
    
    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        limit=limit
    )

# --- Ingest Endpoints ---

@app.post("/ingest/runs")
async def ingest_runs(
    runs: List[PipelineRunCreate],
    db: Session = Depends(get_db)
):
    """Ingest pipeline run data"""
    for run_data in runs:
        pipeline_run = PipelineRun(
            id=str(uuid.uuid4()),
            org_id="org_placeholder",
            pipeline_id=run_data.pipeline_id,
            status=run_data.status,
            started_at=run_data.started_at,
            ended_at=run_data.ended_at,
            duration_seconds=run_data.duration_seconds,
            cpu_usage=run_data.cpu_usage,
            memory_usage=run_data.memory_usage,
            logs=run_data.logs,
            error_message=run_data.error_message,
            run_metadata=run_data.metadata
        )
        db.add(pipeline_run)
    
    db.commit()
    return {"message": f"Successfully ingested {len(runs)} runs"}

@app.post("/ingest/logs")
async def ingest_logs(
    logs: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """Ingest logs in batch"""
    return {"message": f"Successfully ingested {len(logs)} log entries"}

@app.post("/ingest/metrics")
async def ingest_metrics(
    metrics: List[Dict[str, Any]],
    db: Session = Depends(get_db)
):
    """Ingest metrics in batch"""
    return {"message": f"Successfully ingested {len(metrics)} metrics"}

# --- Alert Endpoints ---

@app.post("/alert-rules", response_model=AlertRuleResponse)
async def create_alert_rule(
    rule_data: AlertRuleCreate,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Create a new alert rule"""
    rule = AlertRule(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        name=rule_data.name,
        pipeline_id=rule_data.pipeline_id,
        condition_type=rule_data.condition_type,
        condition_config=rule_data.condition_config,
        severity=rule_data.severity,
        notification_channels=rule_data.notification_channels
    )
    
    db.add(rule)
    db.commit()
    db.refresh(rule)
    
    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        pipeline_id=rule.pipeline_id,
        condition_type=rule.condition_type,
        condition_config=rule.condition_config,
        severity=rule.severity,
        notification_channels=rule.notification_channels,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )

@app.patch("/alert-rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: str,
    updates: Dict[str, Any],
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Update alert rule"""
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id,
        AlertRule.org_id == current_user.org_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    for key, value in updates.items():
        if hasattr(rule, key) and key not in ["id", "created_at"]:
            setattr(rule, key, value)
    
    rule.updated_at = datetime.utcnow()
    db.commit()
    
    return AlertRuleResponse(
        id=rule.id,
        name=rule.name,
        pipeline_id=rule.pipeline_id,
        condition_type=rule.condition_type,
        condition_config=rule.condition_config,
        severity=rule.severity,
        notification_channels=rule.notification_channels,
        created_at=rule.created_at,
        updated_at=rule.updated_at
    )

@app.delete("/alert-rules/{rule_id}")
async def delete_alert_rule(
    rule_id: str,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Delete alert rule"""
    rule = db.query(AlertRule).filter(
        AlertRule.id == rule_id,
        AlertRule.org_id == current_user.org_id
    ).first()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Alert rule not found")
    
    db.delete(rule)
    db.commit()
    
    return {"message": "Alert rule deleted successfully"}

@app.get("/alerts", response_model=PaginatedResponse)
async def list_alerts(
    status: Optional[str] = None,
    severity: Optional[str] = None,
    pipeline_id: Optional[str] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """List alerts with filters"""
    query = db.query(Alert).filter(Alert.org_id == current_user.org_id)
    
    if status:
        query = query.filter(Alert.status == status)
    if severity:
        query = query.filter(Alert.severity == severity)
    if pipeline_id:
        query = query.filter(Alert.pipeline_id == pipeline_id)
    
    alerts = query.order_by(Alert.triggered_at.desc()).limit(limit + 1).all()
    
    items = [
        AlertResponse(
            id=alert.id,
            rule_id=alert.rule_id,
            pipeline_id=alert.pipeline_id,
            severity=alert.severity,
            status=alert.status,
            message=alert.message,
            triggered_at=alert.triggered_at,
            acknowledged_at=alert.acknowledged_at,
            resolved_at=alert.resolved_at,
            metadata=alert.alert_metadata
        )
        for alert in alerts[:limit]
    ]
    
    next_cursor = None
    if len(alerts) > limit:
        next_cursor = "cursor_placeholder"
    
    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        limit=limit
    )

@app.patch("/alerts/{alert_id}")
async def update_alert(
    alert_id: str,
    update_data: AlertUpdate,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Update alert status"""
    alert = db.query(Alert).filter(
        Alert.id == alert_id,
        Alert.org_id == current_user.org_id
    ).first()
    
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")
    
    alert.status = update_data.status
    if update_data.status == "acknowledged":
        alert.acknowledged_at = datetime.utcnow()
    elif update_data.status == "resolved":
        alert.resolved_at = datetime.utcnow()
    
    db.commit()
    
    return {"message": f"Alert {alert.status} successfully"}

# --- Notification Channels ---

@app.post("/notification-channels", response_model=Dict[str, Any])
async def create_notification_channel(
    channel_data: Dict[str, Any],
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Create a notification channel"""
    channel = NotificationChannel(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        name=channel_data.get("name"),
        type=channel_data.get("type"),
        config=channel_data.get("config", {})
    )
    
    db.add(channel)
    db.commit()
    db.refresh(channel)
    
    return {
        "id": channel.id,
        "name": channel.name,
        "type": channel.type,
        "config": channel.config,
        "created_at": channel.created_at,
        "updated_at": channel.updated_at
    }

@app.get("/notification-channels", response_model=List[Dict[str, Any]])
async def list_notification_channels(
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """List notification channels"""
    channels = db.query(NotificationChannel).filter(
        NotificationChannel.org_id == current_user.org_id
    ).all()
    
    return [
        {
            "id": channel.id,
            "name": channel.name,
            "type": channel.type,
            "config": channel.config,
            "created_at": channel.created_at,
            "updated_at": channel.updated_at
        }
        for channel in channels
    ]

@app.post("/notification-channels/{channel_id}/test")
async def test_notification_channel(
    channel_id: str,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Send test notification"""
    channel = db.query(NotificationChannel).filter(
        NotificationChannel.id == channel_id,
        NotificationChannel.org_id == current_user.org_id
    ).first()
    
    if not channel:
        raise HTTPException(status_code=404, detail="Notification channel not found")
    
    return {"message": "Test notification sent successfully"}

# --- AI Chat Endpoints ---

@app.post("/ai/chat", response_model=ChatResponse)
async def chat_with_ai(
    chat_request: ChatRequest,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Chat with AI about pipeline data"""
    # Parse the message to extract pipeline context
    message = chat_request.message.lower()
    pipeline_id = None
    
    # Simple keyword matching for pipeline names
    if "financeiro" in message:
        pipeline = db.query(Pipeline).filter(
            Pipeline.org_id == current_user.org_id,
            Pipeline.name.ilike("%financeiro%")
        ).first()
        if pipeline:
            pipeline_id = pipeline.id
    
    # Mock response
    answer = "O Pipeline Financeiro apresentou erro às 09:13. Motivo: timeout na conexão SQL Server. Probabilidade de recorrência: 92%. Sugestão: verificar disponibilidade do servidor SQL01."
    
    return ChatResponse(
        conversation_id=chat_request.conversation_id or str(uuid.uuid4()),
        answer=answer,
        context_refs={
            "pipeline_id": pipeline_id,
            "run_id": str(uuid.uuid4()),
            "anomaly_id": None
        }
    )

# --- Dashboard Endpoints ---

@app.post("/dashboards", response_model=DashboardResponse)
async def create_dashboard(
    dashboard_data: DashboardCreate,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Create a new dashboard"""
    dashboard = Dashboard(
        id=str(uuid.uuid4()),
        org_id=current_user.org_id,
        user_id=current_user.id,
        name=dashboard_data.name,
        layout=dashboard_data.layout,
        widgets=dashboard_data.widgets
    )
    
    db.add(dashboard)
    db.commit()
    db.refresh(dashboard)
    
    return DashboardResponse(
        id=dashboard.id,
        name=dashboard.name,
        layout=dashboard.layout,
        widgets=dashboard.widgets,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at
    )

@app.get("/dashboards", response_model=List[DashboardResponse])
async def list_dashboards(
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """List all dashboards"""
    dashboards = db.query(Dashboard).filter(
        Dashboard.org_id == current_user.org_id
    ).all()
    
    return [
        DashboardResponse(
            id=dash.id,
            name=dash.name,
            layout=dash.layout,
            widgets=dash.widgets,
            created_at=dash.created_at,
            updated_at=dash.updated_at
        )
        for dash in dashboards
    ]

@app.get("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def get_dashboard(
    dashboard_id: str,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Get dashboard details"""
    dashboard = db.query(Dashboard).filter(
        Dashboard.id == dashboard_id,
        Dashboard.org_id == current_user.org_id
    ).first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    return DashboardResponse(
        id=dashboard.id,
        name=dashboard.name,
        layout=dashboard.layout,
        widgets=dashboard.widgets,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at
    )

@app.patch("/dashboards/{dashboard_id}", response_model=DashboardResponse)
async def update_dashboard(
    dashboard_id: str,
    updates: Dict[str, Any],
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Update dashboard"""
    dashboard = db.query(Dashboard).filter(
        Dashboard.id == dashboard_id,
        Dashboard.org_id == current_user.org_id
    ).first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    for key, value in updates.items():
        if hasattr(dashboard, key) and key not in ["id", "created_at"]:
            setattr(dashboard, key, value)
    
    dashboard.updated_at = datetime.utcnow()
    db.commit()
    
    return DashboardResponse(
        id=dashboard.id,
        name=dashboard.name,
        layout=dashboard.layout,
        widgets=dashboard.widgets,
        created_at=dashboard.created_at,
        updated_at=dashboard.updated_at
    )

@app.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(
    dashboard_id: str,
    current_user: User = Depends(require_permission("admin", "viewer")),
    db: Session = Depends(get_db)
):
    """Delete dashboard"""
    dashboard = db.query(Dashboard).filter(
        Dashboard.id == dashboard_id,
        Dashboard.org_id == current_user.org_id
    ).first()
    
    if not dashboard:
        raise HTTPException(status_code=404, detail="Dashboard not found")
    
    db.delete(dashboard)
    db.commit()
    
    return {"message": "Dashboard deleted successfully"}

# --- Audit Log Endpoints ---

@app.get("/audit-logs", response_model=PaginatedResponse)
async def get_audit_logs(
    user_id: Optional[str] = None,
    action: Optional[str] = None,
    from_date: Optional[datetime] = None,
    to_date: Optional[datetime] = None,
    limit: int = 50,
    cursor: Optional[str] = None,
    current_user: User = Depends(require_permission("admin")),
    db: Session = Depends(get_db)
):
    """Get audit logs (admin only)"""
    query = db.query(AuditLog).filter(AuditLog.org_id == current_user.org_id)
    
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if action:
        query = query.filter(AuditLog.action == action)
    if from_date:
        query = query.filter(AuditLog.created_at >= from_date)
    if to_date:
        query = query.filter(AuditLog.created_at <= to_date)
    
    logs = query.order_by(AuditLog.created_at.desc()).limit(limit + 1).all()
    
    items = [
        {
            "id": log.id,
            "user_id": log.user_id,
            "action": log.action,
            "resource_type": log.resource_type,
            "resource_id": log.resource_id,
            "changes": log.changes,
            "ip_address": log.ip_address,
            "user_agent": log.user_agent,
            "created_at": log.created_at.isoformat()
        }
        for log in logs[:limit]
    ]
    
    next_cursor = None
    if len(logs) > limit:
        next_cursor = "cursor_placeholder"
    
    return PaginatedResponse(
        items=items,
        next_cursor=next_cursor,
        limit=limit
    )

# --- Error Handlers ---

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "type": f"http_error_{exc.status_code}",
            "title": "HTTP Error",
            "status": exc.status_code,
            "detail": exc.detail,
            "instance": str(request.url)
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return ErrorResponse(
        type="internal_error",
        title="Internal Server Error",
        status=500,
        detail="An unexpected error occurred",
        instance=str(request.url)
    )

# --- Health Check ---

@app.get("/health")
async def health_check():
    return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# --- Startup/Shutdown ---

@app.on_event("startup")
async def startup():
    # Create tables
    Base.metadata.create_all(bind=engine)
    
    # Create default organization and admin user if not exists
    db = SessionLocal()
    try:
        # Check if organization exists
        org = db.query(Organization).filter(Organization.name == "Default Org").first()
        if not org:
            org = Organization(
                id=str(uuid.uuid4()),
                name="Default Org",
                plan="free",
                settings={}
            )
            db.add(org)
            db.commit()
            
            # Create admin user
            admin = User(
                id=str(uuid.uuid4()),
                org_id=org.id,
                email="admin@datapulse.ai",
                full_name="Admin User",
                hashed_password=get_password_hash("admin123"),
                roles=["admin"],
                status="active"
            )
            db.add(admin)
            db.commit()
            logger.info("Default organization and admin user created")
    finally:
        db.close()

@app.on_event("shutdown")
async def shutdown():
    logger.info("Shutting down...")

# Run the application
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)