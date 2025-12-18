"""
API Routes for the Conversational Analytics System.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Optional, List
import logging

from app.models.schemas import QueryRequest, QueryResponse, ConversationHistory, ChatHistoryResponse
from app.services.rag_pipeline import RAGPipeline, SimplePipeline, get_rag_pipeline, get_simple_pipeline
from app.services.chat_history_service import get_chat_history_service
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


def get_pipeline():
    """Get the appropriate pipeline based on configuration."""
    settings = get_settings()
    if settings.llm_api_key and settings.llm_api_key != "not_needed":
        return get_rag_pipeline()
    elif settings.llm_provider == "ollama":
        # Ollama doesn't need API key
        return get_rag_pipeline()
    else:
        logger.warning("LLM API key not set. Using simple pipeline.")
        return get_simple_pipeline()


@router.post("/chat", response_model=QueryResponse)
async def chat(request: QueryRequest):
    """
    Main chat endpoint for natural language queries.

    Process flow:
    1. Query Refinement
    2. Context Retrieval (RAG)
    3. SQL Generation
    4. SQL Execution
    5. Answer Composition
    6. Answer Polishing

    Args:
        request: QueryRequest with question and optional conversation_id

    Returns:
        QueryResponse with refined question, SQL, results table, and final answer
    """
    try:
        pipeline = get_pipeline()
        response = pipeline.process_query(
            question=request.question,
            conversation_id=request.conversation_id,
        )
        return response
    except Exception as e:
        logger.error(f"Chat error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/conversation/{conversation_id}", response_model=ConversationHistory)
async def get_conversation(conversation_id: str):
    """
    Get conversation history by ID.

    Args:
        conversation_id: The conversation ID

    Returns:
        ConversationHistory with all messages
    """
    pipeline = get_pipeline()
    history = pipeline.get_conversation_history(conversation_id)
    if history is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return history


@router.delete("/conversation/{conversation_id}")
async def delete_conversation(conversation_id: str):
    """
    Delete/clear a conversation.

    Args:
        conversation_id: The conversation ID

    Returns:
        Success message
    """
    pipeline = get_pipeline()
    chat_history = get_chat_history_service()

    # Clear from both in-memory and persistent storage
    pipeline.clear_conversation(conversation_id)
    chat_history.delete_session(conversation_id)

    return {"message": "Conversation deleted successfully"}


@router.get("/chat/history", response_model=ChatHistoryResponse)
async def get_chat_history(days: int = 1):
    """
    Get chat history for the last N days.

    Args:
        days: Number of days to retrieve (default: 1)

    Returns:
        ChatHistoryResponse with list of sessions
    """
    chat_history = get_chat_history_service()
    sessions = chat_history.get_sessions(days=days)
    return ChatHistoryResponse(sessions=sessions, total=len(sessions))


@router.get("/chat/history/{conversation_id}/messages")
async def get_chat_messages(conversation_id: str):
    """
    Get all messages for a specific chat session.

    Args:
        conversation_id: The conversation ID

    Returns:
        List of messages
    """
    chat_history = get_chat_history_service()
    messages = chat_history.get_session_messages(conversation_id)
    return {"conversation_id": conversation_id, "messages": messages}


@router.put("/chat/history/{conversation_id}/title")
async def update_chat_title(conversation_id: str, title: str):
    """
    Update the title of a chat session.

    Args:
        conversation_id: The conversation ID
        title: New title

    Returns:
        Success message
    """
    chat_history = get_chat_history_service()
    if chat_history.update_session_title(conversation_id, title):
        return {"message": "Title updated successfully"}
    raise HTTPException(status_code=404, detail="Session not found")


@router.get("/health")
async def health_check():
    """
    Health check endpoint.

    Returns:
        Health status and configuration info
    """
    settings = get_settings()
    return {
        "status": "healthy",
        "llm_provider": settings.llm_provider,
        "llm_model": settings.llm_model,
        "llm_configured": bool(settings.llm_api_key) or settings.llm_provider == "ollama",
        "database_url": settings.database_url.split("@")[-1] if "@" in settings.database_url else settings.database_url,
        "environment": settings.app_env,
    }


@router.get("/schema")
async def get_schema():
    """
    Get database schema information.

    Returns:
        Dictionary of tables and their columns
    """
    from app.services.database_service import get_database_service

    try:
        db = get_database_service()
        schema = db.get_table_schema()
        return {"schema": schema}
    except Exception as e:
        logger.error(f"Schema retrieval error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/query/sql")
async def execute_raw_sql(sql: str):
    """
    Execute a raw SQL query (for debugging/admin purposes).
    Only SELECT queries are allowed.

    Args:
        sql: SQL query string

    Returns:
        Query results
    """
    from app.services.database_service import get_database_service

    try:
        db = get_database_service()
        results = db.execute_query(sql)
        return {"results": results, "count": len(results)}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"SQL execution error: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/metrics")
async def get_available_metrics():
    """
    Get list of available metrics that can be queried.

    Returns:
        List of metric definitions
    """
    from app.services.knowledge_base import get_metric_definitions

    metrics = get_metric_definitions()
    return {
        "metrics": [
            {
                "id": m["id"],
                "name": m["metadata"].get("metric_name", "Unknown"),
                "description": m["content"].split("\n")[1] if "\n" in m["content"] else m["content"][:100],
            }
            for m in metrics
        ]
    }


@router.get("/tables")
async def get_available_tables():
    """
    Get list of available tables with descriptions.

    Returns:
        List of table information
    """
    from app.services.knowledge_base import get_data_dictionary

    data_dict = get_data_dictionary()
    return {
        "tables": [
            {
                "id": d["id"],
                "name": d["metadata"].get("table_name", "Unknown"),
                "description": d["content"].split("\n")[1] if "\n" in d["content"] else d["content"][:100],
            }
            for d in data_dict
        ]
    }


@router.get("/database/tables")
async def get_database_tables():
    """
    Get list of all database table names.
    """
    from app.services.database_service import get_database_service

    try:
        db = get_database_service()
        schema = db.get_table_schema()
        return {"tables": list(schema.keys())}
    except Exception as e:
        logger.error(f"Error getting tables: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/database/tables/{table_name}")
async def get_table_data(table_name: str, limit: int = 100, offset: int = 0):
    """
    Get data from a specific table with pagination.
    """
    from app.services.database_service import get_database_service

    # Validate table name to prevent SQL injection
    allowed_tables = ["regions", "products", "customers", "sales", "invoices", "expenses"]
    if table_name.lower() not in allowed_tables:
        raise HTTPException(status_code=400, detail=f"Invalid table name. Allowed: {allowed_tables}")

    try:
        db = get_database_service()

        # Get total count
        count_sql = f"SELECT COUNT(*) as total FROM {table_name}"
        count_result = db.execute_query(count_sql)
        total = count_result[0]["total"] if count_result else 0

        # Get paginated data
        data_sql = f"SELECT * FROM {table_name} LIMIT {limit} OFFSET {offset}"
        data = db.execute_query(data_sql)

        # Get column info
        schema = db.get_table_schema()
        columns = schema.get(table_name, [])

        return {
            "table": table_name,
            "columns": columns,
            "data": data,
            "total": total,
            "limit": limit,
            "offset": offset
        }
    except Exception as e:
        logger.error(f"Error getting table data: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
