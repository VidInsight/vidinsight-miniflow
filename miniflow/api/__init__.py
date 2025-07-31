"""
API Module for Miniflow
=======================
FastAPI based REST API for workflow management
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
from datetime import datetime
import logging

from ..database_manager import *
from ..exceptions import MiniflowException, ErrorManager, create_error_response, handle_unexpected_error
from .models import ErrorResponse

# Import MiniflowCore from main.py (root level)
import sys
import os

# Add project root to path
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from ..main import MiniflowCore

# Setup logging
logger = logging.getLogger(__name__)

# Initialize MiniflowCore
# (Moved up so lifespan can reference it)
test_mode = os.getenv("MINIFLOW_TEST_MODE", "false").lower() == "true"
if test_mode:
    db_name = os.getenv("MINIFLOW_TEST_DB_NAME", "test_miniflow_api")
    print(f"🧪 Running in TEST MODE with database: {db_name}")
    miniflow_core = MiniflowCore(db_type="sqlite", db_name=db_name)
else:
    miniflow_core = MiniflowCore(db_type="sqlite", db_name="miniflow_api")

# Lifespan context manager for startup/shutdown events
@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize database and start MiniflowCore on startup, cleanup on shutdown"""
    # Startup
    try:
        miniflow_core.start()
        logger.info("MiniflowCore started successfully")
    except Exception as e:
        logger.error(f"Failed to start MiniflowCore: {e}")
        raise
    
    yield
    
    # Shutdown
    try:
        miniflow_core.stop()
        logger.info("MiniflowCore stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping MiniflowCore: {e}")

# Initialize FastAPI app
app = FastAPI(
    title="Miniflow API",
    description="Workflow orchestration and management API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API Metrics Middleware (conditionally added)
try:
    app.add_middleware(
        APIMetricsMiddleware,
        performance_tracker=None,  # Will be set when miniflow_core starts
        track_request_body=True,
        track_response_body=True
    )
except Exception as e:
    import logging
    logging.warning(f"API Metrics Middleware not added: {e}")

# CENTRALIZED EXCEPTION HANDLERS
# ==============================================================
@app.exception_handler(MiniflowException)
async def miniflow_exception_handler(request: Request, exc: MiniflowException):
    """Handle all MiniflowException types with proper HTTP status codes"""
    status_code = ErrorManager.get_http_status_code(exc)
    error_response = ErrorManager.exception_to_error_response(exc)
    
    logger.warning(f"MiniflowException in {request.url.path}: {exc.error_code} - {exc.message}")
    
    return JSONResponse(
        status_code=status_code,
        content=error_response
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    error_response = handle_unexpected_error(exc, f"API endpoint {request.url.path}")
    
    logger.error(f"Unexpected exception in {request.url.path}: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )

# HEALTH CHECK ENDPOINT (Enhanced Monitoring)
# ==============================================================
@app.get("/health", tags=["Health Check"])
async def health_check():
    """
    Enhanced system health check with detailed resource metrics
    
    Returns comprehensive monitoring data including:
    - Component status (database, execution engine, scheduler)
    - System resources (CPU, memory, disk, network)
    - Business metrics (execution count, success rate)
    - Performance indicators
    """
    try:
        health_data = miniflow_core.health_check()
        
        # Determine HTTP status code based on health
        status_code = 200
        if health_data["status"] == "unhealthy":
            status_code = 503  # Service Unavailable
        elif health_data["status"] == "error":
            status_code = 500  # Internal Server Error
        
        return JSONResponse(
            status_code=status_code,
            content={
                "health": health_data,
                "api_version": "1.0.0",
                "service": "Miniflow Workflow Engine"
            }
        )
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "health": {
                    "status": "error",
                    "timestamp": datetime.utcnow().isoformat() + "Z",
                    "error": str(e)
                },
                "api_version": "1.0.0",
                "service": "Miniflow Workflow Engine"
            }
        )

# Basic health check for load balancers
@app.get("/ping", tags=["Health Check"])
async def ping():
    """Simple ping endpoint for load balancer health checks"""
    return {"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"}

# MONITORING ENDPOINTS
# ==============================================================
@app.get("/metrics", tags=["Monitoring"])
async def get_metrics():
    """
    Get current system metrics and performance data
    
    Returns real-time monitoring data including:
    - Current system metrics (CPU, memory, disk, network)
    - Performance tracking data
    - Historical trends
    """
    try:
        if not miniflow_core.enable_monitoring:
            return JSONResponse(
                status_code=503,
                content={"error": "Monitoring is disabled", "metrics": None}
            )
        
        metrics_data = {}
        
        # Current metrics
        if miniflow_core.metrics_collector:
            metrics_data["current"] = miniflow_core.metrics_collector.get_current_metrics()
            metrics_data["collection_stats"] = miniflow_core.metrics_collector.get_collection_stats()
            metrics_data["metrics_summary"] = miniflow_core.metrics_collector.get_metrics_summary()
        
        # Performance data
        if miniflow_core.performance_tracker:
            metrics_data["performance_summary"] = miniflow_core.performance_tracker.get_all_operations_summary(minutes=10)
            metrics_data["tracker_stats"] = miniflow_core.performance_tracker.get_tracker_stats()
        
        # Database metrics
        if miniflow_core.database_metrics:
            # Update pool metrics before getting data
            if miniflow_core.db_engine:
                miniflow_core.database_metrics.update_pool_metrics(miniflow_core.db_engine)
            
            metrics_data["database_summary"] = miniflow_core.database_metrics.get_database_summary()
            metrics_data["query_stats"] = miniflow_core.database_metrics.get_query_stats(minutes=10)
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "monitoring_enabled": True,
                "metrics": metrics_data
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "error": f"Failed to get metrics: {str(e)}",
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }
        )

