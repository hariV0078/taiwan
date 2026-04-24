"""
Deal Intelligence Agent - Autonomous monitoring and intervention for transactions.

Features:
- Trust score calculation based on transaction history
- Stalled deal detection and proactive notifications
- LLM-based deal analysis and recommendations
- Automatic intervention triggers for at-risk deals
"""

import json
import logging
from datetime import datetime, timedelta
from typing import Optional

from sqlmodel import Session, select

from app.database import engine
from app.models.listing import WasteListing
from app.models.notification import Notification, NotificationType
from app.models.transaction import Transaction, TransactionStatus
from app.models.user import User
from app.config import get_settings

try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

logger = logging.getLogger(__name__)
settings = get_settings()


class TrustScore:
    """
    Calculates reputation/trust score for users based on transaction history.
    Scores degrade based on:
    - Transaction completion rates
    - Negotiation responsiveness (time to respond)
    - Deal success vs. disputes
    - Stalled deals
    """

    @staticmethod
    def calculate_user_trust_score(user_id: str, session: Session) -> float:
        """
        Calculate trust score for a user (0.0 to 1.0).
        
        Factors:
        - Completion rate: 40% weight
        - Responsiveness: 30% weight
        - Dispute rate: 30% weight
        """
        from uuid import UUID
        
        user_uuid = UUID(user_id) if isinstance(user_id, str) else user_id
        
        # Get all transactions involving this user (as buyer or seller)
        transactions = (
            session.exec(
                select(Transaction).where(
                    (Transaction.seller_id == user_uuid) | (Transaction.buyer_id == user_uuid)
                )
            )
            .unique()
            .all()
        )

        if not transactions:
            return 1.0  # New users start with perfect score

        total_deals = len(transactions)
        completed_deals = sum(1 for t in transactions if t.status == TransactionStatus.released)
        disputed_deals = sum(1 for t in transactions if t.status == TransactionStatus.disputed)
        failed_deals = sum(1 for t in transactions if t.status == TransactionStatus.failed)

        # Completion rate (40%)
        completion_rate = completed_deals / total_deals if total_deals > 0 else 0.0

        # Responsiveness (30%) - measured by negotiation rounds per deal
        total_rounds = sum(t.negotiation_rounds for t in transactions)
        avg_rounds_per_deal = total_rounds / total_deals if total_deals > 0 else 0
        # Penalize slow responders (5+ rounds per deal is bad)
        responsiveness_score = max(0.0, 1.0 - (avg_rounds_per_deal / 10.0))

        # Dispute/failure rate (30%)
        dispute_rate = (disputed_deals + failed_deals) / total_deals if total_deals > 0 else 0.0
        integrity_score = 1.0 - dispute_rate

        # Weighted average
        trust_score = (
            completion_rate * 0.4 +
            responsiveness_score * 0.3 +
            integrity_score * 0.3
        )

        return max(0.0, min(1.0, trust_score))

    @staticmethod
    def bulk_update_trust_scores(session: Session) -> dict:
        """Calculate and store trust scores for all active users."""
        users = session.exec(select(User)).all()
        scores = {}
        for user in users:
            score = TrustScore.calculate_user_trust_score(str(user.id), session)
            scores[str(user.id)] = score
        return scores


