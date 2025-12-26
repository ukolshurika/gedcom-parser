"""
FastAPI application factory and configuration.

This module creates and configures the FastAPI application instance
with all routes, middleware, and exception handlers.
"""

from __future__ import annotations

import logging
import os

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .api.v1 import router as api_v1_router
from .core.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """
    Create and configure the FastAPI application.

    This factory function creates a new FastAPI instance with:
    - API metadata
    - Middleware (UTF-8 charset)
    - All API routes
    - Exception handlers

    Returns:
        Configured FastAPI application instance
    """
    app = FastAPI(
        title="GEDCOM Parser API",
        description="API for parsing and querying GEDCOM genealogy files with S3 support",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json"
    )

    # Register middleware
    _register_middleware(app)

    # Register routes
    _register_routes(app)

    # Register exception handlers
    _register_exception_handlers(app)

    # Startup event
    @app.on_event("startup")
    async def startup_event():
        logger.info("Starting GEDCOM Parser API")
        logger.info(f"Cache directory: {settings.cache_dir}")
        logger.info(f"S3 bucket: {settings.s3_bucket or 'Not configured'}")

    return app


def _register_middleware(app: FastAPI) -> None:
    """
    Register application middleware.

    Args:
        app: FastAPI application instance
    """

    @app.middleware("http")
    async def add_utf8_charset(request: Request, call_next):
        """Ensure UTF-8 charset in JSON responses."""
        response = await call_next(request)
        if "application/json" in response.headers.get("content-type", ""):
            response.headers["content-type"] = "application/json; charset=utf-8"
        return response


def _register_routes(app: FastAPI) -> None:
    """
    Register API routes.

    Args:
        app: FastAPI application instance
    """
    # Include v1 API routes at root level (for backward compatibility)
    app.include_router(api_v1_router)

    # Optionally, you can also mount under /api/v1 for versioned access
    # app.include_router(api_v1_router, prefix="/api/v1")


def _register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        """Handle unhandled exceptions gracefully."""
        logger.error(f"Unhandled exception: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )


# Create the application instance
app = create_app()


def main() -> None:
    """
    Run the FastAPI server.

    This is the entry point for running the application directly.
    """
    import uvicorn

    port = int(os.getenv("PORT", str(settings.port)))
    host = os.getenv("HOST", settings.host)

    logger.info(f"Starting GEDCOM API server on {host}:{port}")

    uvicorn.run(
        "gedcom_mcp.app:app",
        host=host,
        port=port,
        reload=os.getenv("DEBUG", "").lower() == "true"
    )


if __name__ == "__main__":
    main()
