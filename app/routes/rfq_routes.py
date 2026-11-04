"""
API Endpoints for Procurement Requests (RFQs)
Provides clean endpoints to fetch and submit procurement requests.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import List
from datetime import datetime
import random

from app.database.session import get_db
from app.database.models import RFQ

router = APIRouter(prefix="/api/rfqs", tags=["RFQs"])

class PriorityWeightsSchema(BaseModel):
    price: float = Field(..., ge=0, le=100)
    quality: float = Field(..., ge=0, le=100)
    delivery: float = Field(..., ge=0, le=100)
    warranty: float = Field(..., ge=0, le=100)

class RFQCreateRequest(BaseModel):
    category: str
    size: str
    quantity: int = Field(..., gt=0)
    budget_ceiling: float = Field(..., gt=0)
    delivery_deadline: str
    quality_grade: str
    max_breakage: float = Field(..., ge=0, le=10)
    weights: PriorityWeightsSchema

class RFQResponse(BaseModel):
    id: str
    category: str
    size: str
    quantity: int
    budget_ceiling: float
    delivery_deadline: str
    quality_grade: str
    max_breakage: float
    source_hub: str
    status: str
    weight_price: float
    weight_quality: float
    weight_delivery: float
    weight_warranty: float
    created_at: datetime

    class Config:
        from_attributes = True

@router.get("", response_model=List[RFQResponse])
def get_all_rfqs(db: Session = Depends(get_db)):
    """Fetch all RFQs from SQLite, newest first."""
    return db.query(RFQ).order_by(RFQ.created_at.desc()).all()

@router.post("", response_model=RFQResponse)
def create_rfq(payload: RFQCreateRequest, db: Session = Depends(get_db)):
    """Create a new procurement request with validation."""
    total_weights = (
        payload.weights.price + 
        payload.weights.quality + 
        payload.weights.delivery + 
        payload.weights.warranty
    )
    if round(total_weights, 1) != 100.0:
        raise HTTPException(
            status_code=400, 
            detail=f"Weights must sum to exactly 100%. Current sum: {total_weights}%"
        )

    rfq_id = f"RFQ-MMG-{random.randint(104, 999)}"
    
    new_rfq = RFQ(
        id=rfq_id,
        category=payload.category,
        size=payload.size,
        quantity=payload.quantity,
        budget_ceiling=payload.budget_ceiling,
        delivery_deadline=payload.delivery_deadline,
        quality_grade=payload.quality_grade,
        max_breakage=payload.max_breakage,
        source_hub="Regional Supply to Mudhal Titta Depot",
        status="Evaluating Quotes",
        weight_price=payload.weights.price,
        weight_quality=payload.weights.quality,
        weight_delivery=payload.weights.delivery,
        weight_warranty=payload.weights.warranty
    )

    db.add(new_rfq)
    db.commit()
    db.refresh(new_rfq)
    return new_rfq