class DealAnalysis:
    """LLM-based analysis of transaction state and recommendations."""

    @staticmethod
    def analyze_stalled_deal(transaction: Transaction, listing: WasteListing, seller: User, buyer: User, session: Session) -> dict:
        """
        Analyze a stalled transaction and generate recommendations.
        Returns: {
            "risk_level": "high|medium|low",
            "reason": "...",
            "recommendation": "...",
            "suggested_action": "..."
        }
        """
        if not OpenAI:
            return {
                "risk_level": "medium",
                "reason": "OpenAI client not available",
                "recommendation": "Check deal manually",
                "suggested_action": "notify_both_parties"
            }

        try:
            client = OpenAI(api_key=settings.OPENAI_API_KEY)

            # Gather context
            deal_context = {
                "material": listing.material_type,
                "quantity_kg": listing.quantity_kg,
                "asking_price": listing.ask_price_per_kg,
                "proposed_price": transaction.initial_proposed_price,
                "seller_company": seller.company,
                "buyer_company": buyer.company,
                "negotiation_rounds": transaction.negotiation_rounds,
                "status": transaction.status.value,
                "time_stalled_minutes": int(
                    (datetime.utcnow() - (transaction.buyer_confirmed_interest_at or transaction.matched_at)).total_seconds() / 60
                )
            }

            prompt = f"""
You are a deal analyst for a waste materials marketplace. Analyze this stalled transaction:

Deal Details:
- Material: {deal_context['material']}
- Quantity: {deal_context['quantity_kg']} kg
- Seller: {deal_context['seller_company']}
- Buyer: {deal_context['buyer_company']}
- Asking price: ${deal_context['asking_price']}/kg
- Proposed price: ${deal_context['proposed_price']}/kg
- Negotiation rounds: {deal_context['negotiation_rounds']}
- Status: {deal_context['status']}
- Stalled for: {deal_context['time_stalled_minutes']} minutes

Provide a brief analysis (2-3 sentences):
1. Risk level (high/medium/low)
2. Why it stalled
3. Specific recommendation (price move, deadline, incentive, etc.)

Format your response as JSON:
{{
    "risk_level": "high|medium|low",
    "reason": "brief reason",
    "recommendation": "specific actionable recommendation"
}}
"""

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "You are a deal analyst assistant. Respond only with valid JSON."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.7,
                max_tokens=200
            )

            analysis_text = response.choices[0].message.content.strip()
            # Try to parse JSON from response
            try:
                analysis = json.loads(analysis_text)
                analysis["suggested_action"] = "notify_both_parties"
                return analysis
            except json.JSONDecodeError:
                # Fallback if response isn't valid JSON
                return {
                    "risk_level": "medium",
                    "reason": analysis_text[:100],
                    "recommendation": "Continue negotiation",
                    "suggested_action": "notify_both_parties"
                }

        except Exception as e:
            logger.error(f"Error analyzing deal: {e}")
            return {
                "risk_level": "medium",
                "reason": "Analysis unavailable",
                "recommendation": "Review deal manually",
                "suggested_action": "notify_both_parties"
            }


