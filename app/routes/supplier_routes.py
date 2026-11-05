"""
API Endpoints for Simulated Supplier Agents
Provides routes to inspect and configure supplier agent profiles.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List
import random

from app.database.session import get_db
from app.database.models import Supplier

router = APIRouter(prefix="/api/suppliers", tags=["Suppliers"])

from typing import Optional

class SupplierCreateRequest(BaseModel):
    name: str = Field(..., min_length=3)
    contact_number: Optional[str] = Field(default=None)  # <-- ADD HERE
    hub_location: str = Field(..., min_length=3)
    base_price_per_box: float = Field(..., gt=0)
    min_walkaway_price: float = Field(..., gt=0)
    standard_lead_days: int = Field(..., gt=0)
    min_lead_days: int = Field(..., gt=0)
    offered_breakage_pct: float = Field(..., ge=0, le=10)
    quality_score: float = Field(..., ge=0, le=100)
    reliability_score: float = Field(..., ge=0, le=100)
    agent_strategy: str = Field(default="balanced")

class SupplierResponse(BaseModel):
    id: str
    name: str
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

@router.get("", response_model=List[SupplierResponse])
def get_all_suppliers(db: Session = Depends(get_db)):
    """Retrieve all simulated supplier agent profiles."""
    return db.query(Supplier).all()

@router.post("/", response_model=SupplierResponse)
def create_supplier(payload: SupplierCreateRequest, db: Session = Depends(get_db)):
    # ... validation or ID generation logic ...

    new_supplier = Supplier(
        id=supplier_id,
        name=payload.name,
        contact_number=payload.contact_number,  # <-- ADD HERE
        hub_location=payload.hub_location,
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

    if payload.min_lead_days > payload.standard_lead_days:
        raise HTTPException(
            status_code=400,
            detail="Minimum lead days cannot exceed standard lead days."
        )

    supplier_id = f"SUP-TILE-{random.randint(100, 999)}"
    new_supplier = Supplier(
        id=supplier_id,
        name=payload.name,
        hub_location=payload.hub_location,
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