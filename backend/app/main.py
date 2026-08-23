from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import router as api_router
from app.config import settings
from app.services.storage import ensure_bucket_exists


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure S3 bucket exists (safe no-op if it already does)
    try:
        ensure_bucket_exists()
    except Exception:
        pass  # MinIO might not be running in test/CI
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.app_name,
        version="0.1.0",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )

    # CORS — allow the Vite dev server in development
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
