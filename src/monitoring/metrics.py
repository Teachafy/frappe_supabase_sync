"""
Metrics collection system for Frappe-Supabase Sync Service
"""
from typing import Dict, Any, List
from datetime import datetime, timedelta
from collections import defaultdict
import structlog

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class MetricsCollector:
    """Metrics collection and aggregation system"""
    
    def __init__(self):
        self.metrics = {
            "webhook_counts": defaultdict(int),
            "sync_operations": defaultdict(int),
            "sync_durations": [],
            "error_counts": defaultdict(int),
            "conflict_counts": defaultdict(int),
            "retry_counts": defaultdict(int)
        }
        self.start_time = datetime.utcnow()
    
    async def initialize(self):
        """Initialize metrics collector"""
        logger.info("Metrics collector initialized")
    
    async def increment_webhook_count(self, source: str):
        """Increment webhook count for a source"""
        self.metrics["webhook_counts"][source] += 1
        logger.debug("Webhook count incremented", source=source)
    
    async def increment_sync_operation(self, operation_type: str, status: str):
        """Increment sync operation count"""
        key = f"{operation_type}_{status}"
        self.metrics["sync_operations"][key] += 1
        logger.debug("Sync operation count incremented", operation_type=operation_type, status=status)
    
    async def record_sync_duration(self, duration: float, operation_type: str):
        """Record sync operation duration"""
        self.metrics["sync_durations"].append({
            "duration": duration,
            "operation_type": operation_type,
            "timestamp": datetime.utcnow().isoformat()
        })
        
        # Keep only last 1000 durations to prevent memory issues
        if len(self.metrics["sync_durations"]) > 1000:
            self.metrics["sync_durations"] = self.metrics["sync_durations"][-1000:]
    
    async def increment_error_count(self, error_type: str, source: str):
        """Increment error count"""
        key = f"{error_type}_{source}"
        self.metrics["error_counts"][key] += 1
        logger.debug("Error count incremented", error_type=error_type, source=source)
    
    async def increment_conflict_count(self, doctype: str):
        """Increment conflict count for a doctype"""
        self.metrics["conflict_counts"][doctype] += 1
        logger.debug("Conflict count incremented", doctype=doctype)
    
    async def increment_retry_count(self, operation_id: str):
        """Increment retry count for an operation"""
        self.metrics["retry_counts"][operation_id] += 1
        logger.debug("Retry count incremented", operation_id=operation_id)
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics"""
        uptime = datetime.utcnow() - self.start_time
        
        # Calculate average sync duration
        avg_duration = 0
        if self.metrics["sync_durations"]:
            total_duration = sum(d["duration"] for d in self.metrics["sync_durations"])
            avg_duration = total_duration / len(self.metrics["sync_durations"])
        
        # Calculate success rate
        total_operations = sum(self.metrics["sync_operations"].values())
        successful_operations = sum(
            count for key, count in self.metrics["sync_operations"].items() 
            if key.endswith("_completed")
        )
        success_rate = (successful_operations / total_operations * 100) if total_operations > 0 else 0
        
        # Calculate error rate
        total_errors = sum(self.metrics["error_counts"].values())
        error_rate = (total_errors / total_operations * 100) if total_operations > 0 else 0
        
        return {
            "timestamp": datetime.utcnow().isoformat(),
            "uptime_seconds": uptime.total_seconds(),
            "uptime_human": str(uptime),
            "webhook_counts": dict(self.metrics["webhook_counts"]),
            "sync_operations": dict(self.metrics["sync_operations"]),
            "sync_durations": {
                "average_seconds": avg_duration,
                "total_operations": len(self.metrics["sync_durations"]),
                "recent_durations": self.metrics["sync_durations"][-10:]  # Last 10 durations
            },
            "error_counts": dict(self.metrics["error_counts"]),
            "conflict_counts": dict(self.metrics["conflict_counts"]),
            "retry_counts": dict(self.metrics["retry_counts"]),
            "rates": {
                "success_rate_percent": round(success_rate, 2),
                "error_rate_percent": round(error_rate, 2)
            },
            "summary": {
                "total_webhooks": sum(self.metrics["webhook_counts"].values()),
                "total_sync_operations": total_operations,
                "total_errors": total_errors,
                "total_conflicts": sum(self.metrics["conflict_counts"].values()),
                "total_retries": sum(self.metrics["retry_counts"].values())
            }
        }
    
    async def get_metrics_summary(self) -> Dict[str, Any]:
        """Get a summary of key metrics"""
        metrics = await self.get_metrics()
        
        return {
            "status": "healthy" if metrics["rates"]["error_rate_percent"] < 10 else "degraded",
            "uptime": metrics["uptime_human"],
            "total_operations": metrics["summary"]["total_sync_operations"],
            "success_rate": f"{metrics['rates']['success_rate_percent']}%",
            "error_rate": f"{metrics['rates']['error_rate_percent']}%",
            "average_duration": f"{metrics['sync_durations']['average_seconds']:.2f}s"
        }
    
    async def reset_metrics(self):
        """Reset all metrics"""
        self.metrics = {
            "webhook_counts": defaultdict(int),
            "sync_operations": defaultdict(int),
            "sync_durations": [],
            "error_counts": defaultdict(int),
            "conflict_counts": defaultdict(int),
            "retry_counts": defaultdict(int)
        }
        self.start_time = datetime.utcnow()
        logger.info("Metrics reset")
    
    async def get_metrics_by_timeframe(self, hours: int = 24) -> Dict[str, Any]:
        """Get metrics for a specific timeframe"""
        cutoff_time = datetime.utcnow() - timedelta(hours=hours)
        
        # Filter durations by timeframe
        recent_durations = [
            d for d in self.metrics["sync_durations"]
            if datetime.fromisoformat(d["timestamp"]) > cutoff_time
        ]
        
        # Calculate metrics for timeframe
        avg_duration = 0
        if recent_durations:
            total_duration = sum(d["duration"] for d in recent_durations)
            avg_duration = total_duration / len(recent_durations)
        
        return {
            "timeframe_hours": hours,
            "cutoff_time": cutoff_time.isoformat(),
            "operations_in_timeframe": len(recent_durations),
            "average_duration": avg_duration,
            "durations": recent_durations
        }