class DealIntelligenceAgent:
    """
    Autonomous agent monitoring transactions and intervening proactively.
    
    Responsibilities:
    1. Monitor transactions for stalls (no activity > threshold)
    2. Calculate trust scores for all participants
    3. Analyze stalled deals with LLM
    4. Generate context-aware recommendations
    5. Send proactive notifications to participants
    6. Flag high-risk deals for manual intervention
    """

    def __init__(self, stall_threshold_minutes: int = 5):
        """
        Initialize the agent.
        
        Args:
            stall_threshold_minutes: How long a deal can be inactive before triggering analysis.
                                    Default 5 minutes for production, 2 minutes for demo.
        """
        self.stall_threshold = timedelta(minutes=stall_threshold_minutes)
        self.logger = logging.getLogger(__name__)

    def detect_stalled_deals(self, session: Session) -> list[Transaction]:
        """Find transactions that have stalled (no activity > threshold)."""
        stalled = []
        
        # Get all active transactions
        active_transactions = session.exec(
            select(Transaction).where(
                Transaction.status.in_([
                    TransactionStatus.matched,
                    TransactionStatus.buyer_interested,
                    TransactionStatus.price_proposed,
                    TransactionStatus.price_countered,
                ])
            )
        ).all()

        now = datetime.utcnow()
        for transaction in active_transactions:
            # Check last activity time
            last_activity = transaction.buyer_confirmed_interest_at or transaction.matched_at
            time_since_activity = now - last_activity

            if time_since_activity > self.stall_threshold:
                stalled.append(transaction)

        return stalled

    def process_stalled_deals(self) -> dict:
        """
        Detect, analyze, and notify about stalled deals.
        Returns metadata about processed deals.
        """
        processed = {
            "stalled_deals_found": 0,
            "deals_analyzed": 0,
            "notifications_sent": 0,
            "high_risk_deals": 0,
            "deals": []
        }

        with Session(engine) as session:
            stalled_deals = self.detect_stalled_deals(session)
            processed["stalled_deals_found"] = len(stalled_deals)

            for transaction in stalled_deals:
                try:
                    # Get related data
                    listing = session.get(WasteListing, transaction.listing_id)
                    seller = session.get(User, transaction.seller_id)
                    buyer = session.get(User, transaction.buyer_id)

                    if not all([listing, seller, buyer]):
                        continue

                    # Analyze the deal
                    analysis = DealAnalysis.analyze_stalled_deal(
                        transaction, listing, seller, buyer, session
                    )
                    processed["deals_analyzed"] += 1

                    # Generate notification message
                    message = self._generate_intervention_message(
                        transaction, listing, seller, buyer, analysis
                    )

                    # Create notifications for both parties
                    notification = Notification(
                        user_id=buyer.id,
                        notification_type=NotificationType.deal_update.value,
                        title="Deal Analysis: Negotiation Stalled",
                        message=message,
                        transaction_id=transaction.id,
                        is_read=False
                    )
                    session.add(notification)

                    notification = Notification(
                        user_id=seller.id,
                        notification_type=NotificationType.deal_update.value,
                        title="Deal Analysis: Negotiation Stalled",
                        message=message,
                        transaction_id=transaction.id,
                        is_read=False
                    )
                    session.add(notification)

                    processed["notifications_sent"] += 2

                    # Track high-risk deals
                    if analysis.get("risk_level") == "high":
                        processed["high_risk_deals"] += 1

                    processed["deals"].append({
                        "transaction_id": str(transaction.id),
                        "listing_id": str(listing.id),
                        "material": listing.material_type,
                        "risk_level": analysis.get("risk_level"),
                        "recommendation": analysis.get("recommendation")
                    })

                    session.commit()

                except Exception as e:
                    self.logger.error(f"Error processing stalled deal {transaction.id}: {e}")
                    session.rollback()
                    continue

        return processed

    def calculate_all_trust_scores(self) -> dict:
        """Calculate and return trust scores for all users."""
        with Session(engine) as session:
            return TrustScore.bulk_update_trust_scores(session)

    def _generate_intervention_message(
        self, transaction: Transaction, listing: WasteListing, 
        seller: User, buyer: User, analysis: dict
    ) -> str:
        """Generate a context-aware notification message."""
        return f"""
Your negotiation for {listing.material_type} ({listing.quantity_kg} kg) has been inactive.

Current Status:
- Asking: ${listing.ask_price_per_kg}/kg
- Proposed: ${transaction.initial_proposed_price}/kg
- Rounds: {transaction.negotiation_rounds}

AI Analysis: {analysis.get('reason', 'N/A')}

Recommendation: {analysis.get('recommendation', 'Continue negotiating')}

Take action to move this deal forward.
"""

    def run_once(self) -> dict:
        """Execute one full cycle of deal monitoring."""
        try:
            self.logger.info("Starting deal intelligence cycle...")
            
            # Process stalled deals
            stalled_result = self.process_stalled_deals()
            
            # Calculate trust scores
            scores = self.calculate_all_trust_scores()
            
            self.logger.info(
                f"Cycle complete: {stalled_result['notifications_sent']} notifications, "
                f"{len(scores)} users scored"
            )
            
            return {
                "status": "success",
                "stalled_deals": stalled_result,
                "trust_scores_updated": len(scores),
                "timestamp": datetime.utcnow().isoformat()
            }
        except Exception as e:
            self.logger.error(f"Error in deal intelligence cycle: {e}")
            return {
                "status": "error",
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }


# Global agent instance
_agent = None


def get_deal_intelligence_agent(stall_threshold_minutes: int = 5) -> DealIntelligenceAgent:
    """Get or create the global deal intelligence agent."""
    global _agent
    if _agent is None:
        _agent = DealIntelligenceAgent(stall_threshold_minutes)
    return _agent


def reset_agent(stall_threshold_minutes: int = 5) -> DealIntelligenceAgent:
    """Reset the agent (useful for testing with different thresholds)."""
    global _agent
    _agent = DealIntelligenceAgent(stall_threshold_minutes)
    return _agent
