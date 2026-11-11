"""
Database Seeder
Populates initial tile/granite RFQs and authentic supplier agents 
for Shree Mahalaxmi Marbel and Granite, Mudhal Titta, Kolhapur.
"""

import hashlib
from app.database.session import SessionLocal, engine, Base
from app.database.models import RFQ, Supplier


def hash_password(password: str) -> str:
    """Generates SHA-256 hash for supplier authentication."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def seed_database():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # 1. Seed Initial RFQs if table is empty
        if db.query(RFQ).count() == 0:
            sample_rfqs = [
                RFQ(
                    id="RFQ-TILE-101",
                    category="PGVT Vitrified Floor Tiles",
                    size="600x1200 mm (2x4 ft)",
                    quantity=850,
                    budget_ceiling=467500.0,
                    delivery_deadline="2026-11-20",
                    quality_grade="Premium Grade",
                    max_breakage=2.0,
                    source_hub="Morbi Cluster to Mudhal Titta Depot",
                    status="Round 2 Counter-Offer",
                    weight_price=45.0,
                    weight_quality=25.0,
                    weight_delivery=20.0,
                    weight_warranty=10.0
                ),
                RFQ(
                    id="RFQ-TILE-102",
                    category="Ceramic Glazed Wall Tiles",
                    size="300x600 mm (Wall Tile)",
                    quantity=1200,
                    budget_ceiling=336000.0,
                    delivery_deadline="2026-11-15",
                    quality_grade="Standard / Commercial",
                    max_breakage=2.5,
                    source_hub="Kolhapur Regional Tiles & Granite Yard",
                    status="Ready for Approval",
                    weight_price=40.0,
                    weight_quality=20.0,
                    weight_delivery=25.0,
                    weight_warranty=15.0
                ),
                RFQ(
                    id="RFQ-TILE-103",
                    category="Polished Black Granite Slabs",
                    size="10x3 ft (Granite Slab)",
                    quantity=500,
                    budget_ceiling=225000.0,
                    delivery_deadline="2026-11-25",
                    quality_grade="Premium Grade",
                    max_breakage=1.5,
                    source_hub="Pune Industrial Supply Route",
                    status="Evaluating Quotes",
                    weight_price=50.0,
                    weight_quality=20.0,
                    weight_delivery=20.0,
                    weight_warranty=10.0
                )
            ]
            db.add_all(sample_rfqs)
            db.commit()
            print(" -> Seeded 3 initial procurement RFQs into SQLite database.")

        # 2. Seed Simulated Suppliers with Login Credentials if table is empty
        if db.query(Supplier).count() == 0:
            sample_suppliers = [
                Supplier(
                    id="SUP-MORBI-01",
                    username="morbi_ceramics",
                    password_hash=hash_password("morbi@123"),
                    name="Morbi Ceramics Hub Direct",
                    contact_number="+91 98250 12345",
                    hub_location="Morbi Industrial Area, Gujarat",
                    base_price_per_box=540.0,
                    min_walkaway_price=470.0,
                    standard_lead_days=14,
                    min_lead_days=9,
                    offered_breakage_pct=1.5,
                    quality_score=94.0,
                    reliability_score=92.0,
                    agent_strategy="balanced"
                ),
                Supplier(
                    id="SUP-KOLH-02",
                    username="kolhapur_tiles",
                    password_hash=hash_password("kolhapur@123"),
                    name="Kolhapur Regional Tiles & Granite Yard",
                    contact_number="+91 98900 54321",
                    hub_location="MIDC Shiroli, Kolhapur",
                    base_price_per_box=575.0,
                    min_walkaway_price=510.0,
                    standard_lead_days=4,
                    min_lead_days=2,
                    offered_breakage_pct=0.8,
                    quality_score=88.0,
                    reliability_score=96.0,
                    agent_strategy="cooperative"
                ),
                Supplier(
                    id="SUP-PUNE-03",
                    username="pune_vitrified",
                    password_hash=hash_password("pune@123"),
                    name="Maharashtra Bulk Vitrified Supply",
                    contact_number="+91 98220 98765",
                    hub_location="MIDC Chakan, Pune",
                    base_price_per_box=525.0,
                    min_walkaway_price=460.0,
                    standard_lead_days=8,
                    min_lead_days=5,
                    offered_breakage_pct=2.0,
                    quality_score=85.0,
                    reliability_score=84.0,
                    agent_strategy="aggressive"
                )
            ]
            db.add_all(sample_suppliers)
            db.commit()
            print(" -> Seeded 3 simulated supplier agents into SQLite database.")

    finally:
        db.close()