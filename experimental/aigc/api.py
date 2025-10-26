from fastapi import FastAPI, HTTPException, BackgroundTasks, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import logging
import time

from config import Config
from models import CharacterGenerationRequest, CharacterGenerationResponse
from character_agent import CharacterAgent

# Initialize FastAPI app
app = FastAPI(
    title="AI Character Generator",
    description="Generate comprehensive fictional character profiles with images and encounter scenarios",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize character agent
character_agent = None
logger = logging.getLogger(__name__)

@app.on_event("startup")
async def startup_event():
    """Validate configuration on startup"""
    global character_agent
    
    logger.info("Starting AI Character Generator API...")
    
    try:
        Config.validate()
        logger.info("✅ Configuration validated successfully")
        
        # Initialize character agent
        logger.info("Initializing Character Agent...")
        character_agent = CharacterAgent()
        logger.info("✅ Character Agent initialized successfully")
        
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
    logger.debug(f"Client IP: {request.client.host if request.client else 'Unknown'}")
    
    # Process request
    response = await call_next(request)
    
    # Calculate processing time
    process_time = time.time() - start_time
    
    # Log response details
    logger.info(f"📤 {request.method} {request.url.path} - Status: {response.status_code} - Time: {process_time:.3f}s")
    
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
            "generate_character": "/generate",
            "health": "/health",
            "docs": "/docs"
        }
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    logger.debug("Health check requested")
    return {"status": "healthy", "service": "ai-character-generator"}

@app.post("/generate", response_model=CharacterGenerationResponse)
async def generate_character(request: CharacterGenerationRequest):
    """Generate a complete character profile"""
    
    logger.info(f"📝 Character generation request received")
    logger.info(f"Description: {request.brief_description}")
    logger.debug(f"Genre: {request.genre}, Tone: {request.tone}")
    logger.debug(f"Image style: {request.image_style}, Num images: {request.num_images}")
    
    if character_agent is None:
        logger.error("Character agent not initialized")
        raise HTTPException(status_code=500, detail="Character agent not initialized")
    
    try:
        # Generate character using the agent
        logger.info("Starting character generation process...")
        response = character_agent.generate_character(request)
        
        if response.success:
            logger.info(f"✅ Character generated successfully: {response.character.name}")
            logger.info(f"⏱️ Generation time: {response.generation_time:.2f} seconds")
            return response
        else:
            logger.error(f"❌ Character generation failed: {response.error}")
            raise HTTPException(status_code=500, detail=response.error)
            
    except HTTPException:
        # Re-raise HTTP exceptions as-is
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error in character generation: {str(e)}")
        logger.exception("Full exception details:")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.post("/generate/async")
async def generate_character_async(
    request: CharacterGenerationRequest,
    background_tasks: BackgroundTasks
):
    """Generate character asynchronously (for long-running requests)"""
    
    logger.info(f"📝 Async character generation request received")
    logger.info(f"Description: {request.brief_description}")
    
    if character_agent is None:
        logger.error("Character agent not initialized")
        raise HTTPException(status_code=500, detail="Character agent not initialized")
    
    # For now, we'll return a simple response
    # In a full implementation, you'd use a task queue like Celery
    background_tasks.add_task(character_agent.generate_character, request)
    
    request_id = f"char_{hash(request.brief_description)}"
    logger.info(f"✅ Async task queued with ID: {request_id}")
    
    return {
        "message": "Character generation started",
        "request_id": request_id,
        "status": "processing"
    }

@app.get("/characters/{character_id}")
async def get_character(character_id: str):
    """Get a previously generated character (placeholder)"""
    logger.info(f"📝 Character retrieval request for ID: {character_id}")
    logger.warning("Character retrieval not implemented yet")
    # This would typically fetch from a database
    raise HTTPException(status_code=404, detail="Character not found")

@app.get("/export/{character_id}")
async def export_character(
    character_id: str,
    format: str = "json"
):
    """Export character in specified format"""
    logger.info(f"📝 Character export request for ID: {character_id}, format: {format}")
    logger.warning("Character export not implemented yet")
    # This would typically fetch from a database and export
    raise HTTPException(status_code=404, detail="Character not found")

@app.get("/examples")
async def get_example_requests():
    """Get example character generation requests"""
    
    logger.info("📝 Example requests endpoint accessed")
    
    examples = [
        {
            "brief_description": "A mysterious wizard who lives in a floating tower",
            "genre": "fantasy",
            "tone": "mysterious",
            "image_style": "fantasy_art",
            "num_images": 4
        },
        {
            "brief_description": "A cyberpunk hacker with neon-colored hair",
            "genre": "sci-fi",
            "tone": "edgy",
            "image_style": "cyberpunk",
            "num_images": 3
        },
        {
            "brief_description": "A wise old librarian who knows ancient secrets",
            "genre": "mystery",
            "tone": "wise",
            "image_style": "realistic",
            "num_images": 4
        },
        {
            "brief_description": "A cheerful barista who dreams of opening their own cafe",
            "genre": "slice_of_life",
            "tone": "cheerful",
            "image_style": "anime",
            "num_images": 3
        }
    ]
    
    logger.info(f"✅ Returning {len(examples)} example requests")
    return {"examples": examples}

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
            "path": request.url.path
        }
    )

if __name__ == "__main__":
    logger.info("Starting API server...")
    uvicorn.run(
        "api:app",
        host=Config.HOST,
        port=Config.PORT,
        reload=Config.DEBUG,
        log_level=Config.LOG_LEVEL.lower()
    ) 