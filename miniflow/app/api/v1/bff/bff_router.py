"""
Web API Router

Miniflow web uygulaması için tüm API endpoint'lerini organize eden router
Workflow yönetimi, node'lar, edge'ler, script'ler ve execution'ları içerir
"""

from fastapi import APIRouter

# Import all route modules
from . import workflow_bff_routes as workflows
from . import node_bff_routes as nodes
from . import edges_bff_routes as edges
from . import env_var_bff_routes as env_vars
from . import script_bff_routes as scripts
from . import execution_bff_routes as executions

# Web API Router
router = APIRouter()

# Status endpoint
@router.get("/status")
async def web_status():
    """Web API status kontrolü"""
    return {
        "message": "Web API is running", 
        "version": "1.0",
        "modules": ["workflows", "nodes", "edges", "environment_variables", "scripts", "executions"]
    }

# Workflow Management
router.include_router(
    workflows.router,
    prefix="/workflows",
    tags=["workflows"]
)

# Node Management
router.include_router(
    nodes.router,
    prefix="/nodes",
    tags=["nodes"]
)

# Edge Management
router.include_router(
    edges.router,
    prefix="/edges",
    tags=["edges"]
)

# Environment Variables Management
router.include_router(
    env_vars.router,
    prefix="/environment-variables",
    tags=["environment-variables"]
)

# Script Management
router.include_router(
    scripts.router,
    prefix="/scripts",
    tags=["scripts"]
)

# Execution Management
router.include_router(
    executions.router,
    prefix="/executions",
    tags=["executions"]
)
