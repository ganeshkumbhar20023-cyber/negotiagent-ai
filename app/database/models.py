"""
SQLAlchemy Database Models
Schema for RFQs, Suppliers, Negotiation Rounds, Purchase Orders, and Notifications.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database.session import Base

class RFQ(Base):
    __tablename__ = "rfqs"

    id = Column(String(50), primary_key=True, index=True)
    category = Column(String(100), nullable=False)
    size = Column(String(50), nullable=False)
    quantity = Column(Integer, nullable=False)
    budget_ceiling = Column(Float, nullable=False)
    delivery_deadline = Column(String(50), nullable=False)
    quality_grade = Column(String(50), nullable=False)
    max_breakage = Column(Float, nullable=False)
    source_hub = Column(String(100), default="Regional Supply to Mudhal Titta Depot")
    status = Column(String(50), default="Evaluating Quotes")
    
    # Priority weights
    weight_price = Column(Float, default=45.0)
    weight_quality = Column(Float, default=25.0)
    weight_delivery = Column(Float, default=20.0)
    weight_warranty = Column(Float, default=10.0)
    
    created_at = Column(DateTime, default=datetime.utcnow)

    sessions = relationship("NegotiationSession", back_populates="rfq", cascade="all, delete-orphan")
    purchase_orders = relationship("PurchaseOrder", back_populates="rfq", cascade="all, delete-orphan")


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(String(50), primary_key=True, index=True)
    name = Column(String(150), nullable=False)
    contact_number = Column(String(50), nullable=True)  # <-- ADD HERE
    hub_location = Column(String(150), nullable=False)
    base_price_per_box = Column(Float, nullable=False)
    min_walkaway_price = Column(Float, nullable=False)
    standard_lead_days = Column(Integer, nullable=False)
    min_lead_days = Column(Integer, nullable=False)
    offered_breakage_pct = Column(Float, nullable=False)
    quality_score = Column(Float, nullable=False)
    reliability_score = Column(Float, nullable=False)
    agent_strategy = Column(String(50), default="balanced")


class NegotiationSession(Base):
    __tablename__ = "negotiation_sessions"

    id = Column(String(50), primary_key=True, index=True)
    rfq_id = Column(String(50), ForeignKey("rfqs.id"), nullable=False)
    status = Column(String(50), default="in_progress")
    recommended_supplier_id = Column(String(50), nullable=True)
    final_price = Column(Float, nullable=True)
    savings_amount = Column(Float, default=0.0)
    explanation_summary = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    rfq = relationship("RFQ", back_populates="sessions")
    rounds = relationship("NegotiationRound", back_populates="session", cascade="all, delete-orphan")


class NegotiationRound(Base):
    __tablename__ = "negotiation_rounds"

    id = Column(Integer, primary_key=True, autoincrement=True)
    session_id = Column(String(50), ForeignKey("negotiation_sessions.id"), nullable=False)
    round_number = Column(Integer, nullable=False)
    supplier_id = Column(String(50), nullable=False)
    supplier_quote = Column(Float, nullable=False)
    buyer_counter = Column(Float, nullable=True)
    lead_days_offered = Column(Integer, nullable=False)
    breakage_offered = Column(Float, nullable=False)
    composite_score = Column(Float, nullable=False)
    decision = Column(String(50), nullable=False)
    rationale = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow)

    session = relationship("NegotiationSession", back_populates="rounds")


class PurchaseOrder(Base):
    __tablename__ = "purchase_orders"

    id = Column(String(50), primary_key=True, index=True)
    rfq_id = Column(String(50), ForeignKey("rfqs.id"), nullable=False)
    supplier_id = Column(String(50), nullable=False)
    supplier_name = Column(String(150), nullable=False)
    item_description = Column(String(200), nullable=False)
    quantity = Column(Integer, nullable=False)
    rate_per_box = Column(Float, nullable=False)
    subtotal_amount = Column(Float, nullable=False)
    gst_rate_pct = Column(Float, default=18.0)
    gst_amount = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    lead_days = Column(Integer, nullable=False)
    breakage_allowance_pct = Column(Float, nullable=False)
    payment_status = Column(String(50), default="PENDING")
    approval_status = Column(String(50), default="APPROVED")
    approver_name = Column(String(100), default="Ganesh G. Kumbhar (DYPCET)")
    created_at = Column(DateTime, default=datetime.utcnow)

    rfq = relationship("RFQ", back_populates="purchase_orders")


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    rfq_id = Column(String(50), nullable=True)
    title = Column(String(150), nullable=False)
    message = Column(Text, nullable=False)
    category = Column(String(50), default="info")
    is_read = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)