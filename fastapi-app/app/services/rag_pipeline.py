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
import re
from datetime import datetime

from app.services.llm_service import LLMService, get_llm_service
from app.services.vector_store import VectorStoreService, get_vector_store
from app.services.database_service import DatabaseService, get_database_service
from app.services.chat_history_service import ChatHistoryService, get_chat_history_service
from app.models.schemas import QueryResponse, ChatMessage, ConversationHistory

logger = logging.getLogger(__name__)


class RAGPipeline:
    # Keywords that indicate a data/analytics question
    DATA_KEYWORDS = [
        'sales', 'revenue', 'profit', 'order', 'customer', 'product', 'region',
        'total', 'sum', 'count', 'average', 'top', 'bottom', 'best', 'worst',
        'how many', 'how much', 'what is the', 'show me', 'list', 'give me',
        'compare', 'trend', 'growth', 'decline', 'increase', 'decrease',
        'monthly', 'daily', 'weekly', 'yearly', 'today', 'yesterday', 'this month',
        'last month', 'this year', 'last year', 'quarter', 'performance',
        'amount', 'quantity', 'price', 'cost', 'margin', 'discount',
        'category', 'status', 'pending', 'completed', 'cancelled'
    ]

    # Keywords/patterns that indicate conversational questions
    CONVERSATIONAL_PATTERNS = [
        'who are you', 'what are you', 'what can you do', 'how do you work',
        'hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening',
        'thank you', 'thanks', 'bye', 'goodbye', 'help me', 'what is your name',
        'introduce yourself', 'tell me about yourself', 'your name',
        'i am', 'my name is', 'call me', "i'm"
    ]

    # Keywords that indicate out-of-scope/general knowledge questions
    OUT_OF_SCOPE_PATTERNS = [
        'do you know about', 'tell me about', 'what is', 'who is', 'where is',
        'explain', 'define', 'meaning of', 'history of', 'how does', 'why does',
        'google', 'facebook', 'microsoft', 'amazon', 'apple', 'twitter', 'openai',
        'weather', 'news', 'politics', 'sports', 'movie', 'music', 'recipe',
        'programming', 'python', 'javascript', 'code', 'write a', 'create a',
        'translate', 'capital of', 'population of', 'president', 'prime minister'
    ]

    def __init__(
        self,
        llm_service: Optional[LLMService] = None,
        vector_store: Optional[VectorStoreService] = None,
        database_service: Optional[DatabaseService] = None,
        chat_history_service: Optional[ChatHistoryService] = None,
    ):
        self.llm = llm_service or get_llm_service()
        self.vector_store = vector_store or get_vector_store()
        self.db = database_service or get_database_service()
        self.chat_history = chat_history_service or get_chat_history_service()

        # Conversation history storage (in-memory for demo)
        self.conversations: Dict[str, ConversationHistory] = {}

    def _is_multi_question(self, question: str) -> bool:
        """
        Detect if the user is asking multiple questions at once.
        Returns True if multiple questions are detected.
        """
        # Check for bullet points or numbered lists
        lines = question.strip().split('\n')
        bullet_count = 0
        for line in lines:
            line = line.strip()
            # Check for bullet points (•, -, *, numbers)
            if re.match(r'^[\•\-\*\d\.]\s*.+', line):
                bullet_count += 1

        if bullet_count >= 2:
            return True

        # Check for multiple question marks
        if question.count('?') >= 2:
            return True

        return False

    def _extract_questions(self, text: str) -> List[str]:
        """
        Extract individual questions from multi-question input.
        Handles bullet points, numbered lists, and multiple question marks.
        """
        questions = []

        # First, check for bullet points or numbered lists
        lines = text.strip().split('\n')
        bullet_questions = []
        for line in lines:
            line = line.strip()
            # Match bullet points (•, -, *, numbers)
            match = re.match(r'^[\•\-\*]\s*(.+)', line)
            if match:
                bullet_questions.append(match.group(1).strip())
                continue
            # Match numbered lists (1., 2., etc.)
            match = re.match(r'^\d+[\.\)]\s*(.+)', line)
            if match:
                bullet_questions.append(match.group(1).strip())

        if len(bullet_questions) >= 2:
            return bullet_questions

        # Otherwise, split by question marks
        if text.count('?') >= 2:
            parts = text.split('?')
            for part in parts:
                part = part.strip()
                if part and len(part) > 3:  # Filter out very short fragments
                    questions.append(part + '?')
            return questions

        # Fallback: return the original text as a single question
        return [text.strip()]

    def _process_single_question(self, question: str) -> dict:
        """
        Process a single question through the RAG pipeline.
        Returns a dict with refined_question, sql, table, and answer.
        """
        # Check if this is a conversational query
        if self._is_conversational_query_single(question):
            response = self._get_conversational_response_single(question)
            return {
                "question": question,
                "refined_question": question,
                "sql": None,
                "table": [],
                "answer": response
            }

        try:
            # Context Retrieval
            context = self.vector_store.get_all_context(question)

            # SQL Generation
            refined_question, sql = self.llm.generate_sql(question, context)

            # SQL Execution
            try:
                sql_results = self.db.execute_query(sql)
            except Exception as e:
                logger.error(f"SQL execution error for '{question}': {str(e)}")
                return {
                    "question": question,
                    "refined_question": refined_question,
                    "sql": sql,
                    "table": [],
                    "answer": f"Error executing query: {str(e)}"
                }

            # Answer Composition
            final_answer = self.llm.compose_answer(
                refined_question=refined_question,
                sql_results=sql_results,
            )

            return {
                "question": question,
                "refined_question": refined_question,
                "sql": sql,
                "table": sql_results,
                "answer": final_answer
            }

        except Exception as e:
            logger.error(f"Pipeline error for '{question}': {str(e)}")
            return {
                "question": question,
                "refined_question": question,
                "sql": None,
                "table": [],
                "answer": f"Error processing question: {str(e)}"
            }

    def _is_conversational_query_single(self, question: str) -> bool:
        """
        Check if a single question is conversational (used for multi-question processing).
        Similar to _is_conversational_query but without multi-question check.
        """
        question_lower = question.lower().strip()

        # Check data keywords FIRST
        for keyword in self.DATA_KEYWORDS:
            if keyword in question_lower:
                return False

        # Check for out-of-scope/general knowledge questions
        for pattern in self.OUT_OF_SCOPE_PATTERNS:
            if pattern in question_lower:
                return True

        # Check conversational patterns
        for pattern in self.CONVERSATIONAL_PATTERNS:
            if pattern in question_lower:
                return True

        # If very short and no data keywords, likely conversational
        if len(question_lower.split()) <= 4:
            return True

        return False

    def _get_conversational_response_single(self, question: str) -> str:
        """Get conversational response for a single question (used in multi-question processing)."""
        question_lower = question.lower().strip()

        # Identity questions
        if any(p in question_lower for p in ['who are you', 'what are you', 'introduce yourself', 'tell me about yourself', 'what is your name', 'your name']):
            return "I'm your Analytics Assistant for business data queries."

        # Capability questions
        if any(p in question_lower for p in ['what can you do', 'how do you work', 'help me']):
            return "I can help you analyze sales, revenue, customers, products, and regional data."

        # Greetings
        if any(p in question_lower for p in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            return "Hello! How can I help you with your business data?"

        # Thanks
        if any(p in question_lower for p in ['thank you', 'thanks']):
            return "You're welcome!"

        # Goodbye
        if any(p in question_lower for p in ['bye', 'goodbye']):
            return "Goodbye!"

        # Out-of-scope
        for pattern in self.OUT_OF_SCOPE_PATTERNS:
            if pattern in question_lower:
                return "Sorry, I can only answer questions about your business data."

        return "I'm your Analytics Assistant for business data queries."

    def _is_conversational_query(self, question: str) -> bool:
        """
        Determine if a question is conversational (not requiring database access).
        Returns True for greetings, identity questions, help requests, out-of-scope questions, etc.
        """
        question_lower = question.lower().strip()

        # Check for multi-question input
        if self._is_multi_question(question):
            return True

        # IMPORTANT: Check data keywords FIRST - if it contains data keywords,
        # it's a data query regardless of other patterns
        for keyword in self.DATA_KEYWORDS:
            if keyword in question_lower:
                return False

        # Check for out-of-scope/general knowledge questions
        for pattern in self.OUT_OF_SCOPE_PATTERNS:
            if pattern in question_lower:
                return True

        # Check conversational patterns
        for pattern in self.CONVERSATIONAL_PATTERNS:
            if pattern in question_lower:
                return True

        # If very short and no data keywords, likely conversational
        if len(question_lower.split()) <= 4:
            return True

        return False

    def _get_conversational_response(self, question: str) -> str:
        """Generate a response for conversational queries without database access."""
        question_lower = question.lower().strip()

        # Multi-question input - this should not be called for multi-questions anymore
        # as they are handled separately in process_query
        if self._is_multi_question(question):
            # Fallback - should not reach here normally
            return "Processing multiple questions..."

        # Identity questions
        if any(p in question_lower for p in ['who are you', 'what are you', 'introduce yourself', 'tell me about yourself', 'what is your name', 'your name']):
            return (
                "I'm your Analytics Assistant! I help you explore and understand your business data "
                "through natural language questions. You can ask me about sales, revenue, customers, "
                "products, regional performance, and more. Just ask questions like 'What are the total sales?' "
                "or 'Show me the top customers' and I'll query the database and provide insights."
            )

        # Capability questions
        if any(p in question_lower for p in ['what can you do', 'how do you work', 'help me']):
            return (
                "I can help you analyze your business data! Here's what I can do:\n\n"
                "• Answer questions about sales, revenue, and profits\n"
                "• Show customer and product performance\n"
                "• Analyze regional data and trends\n"
                "• Compare time periods (today, this month, etc.)\n"
                "• Find top performers and identify patterns\n\n"
                "Try asking: 'What is the total sales?' or 'Show me sales by region'"
            )

        # Greetings
        if any(p in question_lower for p in ['hello', 'hi', 'hey', 'good morning', 'good afternoon', 'good evening']):
            return "Hello! I'm your Analytics Assistant. How can I help you explore your business data today?"

        # User introductions (i am X, my name is X, call me X, i'm X)
        intro_patterns = [
            r"(?:i am|i'm|my name is|call me)\s+(.+)",
        ]
        for pattern in intro_patterns:
            match = re.search(pattern, question_lower)
            if match:
                # Extract and capitalize the name
                name = match.group(1).strip().rstrip('.,!?')
                name = ' '.join(word.capitalize() for word in name.split())
                return f"Nice to meet you, {name}! I'm your Analytics Assistant. How can I help you explore your business data today?"

        # Thanks
        if any(p in question_lower for p in ['thank you', 'thanks']):
            return "You're welcome! Feel free to ask if you have more questions about your data."

        # Goodbye
        if any(p in question_lower for p in ['bye', 'goodbye']):
            return "Goodbye! Come back anytime you need help with your business analytics."

        # Out-of-scope / general knowledge questions
        for pattern in self.OUT_OF_SCOPE_PATTERNS:
            if pattern in question_lower:
                return (
                    "Sorry, I'm your Analytics Assistant and I can only help with questions about your business data. "
                    "I can't answer general knowledge questions.\n\n"
                    "Try asking questions like:\n"
                    "• 'What is the total sales?'\n"
                    "• 'Show me top customers'\n"
                    "• 'What are the sales by region?'"
                )

        # Default fallback
        return (
            "I'm your Analytics Assistant, designed to help you explore business data. "
            "Try asking questions about sales, customers, products, or regional performance!"
        )

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

        # Save to persistent chat history
        is_first_message = len(conversation.messages) == 1
        self.chat_history.create_or_update_session(
            conversation.conversation_id,
            first_question=question if is_first_message else None
        )
        self.chat_history.save_message(
            conversation.conversation_id,
            role="user",
            content=question
        )

        # Check for multiple questions first
        if self._is_multi_question(question):
            logger.info("Detected multiple questions - processing sequentially")
            questions = self._extract_questions(question)
            logger.info(f"Extracted {len(questions)} questions: {questions}")

            results = []
            all_tables = []
            all_sql = []

            for i, q in enumerate(questions):
                logger.info(f"Processing question {i+1}/{len(questions)}: {q}")
                result = self._process_single_question(q)
                results.append(result)
                if result["table"]:
                    all_tables.extend(result["table"])
                if result["sql"]:
                    all_sql.append(result["sql"])

            # Combine all answers into a formatted response
            combined_answer = "Here are the answers to your questions:\n\n"
            for i, result in enumerate(results):
                combined_answer += f"**Q{i+1}: {result['question']}**\n"
                combined_answer += f"{result['answer']}\n\n"

            # Combine SQL queries
            combined_sql = "\n\n---\n\n".join(all_sql) if all_sql else None

            self._add_message(conversation, "assistant", combined_answer)

            # Persist to chat history
            self.chat_history.save_message(
                conversation.conversation_id,
                role="assistant",
                content=combined_answer,
                sql_query=combined_sql,
                table_data=all_tables,
                refined_question=question
            )

            return QueryResponse(
                refined_question=question,
                sql=combined_sql,
                table=all_tables,
                final_answer=combined_answer,
                conversation_id=conversation.conversation_id,
            )

        # Check if this is a conversational query (not requiring database access)
        if self._is_conversational_query(question):
            logger.info("Detected conversational query - responding without database access")
            response = self._get_conversational_response(question)
            self._add_message(conversation, "assistant", response)

            # Persist to chat history
            self.chat_history.save_message(
                conversation.conversation_id,
                role="assistant",
                content=response
            )

            return QueryResponse(
                refined_question=question,
                sql=None,
                table=[],
                final_answer=response,
                conversation_id=conversation.conversation_id,
            )

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

            # Persist to chat history
            self.chat_history.save_message(
                conversation.conversation_id,
                role="assistant",
                content=final_answer,
                sql_query=sql,
                table_data=sql_results,
                refined_question=refined_question
            )

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
