import logging
import asyncio
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from .config.settings import Settings
from .api import api_router
from .dependencies import get_core
from miniflow.exceptions import MiniflowException, ErrorManager
from miniflow.utils import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Global variables for application state
_core_instance = None
_health_status = {"status": "starting", "database": "unknown", "scheduler": "unknown"}

@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan events - startup and shutdown"""
    global _core_instance, _health_status
    
    # Startup
    logger.info("🚀 Miniflow API starting up...")
    try:
        # Get core system (should be set by main.py)
        _core_instance = get_core()
        
        # Test database connection only if engine is available
        if _core_instance and _core_instance.db_engine:
            await test_database_connection()
            _health_status["database"] = "healthy"
        else:
            logger.warning("⚠️ Database engine not available during startup")
            _health_status["database"] = "not_initialized"
        
        # Check scheduler status
        if _core_instance and _core_instance.enable_scheduler:
            _health_status["scheduler"] = "enabled"
        else:
            _health_status["scheduler"] = "disabled"
            
        _health_status["status"] = "healthy"
        logger.info("✅ Miniflow API startup completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        _health_status["status"] = "unhealthy"
        _health_status["database"] = "error"
        # Don't raise - let the API start even if core isn't fully ready
        logger.warning("⚠️ API starting in degraded mode")
    
    yield  # Application runs here
    
    # Shutdown
    logger.info("🛑 Miniflow API shutting down...")
    try:
        if _core_instance:
            # Note: Don't stop core here since it's managed by main.py
            # Just close any API-specific resources
            logger.info("✅ API shutdown - core instance managed externally")
        else:
            logger.info("✅ API shutdown - no core instance to cleanup")
                    
    except Exception as e:
        logger.error(f"❌ Shutdown error: {e}")

async def test_database_connection():
    """Test database connection during startup"""
    try:
        from sqlalchemy import text
        core = get_core()
        # Simple database test - try to create a session
        with core.db_engine.get_session_context() as session:
            session.execute(text("SELECT 1"))
        logger.info("✅ Database connection test successful")
    except Exception as e:
        logger.error(f"❌ Database connection test failed: {e}")
        raise

# FastAPI instance with lifespan
app = FastAPI(
    title=Settings.PROJECT_NAME,
    description=Settings.PROJECT_DESCRIPTION,
    version=Settings.PROJECT_VERSION,
    docs_url='/docs',
    redoc_url='/redoc',
    lifespan=lifespan
)

# CORS Middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global Exception Handler
@app.exception_handler(MiniflowException)
async def miniflow_exception_handler(request: Request, exc: MiniflowException):
    """Handle custom Miniflow exceptions"""
    logger.error(f"Miniflow exception in {request.url}: {exc}")
    
    error_response = ErrorManager.create_error_response(
        error=exc,
        request_id=getattr(request.state, 'request_id', None),
        endpoint=str(request.url)
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content=error_response
    )

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions"""
    logger.warning(f"HTTP exception in {request.url}: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "success": False,
            "error": {
                "type": "HTTPException",
                "message": exc.detail,
                "status_code": exc.status_code
            },
            "timestamp": str(asyncio.get_event_loop().time())
        }
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error in {request.url}: {exc}", exc_info=True)
    
    error_response = ErrorManager.handle_unexpected_error(
        error=exc,
        context={
            "endpoint": str(request.url),
            "method": request.method
        }
    )
    
    return JSONResponse(
        status_code=500,
        content=error_response
    )

# Health Check Endpoint
@app.get("/health")
async def health_check():
    """System health check endpoint"""
    global _health_status
    
    # Test database if healthy status
    if _health_status["status"] == "healthy":
        try:
            await test_database_connection()
            _health_status["database"] = "healthy"
        except Exception:
            _health_status["database"] = "error"
            _health_status["status"] = "degraded"
    
    return {
        "status": _health_status["status"],
        "timestamp": str(asyncio.get_event_loop().time()),
        "version": Settings.PROJECT_VERSION,
        "components": {
            "database": _health_status["database"],
            "scheduler": _health_status["scheduler"]
        }
    }

# Root Endpoint
@app.get("/")
async def root():
    """API root endpoint with basic information"""
    return {
        "message": "Miniflow API çalışıyor!",
        "version": Settings.PROJECT_VERSION,
        "status": _health_status["status"],
        "docs": "/docs",
        "health": "/health",
        "api": Settings.API_PREFIX
    }

# Include API Router
app.include_router(api_router, prefix=Settings.API_PREFIX)