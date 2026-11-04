"""
Pytest Fixtures & Test Setup
Provides an isolated in-memory SQLite database and FastAPI TestClient.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.session import Base, get_db
from app.database.models import RFQ, Supplier
from app.main import app

# In-memory SQLite database for isolated fast testing
SQLALCHEMY_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """Creates a fresh database schema for each test and seeds baseline data."""
    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()

    # Seed baseline suppliers for tests
    suppliers = [
        Supplier(
            id="SUP-TEST-MORBI",
            name="Morbi Ceramics Hub Direct",
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
            id="SUP-TEST-KOLH",
            name="Kolhapur Regional Tiles & Granite Yard",
            hub_location="MIDC Shiroli, Kolhapur",
            base_price_per_box=575.0,
            min_walkaway_price=510.0,
            standard_lead_days=4,
            min_lead_days=2,
            offered_breakage_pct=0.8,
            quality_score=88.0,
            reliability_score=96.0,
            agent_strategy="cooperative"
        )
    ]
    db.add_all(suppliers)

    # Seed baseline RFQ
    rfq = RFQ(
        id="RFQ-TEST-001",
        category="PGVT Vitrified Floor Tiles",
        size="600x1200 mm (2x4 ft)",
        quantity=500,
        budget_ceiling=275000.0,
        delivery_deadline="2026-11-30",
        quality_grade="Premium Grade",
        max_breakage=2.0,
        source_hub="Regional Supply to Mudhal Titta Depot",
        status="Evaluating Quotes",
        weight_price=45.0,
        weight_quality=25.0,
        weight_delivery=20.0,
        weight_warranty=10.0
    )
    db.add(rfq)
    db.commit()

    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="function")
def client(db_session):
    """FastAPI TestClient wired to the in-memory test database session."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()