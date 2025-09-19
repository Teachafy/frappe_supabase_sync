"""
Health check system for Frappe-Supabase Sync Service
"""
from typing import Dict, Any, List
from datetime import datetime
import httpx
import redis
import structlog

from ..config import settings
from ..utils.logger import get_logger

logger = get_logger(__name__)


class HealthChecker:
    """Health check system for monitoring service dependencies"""
    
    def __init__(self):
        self.checks = {
            "frappe": self._check_frappe_health,
            "supabase": self._check_supabase_health,
            "redis": self._check_redis_health,
            "database": self._check_database_health
        }
    
    async def initialize(self):
        """Initialize health checker"""
        logger.info("Health checker initialized")
    
    async def check_health(self) -> Dict[str, Any]:
        """Perform comprehensive health check"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "checks": {},
            "overall_status": "healthy"
        }
        
        # Run all health checks
        for check_name, check_func in self.checks.items():
            try:
                check_result = await check_func()
                health_status["checks"][check_name] = check_result
                
                if not check_result["healthy"]:
                    health_status["overall_status"] = "unhealthy"
                    health_status["status"] = "unhealthy"
                    
            except Exception as e:
                logger.error(f"Health check failed for {check_name}", error=str(e))
                health_status["checks"][check_name] = {
                    "healthy": False,
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
                health_status["overall_status"] = "unhealthy"
                health_status["status"] = "unhealthy"
        
        return health_status
    
    async def _check_frappe_health(self) -> Dict[str, Any]:
        """Check Frappe API health"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{settings.frappe_url}/api/method/ping",
                    headers={
                        "Authorization": f"token {settings.frappe_api_key}:{settings.frappe_api_secret}"
                    },
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {
                        "healthy": True,
                        "response_time": response.elapsed.total_seconds(),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                else:
                    return {
                        "healthy": False,
                        "status_code": response.status_code,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_supabase_health(self) -> Dict[str, Any]:
        """Check Supabase API health"""
        try:
            from ..utils.supabase_client import SupabaseClient
            supabase_client = SupabaseClient()
            
            # Try to execute a simple query
            response = await supabase_client.get_records("_health_check", limit=1)
            
            return {
                "healthy": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_redis_health(self) -> Dict[str, Any]:
        """Check Redis health"""
        try:
            redis_client = redis.from_url(settings.redis_url)
            
            # Test Redis connection
            redis_client.ping()
            
            # Get Redis info
            info = redis_client.info()
            
            return {
                "healthy": True,
                "redis_version": info.get("redis_version"),
                "used_memory": info.get("used_memory_human"),
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def _check_database_health(self) -> Dict[str, Any]:
        """Check database health"""
        try:
            # This would check the sync state database
            # For now, return healthy if we can connect to Redis
            redis_client = redis.from_url(settings.redis_url)
            redis_client.ping()
            
            return {
                "healthy": True,
                "timestamp": datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            return {
                "healthy": False,
                "error": str(e),
                "timestamp": datetime.utcnow().isoformat()
            }
    
    async def get_detailed_health(self) -> Dict[str, Any]:
        """Get detailed health information"""
        health_status = await self.check_health()
        
        # Add additional details
        health_status["service_info"] = {
            "name": "Frappe-Supabase Sync Service",
            "version": "1.0.0",
            "uptime": "N/A",  # Would be calculated from start time
            "environment": "production"  # Would be from config
        }
        
        health_status["dependencies"] = {
            "frappe_url": settings.frappe_url,
            "supabase_url": settings.supabase_url,
            "redis_url": settings.redis_url
        }
        
        return health_status
