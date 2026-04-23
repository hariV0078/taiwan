"""Market Price Service.

Supports two formats:
1) New reference dataset at project root in file "price" (per_tonne rows)
2) Legacy nested storage/market_prices.json (per_kg)
"""

import json
import re
from pathlib import Path


NEW_MARKET_PRICES_FILE = Path(__file__).parent.parent.parent / "price"
LEGACY_MARKET_PRICES_FILE = Path(__file__).parent.parent.parent / "storage" / "market_prices.json"
_STOP_WORDS = {
    "grade",
    "scrap",
    "mixed",
    "clean",
    "used",
    "bulk",
    "waste",
    "post",
    "consumer",
    "industrial",
    "recycled",
}


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_market_prices() -> dict:
    """Load market prices preferring the new root-level dataset."""
    data = _read_json(NEW_MARKET_PRICES_FILE)
    if data:
        return data
    return _read_json(LEGACY_MARKET_PRICES_FILE)


def _normalize_tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", (text or "").lower())
    return {w for w in words if len(w) > 2 and w not in _STOP_WORDS}


def _build_keyword_aliases() -> dict[str, set[str]]:
    return {
        "aluminum": {"aluminum", "aluminium", "ubc"},
        "copper": {"copper", "wire"},
        "steel": {"steel", "hms", "stainless"},
        "plastic": {"plastic", "pet", "hdpe", "pp", "ldpe", "pvc"},
        "paper": {"paper", "cardboard", "occ", "newsprint"},
        "fiber": {"fiber", "paper", "cardboard", "occ"},
        "electronics": {"electronics", "pcb", "cpu", "ram", "ewaste", "battery"},
        "textile": {"textile", "cotton", "fibre", "fiber"},
        "chemical": {"chemical", "ipa", "toluene", "acetone", "methanol", "xylene", "mek"},
        "rubber": {"rubber", "tyre", "tire", "crumb", "tdf"},
        "wood": {"wood", "timber", "pallet"},
        "glass": {"glass"},
    }


def _score_market_item(material_category: str, item: dict, aliases: dict[str, set[str]]) -> int:
    category_tokens = _normalize_tokens(material_category)
    item_tokens = _normalize_tokens(item.get("material", ""))
    item_category_tokens = _normalize_tokens(item.get("category", ""))

    overlap = category_tokens & item_tokens
    overlap_category = category_tokens & item_category_tokens

    alias_hits = 0
    for root, words in aliases.items():
        if root in category_tokens or (category_tokens & words):
            if item_tokens & words or item_category_tokens & words:
                alias_hits += 1

    return (len(overlap) * 5) + (len(overlap_category) * 3) + (alias_hits * 4)


def _from_new_dataset(data: dict, material_category: str, grade: str) -> dict:
    market_data = data.get("market_data")
    if not isinstance(market_data, list):
        return {}

    aliases = _build_keyword_aliases()
    best_item = None
    best_score = 0

    for item in market_data:
        if not isinstance(item, dict):
            continue
        score = _score_market_item(material_category, item, aliases)
        if score > best_score:
            best_score = score
            best_item = item

    if not best_item or best_score <= 0:
        return {}

    unit = ((data.get("_metadata") or {}).get("unit") or "").lower()
    per_kg_divisor = 1000.0 if unit == "per_tonne" else 1.0

    low = float(best_item.get("low", 0)) / per_kg_divisor
    mid = float(best_item.get("mid", 0)) / per_kg_divisor
    high = float(best_item.get("high", 0)) / per_kg_divisor

    source_list = ((data.get("_metadata") or {}).get("sources") or [])
    source = ", ".join(source_list) if source_list else "Market reference dataset"

    return {
        "category": material_category.lower().strip(),
        "grade": grade.upper().strip(),
        "low_price_per_kg": low,
        "mid_price_per_kg": mid,
        "high_price_per_kg": high,
        "matched_material": best_item.get("material", ""),
        "source": source,
        "confidence": 0.9,
        "found": True,
    }


