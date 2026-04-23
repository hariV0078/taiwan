"""
ZOPA (Zone of Possible Agreement) Service
Calculates whether buyer and seller can reach a deal and proposes fair price.

This replaces the autonomous negotiator. It's pure calculation, no state machine.
"""

from typing import Optional


def calculate_zopa(
    seller_floor_price: float,
    buyer_ceiling_price: float,
    market_low: float = 0,
    market_high: float = 0
) -> dict:
    """
    Calculate Zone of Possible Agreement between seller and buyer.
    
    The ZOPA is the range where both parties can agree. If it's empty, no deal is possible.
    
    Algorithm:
    1. ZOPA = intersection of [seller_floor, ∞) and (-∞, buyer_ceiling]
    2. If market data exists, constrain ZOPA to [market_low, market_high]
    3. If ZOPA is non-empty, propose midpoint
    4. If ZOPA is empty, return failure
    
    Args:
        seller_floor_price: Seller's minimum acceptable price ($/kg)
        buyer_ceiling_price: Buyer's maximum acceptable price ($/kg)
        market_low: Market reference low price (optional, $/kg)
        market_high: Market reference high price (optional, $/kg)
    
    Returns:
        {
            "has_zopa": bool,
            "zopa_low": float | None,
            "zopa_high": float | None,
            "proposed_price": float | None,
            "reasoning": str,
            "seller_floor": float,
            "buyer_ceiling": float,
            "market_low": float,
            "market_high": float
        }
    """
    
    # Basic check: overlapping price ranges
    if seller_floor_price > buyer_ceiling_price:
        return {
            "has_zopa": False,
            "zopa_low": None,
            "zopa_high": None,
            "proposed_price": None,
            "reasoning": f"No ZOPA: seller floor (${seller_floor_price:.2f}/kg) > buyer ceiling (${buyer_ceiling_price:.2f}/kg)",
            "seller_floor": seller_floor_price,
            "buyer_ceiling": buyer_ceiling_price,
            "market_low": market_low,
            "market_high": market_high
        }
    
    # Initial ZOPA: [seller_floor, buyer_ceiling]
    zopa_low = seller_floor_price
    zopa_high = buyer_ceiling_price
    
    # Constrain to market range if provided
    if market_low > 0 and market_high > 0:
        zopa_low = max(zopa_low, market_low)
        zopa_high = min(zopa_high, market_high)
        
        # Check if market constraint created empty ZOPA
        if zopa_low > zopa_high:
            return {
                "has_zopa": False,
                "zopa_low": None,
                "zopa_high": None,
                "proposed_price": None,
                "reasoning": f"No ZOPA after market constraint: seller floor ${seller_floor_price:.2f}, buyer ceiling ${buyer_ceiling_price:.2f}, market range ${market_low:.2f}-${market_high:.2f}",
                "seller_floor": seller_floor_price,
                "buyer_ceiling": buyer_ceiling_price,
                "market_low": market_low,
                "market_high": market_high
            }
    
    # Calculate proposed price as midpoint of ZOPA
    proposed_price = (zopa_low + zopa_high) / 2
    
    return {
        "has_zopa": True,
        "zopa_low": zopa_low,
        "zopa_high": zopa_high,
        "proposed_price": proposed_price,
        "reasoning": f"ZOPA found: ${zopa_low:.2f} - ${zopa_high:.2f}/kg. Proposing midpoint: ${proposed_price:.2f}/kg",
        "seller_floor": seller_floor_price,
        "buyer_ceiling": buyer_ceiling_price,
        "market_low": market_low,
        "market_high": market_high
    }


def check_counter_offer_zopa(
    seller_floor: float,
    seller_counter: Optional[float],
    buyer_ceiling: float,
    buyer_counter: Optional[float]
) -> dict:
    """
    Check if counter-offers from one or both parties still have ZOPA.
    
    Returns:
        {
            "has_zopa": bool,
            "can_proceed_to_agreed": bool,
            "reasoning": str,
            "effective_low": float,
            "effective_high": float
        }
    """
    
    # Determine effective boundaries after counter-offers
    effective_low = seller_counter if seller_counter is not None else seller_floor
    effective_high = buyer_counter if buyer_counter is not None else buyer_ceiling
    
    if effective_low > effective_high:
        return {
            "has_zopa": False,
            "can_proceed_to_agreed": False,
            "reasoning": f"No ZOPA after counter-offers: seller effective ${effective_low:.2f} > buyer effective ${effective_high:.2f}",
            "effective_low": effective_low,
            "effective_high": effective_high
        }
    
    return {
        "has_zopa": True,
        "can_proceed_to_agreed": True,
        "reasoning": f"ZOPA exists: ${effective_low:.2f} - ${effective_high:.2f}/kg",
        "effective_low": effective_low,
        "effective_high": effective_high
    }
