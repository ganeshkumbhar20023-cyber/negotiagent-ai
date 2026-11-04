"""
Multi-Round Procurement Negotiation Engine
Domain: Tiles, Marbles & Granite Trading for Shree Mahalaxmi Marbel and Granite (Mudhal Titta, Kolhapur).
Supports offline deterministic rule-based scoring and optional Gemini Flash reasoning.
"""

import os
from typing import List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

GEMINI_AVAILABLE = False
client = None
gemini_api_key = os.getenv("GEMINI_API_KEY")

if gemini_api_key:
    try:
        from google import genai
        client = genai.Client(api_key=gemini_api_key)
        GEMINI_AVAILABLE = True
    except Exception as e:
        print(f"Notice: Google GenAI initialization skipped ({e}). Using deterministic rule engine.")


def calculate_composite_score(
    quote_per_box: float,
    budget_ceiling_per_box: float,
    quality_score: float,
    lead_days: int,
    max_acceptable_days: int,
    breakage_pct: float,
    max_breakage_limit: float,
    weights: Dict[str, float]
) -> float:
    """Computes a normalized multi-criteria utility score (0 to 100)."""
    if quote_per_box <= budget_ceiling_per_box:
        price_ratio = (budget_ceiling_per_box - quote_per_box) / budget_ceiling_per_box
        price_score = min(100.0, max(0.0, 50.0 + (price_ratio * 150.0)))
    else:
        price_score = max(0.0, 50.0 - ((quote_per_box - budget_ceiling_per_box) / budget_ceiling_per_box * 100.0))

    qual_score = min(100.0, max(0.0, quality_score))

    if max_acceptable_days > 0:
        delivery_score = min(100.0, max(0.0, (1.0 - (lead_days / (max_acceptable_days * 1.5))) * 100.0))
    else:
        delivery_score = 70.0

    if max_breakage_limit > 0:
        breakage_score = min(100.0, max(0.0, (1.0 - (breakage_pct / max_breakage_limit)) * 100.0))
    else:
        breakage_score = 80.0

    w_p = weights.get("price", 45.0) / 100.0
    w_q = weights.get("quality", 25.0) / 100.0
    w_d = weights.get("delivery", 20.0) / 100.0
    w_w = weights.get("warranty", 10.0) / 100.0

    composite = (price_score * w_p) + (qual_score * w_q) + (delivery_score * w_d) + (breakage_score * w_w)
    return round(composite, 2)


def generate_gemini_summary(rfq_data: Dict[str, Any], winner_data: Dict[str, Any], initial_cost: float, final_cost: float) -> str:
    """Synthesizes executive reasoning for Shree Mahalaxmi Marbel and Granite."""
    savings = initial_cost - final_cost
    savings_pct = (savings / initial_cost * 100) if initial_cost > 0 else 0

    prompt = (
        f"You are the autonomous procurement agent for Shree Mahalaxmi Marbel and Granite (Mudhal Titta, Kolhapur), a premier stone and tiles dealer.\n"
        f"Proprietor: Mr. Vikram Gurav.\n"
        f"Context: Negotiating bulk consignment of {rfq_data['quantity']} units of {rfq_data['category']} ({rfq_data['size']}).\n"
        f"Selected Supplier: {winner_data['name']} located at {winner_data['hub_location']}.\n"
        f"Initial Opening Cost: INR {initial_cost:,.0f}. Negotiated Final Cost: INR {final_cost:,.0f}.\n"
        f"Simulated Cost Savings: INR {savings:,.0f} ({savings_pct:.1f}% reduction).\n"
        f"Lead Time: {winner_data['lead_days']} days | Guaranteed Breakage: {winner_data['breakage_pct']}% | Quality Rating: {winner_data['quality_score']}/100.\n"
        f"Provide a concise 2-sentence executive justification explaining why this offer was accepted based on unit pricing, transport safety, and Mudhal Titta depot dispatch."
    )

    if GEMINI_AVAILABLE and client:
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt,
            )
            if response.text:
                return response.text.strip()
        except Exception as e:
            print(f"Gemini API call skipped fallback engaged: {e}")

    # Deterministic fallback
    return (
        f"Recommended {winner_data['name']} after 3 negotiation rounds for Shree Mahalaxmi Marbel and Granite, locking in ₹{final_cost:,.0f} "
        f"(saving ₹{savings:,.0f} or {savings_pct:.1f}% below opening quotes). "
        f"The supplier meets the {rfq_data['quality_grade']} standard with transit breakage capped at {winner_data['breakage_pct']}% "
        f"and direct transport dispatch within {winner_data['lead_days']} days to Mudhal Titta Depot."
    )


