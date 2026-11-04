"""
API Endpoints for Multi-Round Negotiations and Live Mobile Bidding
Supports autonomous multi-agent simulation and live real-time human bidding via mobile portal.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
from typing import Optional

from app.database.session import get_db
from app.database.models import RFQ, Supplier, NegotiationSession, NegotiationRound
from app.services.negotiation_engine import run_negotiation_simulation

router = APIRouter(prefix="/api/negotiations", tags=["Negotiations"])


class LiveSupplierBidRequest(BaseModel):
    rfq_id: str
    supplier_id: str
    round_number: int = Field(..., ge=1, le=3)
    rate_per_box: float = Field(..., gt=0)
    lead_days: int = Field(..., gt=0)
    breakage_pct: float = Field(..., ge=0.0, le=10.0)
    remarks: Optional[str] = ""


@router.post("/start/{rfq_id}")
def start_negotiation(rfq_id: str, db: Session = Depends(get_db)):
    """Executes the autonomous 3-round multi-agent auction for an RFQ."""
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=404, detail=f"RFQ '{rfq_id}' not found.")

    suppliers = db.query(Supplier).all()
    if not suppliers:
        raise HTTPException(status_code=400, detail="No registered supplier agents found in database.")

    # Run multi-agent simulation engine
    outcome = run_negotiation_simulation(rfq, suppliers)

    # Persist or update negotiation session
    session_id = f"SESS-{rfq.id}"
    session = db.query(NegotiationSession).filter(NegotiationSession.id == session_id).first()
    if not session:
        session = NegotiationSession(
            id=session_id,
            rfq_id=rfq.id,
            status="completed"
        )
        db.add(session)
    else:
        # Clear previous rounds if re-running
        db.query(NegotiationRound).filter(NegotiationRound.session_id == session_id).delete()

    winning_sup = outcome.get("winning_supplier") or {}
    session.recommended_supplier_id = winning_sup.get("id")
    session.final_price = float(outcome.get("final_total_cost") or 0.0)
    session.savings_amount = float(outcome.get("savings_amount") or 0.0)
    session.explanation_summary = str(outcome.get("explanation") or "")
    session.status = "completed"

    # Persist each round record, handling alternative key names safely
    rounds_list = outcome.get("rounds") or []
    for r in rounds_list:
        quote_val = (
            r.get("supplier_quote")
            if r.get("supplier_quote") is not None
            else r.get("quote")
            if r.get("quote") is not None
            else r.get("rate_per_box", 500.0)
        )
        lead_val = (
            r.get("lead_days_offered")
            if r.get("lead_days_offered") is not None
            else r.get("lead_days", 4)
        )
        breakage_val = (
            r.get("breakage_offered")
            if r.get("breakage_offered") is not None
            else r.get("breakage_pct")
            if r.get("breakage_pct") is not None
            else r.get("breakage", 1.0)
        )
        score_val = (
            r.get("composite_score")
            if r.get("composite_score") is not None
            else r.get("score", 70.0)
        )

        rnd_record = NegotiationRound(
            session_id=session.id,
            round_number=int(r.get("round_number", 1)),
            supplier_id=str(r.get("supplier_id", "")),
            supplier_quote=float(quote_val),
            buyer_counter=float(r.get("buyer_counter") or 0.0),
            lead_days_offered=int(lead_val),
            breakage_offered=float(breakage_val),
            composite_score=float(score_val),
            decision=str(r.get("decision", "EVALUATING")),
            rationale=str(r.get("rationale", ""))
        )
        db.add(rnd_record)

    rfq.status = "Negotiation Awarded"
    db.commit()

    return outcome


@router.get("/{rfq_id}")
def get_negotiation_history(rfq_id: str, db: Session = Depends(get_db)):
    """Retrieves full transcript, concession rounds, and rationale for audit replay."""
    session = (
        db.query(NegotiationSession)
        .filter(NegotiationSession.rfq_id == rfq_id)
        .order_by(NegotiationSession.created_at.desc())
        .first()
    )

    if not session:
        raise HTTPException(status_code=404, detail=f"No negotiation session found for RFQ '{rfq_id}'.")

    rounds = (
        db.query(NegotiationRound)
        .filter(NegotiationRound.session_id == session.id)
        .order_by(NegotiationRound.round_number.asc(), NegotiationRound.id.asc())
        .all()
    )

    suppliers_map = {s.id: s.name for s in db.query(Supplier).all()}

    rounds_data = []
    for r in rounds:
        rounds_data.append({
            "id": r.id,
            "round_number": r.round_number,
            "supplier_id": r.supplier_id,
            "supplier_name": suppliers_map.get(r.supplier_id, r.supplier_id),
            "supplier_quote": r.supplier_quote,
            "buyer_counter": r.buyer_counter,
            "lead_days_offered": r.lead_days_offered,
            "breakage_offered": r.breakage_offered,
            "composite_score": r.composite_score,
            "decision": r.decision,
            "rationale": r.rationale,
            "timestamp": r.timestamp.isoformat() if r.timestamp else None
        })

    return {
        "session_id": session.id,
        "rfq_id": session.rfq_id,
        "status": session.status,
        "recommended_supplier_id": session.recommended_supplier_id,
        "recommended_supplier_name": suppliers_map.get(session.recommended_supplier_id, session.recommended_supplier_id),
        "final_price": session.final_price,
        "savings_amount": session.savings_amount,
        "explanation": session.explanation_summary,
        "rounds": rounds_data
    }


@router.post("/live-bid")
def submit_live_supplier_bid(payload: LiveSupplierBidRequest, db: Session = Depends(get_db)):
    """Processes a live manual bid entered from a mobile phone by a human supplier."""
    rfq = db.query(RFQ).filter(RFQ.id == payload.rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=404, detail=f"RFQ '{payload.rfq_id}' not found.")

    supplier = db.query(Supplier).filter(Supplier.id == payload.supplier_id).first()
    supplier_name = supplier.name if supplier else payload.supplier_id

    # Retrieve or create negotiation session
    session = (
        db.query(NegotiationSession)
        .filter(NegotiationSession.rfq_id == payload.rfq_id)
        .order_by(NegotiationSession.created_at.desc())
        .first()
    )

    if not session:
        session = NegotiationSession(
            id=f"SESS-{payload.rfq_id}",
            rfq_id=payload.rfq_id,
            status="in_progress"
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    target_rate = round(rfq.budget_ceiling / rfq.quantity, 2)
    buyer_counter = round(target_rate * 0.94, 2) if payload.rate_per_box > target_rate else payload.rate_per_box

    # Calculate sub-scores and multi-criteria utility score U
    price_ratio = (rfq.budget_ceiling - (payload.rate_per_box * rfq.quantity)) / rfq.budget_ceiling
    if payload.rate_per_box <= target_rate:
        s_price = min(100.0, max(0.0, 50.0 + (price_ratio * 150.0)))
    else:
        s_price = max(0.0, 50.0 - (abs(price_ratio) * 100.0))

    s_lead = min(100.0, max(0.0, (1.0 - (payload.lead_days / 7.0)) * 100.0))
    s_breakage = min(100.0, max(0.0, (1.0 - (payload.breakage_pct / max(0.1, rfq.max_breakage))) * 100.0))
    s_quality = supplier.quality_score if supplier else 90.0

    u_score = (
        (s_price * (rfq.weight_price / 100.0)) +
        (s_quality * (rfq.weight_quality / 100.0)) +
        (s_lead * (rfq.weight_delivery / 100.0)) +
        (s_breakage * (rfq.weight_warranty / 100.0))
    )

    decision = "ACCEPTED" if (payload.round_number == 3 and payload.rate_per_box <= target_rate) else "COUNTER_OFFERED"

    round_record = NegotiationRound(
        session_id=session.id,
        round_number=payload.round_number,
        supplier_id=payload.supplier_id,
        supplier_quote=payload.rate_per_box,
        buyer_counter=buyer_counter,
        lead_days_offered=payload.lead_days,
        breakage_offered=payload.breakage_pct,
        composite_score=round(u_score, 2),
        decision=decision,
        rationale=payload.remarks or f"Live Mobile Bid submitted by {supplier_name} for Round {payload.round_number}"
    )
    db.add(round_record)

    # If Round 3 completed, award session
    if payload.round_number == 3:
        session.status = "completed"
        session.recommended_supplier_id = payload.supplier_id
        session.final_price = round(payload.rate_per_box * rfq.quantity, 2)
        initial_cost = (supplier.base_price_per_box * rfq.quantity) if supplier else rfq.budget_ceiling
        session.savings_amount = max(0.0, round(initial_cost - session.final_price, 2))
        session.explanation_summary = (
            f"Consignment awarded to {supplier_name} at ₹{payload.rate_per_box}/box "
            f"via live phone bidding. Total order ₹{session.final_price:,.2f} with {payload.lead_days} days lead time."
        )
        rfq.status = "Negotiation Awarded"

    db.commit()

    return {
        "status": "success",
        "round_number": payload.round_number,
        "submitted_rate": payload.rate_per_box,
        "buyer_counter": buyer_counter,
        "composite_score": round(u_score, 2),
        "decision": decision
    }