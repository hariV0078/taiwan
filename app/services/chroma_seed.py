import uuid

from app.services.matcher import init_chroma, _embed_text


def _seed_rows() -> list[dict]:
    return [
        {"name": "IndoPoly Recyclers", "needs": "HDPE post-industrial and post-consumer bales", "grades": "A1,A2,B1", "countries": "IN,BD,PK", "max_price": 0.62, "min_qty": 5000, "max_qty": 120000},
        {"name": "Rhein Circular Polymers", "needs": "HDPE washed flakes and pellets", "grades": "A1,A2", "countries": "DE,NL,BE,PL", "max_price": 0.95, "min_qty": 3000, "max_qty": 60000},
        {"name": "Shenzhen Steel Renew", "needs": "HMS steel scrap and turnings", "grades": "A2,B1,B2", "countries": "CN,KR,JP", "max_price": 0.41, "min_qty": 10000, "max_qty": 300000},
        {"name": "Anatolia Metals", "needs": "Ferrous steel scrap for EAF feedstock", "grades": "A2,B1", "countries": "TR,GE,BG", "max_price": 0.39, "min_qty": 8000, "max_qty": 250000},
        {"name": "Gulf Foundry Inputs", "needs": "Steel scrap bundles and plate offcuts", "grades": "A1,A2,B1", "countries": "AE,SA,OM", "max_price": 0.44, "min_qty": 12000, "max_qty": 280000},
        {"name": "Bayern Aluminium Loop", "needs": "Aluminium extrusion scrap and clean sheet offcuts", "grades": "A1,A2,B1", "countries": "DE,AT,CZ", "max_price": 1.85, "min_qty": 3000, "max_qty": 90000},
        {"name": "Kansai Alloy Recovery", "needs": "Aluminium UBC and casting scrap", "grades": "A1,A2,B1,B2", "countries": "JP,KR,TW", "max_price": 2.05, "min_qty": 2500, "max_qty": 85000},
        {"name": "Seoul Copper Circuits", "needs": "Copper wire granules and stripped copper cable", "grades": "A1,A2,B1", "countries": "KR,JP,CN,TW", "max_price": 5.25, "min_qty": 1500, "max_qty": 70000},
        {"name": "Taipei Conductive Metals", "needs": "Recovered copper wire and busbar cuttings", "grades": "A1,A2", "countries": "TW,JP,KR", "max_price": 5.55, "min_qty": 1200, "max_qty": 65000},
        {"name": "Rotterdam Fiber Cycle", "needs": "OCC cardboard and mixed paper bales", "grades": "A2,B1,B2", "countries": "NL,BE,DE,FR", "max_price": 0.22, "min_qty": 7000, "max_qty": 140000},
        {"name": "Sao Paulo Board Reclaim", "needs": "Cardboard and paper pulp feedstock", "grades": "A2,B1", "countries": "BR,AR,UY", "max_price": 0.19, "min_qty": 6000, "max_qty": 110000},
        {"name": "Milano Glass Loop", "needs": "Glass cullet sorted by color", "grades": "A1,A2,B1", "countries": "IT,ES,FR", "max_price": 0.12, "min_qty": 9000, "max_qty": 150000},
        {"name": "Lyon Verrerie ReUse", "needs": "Flint and amber glass cullet", "grades": "A1,A2,B1,B2", "countries": "FR,BE,DE,IT", "max_price": 0.11, "min_qty": 8000, "max_qty": 130000},
        {"name": "SG Circular Electronics", "needs": "Shredded e-waste boards and high-metal fraction", "grades": "A1,A2,B1", "countries": "SG,MY,TH,ID", "max_price": 3.15, "min_qty": 1000, "max_qty": 30000},
        {"name": "Bangkok Rubber ReForm", "needs": "Rubber crumb and tire-derived rubber scrap", "grades": "A2,B1,B2", "countries": "TH,MY,VN", "max_price": 0.34, "min_qty": 4000, "max_qty": 100000},
    ]


def seed_buyers() -> None:
    collection = init_chroma()
    existing = collection.count()
    if existing > 0:
        return

    rows = _seed_rows()
    ids = []
    embeddings = []
    docs = []
    metas = []

    for row in rows:
        buyer_id = uuid.uuid4()
        text = f"{row['needs']} {row['grades']} {row['countries']}"
        ids.append(str(uuid.uuid4()))
        embeddings.append(_embed_text(text))
        docs.append(text)
        metas.append(
            {
                "buyer_id": str(buyer_id),
                "buyer_name": row["name"],
                "max_price_per_kg": row["max_price"],
                "min_quantity_kg": row["min_qty"],
                "max_quantity_kg": row["max_qty"],
                "accepted_grades": row["grades"],
                "accepted_countries": row["countries"],
            }
        )

    collection.upsert(ids=ids, embeddings=embeddings, documents=docs, metadatas=metas)


def clear_and_reseed() -> None:
    client = init_chroma()._client
    try:
        client.delete_collection(name="buyer_profiles")
    except Exception:
        pass
    collection = client.get_or_create_collection(name="buyer_profiles")
    if collection.count() == 0:
        seed_buyers()