@app.get("/metrics/history", tags=["Monitoring"])
async def get_metrics_history(minutes: int = 10):
    """Get historical metrics data for specified time period"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.metrics_collector:
            return JSONResponse(
                status_code=503,
                content={"error": "Monitoring or metrics collection is disabled"}
            )
        
        # Limit history request to reasonable bounds
        minutes = max(1, min(minutes, 1440))  # Between 1 minute and 24 hours
        
        history_data = miniflow_core.metrics_collector.get_metrics_history(minutes=minutes)
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "time_window_minutes": minutes,
                "data_points": len(history_data),
                "history": history_data
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get metrics history: {str(e)}"}
        )

@app.get("/performance", tags=["Monitoring"])
async def get_performance_data(minutes: int = 10):
    """Get performance tracking data for all operations"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.performance_tracker:
            return JSONResponse(
                status_code=503,
                content={"error": "Monitoring or performance tracking is disabled"}
            )
        
        # Limit time window
        minutes = max(1, min(minutes, 1440))  # Between 1 minute and 24 hours
        
        performance_data = {
            "summary": miniflow_core.performance_tracker.get_all_operations_summary(minutes=minutes),
            "tracker_stats": miniflow_core.performance_tracker.get_tracker_stats(),
            "slow_operations": miniflow_core.performance_tracker.get_slow_operations(threshold_ms=1000, minutes=minutes),
            "failed_operations": miniflow_core.performance_tracker.get_error_operations(minutes=minutes)
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "time_window_minutes": minutes,
                "performance": performance_data
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get performance data: {str(e)}"}
        )

@app.get("/performance/{operation}", tags=["Monitoring"])
async def get_operation_performance(operation: str, minutes: int = 10):
    """Get performance data for a specific operation"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.performance_tracker:
            return JSONResponse(
                status_code=503,
                content={"error": "Monitoring or performance tracking is disabled"}
            )
        
        # Limit time window
        minutes = max(1, min(minutes, 1440))
        
        operation_stats = miniflow_core.performance_tracker.get_operation_stats(operation, minutes=minutes)
        operation_trends = miniflow_core.performance_tracker.get_performance_trends(operation, hours=1)
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "operation": operation,
                "time_window_minutes": minutes,
                "stats": operation_stats,
                "trends": operation_trends
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get operation performance: {str(e)}"}
        )

# DATABASE MONITORING ENDPOINTS
# ==============================================================
@app.get("/database/metrics", tags=["Database Monitoring"])
async def get_database_metrics():
    """Get comprehensive database performance metrics"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.database_metrics:
            return JSONResponse(
                status_code=503,
                content={"error": "Database monitoring is disabled"}
            )
        
        # Update pool metrics before getting data
        if miniflow_core.db_engine:
            miniflow_core.database_metrics.update_pool_metrics(miniflow_core.db_engine)
        
        database_data = {
            "summary": miniflow_core.database_metrics.get_database_summary(),
            "query_stats": miniflow_core.database_metrics.get_query_stats(minutes=10),
            "pool_status": miniflow_core.database_metrics.get_pool_status(),
            "slow_queries": miniflow_core.database_metrics.get_slow_queries(minutes=10, threshold_ms=1000),
            "failed_queries": miniflow_core.database_metrics.get_failed_queries(minutes=10)
        }
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "database": database_data
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get database metrics: {str(e)}"}
        )

