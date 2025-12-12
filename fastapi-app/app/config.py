from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # LLM Provider Configuration
    # Options: "gemini", "groq", "ollama", "openai"
    llm_provider: str = "gemini"
    llm_api_key: str = ""
    llm_model: str = "gemini-1.5-flash"

    # Database
    database_url: str = "sqlite:///./analytics.db"

    # ChromaDB
    chroma_persist_directory: str = "./chroma_db"

    # Application
    app_env: str = "development"
    debug: bool = True

    # RAG Settings
    top_k_results: int = 5

    class Config:
        env_file = ".env"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
