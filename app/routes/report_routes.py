"""
API Endpoints for Analytical Reports & CSV Data Export
Domain: Shree Mahalaxmi Marbel and Granite (Mudhal Titta, Kolhapur)
"""

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from sqlalchemy.orm import Session
import csv
import io

from app.database.session import get_db
from app.database.models import RFQ, Supplier, NegotiationSession, PurchaseOrder

router = APIRouter(prefix="/api/reports", tags=["Reports & Analytics"])


@router.get("/summary")
def get_procurement_summary(db: Session = Depends(get_db)):
    """Computes executive KPIs across all RFQs, negotiation sessions, and POs."""
    rfqs = db.query(RFQ).all()
    sessions = db.query(NegotiationSession).all()
    orders = db.query(PurchaseOrder).all()
    suppliers = db.query(Supplier).all()

    total_rfqs = len(rfqs)
    total_savings = sum(s.savings_amount for s in sessions if s.savings_amount)
    total_orders = len(orders)
    paid_orders = len([po for po in orders if po.payment_status == "PAID"])
    total_spent = sum(po.total_amount for po in orders if po.payment_status == "PAID")

    supplier_wins = {s.name: 0 for s in suppliers}
    for sess in sessions:
        if sess.recommended_supplier_id:
            sup = next((s for s in suppliers if s.id == sess.recommended_supplier_id), None)
            if sup:
                supplier_wins[sup.name] = supplier_wins.get(sup.name, 0) + 1

    avg_savings_pct = 0.0
    if sessions:
        total_initial = sum((s.final_price + s.savings_amount) for s in sessions if s.final_price)
        if total_initial > 0:
            avg_savings_pct = round((total_savings / total_initial) * 100, 1)

    return {
        "sponsor": "Shree Mahalaxmi Marbel and Granite",
        "total_rfqs": total_rfqs,
        "total_savings": round(total_savings, 2),
        "total_orders": total_orders,
        "paid_orders": paid_orders,
        "total_spent": round(total_spent, 2),
        "avg_savings_pct": avg_savings_pct,
        "supplier_win_distribution": supplier_wins
    }


@router.get("/export/csv")
def export_procurement_csv(db: Session = Depends(get_db)):
    """Generates an RFC 4180 compliant CSV export of all procurement sessions."""
    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "RFQ ID",
        "Material Category",
        "Dimension/Size",
        "Quantity",
        "Budget Ceiling (INR)",
        "Final Price (INR)",
        "Cost Savings (INR)",
        "Recommended Supplier",
        "Delivery Deadline",
        "Status"
    ])

    rfqs = db.query(RFQ).all()
    for r in rfqs:
        sess = (
            db.query(NegotiationSession)
            .filter(NegotiationSession.rfq_id == r.id)
            .order_by(NegotiationSession.created_at.desc())
            .first()
        )

        final_price = sess.final_price if sess else 0.0
        savings = sess.savings_amount if sess else 0.0
        winner = sess.recommended_supplier_id if sess else "N/A"

        writer.writerow([
            r.id,
            r.category,
            r.size,
            r.quantity,
            r.budget_ceiling,
            final_price,
            savings,
            winner,
            r.delivery_deadline,
            r.status
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=mahalaxmi_procurement_audit.csv"}
    )