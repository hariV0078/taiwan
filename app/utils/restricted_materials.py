from __future__ import annotations

from typing import Optional

from BANNED_ITEMS import CIRCULARX_NO_TRADE_LIST

RESTRICTED_MATERIALS = [
    "radioactive waste",
    "pcb",
    "polychlorinated biphenyl",
    "asbestos",
    "mercury",
    "lead-acid battery",
    "chemical weapons",
    "biological waste",
    "nuclear",
    "unexploded ordnance",
]


def _candidate_terms() -> list[str]:
    terms: list[str] = []
    for entry in CIRCULARX_NO_TRADE_LIST:
        item = (entry.get("item") or "").strip().lower()
        cas = (entry.get("cas") or "").strip().lower()

        if item:
            terms.append(item)
        if cas and cas not in {"n/a", "unknown", "multiple"}:
            terms.append(cas)

        for token in item.replace("/", " ").replace("(", " ").replace(")", " ").replace(",", " ").split():
            token = token.strip().lower()
            if len(token) >= 4 and token not in terms:
                terms.append(token)

    for material in RESTRICTED_MATERIALS:
        normalized = material.lower()
        if normalized not in terms:
            terms.append(normalized)

    return terms


RESTRICTED_TERMS = _candidate_terms()


def check_restricted(description: str) -> tuple[bool, Optional[str]]:
    text = (description or "").lower()
    for material in RESTRICTED_TERMS:
        if material in text:
            return True, f"Restricted material detected: {material}"
    return False, None
