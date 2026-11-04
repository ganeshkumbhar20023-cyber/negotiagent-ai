"""
API Endpoints for Human Approvals, Purchase Orders & Sandbox Payments
Domain: Shree Mahalaxmi Marbel and Granite (Mudhal Titta, Kolhapur)
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import datetime
import uuid

from app.database.session import get_db
from app.database.models import RFQ, Supplier, NegotiationSession, PurchaseOrder, Notification

router = APIRouter(prefix="/api/orders", tags=["Approvals & Purchase Orders"])


@router.get("")
def list_purchase_orders(db: Session = Depends(get_db)):
    """Fetch all generated Purchase Orders from SQLite, newest first."""
    orders = db.query(PurchaseOrder).order_by(PurchaseOrder.created_at.desc()).all()
    return [
        {
            "id": po.id,
            "rfq_id": po.rfq_id,
            "supplier_id": po.supplier_id,
            "supplier_name": po.supplier_name,
            "item_description": po.item_description,
            "quantity": po.quantity,
            "rate_per_box": po.rate_per_box,
            "subtotal_amount": po.subtotal_amount,
            "gst_rate_pct": po.gst_rate_pct,
            "gst_amount": po.gst_amount,
            "total_amount": po.total_amount,
            "lead_days": po.lead_days,
            "breakage_allowance_pct": po.breakage_allowance_pct,
            "payment_status": po.payment_status,
            "approval_status": po.approval_status,
            "approver_name": po.approver_name,
            "created_at": po.created_at.strftime("%d %b %Y, %I:%M %p") if po.created_at else ""
        }
        for po in orders
    ]


@router.post("/approve/{rfq_id}")
def approve_negotiation(rfq_id: str, db: Session = Depends(get_db)):
    """
    Human Approver sign-off for Shree Mahalaxmi Marbel and Granite.
    Calculates 18% GST (Tiles/Granite standard).
    """
    rfq = db.query(RFQ).filter(RFQ.id == rfq_id).first()
    if not rfq:
        raise HTTPException(status_code=404, detail="RFQ not found")

    session = (
        db.query(NegotiationSession)
        .filter(NegotiationSession.rfq_id == rfq_id)
        .order_by(NegotiationSession.created_at.desc())
        .first()
    )
    if not session or not session.recommended_supplier_id:
        raise HTTPException(status_code=400, detail="Cannot approve: No completed negotiation session found for this RFQ")

    supplier = db.query(Supplier).filter(Supplier.id == session.recommended_supplier_id).first()
    if not supplier:
        raise HTTPException(status_code=400, detail="Recommended supplier profile missing")

    existing_po = db.query(PurchaseOrder).filter(PurchaseOrder.rfq_id == rfq_id).first()
    if existing_po:
        return {
            "status": "already_approved",
            "message": f"PO already exists for {rfq_id}",
            "po_id": existing_po.id
        }

    po_id = f"PO-SMMG-{datetime.utcnow().strftime('%y%m')}-{uuid.uuid4().hex[:4].upper()}"
    subtotal = session.final_price
    rate_box = round(subtotal / rfq.quantity, 2)
    gst_pct = 18.0
    gst_val = round(subtotal * (gst_pct / 100.0), 2)
    total_val = round(subtotal + gst_val, 2)

    new_po = PurchaseOrder(
        id=po_id,
        rfq_id=rfq.id,
        supplier_id=supplier.id,
        supplier_name=supplier.name,
        item_description=f"{rfq.category} {rfq.size} ({rfq.quality_grade})",
        quantity=rfq.quantity,
        rate_per_box=rate_box,
        subtotal_amount=subtotal,
        gst_rate_pct=gst_pct,
        gst_amount=gst_val,
        total_amount=total_val,
        lead_days=supplier.standard_lead_days,
        breakage_allowance_pct=supplier.offered_breakage_pct,
        payment_status="PENDING",
        approval_status="APPROVED",
        approver_name="Ganesh G. Kumbhar (Lead) / Mr. Vikram Gurav (Owner)"
    )

    rfq.status = "Order Simulated"

    notif = Notification(
        rfq_id=rfq.id,
        title=f"Purchase Order Generated: {po_id}",
        message=f"Commercial sign-off completed for Shree Mahalaxmi Marbel and Granite. Total: ₹{total_val:,.0f} with {supplier.name}.",
        category="success"
    )

    db.add(new_po)
    db.add(notif)
    db.commit()

    return {
        "status": "success",
        "po_id": po_id,
        "total_amount": total_val,
        "supplier_name": supplier.name,
        "message": "Purchase Order approved and created successfully."
    }


@router.post("/pay/{po_id}")
def process_sandbox_payment(po_id: str, action: str = "success", db: Session = Depends(get_db)):
    """Simulates sandbox settlement."""
    po = db.query(PurchaseOrder).filter(PurchaseOrder.id == po_id).first()
    if not po:
        raise HTTPException(status_code=404, detail="Purchase Order not found")

    if action == "success":
        po.payment_status = "PAID"
        notif = Notification(
            rfq_id=po.rfq_id,
            title=f"Payment Settled: {po.id}",
            message=f"Sandbox payment of ₹{po.total_amount:,.0f} confirmed for Shree Mahalaxmi Marbel and Granite. Dispatched to Mudhal Titta depot.",
            category="success"
        )
    else:
        po.payment_status = "FAILED"
        notif = Notification(
            rfq_id=po.rfq_id,
            title=f"Payment Failed: {po.id}",
            message=f"Simulated transaction authorization declined. Retry available.",
            category="alert"
        )

    db.add(notif)
    db.commit()

    return {
        "po_id": po.id,
        "payment_status": po.payment_status,
        "timestamp": datetime.utcnow().isoformat()
    }