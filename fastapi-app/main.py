"""
RAG-based Conversational Analytics System
FastAPI Application Entry Point

This system enables natural language queries against a business analytics database
using a multi-stage LLM pipeline with RAG (Retrieval Augmented Generation).

Supports FREE LLM providers:
- Google Gemini (recommended)
- Groq (very fast)
- Ollama (local, completely free)
- OpenAI (paid)
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
import os

from app.api.routes import router
from app.config import get_settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="Conversational Analytics API",
    description="""
    A ChatGPT-style conversational interface for business analytics.

    ## Features
    - Natural language query processing
    - RAG-powered context retrieval
    - Automatic SQL generation
    - Business-friendly answer composition

    ## Supported LLM Providers (FREE options available!)
    - **Google Gemini** (Free tier - recommended)
    - **Groq** (Free tier - very fast)
    - **Ollama** (Local - completely free)
    - **OpenAI** (Paid)

    ## Pipeline Stages
    1. **Query Refinement**: Rewrite user questions for clarity
    2. **Context Retrieval**: Fetch relevant schema, metrics, and rules from vector DB
    3. **SQL Generation**: Generate safe, read-only SQL queries
    4. **SQL Execution**: Execute queries against the analytics database
    5. **Answer Composition**: Create business-friendly responses
    6. **Answer Polishing**: Improve clarity and presentation
    """,
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(router, prefix="/api/v1", tags=["Analytics"])


@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    logger.info("Starting Conversational Analytics API...")
    settings = get_settings()

    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"LLM Model: {settings.llm_model}")

    # Initialize database
    from app.services.database_service import get_database_service

    # Use SQLite for demo/development
    db_url = settings.database_url
    if not os.path.exists("analytics.db") and "sqlite" in db_url:
        logger.info("Initializing SQLite database with sample data...")
        db_service = get_database_service(db_url)
        db_service.create_tables()

        # Seed sample data
        from app.services.seed_data import seed_database
        with db_service.get_session() as session:
            seed_database(session)
        logger.info("Sample data seeded successfully")
    else:
        db_service = get_database_service(db_url)
        db_service.create_tables()

    # Initialize vector store with knowledge base
    try:
        from app.services.vector_store import get_vector_store
        from app.services.knowledge_base import initialize_knowledge_base

        vector_store = get_vector_store()
        initialize_knowledge_base(vector_store)
        logger.info("Vector store initialized with knowledge base")
    except Exception as e:
        logger.warning(f"Could not initialize vector store: {e}")

    # Check LLM configuration
    if settings.llm_api_key or settings.llm_provider == "ollama":
        logger.info(f"LLM configured: {settings.llm_provider} / {settings.llm_model}")
    else:
        logger.warning("LLM API key not configured. Running in simple mode (pattern matching only).")

    logger.info("API startup complete!")


@app.get("/")
async def root():
    """Root endpoint with API information."""
    settings = get_settings()
    return {
        "name": "Conversational Analytics API",
        "version": "1.0.0",
        "description": "Natural language interface for business analytics",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "docs": "/docs",
        "health": "/api/v1/health",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8009,
        reload=True,
    )
