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
        "standard_lead_days": 7,
        "min_lead_days": 4,
        "offered_breakage_pct": 1.2,
    },
    {
        "id": "SUP-SHIROLI-02",
        "name": "Deccan Stone & Marble Depot (Shiroli MIDC)",
        "base_price_per_box": 555.0,
        "min_walkaway_price": 490.0,
        "quality_score": 89.0,
        "standard_lead_days": 2,
        "min_lead_days": 1,
        "offered_breakage_pct": 0.6,
    },
    {
        "id": "SUP-UDAIPUR-03",
        "name": "Mewar Natural Marble & Granite Co.",
        "base_price_per_box": 565.0,
        "min_walkaway_price": 495.0,
        "quality_score": 94.0,
        "standard_lead_days": 8,
        "min_lead_days": 5,
        "offered_breakage_pct": 1.0,
    },
]


class SupplierCreateRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = Field(
        default=None,
        validation_alias=AliasChoices("id", "supplier_id", "username", "choose_username")
    )
    username: Optional[str] = None
    password: Optional[str] = Field(
        default="supplier123",
        validation_alias=AliasChoices("password", "create_password")
    )
    name: str = Field(
        validation_alias=AliasChoices("name", "company_name", "company", "depot_name", "company_depot_name")
    )
    phone: Optional[str] = Field(
        default="",
        validation_alias=AliasChoices("phone", "contact_number", "contact", "whatsapp", "supplier_contact")
    )
    location: Optional[str] = Field(
        default="Kolhapur Hub",
        validation_alias=AliasChoices("location", "hub_location", "hub", "depot_hub", "manufacturing_hub")
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
    standard_lead_days: int = Field(
        default=4,
        ge=1,
        validation_alias=AliasChoices("standard_lead_days", "delivery_lead_days", "lead_days", "lead")
    )
    min_lead_days: Optional[int] = Field(default=None, ge=1)
    offered_breakage_pct: float = Field(
        default=0.8,
        ge=0.0,
        le=25.0,
        validation_alias=AliasChoices("offered_breakage_pct", "breakage_pct", "breakage_guarantee", "breakage")
    )
    quality_score: float = Field(default=92.0, ge=0.0, le=100.0)
    reliability_score: float = Field(default=90.0, ge=0.0, le=100.0)
    strategy: Optional[str] = Field(
        default="balanced",
        validation_alias=AliasChoices("strategy", "agent_strategy")
    )


class SupplierLoginRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    supplier_id: str = Field(validation_alias=AliasChoices("supplier_id", "username", "id"))
    password: Optional[str] = ""


def _hash_password(raw: str) -> str:
    return hashlib.sha256((raw or "").encode("utf-8")).hexdigest()


def _model_columns() -> set:
    return set(Supplier.__table__.columns.keys())


def _build_supplier_instance(values: dict) -> Supplier:
    cols = _model_columns()
    clean_kwargs = {k: v for k, v in values.items() if k in cols and v is not None}
    return Supplier(**clean_kwargs)


def _serialize_supplier(s: Supplier) -> dict:
    lead_val = (
        getattr(s, "standard_lead_days", None)
        if getattr(s, "standard_lead_days", None) is not None
        else getattr(s, "delivery_lead_days", 4)
    )
    breakage_val = (
        getattr(s, "offered_breakage_pct", None)
        if getattr(s, "offered_breakage_pct", None) is not None
        else getattr(s, "breakage_pct", 0.8)
    )
    loc_val = (
        getattr(s, "hub_location", None)
        or getattr(s, "location", None)
        or "Kolhapur Hub"
    )
    phone_val = (
        getattr(s, "contact_number", None)
        or getattr(s, "phone", None)
        or ""
    )
    strat_val = (
        getattr(s, "agent_strategy", None)
        or getattr(s, "strategy", None)
        or "balanced"
    )

    return {
        "id": s.id,
        "username": getattr(s, "username", None) or s.id,
        "name": s.name,
        "company_name": s.name,
        "phone": phone_val,
        "contact_number": phone_val,
        "location": loc_val,
        "hub_location": loc_val,
        "base_price_per_box": float(getattr(s, "base_price_per_box", 540.0) or 540.0),
        "list_quote": float(getattr(s, "base_price_per_box", 540.0) or 540.0),
        "min_walkaway_price": float(getattr(s, "min_walkaway_price", 480.0) or 480.0),
        "bottom_margin": float(getattr(s, "min_walkaway_price", 480.0) or 480.0),
        "standard_lead_days": int(lead_val or 4),
        "delivery_lead_days": int(lead_val or 4),
        "offered_breakage_pct": float(breakage_val if breakage_val is not None else 0.8),
        "breakage_pct": float(breakage_val if breakage_val is not None else 0.8),
        "quality_score": float(getattr(s, "quality_score", 92.0) or 92.0),
        "reliability_score": float(getattr(s, "reliability_score", 90.0) or 90.0),
        "strategy": strat_val,
        "agent_strategy": strat_val,
    }


def _ensure_simulated_suppliers(db: Session) -> List[Supplier]:
    existing = db.query(Supplier).all()
    if existing:
        return existing

    created_rows = []
    for item in DEFAULT_SIMULATED_SUPPLIERS:
        row = _build_supplier_instance({
            "id": item["id"],
            "username": item["id"],
            "name": item["name"],
            "password_hash": _hash_password("supplier123"),
            "base_price_per_box": item["base_price_per_box"],
            "min_walkaway_price": item["min_walkaway_price"],
            "quality_score": item["quality_score"],
            "reliability_score": 90.0,
            "standard_lead_days": item["standard_lead_days"],
            "min_lead_days": item["min_lead_days"],
            "offered_breakage_pct": item["offered_breakage_pct"],
            "agent_strategy": "balanced",
        })
        db.add(row)
        created_rows.append(row)

    db.commit()
    for row in created_rows:
        db.refresh(row)
    return created_rows


def _generate_supplier_id(raw_id: Optional[str], name: str, db: Session) -> str:
    seed_text = (raw_id or "").strip() or name
    slug = re.sub(r"[^A-Za-z0-9]+", "", seed_text).upper()[:10] or "SUP"
    base = slug if slug.startswith("SUP") else f"SUP-{slug}"
    candidate = base
    counter = 1
    while db.query(Supplier).filter(Supplier.id == candidate).first() is not None:
        counter += 1
        candidate = f"{base}-{counter}"
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
    clean_user = (payload.username or payload.id or supplier_id).strip()
    min_lead = payload.min_lead_days if payload.min_lead_days is not None else max(1, payload.standard_lead_days - 2)

    new_supplier = _build_supplier_instance({
        "id": supplier_id,
        "username": clean_user,
        "name": clean_name,
        "password_hash": _hash_password(payload.password or "supplier123"),
        "password": payload.password or "supplier123",
        "phone": (payload.phone or "").strip(),
        "contact_number": (payload.phone or "").strip(),
        "location": (payload.location or "Kolhapur Hub").strip(),
        "hub_location": (payload.location or "Kolhapur Hub").strip(),
        "base_price_per_box": float(payload.base_price_per_box),
        "min_walkaway_price": float(payload.min_walkaway_price),
        "quality_score": float(payload.quality_score),
        "reliability_score": float(payload.reliability_score),
        "standard_lead_days": int(payload.standard_lead_days),
        "min_lead_days": int(min_lead),
        "offered_breakage_pct": float(payload.offered_breakage_pct),
        "agent_strategy": payload.strategy or "balanced",
    })

    db.add(new_supplier)
    db.commit()
    db.refresh(new_supplier)

    serialized = _serialize_supplier(new_supplier)
    return {
        "status": "registered",
        "message": f"Registered '{new_supplier.name}' successfully! Supplier ID: {new_supplier.id}",
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

    serialized = _serialize_supplier(supplier)
    return {
        "status": "authenticated",
        "supplier": serialized,
        **serialized,
    }