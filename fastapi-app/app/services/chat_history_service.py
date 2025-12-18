"""
Chat History Service - Manages persistent storage of chat sessions.
Stores conversation metadata and allows retrieval of recent chat history.
"""

import sqlite3
import json
from typing import List, Optional
from datetime import datetime, timedelta
import logging

from app.models.schemas import ChatSession, ChatMessage, ConversationHistory

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """Service for managing chat history persistence."""

    def __init__(self, db_path: str = "./chat_history.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        """Get a database connection."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize the chat history database tables."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Create sessions table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_sessions (
                conversation_id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                first_question TEXT,
                created_at TIMESTAMP NOT NULL,
                updated_at TIMESTAMP NOT NULL,
                message_count INTEGER DEFAULT 0
            )
        ''')

        # Create messages table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS chat_messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP NOT NULL,
                sql_query TEXT,
                table_data TEXT,
                refined_question TEXT,
                FOREIGN KEY (conversation_id) REFERENCES chat_sessions(conversation_id)
            )
        ''')

        # Create index for faster queries
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_messages_conversation
            ON chat_messages(conversation_id)
        ''')

        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_sessions_updated
            ON chat_sessions(updated_at DESC)
        ''')

        conn.commit()
        conn.close()
        logger.info("Chat history database initialized")

    def create_or_update_session(
        self,
        conversation_id: str,
        first_question: Optional[str] = None
    ) -> ChatSession:
        """Create a new session or update an existing one."""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now()

        # Check if session exists
        cursor.execute(
            "SELECT * FROM chat_sessions WHERE conversation_id = ?",
            (conversation_id,)
        )
        existing = cursor.fetchone()

        if existing:
            # Update existing session
            cursor.execute('''
                UPDATE chat_sessions
                SET updated_at = ?,
                    message_count = message_count + 1
                WHERE conversation_id = ?
            ''', (now, conversation_id))

            session = ChatSession(
                conversation_id=conversation_id,
                title=existing['title'],
                first_question=existing['first_question'],
                created_at=datetime.fromisoformat(existing['created_at']),
                updated_at=now,
                message_count=existing['message_count'] + 1
            )
        else:
            # Create new session
            title = self._generate_title(first_question) if first_question else "New Chat"

            cursor.execute('''
                INSERT INTO chat_sessions
                (conversation_id, title, first_question, created_at, updated_at, message_count)
                VALUES (?, ?, ?, ?, ?, 1)
            ''', (conversation_id, title, first_question, now, now))

            session = ChatSession(
                conversation_id=conversation_id,
                title=title,
                first_question=first_question,
                created_at=now,
                updated_at=now,
                message_count=1
            )

        conn.commit()
        conn.close()
        return session

    def _generate_title(self, question: str) -> str:
        """Generate a title from the first question."""
        if not question:
            return "New Chat"
        # Truncate long questions
        title = question.strip()
        if len(title) > 50:
            title = title[:47] + "..."
        return title

    def save_message(
        self,
        conversation_id: str,
        role: str,
        content: str,
        sql_query: Optional[str] = None,
        table_data: Optional[List[dict]] = None,
        refined_question: Optional[str] = None
    ):
        """Save a message to the chat history."""
        conn = self._get_connection()
        cursor = conn.cursor()

        now = datetime.now()
        table_json = json.dumps(table_data) if table_data else None

        cursor.execute('''
            INSERT INTO chat_messages
            (conversation_id, role, content, timestamp, sql_query, table_data, refined_question)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (conversation_id, role, content, now, sql_query, table_json, refined_question))

        # Update session's updated_at and message_count
        cursor.execute('''
            UPDATE chat_sessions
            SET updated_at = ?, message_count = message_count + 1
            WHERE conversation_id = ?
        ''', (now, conversation_id))

        conn.commit()
        conn.close()

    def get_sessions(self, days: int = 1) -> List[ChatSession]:
        """Get chat sessions from the last N days."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cutoff = datetime.now() - timedelta(days=days)

        cursor.execute('''
            SELECT * FROM chat_sessions
            WHERE updated_at >= ?
            ORDER BY updated_at DESC
        ''', (cutoff,))

        rows = cursor.fetchall()
        conn.close()

        sessions = []
        for row in rows:
            sessions.append(ChatSession(
                conversation_id=row['conversation_id'],
                title=row['title'],
                first_question=row['first_question'],
                created_at=datetime.fromisoformat(row['created_at']),
                updated_at=datetime.fromisoformat(row['updated_at']),
                message_count=row['message_count']
            ))

        return sessions

    def get_session_messages(self, conversation_id: str) -> List[dict]:
        """Get all messages for a specific session."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            SELECT * FROM chat_messages
            WHERE conversation_id = ?
            ORDER BY timestamp ASC
        ''', (conversation_id,))

        rows = cursor.fetchall()
        conn.close()

        messages = []
        for row in rows:
            message = {
                'role': row['role'],
                'content': row['content'],
                'timestamp': row['timestamp'],
                'sql': row['sql_query'],
                'refined_question': row['refined_question'],
            }
            if row['table_data']:
                message['table'] = json.loads(row['table_data'])
            messages.append(message)

        return messages

    def delete_session(self, conversation_id: str) -> bool:
        """Delete a session and all its messages."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Delete messages first
        cursor.execute(
            "DELETE FROM chat_messages WHERE conversation_id = ?",
            (conversation_id,)
        )

        # Delete session
        cursor.execute(
            "DELETE FROM chat_sessions WHERE conversation_id = ?",
            (conversation_id,)
        )

        deleted = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return deleted

    def update_session_title(self, conversation_id: str, title: str) -> bool:
        """Update the title of a session."""
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute('''
            UPDATE chat_sessions
            SET title = ?
            WHERE conversation_id = ?
        ''', (title, conversation_id))

        updated = cursor.rowcount > 0
        conn.commit()
        conn.close()

        return updated


# Singleton instance
_chat_history_service: Optional[ChatHistoryService] = None


def get_chat_history_service() -> ChatHistoryService:
    """Get the singleton chat history service instance."""
    global _chat_history_service
    if _chat_history_service is None:
        _chat_history_service = ChatHistoryService()
    return _chat_history_service
