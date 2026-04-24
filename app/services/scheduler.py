"""
Background scheduler for autonomous deal intelligence monitoring.

Uses APScheduler to run deal intelligence cycles periodically.
"""

import logging
from typing import Optional

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

from app.services.deal_intelligence import get_deal_intelligence_agent

logger = logging.getLogger(__name__)


class DealScheduler:
    """
    Manages the background scheduler for deal intelligence.
    
    Allows:
    - Starting/stopping the scheduler
    - Configuring check intervals
    - Manual trigger of deal intelligence cycles
    """

    def __init__(self):
        self.scheduler: Optional[BackgroundScheduler] = None
        self.is_running = False
        self.interval_seconds = 60  # Default: check every 60 seconds

    def start(self, interval_seconds: int = 60) -> bool:
        """
        Start the background scheduler.
        
        Args:
            interval_seconds: How often to run deal intelligence checks
        
        Returns:
            True if started successfully, False if already running
        """
        if self.is_running:
            logger.warning("Scheduler already running")
            return False

        try:
            self.interval_seconds = interval_seconds
            self.scheduler = BackgroundScheduler()
            
            # Schedule deal intelligence checks
            self.scheduler.add_job(
                self._run_deal_intelligence,
                trigger=IntervalTrigger(seconds=interval_seconds),
                id="deal_intelligence_monitor",
                name="Deal Intelligence Monitor",
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info(f"Scheduler started (interval: {interval_seconds}s)")
            return True

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            self.is_running = False
            return False

    def _run_deal_intelligence(self):
        """Internal method called by the scheduler to run deal intelligence."""
        try:
            agent = get_deal_intelligence_agent()
            result = agent.run_once()
            logger.info(f"Deal intelligence cycle completed: {result['status']}")
        except Exception as e:
            logger.error(f"Error in scheduled deal intelligence: {e}")

    def stop(self) -> bool:
        """
        Stop the background scheduler.
        
        Returns:
            True if stopped successfully, False if not running
        """
        if not self.is_running or not self.scheduler:
            logger.warning("Scheduler not running")
            return False

        try:
            self.scheduler.shutdown(wait=False)
            self.is_running = False
            logger.info("Scheduler stopped")
            return True
        except Exception as e:
            logger.error(f"Failed to stop scheduler: {e}")
            return False

    def trigger_now(self) -> dict:
        """
        Manually trigger a deal intelligence cycle immediately.
        
        Returns:
            Result from the deal intelligence agent
        """
        try:
            agent = get_deal_intelligence_agent()
            result = agent.run_once()
            logger.info(f"Manual trigger completed: {result}")
            return result
        except Exception as e:
            logger.error(f"Error in manual trigger: {e}")
            return {
                "status": "error",
                "error": str(e)
            }

    def reconfigure(self, interval_seconds: int) -> bool:
        """
        Change the interval for deal intelligence checks.
        Requires restart of scheduler.
        """
        was_running = self.is_running
        
        if was_running:
            self.stop()
        
        # Restart with new interval
        return self.start(interval_seconds=interval_seconds)

    def status(self) -> dict:
        """Get current scheduler status."""
        if not self.scheduler:
            return {
                "status": "not_initialized",
                "is_running": False
            }

        jobs = []
        if self.scheduler.get_jobs():
            for job in self.scheduler.get_jobs():
                jobs.append({
                    "id": job.id,
                    "name": job.name,
                    "next_run": job.next_run_time.isoformat() if job.next_run_time else None
                })

        return {
            "status": "running" if self.is_running else "stopped",
            "is_running": self.is_running,
            "interval_seconds": self.interval_seconds,
            "jobs": jobs
        }


# Global scheduler instance
_scheduler = None


def get_scheduler() -> DealScheduler:
    """Get or create the global scheduler."""
    global _scheduler
    if _scheduler is None:
        _scheduler = DealScheduler()
    return _scheduler
