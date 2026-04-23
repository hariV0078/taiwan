import os

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters")

from app.models.listing import WasteListing
from app.models.transaction import BuyerProfile
from app.services import negotiator


class FakeGraph:
    def invoke(self, initial):
        return {
            **initial,
            "agreed": True,
            "agreed_price": 0.6,
            "round": 3,
            "history": [
                {"role": "seller", "price": 0.7, "reasoning": "Initial", "accepted": False, "round": 1},
                {"role": "buyer", "price": 0.55, "reasoning": "Counter", "accepted": False, "round": 2},
                {"role": "seller", "price": 0.6, "reasoning": "Final", "accepted": True, "round": 3},
            ],
            "failure_reason": "",
        }


def _listing():
    import uuid

    return WasteListing(
        seller_id=uuid.uuid4(),
        material_type="HDPE",
        material_category="Plastic/HDPE",
        quantity_kg=1000,
        purity_pct=90,
        location_city="Mumbai",
        location_country="IN",
        ask_price_per_kg=0.7,
    )


def _profile():
    import uuid

    return BuyerProfile(
        buyer_id=uuid.uuid4(),
        material_needs="HDPE",
        accepted_grades="A1,A2",
        accepted_countries="ALL",
        max_price_per_kg=1.0,
        min_quantity_kg=100,
        max_quantity_kg=5000,
    )


def test_agents_converge_within_five_rounds(monkeypatch):
    monkeypatch.setattr(negotiator, "_build_graph", lambda: FakeGraph())
    result = negotiator.run_negotiation(_listing(), _profile(), seller_floor=0.5, buyer_ceiling=0.7)
    assert result.success is True
    assert result.rounds_taken <= 5


def test_no_zopa_returns_failure():
    result = negotiator.run_negotiation(_listing(), _profile(), seller_floor=1.0, buyer_ceiling=0.7)
    assert result.success is False
    assert result.failure_reason == "no_zopa"


def test_agreed_price_midpoint_overlap(monkeypatch):
    class MidpointGraph:
        def invoke(self, initial):
            return {
                **initial,
                "agreed": True,
                "agreed_price": (0.65 + 0.75) / 2,
                "round": 2,
                "history": [
                    {"role": "seller", "price": 0.75, "reasoning": "Offer", "accepted": False, "round": 1},
                    {"role": "buyer", "price": 0.65, "reasoning": "Counter", "accepted": False, "round": 2},
                ],
                "failure_reason": "",
            }

    monkeypatch.setattr(negotiator, "_build_graph", lambda: MidpointGraph())
    result = negotiator.run_negotiation(_listing(), _profile(), seller_floor=0.6, buyer_ceiling=0.8)
    assert result.agreed_price == 0.7
