import os
import uuid

os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
os.environ.setdefault("SECRET_KEY", "test-secret-key-min-32-characters")

from app.models.listing import MaterialGrade, WasteListing
from app.services import matcher


class FakeCollection:
    def query(self, query_embeddings, n_results):
        return {
            "ids": [["d1", "d2", "d3", "d4"]],
            "distances": [[0.1, 0.3, 0.5, 0.8]],
            "metadatas": [[
                {
                    "buyer_id": str(uuid.uuid4()),
                    "buyer_name": "Top Buyer",
                    "max_price_per_kg": 1.0,
                    "min_quantity_kg": 100,
                    "max_quantity_kg": 5000,
                    "accepted_countries": "IN,DE",
                },
                {
                    "buyer_id": str(uuid.uuid4()),
                    "buyer_name": "Price Low",
                    "max_price_per_kg": 0.2,
                    "min_quantity_kg": 100,
                    "max_quantity_kg": 5000,
                    "accepted_countries": "IN",
                },
                {
                    "buyer_id": str(uuid.uuid4()),
                    "buyer_name": "Qty Mismatch",
                    "max_price_per_kg": 1.1,
                    "min_quantity_kg": 6000,
                    "max_quantity_kg": 7000,
                    "accepted_countries": "IN",
                },
                {
                    "buyer_id": str(uuid.uuid4()),
                    "buyer_name": "Second Best",
                    "max_price_per_kg": 1.2,
                    "min_quantity_kg": 100,
                    "max_quantity_kg": 5000,
                    "accepted_countries": "ALL",
                },
            ]],
        }


class FakeExecResult:
    def first(self):
        return None


class FakeSession:
    def __init__(self, _engine):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def exec(self, _query):
        return FakeExecResult()


def _listing():
    return WasteListing(
        seller_id=uuid.uuid4(),
        material_type="HDPE",
        material_category="Plastic/HDPE",
        grade=MaterialGrade.A1,
        quantity_kg=1000,
        purity_pct=90,
        location_city="Mumbai",
        location_country="IN",
        ask_price_per_kg=0.5,
    )


def test_match_returns_top_sorted(monkeypatch):
    monkeypatch.setattr(matcher, "init_chroma", lambda: FakeCollection())
    monkeypatch.setattr(matcher, "_embed_text", lambda _x: [0.1, 0.2])
    monkeypatch.setattr(matcher, "Session", FakeSession)

    out = matcher.match_buyers(_listing(), top_k=3)
    assert len(out) == 2
    assert out[0].score >= out[1].score


def test_buyer_below_price_filtered(monkeypatch):
    monkeypatch.setattr(matcher, "init_chroma", lambda: FakeCollection())
    monkeypatch.setattr(matcher, "_embed_text", lambda _x: [0.1, 0.2])
    monkeypatch.setattr(matcher, "Session", FakeSession)

    out = matcher.match_buyers(_listing(), top_k=3)
    names = [x.buyer_name for x in out]
    assert "Price Low" not in names


def test_quantity_mismatch_filtered(monkeypatch):
    monkeypatch.setattr(matcher, "init_chroma", lambda: FakeCollection())
    monkeypatch.setattr(matcher, "_embed_text", lambda _x: [0.1, 0.2])
    monkeypatch.setattr(matcher, "Session", FakeSession)

    out = matcher.match_buyers(_listing(), top_k=3)
    names = [x.buyer_name for x in out]
    assert "Qty Mismatch" not in names
