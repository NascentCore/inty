import logging
import time
from pathlib import Path

import uvicorn
from config import Config
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from models import CharacterGenerationRequest, MultiStageGenerationResponse
from multistage_generator import MultiStageCharacterGenerator

# Initialize FastAPI app
app = FastAPI(
    title="AI Character Generator",
    description="Generate comprehensive fictional character profiles with images and encounter scenarios",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize multistage generator
multistage_generator = None
from loguru import logger

WEBUI_PATH = Path(__file__).with_name("webui.html")


@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup"""
    global multistage_generator

    logger.info("Starting AI Character Generator API...")

    try:
        Config.validate()
        logger.info("✅ Configuration validated successfully")

        logger.info("Initializing Multistage Character Generator...")
        multistage_generator = MultiStageCharacterGenerator()
        logger.info("✅ Multistage generator initialized successfully")

        logger.info(f"🚀 API server ready on {Config.HOST}:{Config.PORT}")

    except ValueError as e:
        logger.error(f"❌ Configuration error: {e}")
        raise
    except Exception as e:
        logger.error(f"❌ Startup failed: {e}")
        raise


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all incoming requests and their processing time"""
    start_time = time.time()

    # Log request details
    logger.info(f"📥 {request.method} {request.url.path}")
    logger.debug(f"Request headers: {dict(request.headers)}")
    logger.debug(
        f"Client IP: {request.client.host if request.client else 'Unknown'}"
    )

    # Process request
    response = await call_next(request)

    # Calculate processing time
    process_time = time.time() - start_time

    # Log response details
    logger.info(
        f"📤 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s"
    )

    # Add processing time to response headers
    response.headers["X-Process-Time"] = str(process_time)

    return response


@app.get("/")
async def root():
    """Root endpoint with API information"""
    logger.info("Root endpoint accessed")
    return {
        "message": "AI Character Generator API",
        "version": "1.0.0",
        "endpoints": {
            "multistage_generate": "/generate/multistage",
            "multistage_ui": "/ui",
            "health": "/health",
            "docs": "/docs",
        },
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {"status": "healthy", "service": "ai-character-generator"}


@app.post("/generate/multistage", response_model=MultiStageGenerationResponse)
async def generate_character_multistage(request: CharacterGenerationRequest):
    """Generate character assets via the multi-stage pipeline"""

    logger.info("🧩 Multistage character generation request received")
    if multistage_generator is None:
        logger.error("Multistage generator not initialized")
        raise HTTPException(
            status_code=500, detail="Multistage generator not initialized"
        )

    result = multistage_generator.generate(request)
    if result.success:
        logger.info(
            "✅ Multistage character payload ready in %.2fs",
            result.generation_time,
        )
        return result

    logger.error(f"❌ Multistage generation failed: {result.error}")
    raise HTTPException(
        status_code=500, detail=result.error or "Multistage failure"
    )


@app.get("/ui", response_class=HTMLResponse)
async def serve_webui():
    """Serve minimal browser UI for local usage"""

    if not WEBUI_PATH.exists():
        logger.error("webui.html not found")
        raise HTTPException(status_code=500, detail="Web UI asset missing")

    return HTMLResponse(WEBUI_PATH.read_text(encoding="utf-8"))


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Global exception handler for unhandled exceptions"""
    logger.error(f"❌ Unhandled exception: {str(exc)}")
    logger.exception("Full exception details:")

    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "error": str(exc),
            "path": request.url.path,
        },
    )


if __name__ == "__main__":
    logger.info("Starting API server...")
    uvicorn.run(
        "api:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level=Config.LOG_LEVEL.lower(),
    )
