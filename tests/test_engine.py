"""
Unit Tests for Multi-Round Negotiation Engine & Utility Scoring
"""

import pytest
from app.services.negotiation_engine import calculate_composite_score, run_negotiation_simulation
from app.database.models import RFQ, Supplier


def test_composite_score_formula():
    """Verify multi-criteria weighted scoring generates valid 0-100 values."""
    weights = {"price": 45.0, "quality": 25.0, "delivery": 20.0, "warranty": 10.0}
    
    score = calculate_composite_score(
        quote_per_box=500.0,
        budget_ceiling_per_box=550.0,
        quality_score=90.0,
        lead_days=7,
        max_acceptable_days=20,
        breakage_pct=1.0,
        max_breakage_limit=2.0,
        weights=weights
    )

    assert isinstance(score, float)
    assert 0.0 <= score <= 100.0
    assert score > 60.0  # Favorable quote under budget ceiling should score high


def test_score_penalizes_over_budget():
    """Quotes exceeding the buyer's budget ceiling must receive lower scores."""
    weights = {"price": 50.0, "quality": 20.0, "delivery": 20.0, "warranty": 10.0}

    under_budget_score = calculate_composite_score(
        quote_per_box=480.0, budget_ceiling_per_box=500.0, quality_score=85.0,
        lead_days=5, max_acceptable_days=15, breakage_pct=1.0, max_breakage_limit=2.0,
        weights=weights
    )

    over_budget_score = calculate_composite_score(
        quote_per_box=580.0, budget_ceiling_per_box=500.0, quality_score=85.0,
        lead_days=5, max_acceptable_days=15, breakage_pct=1.0, max_breakage_limit=2.0,
        weights=weights
    )

    assert under_budget_score > over_budget_score


def test_negotiation_simulation_execution():
    """Verify that a 3-round negotiation finishes with savings and a winning supplier."""
    rfq = RFQ(
        id="RFQ-MOCK-1",
        category="Polished Black Granite Slabs",
        size="10x3 ft",
        quantity=300,
        budget_ceiling=180000.0,
        quality_grade="Premium Grade",
        max_breakage=2.0,
        weight_price=45.0,
        weight_quality=25.0,
        weight_delivery=20.0,
        weight_warranty=10.0
    )

    suppliers = [
        Supplier(
            id="SUP-A",
            name="Supplier Alpha",
            hub_location="Kolhapur",
            base_price_per_box=580.0,
            min_walkaway_price=500.0,
            standard_lead_days=5,
            min_lead_days=3,
            offered_breakage_pct=1.0,
            quality_score=90.0,
            reliability_score=90.0,
            agent_strategy="balanced"
        ),
        Supplier(
            id="SUP-B",
            name="Supplier Beta",
            hub_location="Morbi",
            base_price_per_box=560.0,
            min_walkaway_price=460.0,
            standard_lead_days=12,
            min_lead_days=8,
            offered_breakage_pct=1.8,
            quality_score=92.0,
            reliability_score=88.0,
            agent_strategy="cooperative"
        )
    ]

    result = run_negotiation_simulation(rfq, suppliers)

    assert result["rfq_id"] == "RFQ-MOCK-1"
    assert "winning_supplier" in result
    assert result["winning_supplier"]["id"] in ["SUP-A", "SUP-B"]
    assert result["final_total_cost"] <= result["initial_total_cost"]
    assert result["savings_amount"] >= 0.0
    assert len(result["rounds"]) == 6  # 3 rounds * 2 suppliers = 6 transcripts
    assert result["explanation"] is not None