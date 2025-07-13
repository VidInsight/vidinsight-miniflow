"""
API Module for Miniflow
=======================
FastAPI based REST API for workflow management
"""

from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
import logging

from ..database_manager import *

# Import MiniflowCore from main.py (root level)
import sys
import os

# Add project root to path
current_dir = os.path.dirname(__file__)
project_root = os.path.dirname(os.path.dirname(current_dir))
sys.path.insert(0, project_root)

from ..main import MiniflowCore

# Models are imported within routes when needed

# Setup logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(
    title="Miniflow API",
    description="Workflow orchestration and management API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize MiniflowCore
miniflow_core = MiniflowCore(db_type="sqlite", db_name="miniflow_api")

# Startup and shutdown events
@app.on_event("startup")
async def startup_event():
    """Initialize database and start MiniflowCore"""
    try:
        miniflow_core.start()
        logger.info("MiniflowCore started successfully")
    except Exception as e:
        logger.error(f"Failed to start MiniflowCore: {e}")
        raise

@app.on_event("shutdown")
async def shutdown_event():
    """Stop MiniflowCore and cleanup"""
    try:
        miniflow_core.stop()
        logger.info("MiniflowCore stopped successfully")
    except Exception as e:
        logger.error(f"Error stopping MiniflowCore: {e}")

# Import and register routes
from .routes.script_routes import router as script_router
from .routes.workflow_routes import router as workflow_router

app.include_router(script_router, prefix="/miniflow")
app.include_router(workflow_router, prefix="/miniflow")