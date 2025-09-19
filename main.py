"""
Main FastAPI application for Frappe-Supabase Sync Service
"""
import os
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import structlog

from src.config import settings
from src.utils.logger import setup_logging
from src.handlers.frappe_webhook import FrappeWebhookHandler
from src.handlers.supabase_webhook import SupabaseWebhookHandler
from src.engine.sync_engine import SyncEngine
from src.queue.sync_queue import SyncQueue
from src.monitoring.health import HealthChecker
from src.monitoring.metrics import MetricsCollector
from src.api.schema_api import router as schema_router

# Setup logging
setup_logging(settings.log_level)
logger = structlog.get_logger(__name__)

# Initialize handlers and services
frappe_handler = FrappeWebhookHandler()
supabase_handler = SupabaseWebhookHandler()
sync_engine = SyncEngine()
sync_queue = SyncQueue()
health_checker = HealthChecker()
metrics_collector = MetricsCollector()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan management"""
    # Startup
    logger.info("Starting Frappe-Supabase Sync Service")
    
    # Initialize health checker
    await health_checker.initialize()
    
    # Initialize metrics collector
    if settings.enable_metrics:
        await metrics_collector.initialize()
    
    yield
    
    # Shutdown
    logger.info("Shutting down Frappe-Supabase Sync Service")


# Create FastAPI app
app = FastAPI(
    title="Frappe-Supabase Sync Service",
    description="2-way synchronization service between Frappe and Supabase",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(schema_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "service": "Frappe-Supabase Sync Service",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        health_status = await health_checker.check_health()
        return health_status
    except Exception as e:
        logger.error("Health check failed", error=str(e))
        raise HTTPException(status_code=500, detail="Health check failed")


@app.get("/metrics")
async def get_metrics():
    """Metrics endpoint"""
    if not settings.enable_metrics:
        raise HTTPException(status_code=404, detail="Metrics not enabled")
    
    try:
        metrics = await metrics_collector.get_metrics()
        return metrics
    except Exception as e:
        logger.error("Failed to get metrics", error=str(e))
        raise HTTPException(status_code=500, detail="Failed to get metrics")


@app.post("/webhook/frappe")
async def frappe_webhook(request: Request, background_tasks: BackgroundTasks):
    """Frappe webhook endpoint"""
    try:
        payload = await request.json()
        logger.info("Received Frappe webhook", payload=payload)
        
        # Process webhook in background
        result = await frappe_handler.process_webhook(request, payload)
        
        # Update metrics
        if settings.enable_metrics:
            await metrics_collector.increment_webhook_count("frappe")
        
        return result
        
    except Exception as e:
        logger.error("Frappe webhook processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/webhook/supabase")
async def supabase_webhook(request: Request, background_tasks: BackgroundTasks):
    """Supabase webhook endpoint"""
    try:
        payload = await request.json()
        logger.info("Received Supabase webhook", payload=payload)
        
        # Process webhook in background
        result = await supabase_handler.process_webhook(request, payload)
        
        # Update metrics
        if settings.enable_metrics:
            await metrics_collector.increment_webhook_count("supabase")
        
        return result
        
    except Exception as e:
        logger.error("Supabase webhook processing failed", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/status")
async def get_sync_status():
    """Get sync service status"""
    try:
        queue_status = await sync_queue.get_queue_status()
        
        return {
            "status": "running",
            "queue_status": queue_status,
            "sync_mappings": len(settings.sync_mappings),
            "enabled_mappings": len([m for m in settings.sync_mappings.values() if m.get("enabled", True)])
        }
        
    except Exception as e:
        logger.error("Failed to get sync status", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/retry-failed")
async def retry_failed_operations():
    """Retry failed sync operations"""
    try:
        retried_count = await sync_queue.retry_failed_operations()
        
        return {
            "status": "success",
            "retried_operations": retried_count
        }
        
    except Exception as e:
        logger.error("Failed to retry operations", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/mappings")
async def get_sync_mappings():
    """Get current sync mappings configuration"""
    try:
        return {
            "mappings": settings.sync_mappings,
            "count": len(settings.sync_mappings)
        }
        
    except Exception as e:
        logger.error("Failed to get sync mappings", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sync/mappings")
async def update_sync_mappings(mappings: dict):
    """Update sync mappings configuration"""
    try:
        # Validate mappings
        for doctype, mapping in mappings.items():
            if not isinstance(mapping, dict):
                raise HTTPException(status_code=400, detail=f"Invalid mapping for {doctype}")
            
            required_fields = ["frappe_doctype", "supabase_table", "sync_fields"]
            for field in required_fields:
                if field not in mapping:
                    raise HTTPException(status_code=400, detail=f"Missing {field} in {doctype} mapping")
        
        # Update mappings
        settings.sync_mappings.update(mappings)
        
        logger.info("Sync mappings updated", mappings=list(mappings.keys()))
        
        return {
            "status": "success",
            "updated_mappings": list(mappings.keys())
        }
        
    except Exception as e:
        logger.error("Failed to update sync mappings", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/sync/mappings/{doctype}")
async def delete_sync_mapping(doctype: str):
    """Delete a sync mapping"""
    try:
        if doctype not in settings.sync_mappings:
            raise HTTPException(status_code=404, detail=f"Mapping for {doctype} not found")
        
        del settings.sync_mappings[doctype]
        
        logger.info("Sync mapping deleted", doctype=doctype)
        
        return {
            "status": "success",
            "deleted_doctype": doctype
        }
        
    except Exception as e:
        logger.error("Failed to delete sync mapping", doctype=doctype, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/operations/{operation_id}")
async def get_sync_operation(operation_id: str):
    """Get sync operation details"""
    try:
        operation = await sync_queue.get_operation_by_id(operation_id)
        
        if not operation:
            raise HTTPException(status_code=404, detail="Operation not found")
        
        return operation.dict()
        
    except Exception as e:
        logger.error("Failed to get sync operation", operation_id=operation_id, error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/sync/operations/failed")
async def get_failed_operations(limit: int = 100):
    """Get failed sync operations"""
    try:
        failed_operations = await sync_queue.get_failed_operations(limit)
        
        return {
            "failed_operations": [op.dict() for op in failed_operations],
            "count": len(failed_operations)
        }
        
    except Exception as e:
        logger.error("Failed to get failed operations", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.log_level.lower()
    )
