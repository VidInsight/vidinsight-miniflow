from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config.settings import Settings
from .config.middleware import setup_middleware
from .api import api_router


# FastAPI instance
app = FastAPI(
    title=Settings.PROJECT_NAME,
    description=Settings.PROJECT_DESCRIPTION,
    version=Settings.PROJECT_VERSION,
    docs_url='/docs',
    redoc_url='/redoc',
)

# CORS Middleware
setup_middleware(app)
app.add_middleware(
    CORSMiddleware,
    allow_origins=Settings.ALLOWED_HOSTS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ana API Router
app.include_router(api_router, prefix=Settings.API_PREFIX)

@app.get("/")
async def root():
    return {
        "message": "Miniflow API çalışıyor!",
        "version": Settings.PROJECT_VERSION,
        "docs": "/docs"
    }