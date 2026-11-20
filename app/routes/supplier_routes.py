"""
API Endpoints for Supplier Agents, Simulated Suppliers, and Vendor Registration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field, AliasChoices, ConfigDict
from typing import Optional, List
import hashlib
import re

from app.database.session import get_db
from app.database.models import Supplier

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])

DEFAULT_SIMULATED_SUPPLIERS = [
    {
        "id": "SUP-MORBI-01",
        "name": "Surya Ceramic & Vitrified Tiles (Morbi)",
        "base_price_per_box": 540.0,
        "min_walkaway_price": 475.0,
        "quality_score": 91.0,
        "delivery_lead_days": 7,
        "breakage_pct": 1.2,
    },
    {
        "id": "SUP-SHIROLI-02",
        "name": "Deccan Stone & Marble Depot (Shiroli MIDC)",
        "base_price_per_box": 555.0,
        "min_walkaway_price": 490.0,
        "quality_score": 89.0,
        "delivery_lead_days": 2,
        "breakage_pct": 0.6,
    },
    {
        "id": "SUP-UDAIPUR-03",
        "name": "Mewar Natural Marble & Granite Co.",
        "base_price_per_box": 565.0,
        "min_walkaway_price": 495.0,
        "quality_score": 94.0,
        "delivery_lead_days": 8,
        "breakage_pct": 1.0,
    },
]


class SupplierCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("id", "supplier_id", "username", "choose_username")
    )
    name: str = Field(
        validation_alias=AliasChoices("name", "company_name", "company", "depot_name", "company_depot_name")
    )
    username: Optional[str] = None
    password: Optional[str] = Field(
        default="supplier123",
        validation_alias=AliasChoices("password", "create_password")
    )
    phone: Optional[str] = Field(
        default="",
        validation_alias=AliasChoices("phone", "contact", "whatsapp", "supplier_contact")
    )
    location: Optional[str] = Field(
        default="Kolhapur Hub",
        validation_alias=AliasChoices("location", "hub", "depot_hub", "manufacturing_hub")
    )
    base_price_per_box: float = Field(
        default=540.0,
        gt=0,
        validation_alias=AliasChoices("base_price_per_box", "list_quote", "base_price", "rate_per_box")
    )
    min_walkaway_price: float = Field(
        default=480.0,
        gt=0,
        validation_alias=AliasChoices("min_walkaway_price", "bottom_margin", "walkaway_price", "min_price")
    )
    delivery_lead_days: int = Field(
        default=4,
        ge=1,
        validation_alias=AliasChoices("delivery_lead_days", "lead_days", "standard_lead_days", "lead")
    )
    breakage_pct: float = Field(
        default=0.8,
        ge=0.0,
        le=25.0,
        validation_alias=AliasChoices("breakage_pct", "breakage_guarantee", "breakage")
    )
    quality_score: float = Field(default=90.0, ge=0.0, le=100.0)
    strategy: Optional[str] = "balanced"


class SupplierLoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_id: str = Field(validation_alias=AliasChoices("supplier_id", "username", "id"))
    password: Optional[str] = ""


def _hash_password(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()


def _serialize_supplier(s: Supplier) -> dict:
    return {
        "id": s.id,
        "username": getattr(s, "username", None) or s.id,
        "name": s.name,
        "company_name": s.name,
        "phone": getattr(s, "phone", None) or "",
        "location": getattr(s, "location", None) or "Kolhapur Hub",
        "base_price_per_box": float(getattr(s, "base_price_per_box", 540.0) or 540.0),
        "list_quote": float(getattr(s, "base_price_per_box", 540.0) or 540.0),
        "min_walkaway_price": float(getattr(s, "min_walkaway_price", 480.0) or 480.0),
        "bottom_margin": float(getattr(s, "min_walkaway_price", 480.0) or 480.0),
        "delivery_lead_days": int(getattr(s, "delivery_lead_days", 4) or 4),
        "breakage_pct": float(getattr(s, "breakage_pct", 0.8) or 0.8),
        "quality_score": float(getattr(s, "quality_score", 90.0) or 90.0),
        "strategy": getattr(s, "strategy", None) or "balanced",
    }


def _ensure_simulated_suppliers(db: Session) -> List[Supplier]:
    existing = db.query(Supplier).all()
    if existing:
        return existing

    created_rows = []
    for item in DEFAULT_SIMULATED_SUPPLIERS:
        row = Supplier(
            id=item["id"],
            name=item["name"],
            base_price_per_box=item["base_price_per_box"],
            min_walkaway_price=item["min_walkaway_price"],
            quality_score=item["quality_score"],
            delivery_lead_days=item["delivery_lead_days"],
            breakage_pct=item["breakage_pct"],
        )
        if hasattr(row, "password_hash"):
            row.password_hash = _hash_password("supplier123")
        db.add(row)
        created_rows.append(row)

    db.commit()
    for row in created_rows:
        db.refresh(row)
    return created_rows


def _generate_supplier_id(raw_id: Optional[str], name: str, db: Session) -> str:
    seed_text = (raw_id or "").strip() or name
    slug = re.sub(r"[^A-Za-z0-9]+", "", seed_text).upper()[:8] or "SUP"
    base_id = slug if slug.startswith("SUP") else f"SUP-{slug}"
    candidate = base_id
    counter = 1
    while db.query(Supplier).filter(Supplier.id == candidate).first() is not None:
        counter += 1
        candidate = f"{base_id}-{counter}"
    return candidate


@router.get("")
@router.get("/")
def list_suppliers(db: Session = Depends(get_db)):
    """Return all registered/simulated suppliers from SQLite."""
    suppliers = _ensure_simulated_suppliers(db)
    return [_serialize_supplier(s) for s in suppliers]


@router.get("/simulated")
def list_simulated_suppliers(db: Session = Depends(get_db)):
    """Return simulated/registered supplier pool."""
    suppliers = _ensure_simulated_suppliers(db)
    return [_serialize_supplier(s) for s in suppliers]


@router.post("", status_code=201)
@router.post("/", status_code=201)
@router.post("/register", status_code=201)
def register_supplier(payload: SupplierCreateRequest, db: Session = Depends(get_db)):
    """Register a new supplier company in SQLite and return confirmation."""
    clean_name = (payload.name or "").strip()
    if not clean_name:
        raise HTTPException(status_code=400, detail="Company / Depot Name is required.")

    if payload.min_walkaway_price > payload.base_price_per_box:
        raise HTTPException(
            status_code=400,
            detail="Bottom Margin (₹ / Box) cannot exceed List Quote (₹ / Box)."
        )

    supplier_id = _generate_supplier_id(payload.id or payload.username, clean_name, db)

    new_supplier = Supplier(
        id=supplier_id,
        name=clean_name,
        base_price_per_box=float(payload.base_price_per_box),
        min_walkaway_price=float(payload.min_walkaway_price),
        quality_score=float(payload.quality_score),
        delivery_lead_days=int(payload.delivery_lead_days),
        breakage_pct=float(payload.breakage_pct),
    )

    if hasattr(new_supplier, "username"):
        new_supplier.username = (payload.username or payload.id or supplier_id).strip()
    if hasattr(new_supplier, "phone") and payload.phone:
        new_supplier.phone = payload.phone.strip()
    if hasattr(new_supplier, "location") and payload.location:
        new_supplier.location = payload.location.strip()
    if hasattr(new_supplier, "strategy") and payload.strategy:
        new_supplier.strategy = payload.strategy.strip()
    if hasattr(new_supplier, "password_hash"):
        new_supplier.password_hash = _hash_password(payload.password or "supplier123")

    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)

    serialized = _serialize_supplier(new_supplier)
    return {
        "status": "registered",
        "message": f"Registered '{new_supplier.name}' successfully! Login ID / Username: {new_supplier.id}",
        "supplier_id": new_supplier.id,
        "supplier": serialized,
        **serialized,
    }


@router.post("/login")
def login_supplier(payload: SupplierLoginRequest, db: Session = Depends(get_db)):
    """Authenticate a supplier by ID or username."""
    query_val = payload.supplier_id.strip()
    upper_val = query_val.upper()

    supplier = (
        db.query(Supplier)
        .filter((Supplier.id == upper_val) | (Supplier.id == query_val))
        .first()
    )
    if not supplier and hasattr(Supplier, "username"):
        supplier = db.query(Supplier).filter(Supplier.username == query_val).first()

    if not supplier:
        raise HTTPException(status_code=404, detail=f"Supplier '{query_val}' not found.")

    stored_hash = getattr(supplier, "password_hash", None)
    if stored_hash and payload.password:
        if _hash_password(payload.password) != stored_hash:
            raise HTTPException(status_code=401, detail="Invalid supplier credentials.")

    return {
        "status": "authenticated",
        "supplier": _serialize_supplier(supplier),
    }