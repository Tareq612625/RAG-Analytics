"""
RAG Pipeline - Orchestrates the complete conversational analytics flow.
Optimized 4-step pipeline (reduced from 6 to minimize API calls):
1. Context Retrieval (RAG Stage)
2. SQL Generation with Query Refinement (LLM Stage 1 - combined)
3. SQL Execution (Backend)
4. Answer Composition (LLM Stage 2 - combined with polishing)
"""

from typing import Dict, Any, Optional, List
import uuid
import logging
from datetime import datetime

from app.services.llm_service import LLMService, get_llm_service
from app.services.vector_store import VectorStoreService, get_vector_store
from app.services.database_service import DatabaseService, get_database_service
from app.models.schemas import QueryResponse, ChatMessage, ConversationHistory

logger = logging.getLogger(__name__)


class RAGPipeline:
    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        vector_store: Optional[VectorStoreService] = None,
        database_service: Optional[DatabaseService] = None,
    ):
        self.llm = llm_service or get_llm_service()
        self.vector_store = vector_store or get_vector_store()
        self.db = database_service or get_database_service()

        # Conversation history storage (in-memory for demo)
        self.conversations: Dict[str, ConversationHistory] = {}

    def _get_or_create_conversation(self, conversation_id: Optional[str]) -> ConversationHistory:
        """Get existing conversation or create a new one."""
        if conversation_id and conversation_id in self.conversations:
            return self.conversations[conversation_id]

        new_id = conversation_id or str(uuid.uuid4())
        conversation = ConversationHistory(conversation_id=new_id, messages=[])
        self.conversations[new_id] = conversation
        return conversation

    def _add_message(self, conversation: ConversationHistory, role: str, content: str):
        """Add a message to conversation history."""
        message = ChatMessage(role=role, content=content, timestamp=datetime.now())
        conversation.messages.append(message)

    def process_query(self, question: str, conversation_id: Optional[str] = None) -> QueryResponse:
        """
        Process a user query through the complete RAG pipeline.

        Args:
            question: User's natural language question
            conversation_id: Optional conversation ID for context

        Returns:
            QueryResponse with refined question, SQL, results, and answer
        """
        logger.info(f"Processing query: {question}")

        # Get or create conversation
        conversation = self._get_or_create_conversation(conversation_id)
        self._add_message(conversation, "user", question)

        try:
            # STEP 1: Context Retrieval from Vector Database
            logger.info("Step 1: Retrieving context...")
            context = self.vector_store.get_all_context(question)
            logger.debug(f"Retrieved context length: {len(context)}")

            # STEP 2: SQL Generation with Query Refinement (combined - 1 LLM call)
            logger.info("Step 2: Generating SQL with query refinement...")
            refined_question, sql = self.llm.generate_sql(question, context)
            logger.info(f"Refined question: {refined_question}")
            logger.info(f"Generated SQL: {sql}")

            # STEP 3: SQL Execution
            logger.info("Step 3: Executing SQL...")
            try:
                sql_results = self.db.execute_query(sql)
                logger.info(f"SQL returned {len(sql_results)} rows")
            except Exception as e:
                logger.error(f"SQL execution error: {str(e)}")
                sql_results = []
                # Create an error response
                error_answer = f"I encountered an error executing the query: {str(e)}. Please try rephrasing your question."
                self._add_message(conversation, "assistant", error_answer)
                return QueryResponse(
                    refined_question=refined_question,
                    sql=sql,
                    table=sql_results,
                    final_answer=error_answer,
                    conversation_id=conversation.conversation_id,
                )

            # STEP 4: Answer Composition (combined with polishing - 1 LLM call)
            logger.info("Step 4: Composing and polishing answer...")
            final_answer = self.llm.compose_answer(
                refined_question=refined_question,
                sql_results=sql_results,
            )
            logger.info("Answer composed successfully")

            # Store assistant response
            self._add_message(conversation, "assistant", final_answer)

            return QueryResponse(
                refined_question=refined_question,
                sql=sql,
                table=sql_results,
                final_answer=final_answer,
                conversation_id=conversation.conversation_id,
            )

        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}")
            error_message = f"I apologize, but I encountered an error processing your question. Please try again or rephrase your question. Error: {str(e)}"
            self._add_message(conversation, "assistant", error_message)
            raise

    def get_conversation_history(self, conversation_id: str) -> Optional[ConversationHistory]:
        """Get conversation history by ID."""
        return self.conversations.get(conversation_id)

    def clear_conversation(self, conversation_id: str) -> bool:
        """Clear a conversation from history."""
        if conversation_id in self.conversations:
            del self.conversations[conversation_id]
            return True
        return False