@app.get("/database/queries/slow", tags=["Database Monitoring"])
async def get_slow_queries(minutes: int = 10, threshold_ms: float = 1000):
    """Get slow database queries that exceeded duration threshold"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.database_metrics:
            return JSONResponse(
                status_code=503,
                content={"error": "Database monitoring is disabled"}
            )
        
        # Limit parameters
        minutes = max(1, min(minutes, 1440))  # 1 minute to 24 hours
        threshold_ms = max(100, min(threshold_ms, 60000))  # 100ms to 60 seconds
        
        slow_queries = miniflow_core.database_metrics.get_slow_queries(
            minutes=minutes, 
            threshold_ms=threshold_ms
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "time_window_minutes": minutes,
                "threshold_ms": threshold_ms,
                "slow_queries_count": len(slow_queries),
                "slow_queries": slow_queries
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get slow queries: {str(e)}"}
        )

@app.get("/database/queries/failed", tags=["Database Monitoring"])
async def get_failed_queries(minutes: int = 10):
    """Get failed database queries"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.database_metrics:
            return JSONResponse(
                status_code=503,
                content={"error": "Database monitoring is disabled"}
            )
        
        # Limit time window
        minutes = max(1, min(minutes, 1440))  # 1 minute to 24 hours
        
        failed_queries = miniflow_core.database_metrics.get_failed_queries(minutes=minutes)
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "time_window_minutes": minutes,
                "failed_queries_count": len(failed_queries),
                "failed_queries": failed_queries
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get failed queries: {str(e)}"}
        )

@app.get("/database/pool", tags=["Database Monitoring"])
async def get_connection_pool_status():
    """Get database connection pool status"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.database_metrics:
            return JSONResponse(
                status_code=503,
                content={"error": "Database monitoring is disabled"}
            )
        
        # Update pool metrics before getting data
        if miniflow_core.db_engine:
            miniflow_core.database_metrics.update_pool_metrics(miniflow_core.db_engine)
        
        pool_status = miniflow_core.database_metrics.get_pool_status()
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "connection_pools": pool_status
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get connection pool status: {str(e)}"}
        )

# API MONITORING ENDPOINTS
# ==============================================================
@app.get("/api/metrics", tags=["API Monitoring"])
async def get_api_metrics(minutes: int = 10):
    """Get API-specific performance metrics"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.performance_tracker:
            return JSONResponse(
                status_code=503,
                content={"error": "API monitoring is disabled"}
            )
        
        # Limit time window
        minutes = max(1, min(minutes, 1440))  # 1 minute to 24 hours
        
        api_data = get_api_metrics_summary(miniflow_core.performance_tracker, minutes=minutes)
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "time_window_minutes": minutes,
                "api_metrics": api_data
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get API metrics: {str(e)}"}
        )

@app.get("/api/requests/slow", tags=["API Monitoring"])
async def get_slow_api_requests_endpoint(minutes: int = 10, threshold_ms: float = 1000):
    """Get slow API requests that exceeded duration threshold"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.performance_tracker:
            return JSONResponse(
                status_code=503,
                content={"error": "API monitoring is disabled"}
            )
        
        # Limit parameters
        minutes = max(1, min(minutes, 1440))  # 1 minute to 24 hours
        threshold_ms = max(100, min(threshold_ms, 60000))  # 100ms to 60 seconds
        
        slow_requests = get_slow_api_requests(
            miniflow_core.performance_tracker,
            minutes=minutes,
            threshold_ms=threshold_ms
        )
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                **slow_requests
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get slow API requests: {str(e)}"}
        )

@app.get("/api/requests/failed", tags=["API Monitoring"])
async def get_failed_api_requests_endpoint(minutes: int = 10):
    """Get failed API requests"""
    try:
        if not miniflow_core.enable_monitoring or not miniflow_core.performance_tracker:
            return JSONResponse(
                status_code=503,
                content={"error": "API monitoring is disabled"}
            )
        
        # Limit time window
        minutes = max(1, min(minutes, 1440))  # 1 minute to 24 hours
        
        failed_requests = get_failed_api_requests(miniflow_core.performance_tracker, minutes=minutes)
        
        return JSONResponse(
            status_code=200,
            content={
                "timestamp": datetime.utcnow().isoformat() + "Z",
                **failed_requests
            }
        )
        
    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"error": f"Failed to get failed API requests: {str(e)}"}
        )

# Import and register routes
from .routes.script_routes import router as script_router
from .routes.workflow_routes import router as workflow_router
from .routes.execution_routes import router as execution_router
from .routes.security_routes import router as security_router
from .routes.environment_variable_routes import router as environment_variable_router

app.include_router(script_router, prefix="/miniflow")
app.include_router(workflow_router, prefix="/miniflow")
app.include_router(execution_router, prefix="/miniflow")
app.include_router(security_router, prefix="/miniflow")
app.include_router(environment_variable_router, prefix="/miniflow")