import uuid
from typing import Any

import chromadb
from openai import OpenAI
from pydantic import BaseModel
from sqlmodel import Session, select

from app.config import get_settings
from app.database import engine
from app.models.transaction import BuyerProfile
from app.models.user import User
from app.models.listing import WasteListing

settings = get_settings()
_openai_client: OpenAI | None = None


def _get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        _openai_client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _openai_client


class MatchResult(BaseModel):
    buyer_id: uuid.UUID
    buyer_name: str
    score: float
    match_reason: str
    max_price_per_kg: float


def _embed_text(text: str) -> list[float]:
    client = _get_openai_client()
    resp = client.embeddings.create(model="text-embedding-3-small", input=text)
    return resp.data[0].embedding


def init_chroma() -> chromadb.Collection:
    client = chromadb.PersistentClient(path=settings.CHROMA_PERSIST_PATH)
    return client.get_or_create_collection(name="buyer_profiles")


def upsert_buyer_profile(profile: BuyerProfile, buyer: User) -> None:
    collection = init_chroma()
    text = f"{profile.material_needs} {profile.accepted_grades} {profile.accepted_countries}"
    embedding = _embed_text(text)
    doc_id = profile.chroma_doc_id or str(profile.buyer_id)

    collection.upsert(
        ids=[doc_id],
        embeddings=[embedding],
        documents=[text],
        metadatas=[
            {
                "buyer_id": str(profile.buyer_id),
                "buyer_name": buyer.name,
                "max_price_per_kg": profile.max_price_per_kg,
                "min_quantity_kg": profile.min_quantity_kg,
                "max_quantity_kg": profile.max_quantity_kg,
                "accepted_grades": profile.accepted_grades,
                "accepted_countries": profile.accepted_countries,
            }
        ],
    )


def _accepted_country(metadata: dict[str, Any], listing_country: str) -> bool:
    accepted = str(metadata.get("accepted_countries", "ALL")).strip()
    if accepted.upper() == "ALL":
        return True
    countries = [c.strip().upper() for c in accepted.split(",") if c.strip()]
    return listing_country.upper() in countries


def match_buyers(listing: WasteListing, top_k: int = 3) -> list[MatchResult]:
    collection = init_chroma()
    grade_text = listing.grade.value if listing.grade else "unknown"
    query_text = (
        f"{listing.material_type} {listing.material_category} "
        f"grade {grade_text} from {listing.location_country}"
    )
    query_embedding = _embed_text(query_text)

    raw = collection.query(query_embeddings=[query_embedding], n_results=10)
    ids = raw.get("ids", [[]])[0]
    distances = raw.get("distances", [[]])[0]
    metadatas = raw.get("metadatas", [[]])[0]

    results: list[MatchResult] = []
    with Session(engine) as session:
        for idx, _ in enumerate(ids):
            md = metadatas[idx] if idx < len(metadatas) else {}
            distance = distances[idx] if idx < len(distances) else 2.0

            max_price = float(md.get("max_price_per_kg", 0.0))
            min_qty = float(md.get("min_quantity_kg", 0.0))
            max_qty = float(md.get("max_quantity_kg", float("inf")))

            if max_price < listing.ask_price_per_kg * 0.8:
                continue
            if not (min_qty <= listing.quantity_kg <= max_qty):
                continue
            if not _accepted_country(md, listing.location_country):
                continue

            buyer_id = uuid.UUID(str(md.get("buyer_id")))
            buyer = session.exec(select(User).where(User.id == buyer_id)).first()
            buyer_name = buyer.name if buyer else str(md.get("buyer_name", "Unknown Buyer"))
            score = max(0.0, min(1.0, 1 - (float(distance) / 2)))

            results.append(
                MatchResult(
                    buyer_id=buyer_id,
                    buyer_name=buyer_name,
                    score=score,
                    match_reason=(
                        f"Vector similarity + price/quantity/country fit for {listing.material_type}."
                    ),
                    max_price_per_kg=max_price,
                )
            )

    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]
