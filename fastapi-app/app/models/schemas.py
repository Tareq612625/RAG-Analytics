from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime


class QueryRequest(BaseModel):
    question: str
    conversation_id: Optional[str] = None


class QueryResponse(BaseModel):
    refined_question: str
    sql: Optional[str] = None
    table: List[dict] = []
    final_answer: str
    conversation_id: str


class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str
    timestamp: datetime = None

    def __init__(self, **data):
        if "timestamp" not in data or data["timestamp"] is None:
            data["timestamp"] = datetime.now()
        super().__init__(**data)


class ConversationHistory(BaseModel):
    conversation_id: str
    messages: List[ChatMessage] = []


class MetricDefinition(BaseModel):
    name: str
    description: str
    formula: str
    tables: List[str]
    columns: List[str]


class TableSchema(BaseModel):
    table_name: str
    description: str
    columns: List[dict]


class BusinessRule(BaseModel):
    name: str
    description: str
    rule_type: str
    conditions: str


class ChatSession(BaseModel):
    """Represents a single chat session with metadata."""
    conversation_id: str
    title: str  # First question or auto-generated title
    created_at: datetime
    updated_at: datetime
    message_count: int = 0
    first_question: Optional[str] = None


class ChatHistoryResponse(BaseModel):
    """Response model for chat history list."""
    sessions: List[ChatSession]
    total: int
