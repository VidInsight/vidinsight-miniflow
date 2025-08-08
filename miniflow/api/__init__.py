"""
API Module for Miniflow
=======================
FastAPI based REST API for workflow management
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
import os

from ..database_manager import *
from ..exceptions import MiniflowException, ErrorManager, create_error_response, handle_unexpected_error
from .models import ErrorResponse
from .config.settings import settings
from .config.middleware import setup_middleware

# Import MiniflowCore from main.py (root level)
import sys

# Add project root to path
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from ..main import MiniflowCore

# Setup logging
logger = logging.getLogger(__name__)

# Initialize MiniflowCore
test_mode = settings.test_mode
if test_mode:
    db_name = settings.test_db_name
    print(f"🧪 Running in TEST MODE with database: {db_name}")
    miniflow_core = MiniflowCore(db_type="sqlite", db_name=db_name)
else:
    miniflow_core = MiniflowCore(db_type="sqlite", db_name=settings.db_name)

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
    title=settings.title,
    description=settings.description,
    version=settings.version,
    docs_url=settings.docs_url,
    redoc_url=settings.redoc_url,
    lifespan=lifespan
)

# Setup middleware
setup_middleware(app)

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

# Import and register V1 routes
from .routes.v1 import workflow_router, script_router, execution_router, health_router

# Register routes with API version prefix
app.include_router(workflow_router, prefix="/api/v1")
app.include_router(script_router, prefix="/api/v1")
app.include_router(execution_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")