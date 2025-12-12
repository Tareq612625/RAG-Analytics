from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from typing import List, Dict, Any, Optional
from contextlib import contextmanager
import logging

from app.config import get_settings
from app.models.database import Base

logger = logging.getLogger(__name__)


class DatabaseService:
    def __init__(self, database_url: Optional[str] = None):
        settings = get_settings()
        self.database_url = database_url or settings.database_url

        # Use SQLite for development/demo if PostgreSQL not available
        if "sqlite" in self.database_url:
            self.engine = create_engine(
                self.database_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
            )
        else:
            self.engine = create_engine(self.database_url)

        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)

    def create_tables(self):
        """Create all database tables."""
        Base.metadata.create_all(bind=self.engine)
        logger.info("Database tables created successfully")

    @contextmanager
    def get_session(self) -> Session:
        """Get a database session."""
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            raise e
        finally:
            session.close()

    def execute_query(self, sql: str) -> List[Dict[str, Any]]:
        """
        Execute a read-only SQL query and return results as list of dictionaries.
        Only allows SELECT statements for security.
        """
        # Security check: Only allow SELECT statements
        sql_upper = sql.strip().upper()
        if not sql_upper.startswith("SELECT"):
            raise ValueError("Only SELECT queries are allowed for security reasons")

        # Block dangerous keywords
        dangerous_keywords = ["INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE", "EXEC", "EXECUTE"]
        for keyword in dangerous_keywords:
            if keyword in sql_upper:
                raise ValueError(f"Query contains forbidden keyword: {keyword}")

        try:
            with self.get_session() as session:
                result = session.execute(text(sql))
                columns = result.keys()
                rows = result.fetchall()
                return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            logger.error(f"Query execution error: {str(e)}")
            raise

    def get_table_schema(self) -> Dict[str, List[Dict[str, str]]]:
        """Get schema information for all tables."""
        schema_info = {}

        # Get table names using SQLAlchemy inspection
        from sqlalchemy import inspect
        inspector = inspect(self.engine)

        for table_name in inspector.get_table_names():
            columns = []
            for column in inspector.get_columns(table_name):
                columns.append({
                    "name": column["name"],
                    "type": str(column["type"]),
                    "nullable": column.get("nullable", True),
                })
            schema_info[table_name] = columns

        return schema_info


# Singleton instance
_db_service: Optional[DatabaseService] = None


def get_database_service(database_url: Optional[str] = None) -> DatabaseService:
    global _db_service
    if _db_service is None:
        _db_service = DatabaseService(database_url)
    return _db_service
