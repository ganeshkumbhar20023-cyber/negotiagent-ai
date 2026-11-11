"""
Supplier Authentication & Profile Routes
Handles supplier registration, login verification, and profile queries.
"""

import hashlib
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.database.models import Supplier

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])


def hash_password(password: str) -> str:
    """Generates a secure SHA-256 hash for credentials."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


# --- REQUEST & RESPONSE SCHEMAS ---

class SupplierRegisterRequest(BaseModel):
    id: Optional[str] = None
    username: str = Field(..., min_length=3, description="Unique login username")
    password: str = Field(..., min_length=4, description="Secret supplier password")
    name: str = Field(..., min_length=2, description="Company / Depot Name")
    contact_number: Optional[str] = Field(default=None, description="Mobile / WhatsApp number")
    hub_location: str = Field(..., min_length=2, description="Depot or manufacturing hub")
    base_price_per_box: float = Field(..., gt=0, description="List price per unit/box")
    min_walkaway_price: float = Field(..., gt=0, description="Absolute bottom concession floor")
    standard_lead_days: int = Field(..., gt=0, description="Normal dispatch lead days")
    min_lead_days: int = Field(..., gt=0, description="Expedited dispatch lead days")
    offered_breakage_pct: float = Field(..., ge=0, le=15, description="Transit breakage tolerance (%)")
    quality_score: float = Field(default=90.0, ge=0, le=100)
    reliability_score: float = Field(default=90.0, ge=0, le=100)
    agent_strategy: str = Field(default="balanced")


class SupplierLegacyCreateRequest(BaseModel):
    """Fallback schema supporting existing unit tests and owner creation modal."""
    id: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None
    name: str = Field(..., min_length=2)
    contact_number: Optional[str] = None
    hub_location: str = Field(..., min_length=2)
    base_price_per_box: float = Field(..., gt=0)
    min_walkaway_price: float = Field(..., gt=0)
    standard_lead_days: int = Field(..., gt=0)
    min_lead_days: int = Field(..., gt=0)
    offered_breakage_pct: float = Field(..., ge=0, le=15)
    quality_score: float = Field(default=90.0, ge=0, le=100)
    reliability_score: float = Field(default=90.0, ge=0, le=100)
    agent_strategy: str = Field(default="balanced")


class SupplierLoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class SupplierProfileResponse(BaseModel):
    id: str
    username: str
    name: str
    contact_number: Optional[str] = None
    hub_location: str
    base_price_per_box: float
    min_walkaway_price: float
    standard_lead_days: int
    min_lead_days: int
    offered_breakage_pct: float
    quality_score: float
    reliability_score: float
    agent_strategy: str

    class Config:
        from_attributes = True


# --- API ROUTE HANDLERS ---

@router.get("", response_model=List[SupplierProfileResponse])
@router.get("/", response_model=List[SupplierProfileResponse])
def get_all_suppliers(db: Session = Depends(get_db)):
    """Returns a list of all registered supplier profiles."""
    return db.query(Supplier).all()


@router.post("/register", response_model=SupplierProfileResponse, status_code=status.HTTP_201_CREATED)
def register_supplier(payload: SupplierRegisterRequest, db: Session = Depends(get_db)):
    """Registers a new supplier with unique credentials and commercial parameters."""
    normalized_user = payload.username.strip().lower()

    # 1. Prevent duplicate usernames
    if db.query(Supplier).filter(Supplier.username == normalized_user).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This username is already taken. Please choose another username."
        )

    # 2. Walkaway bounds check
    if payload.min_walkaway_price > payload.base_price_per_box:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Minimum walkaway price cannot be higher than your opening list price."
        )

    # 3. Lead time sanity check
    if payload.min_lead_days > payload.standard_lead_days:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Expedited lead days cannot exceed standard dispatch lead days."
        )

    # 4. Generate unique ID if not provided
    sup_id = payload.id.strip() if payload.id else f"SUP-DEPOT-{int(datetime.utcnow().timestamp())}"
    if db.query(Supplier).filter(Supplier.id == sup_id).first():
        sup_id = f"SUP-DEPOT-{int(datetime.utcnow().timestamp())}"

    new_supplier = Supplier(
        id=sup_id,
        username=normalized_user,
        password_hash=hash_password(payload.password.strip()),
        name=payload.name.strip(),
        contact_number=payload.contact_number.strip() if payload.contact_number else None,
        hub_location=payload.hub_location.strip(),
        base_price_per_box=payload.base_price_per_box,
        min_walkaway_price=payload.min_walkaway_price,
        standard_lead_days=payload.standard_lead_days,
        min_lead_days=payload.min_lead_days,
        offered_breakage_pct=payload.offered_breakage_pct,
        quality_score=payload.quality_score,
        reliability_score=payload.reliability_score,
        agent_strategy=payload.agent_strategy
    )

    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.post("/", response_model=SupplierProfileResponse, status_code=status.HTTP_201_CREATED)
def create_supplier_legacy(payload: SupplierLegacyCreateRequest, db: Session = Depends(get_db)):
    """
    Backwards-compatible endpoint for pytest test suites and owner admin panel.
    Auto-generates credentials if none are provided.
    """
    ts = int(datetime.utcnow().timestamp())
    sup_id = payload.id.strip() if payload.id else f"SUP-DEPOT-{ts}"
    normalized_user = (payload.username or f"vendor_{ts}").strip().lower()
    raw_password = payload.password or "supplier123"

    existing_user = db.query(Supplier).filter(Supplier.username == normalized_user).first()
    if existing_user:
        normalized_user = f"{normalized_user}_{ts}"

    new_supplier = Supplier(
        id=sup_id,
        username=normalized_user,
        password_hash=hash_password(raw_password),
        name=payload.name.strip(),
        contact_number=payload.contact_number.strip() if payload.contact_number else None,
        hub_location=payload.hub_location.strip(),
        base_price_per_box=payload.base_price_per_box,
        min_walkaway_price=payload.min_walkaway_price,
        standard_lead_days=payload.standard_lead_days,
        min_lead_days=payload.min_lead_days,
        offered_breakage_pct=payload.offered_breakage_pct,
        quality_score=payload.quality_score,
        reliability_score=payload.reliability_score,
        agent_strategy=payload.agent_strategy
    )

    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)
    return new_supplier


@router.post("/login", response_model=SupplierProfileResponse)
def login_supplier(payload: SupplierLoginRequest, db: Session = Depends(get_db)):
    """Verifies supplier credentials and opens session on the supplier console."""
    normalized_user = payload.username.strip().lower()
    hashed = hash_password(payload.password.strip())

    supplier = db.query(Supplier).filter(
        Supplier.username == normalized_user,
        Supplier.password_hash == hashed
    ).first()

    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid supplier username or password."
        )

    return supplier


@router.get("/me/{supplier_id}", response_model=SupplierProfileResponse)
def get_supplier_profile(supplier_id: str, db: Session = Depends(get_db)):
    """Fetches private profile details for the authenticated supplier."""
    supplier = db.query(Supplier).filter(Supplier.id == supplier_id).first()
    if not supplier:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Supplier profile '{supplier_id}' not found."
        )
    return supplier