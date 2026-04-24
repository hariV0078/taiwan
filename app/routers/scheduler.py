"""
Scheduler control endpoints for deal intelligence monitoring.

Allows starting/stopping/triggering the autonomous deal monitoring system.
"""

from fastapi import APIRouter, status
from pydantic import BaseModel, ConfigDict

from app.services.scheduler import get_scheduler
from app.services.deal_intelligence import get_deal_intelligence_agent

router = APIRouter()


class SchedulerStartRequest(BaseModel):
    """Request to start scheduler with custom interval."""
    interval_seconds: int = 60  # Default: check every 60 seconds
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "interval_seconds": 60
            }
        }
    )


class SchedulerResponse(BaseModel):
    """Response from scheduler control endpoints."""
    success: bool
    message: str
    data: dict = {}
    
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "message": "Scheduler started",
                "data": {}
            }
        }
    )


@router.post("/scheduler/start", response_model=SchedulerResponse, status_code=status.HTTP_200_OK)
def start_scheduler(request: SchedulerStartRequest):
    """
    Start the autonomous deal intelligence scheduler.
    
    The scheduler monitors stalled transactions and sends proactive notifications.
    
    Args:
        interval_seconds: How often to check for stalled deals (default: 60 seconds)
    
    For demo: Set to 120 (2 minutes). For production: 300 (5 minutes).
    """
    scheduler = get_scheduler()
    success = scheduler.start(interval_seconds=request.interval_seconds)
    
    if success:
        return SchedulerResponse(
            success=True,
            message=f"Scheduler started with {request.interval_seconds}s interval",
            data={"interval_seconds": request.interval_seconds}
        )
    else:
        return SchedulerResponse(
            success=False,
            message="Scheduler already running",
            data=scheduler.status()
        )


@router.post("/scheduler/stop", response_model=SchedulerResponse, status_code=status.HTTP_200_OK)
def stop_scheduler():
    """
    Stop the autonomous deal intelligence scheduler.
    """
    scheduler = get_scheduler()
    success = scheduler.stop()
    
    if success:
        return SchedulerResponse(
            success=True,
            message="Scheduler stopped"
        )
    else:
        return SchedulerResponse(
            success=False,
            message="Scheduler is not running"
        )


@router.post("/scheduler/trigger", response_model=SchedulerResponse, status_code=status.HTTP_200_OK)
def trigger_scheduler():
    """
    Manually trigger a deal intelligence cycle immediately.
    
    Useful for testing or forcing an immediate check without waiting for interval.
    """
    scheduler = get_scheduler()
    result = scheduler.trigger_now()
    
    return SchedulerResponse(
        success=result.get("status") == "success",
        message="Deal intelligence cycle triggered",
        data=result
    )


@router.get("/scheduler/status", response_model=SchedulerResponse, status_code=status.HTTP_200_OK)
def get_scheduler_status():
    """
    Get current scheduler status and configuration.
    """
    scheduler = get_scheduler()
    status_data = scheduler.status()
    
    return SchedulerResponse(
        success=True,
        message="Scheduler status retrieved",
        data=status_data
    )


@router.post("/scheduler/reconfigure", response_model=SchedulerResponse, status_code=status.HTTP_200_OK)
def reconfigure_scheduler(request: SchedulerStartRequest):
    """
    Reconfigure scheduler with new interval (restarts scheduler).
    
    For demo: 120 seconds (stall threshold 2 minutes)
    For production: 300 seconds (stall threshold 5 minutes)
    """
    scheduler = get_scheduler()
    success = scheduler.reconfigure(interval_seconds=request.interval_seconds)
    
    if success:
        return SchedulerResponse(
            success=True,
            message=f"Scheduler reconfigured to {request.interval_seconds}s interval",
            data={"interval_seconds": request.interval_seconds}
        )
    else:
        return SchedulerResponse(
            success=False,
            message="Failed to reconfigure scheduler"
        )


@router.get("/deal-intelligence/trust-scores", status_code=status.HTTP_200_OK)
def get_all_trust_scores():
    """
    Get trust scores for all users (reputation system).
    
    Scores are calculated based on:
    - Transaction completion rate (40%)
    - Negotiation responsiveness (30%)
    - Dispute/failure rate (30%)
    
    Range: 0.0 (very risky) to 1.0 (fully trusted)
    """
    agent = get_deal_intelligence_agent()
    scores = agent.calculate_all_trust_scores()
    
    return {
        "status": "success",
        "trust_scores": scores
    }