def _from_legacy_dataset(data: dict, material_category: str, grade: str) -> dict:
    category_lower = material_category.lower().strip()
    grade_upper = grade.upper().strip()

    if category_lower in data and grade_upper in data[category_lower]:
        price_data = data[category_lower][grade_upper]
        return {
            "category": category_lower,
            "grade": grade_upper,
            "low_price_per_kg": price_data.get("low", 0),
            "mid_price_per_kg": price_data.get("mid", 0),
            "high_price_per_kg": price_data.get("high", 0),
            "source": "Legacy market_prices.json",
            "confidence": 0.85,
            "found": True,
        }
    return {}


def get_market_price_range(material_category: str, grade: str = "A1") -> dict:
    """
    Get market reference price range for a material.
    
    Args:
        material_category: e.g., "aluminum", "copper", "plastic", "paper"
        grade: Material grade A1, A2, B1, B2, or C (defaults to A1)
    
    Returns:
        {
            "category": str,
            "grade": str,
            "low_price_per_kg": float,
            "mid_price_per_kg": float,
            "high_price_per_kg": float,
            "source": str,
            "confidence": float (0.0-1.0),
            "found": bool
        }
    """
    prices = load_market_prices()
    category_lower = material_category.lower().strip()
    grade_upper = grade.upper().strip()

    # New dataset path (root file "price")
    result = _from_new_dataset(prices, material_category, grade)
    if result:
        return result

    # Legacy dataset fallback
    result = _from_legacy_dataset(prices, material_category, grade)
    if result:
        return result

    return {
        "category": category_lower,
        "grade": grade_upper,
        "low_price_per_kg": 0,
        "mid_price_per_kg": 0,
        "high_price_per_kg": 0,
        "source": "No market data available",
        "confidence": 0,
        "found": False
    }


def validate_seller_floor_price(
    seller_floor: float,
    market_reference: dict,
    threshold_pct: float = 40
) -> dict:
    """
    Validate if seller's floor price is within reasonable bounds.
    
    Returns:
        {
            "is_valid": bool,
            "warning": str or None,
            "deviation_pct": float
        }
    """
    if not market_reference["found"]:
        return {"is_valid": True, "warning": None, "deviation_pct": 0}
    
    market_high = market_reference["high_price_per_kg"]
    threshold_price = market_high * (1 + threshold_pct / 100)
    
    if seller_floor > threshold_price:
        deviation_pct = ((seller_floor - market_high) / market_high) * 100
        return {
            "is_valid": True,  # Don't block, only warn
            "warning": f"Your floor price (${seller_floor:.2f}/kg) is {deviation_pct:.0f}% above market high (${market_high:.2f}/kg). Deal unlikely.",
            "deviation_pct": deviation_pct
        }
    
    return {"is_valid": True, "warning": None, "deviation_pct": 0}


def validate_buyer_ceiling_price(
    buyer_ceiling: float,
    market_reference: dict,
    threshold_pct: float = 40
) -> dict:
    """
    Validate if buyer's ceiling price is within reasonable bounds.
    
    Returns:
        {
            "is_valid": bool,
            "warning": str or None,
            "deviation_pct": float
        }
    """
    if not market_reference["found"]:
        return {"is_valid": True, "warning": None, "deviation_pct": 0}
    
    market_low = market_reference["low_price_per_kg"]
    threshold_price = market_low * (1 - threshold_pct / 100)
    
    if buyer_ceiling < threshold_price:
        deviation_pct = ((market_low - buyer_ceiling) / market_low) * 100
        return {
            "is_valid": True,  # Don't block, only warn
            "warning": f"Your ceiling price (${buyer_ceiling:.2f}/kg) is {deviation_pct:.0f}% below market low (${market_low:.2f}/kg). Deal unlikely.",
            "deviation_pct": deviation_pct
        }
    
    return {"is_valid": True, "warning": None, "deviation_pct": 0}
