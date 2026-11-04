"""
API Endpoints for Multi-Round Negotiations, Audit Trails & Notifications
Triggers simulated supplier rounds, archives transcripts, and manages alerts.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
import uuid

from app.database.session import get_db
from app.database.models import RFQ, Supplier, NegotiationSession, NegotiationRound, Notification
from app.services.negotiation_engine import run_negotiation_simulation

router = APIRouter(prefix="/api", tags=["Negotiations & Notifications"])


@router.post("/negotiations/start/{rfq_id}")
def start_negotiation(rfq_id: str, db: Session = Depends(get_db)):
    """
    Executes a 3-round negotiation for the specified RFQ against all active suppliers.
    Persists rounds, session summary, in-app notifications, and updates RFQ status.
    """
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    suppliers = db.query(Supplier).all()
    if not suppliers:
        raise HTTPException(status_code=400, detail="No suppliers configured in database")

    # Run the multi-round negotiation engine
    outcome = run_negotiation_simulation(rfq, suppliers)

    # Persist the session to SQLite
    session_id = f"NEG-{uuid.uuid4().hex[:8].upper()}"
    new_session = NegotiationSession(
        id=session_id,
        rfq_id=rfq.id,
        status="completed",
        recommended_supplier_id=outcome["winning_supplier"]["id"],
        final_price=outcome["final_total_cost"],
        savings_amount=outcome["savings_amount"],
        explanation_summary=outcome["explanation"]
    )
    db.add(new_session)

    # Persist each round in SQLite
    for r in outcome["rounds"]:
        db_round = NegotiationRound(
            session_id=session_id,
            round_number=r["round_number"],
            supplier_id=r["supplier_id"],
            supplier_quote=r["quote_per_box"],
            buyer_counter=r.get("buyer_counter"),
            lead_days_offered=r["lead_days"],
            breakage_offered=r["breakage_pct"],
            composite_score=r["composite_score"],
            decision=r["decision"],
            rationale=r["rationale"]
        )
        db.add(db_round)

    # Update RFQ status to Ready for Approval
    rfq.status = "Ready for Approval"

    # Add In-App Notification events for the buyer
    notif1 = Notification(
        rfq_id=rfq.id,
        title=f"Negotiation Completed for {rfq.id}",
        message=f"Autonomous agents finalized 3 rounds. Recommended: {outcome['winning_supplier']['name']} with ₹{outcome['savings_amount']:,.0f} saved.",
        category="success"
    )
    notif2 = Notification(
        rfq_id=rfq.id,
        title="Ready for Human Sign-off",
        message=f"Purchase Order ready for review. Budget ceiling respected: ₹{outcome['final_total_cost']:,.0f} <= ₹{rfq.budget_ceiling:,.0f}.",
        category="info"
    )
    db.add(notif1)
    db.add(notif2)
    db.commit()

    return outcome


@router.get("/negotiations/{rfq_id}")
def get_negotiation_history(rfq_id: str, db: Session = Depends(get_db)):
    """
    Fetches the latest completed negotiation audit transcript for an RFQ,
    including each round's quotes, lead days, composite scores, and supplier metadata.
    """
    session = (
        db.query(NegotiationSession)
        .filter(NegotiationSession.rfq_id == rfq_id)
        .order_by(NegotiationSession.created_at.desc())
        .first()
    )
    if not session:
        raise HTTPException(status_code=404, detail="No negotiation session found for this RFQ")

    rounds = (
        db.query(NegotiationRound)
        .filter(NegotiationRound.session_id == session.id)
        .order_by(NegotiationRound.round_number.asc(), NegotiationRound.supplier_id.asc())
        .all()
    )

    suppliers = {s.id: s.name for s in db.query(Supplier).all()}

    rounds_data = []
    for r in rounds:
        rounds_data.append({
            "round_number": r.round_number,
            "supplier_id": r.supplier_id,
            "supplier_name": suppliers.get(r.supplier_id, r.supplier_id),
            "quote_per_box": r.supplier_quote,
            "buyer_counter": r.buyer_counter,
            "lead_days": r.lead_days_offered,
            "breakage_pct": r.breakage_offered,
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
        "recommended_supplier_name": suppliers.get(session.recommended_supplier_id, session.recommended_supplier_id),
        "final_price": session.final_price,
        "savings_amount": session.savings_amount,
        "explanation": session.explanation_summary,
        "rounds": rounds_data
    }


@router.get("/notifications")
def get_notifications(db: Session = Depends(get_db)):
    """Fetch all in-app notifications, newest first."""
    # Ensure tables exist
    notifications = db.query(Notification).order_by(Notification.created_at.desc()).limit(15).all()
    return [
        {
            "id": n.id,
            "rfq_id": n.rfq_id,
            "title": n.title,
            "message": n.message,
            "category": n.category,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%d %b %I:%M %p") if n.created_at else ""
        }
        for n in notifications
    ]