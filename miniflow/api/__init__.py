"""
API Module for Miniflow
=======================
FastAPI based REST API for workflow management
"""

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
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

# Import and register routes
from .routes.script_routes import router as script_router
from .routes.workflow_routes import router as workflow_router
from .routes.execution_routes import router as execution_router

app.include_router(script_router, prefix="/miniflow")
app.include_router(workflow_router, prefix="/miniflow")
app.include_router(execution_router, prefix="/miniflow")