def run_negotiation_simulation(rfq: Any, suppliers: List[Any]) -> Dict[str, Any]:
    budget_per_box = rfq.budget_ceiling / rfq.quantity
    weights = {
        "price": rfq.weight_price,
        "quality": rfq.weight_quality,
        "delivery": rfq.weight_delivery,
        "warranty": rfq.weight_warranty
    }

    round_history = []
    supplier_states = {}

    for s in suppliers:
        supplier_states[s.id] = {
            "name": s.name,
            "hub_location": s.hub_location,
            "quality_score": s.quality_score,
            "reliability_score": s.reliability_score,
            "strategy": s.agent_strategy,
            "current_quote": s.base_price_per_box,
            "walkaway": s.min_walkaway_price,
            "current_lead": s.standard_lead_days,
            "min_lead": s.min_lead_days,
            "current_breakage": s.offered_breakage_pct
        }

    initial_total_cost = min([st["current_quote"] for st in supplier_states.values()]) * rfq.quantity

    # Round 1: Opening
    for s_id, st in supplier_states.items():
        score = calculate_composite_score(
            st["current_quote"], budget_per_box, st["quality_score"],
            st["current_lead"], 20, st["current_breakage"], rfq.max_breakage, weights
        )
        round_history.append({
            "round_number": 1,
            "supplier_id": s_id,
            "supplier_name": st["name"],
            "quote_per_box": st["current_quote"],
            "total_quote": round(st["current_quote"] * rfq.quantity, 2),
            "buyer_counter": round(budget_per_box * 0.92, 2),
            "lead_days": st["current_lead"],
            "breakage_pct": st["current_breakage"],
            "composite_score": score,
            "decision": "countered",
            "rationale": f"Initial opening quote submitted. Buyer agent countered with target ceiling rate of ₹{budget_per_box * 0.92:.0f}/unit."
        })

    # Round 2: Concession
    for s_id, st in supplier_states.items():
        if st["strategy"] == "aggressive":
            margin = st["current_quote"] - st["walkaway"]
            st["current_quote"] -= (margin * 0.25)
            st["current_lead"] = max(st["min_lead"], st["current_lead"] - 1)
        elif st["strategy"] == "cooperative":
            margin = st["current_quote"] - st["walkaway"]
            st["current_quote"] -= (margin * 0.60)
            st["current_breakage"] = max(0.5, st["current_breakage"] - 0.2)
            st["current_lead"] = max(st["min_lead"], st["current_lead"] - 2)
        else:
            margin = st["current_quote"] - st["walkaway"]
            st["current_quote"] -= (margin * 0.45)
            st["current_lead"] = max(st["min_lead"], st["current_lead"] - 1)

        st["current_quote"] = round(st["current_quote"], 2)

        score = calculate_composite_score(
            st["current_quote"], budget_per_box, st["quality_score"],
            st["current_lead"], 20, st["current_breakage"], rfq.max_breakage, weights
        )
        round_history.append({
            "round_number": 2,
            "supplier_id": s_id,
            "supplier_name": st["name"],
            "quote_per_box": st["current_quote"],
            "total_quote": round(st["current_quote"] * rfq.quantity, 2),
            "buyer_counter": round(budget_per_box * 0.96, 2),
            "lead_days": st["current_lead"],
            "breakage_pct": st["current_breakage"],
            "composite_score": score,
            "decision": "countered",
            "rationale": f"Round 2 concession offered under {st['strategy']} profile. Buyer agent pushed for final best terms."
        })

    # Round 3: BAFO
    best_supplier_id = None
    best_score = -1.0
    best_final_cost = 0.0

    for s_id, st in supplier_states.items():
        margin = st["current_quote"] - st["walkaway"]
        st["current_quote"] = round(st["current_quote"] - (margin * 0.60), 2)

        score = calculate_composite_score(
            st["current_quote"], budget_per_box, st["quality_score"],
            st["current_lead"], 20, st["current_breakage"], rfq.max_breakage, weights
        )

        decision = "evaluated"
        if score > best_score:
            best_score = score
            best_supplier_id = s_id
            best_final_cost = st["current_quote"] * rfq.quantity

        round_history.append({
            "round_number": 3,
            "supplier_id": s_id,
            "supplier_name": st["name"],
            "quote_per_box": st["current_quote"],
            "total_quote": round(st["current_quote"] * rfq.quantity, 2),
            "buyer_counter": None,
            "lead_days": st["current_lead"],
            "breakage_pct": st["current_breakage"],
            "composite_score": score,
            "decision": decision,
            "rationale": f"Best and final offer submitted. Composite utility score computed at {score} pts."
        })

    for r in round_history:
        if r["round_number"] == 3:
            if r["supplier_id"] == best_supplier_id:
                r["decision"] = "accepted"
                r["rationale"] = f"Top-ranked offer. Highest composite utility score ({best_score} pts)."
            else:
                r["decision"] = "rejected"
                r["rationale"] = "Outperformed on composite weighted scoring."

    winning_supplier = supplier_states[best_supplier_id]
    winning_data = {
        "id": best_supplier_id,
        "name": winning_supplier["name"],
        "hub_location": winning_supplier["hub_location"],
        "final_box_quote": winning_supplier["current_quote"],
        "final_total_cost": round(best_final_cost, 2),
        "lead_days": winning_supplier["current_lead"],
        "breakage_pct": winning_supplier["current_breakage"],
        "quality_score": winning_supplier["quality_score"],
        "composite_score": best_score
    }

    rfq_dict = {
        "id": rfq.id,
        "category": rfq.category,
        "size": rfq.size,
        "quantity": rfq.quantity,
        "quality_grade": rfq.quality_grade,
        "budget_ceiling": rfq.budget_ceiling
    }

    explanation = generate_gemini_summary(
        rfq_dict, winning_data, initial_total_cost, best_final_cost
    )

    savings_amount = max(0.0, initial_total_cost - best_final_cost)

    return {
        "rfq_id": rfq.id,
        "winning_supplier": winning_data,
        "initial_total_cost": round(initial_total_cost, 2),
        "final_total_cost": round(best_final_cost, 2),
        "savings_amount": round(savings_amount, 2),
        "explanation": explanation,
        "rounds": round_history
    }