class SimplePipeline:
    """
    Simplified pipeline for when OpenAI is not available.
    Uses pattern matching and direct SQL for basic queries.
    """

    def __init__(self, database_service: Optional[DatabaseService] = None):
        self.db = database_service or get_database_service()
        self.conversations: Dict[str, ConversationHistory] = {}

    def _get_or_create_conversation(self, conversation_id: Optional[str]) -> ConversationHistory:
        if conversation_id and conversation_id in self.conversations:
            return self.conversations[conversation_id]

        new_id = conversation_id or str(uuid.uuid4())
        conversation = ConversationHistory(conversation_id=new_id, messages=[])
        self.conversations[new_id] = conversation
        return conversation

    def _pattern_to_sql(self, question: str) -> tuple[str, str]:
        """
        Convert common question patterns to SQL.
        Returns (refined_question, sql)
        """
        question_lower = question.lower()

        # Today's sales
        if "today" in question_lower and ("sale" in question_lower or "revenue" in question_lower):
            return (
                "What is the total sales amount for today?",
                """SELECT SUM(amount) as total_sales
                   FROM sales
                   WHERE status = 'COMPLETED'
                   AND order_date = date('now')"""
            )

        # Total sales (general)
        if "total" in question_lower and "sale" in question_lower:
            return (
                "What is the total sales amount?",
                """SELECT SUM(amount) as total_sales
                   FROM sales
                   WHERE status = 'COMPLETED'"""
            )

        # Sales by region
        if "region" in question_lower and "sale" in question_lower:
            return (
                "What are the total sales by region?",
                """SELECT r.name as region, SUM(s.amount) as total_sales
                   FROM sales s
                   JOIN regions r ON s.region_id = r.id
                   WHERE s.status = 'COMPLETED'
                   GROUP BY r.name
                   ORDER BY total_sales DESC"""
            )

        # Sales by product
        if "product" in question_lower and "sale" in question_lower:
            return (
                "What are the top selling products?",
                """SELECT p.name as product, p.category, SUM(s.amount) as total_sales
                   FROM sales s
                   JOIN products p ON s.product_id = p.id
                   WHERE s.status = 'COMPLETED'
                   GROUP BY p.name, p.category
                   ORDER BY total_sales DESC
                   LIMIT 10"""
            )

        # Order count
        if "order" in question_lower and ("count" in question_lower or "how many" in question_lower):
            return (
                "How many orders have been placed?",
                """SELECT COUNT(*) as order_count
                   FROM sales
                   WHERE status = 'COMPLETED'"""
            )

        # Default: total sales
        return (
            "What is the total sales amount?",
            """SELECT SUM(amount) as total_sales
               FROM sales
               WHERE status = 'COMPLETED'"""
        )

    def process_query(self, question: str, conversation_id: Optional[str] = None) -> QueryResponse:
        """Process query using pattern matching (no LLM required)."""
        conversation = self._get_or_create_conversation(conversation_id)

        refined_question, sql = self._pattern_to_sql(question)

        try:
            results = self.db.execute_query(sql)

            # Format simple answer
            if results and len(results) > 0:
                if len(results) == 1:
                    # Single result
                    result = results[0]
                    values = list(result.values())
                    if values and values[0] is not None:
                        answer = f"The result is: {values[0]:,.2f} BDT" if isinstance(values[0], (int, float)) else f"The result is: {values[0]}"
                    else:
                        answer = "No data found for this query."
                else:
                    # Multiple results
                    answer = "Results:\n"
                    for row in results[:5]:
                        row_str = ", ".join(f"{k}: {v}" for k, v in row.items())
                        answer += f"- {row_str}\n"
            else:
                answer = "No data found for this query."

            return QueryResponse(
                refined_question=refined_question,
                sql=sql,
                table=results,
                final_answer=answer,
                conversation_id=conversation.conversation_id,
            )
        except Exception as e:
            return QueryResponse(
                refined_question=refined_question,
                sql=sql,
                table=[],
                final_answer=f"Error: {str(e)}",
                conversation_id=conversation.conversation_id,
            )


# Singleton instances
_rag_pipeline: Optional[RAGPipeline] = None
_simple_pipeline: Optional[SimplePipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    global _rag_pipeline
    if _rag_pipeline is None:
        _rag_pipeline = RAGPipeline()
    return _rag_pipeline


def get_simple_pipeline() -> SimplePipeline:
    global _simple_pipeline
    if _simple_pipeline is None:
        _simple_pipeline = SimplePipeline()
    return _simple_pipeline
