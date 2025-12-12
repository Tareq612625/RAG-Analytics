"""
LLM Service - Handles all interactions with LLM providers.
Supports multiple FREE providers:
1. Google Gemini (Free tier - 15 req/min)
2. Groq (Free tier - Llama/Mixtral)
3. Ollama (Local - completely free)
4. OpenAI (Paid)

Optimized to use only 2 LLM calls per query (instead of 4) to stay within rate limits.
"""

import httpx
from typing import Optional
import json
import logging
import time

from app.config import get_settings

logger = logging.getLogger(__name__)


class LLMService:
    def __init__(self):
        settings = get_settings()
        self.provider = settings.llm_provider.lower()
        self.api_key = settings.llm_api_key
        self.model = settings.llm_model
        self.max_retries = 3
        self.retry_delay = 5  # seconds

        logger.info(f"Initializing LLM Service with provider: {self.provider}, model: {self.model}")

    def _call_gemini(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Call Google Gemini API (FREE tier available)."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent"

        headers = {"Content-Type": "application/json"}
        params = {"key": self.api_key}

        data = {
            "contents": [
                {
                    "parts": [
                        {"text": f"{system_prompt}\n\n{user_prompt}"}
                    ]
                }
            ],
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": 2000,
            }
        }

        response = httpx.post(url, headers=headers, params=params, json=data, timeout=60.0)
        response.raise_for_status()

        result = response.json()
        return result["candidates"][0]["content"]["parts"][0]["text"].strip()

    def _call_groq(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Call Groq API (FREE, very fast inference)."""
        url = "https://api.groq.com/openai/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": 2000,
        }

        response = httpx.post(url, headers=headers, json=data, timeout=60.0)
        response.raise_for_status()

        result = response.json()
        return result["choices"][0]["message"]["content"].strip()

    def _call_ollama(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Call local Ollama API (completely FREE, runs locally)."""
        url = "http://localhost:11434/api/generate"

        data = {
            "model": self.model,
            "prompt": f"{system_prompt}\n\n{user_prompt}",
            "stream": False,
            "options": {
                "temperature": temperature,
            }
        }

        response = httpx.post(url, json=data, timeout=120.0)
        response.raise_for_status()

        result = response.json()
        return result["response"].strip()

    def _call_openai(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Call OpenAI API (paid)."""
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key)
        response = client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=temperature,
            max_tokens=2000,
        )
        return response.choices[0].message.content.strip()

    def _call_llm(self, system_prompt: str, user_prompt: str, temperature: float = 0.3) -> str:
        """Make a call to the configured LLM provider with retry logic."""
        last_error = None

        for attempt in range(self.max_retries):
            try:
                if self.provider == "gemini":
                    return self._call_gemini(system_prompt, user_prompt, temperature)
                elif self.provider == "groq":
                    return self._call_groq(system_prompt, user_prompt, temperature)
                elif self.provider == "ollama":
                    return self._call_ollama(system_prompt, user_prompt, temperature)
                elif self.provider == "openai":
                    return self._call_openai(system_prompt, user_prompt, temperature)
                else:
                    raise ValueError(f"Unknown LLM provider: {self.provider}")

            except httpx.HTTPStatusError as e:
                last_error = e
                if e.response.status_code == 429:  # Rate limit
                    wait_time = self.retry_delay * (attempt + 1)
                    logger.warning(f"Rate limited. Waiting {wait_time}s before retry {attempt + 1}/{self.max_retries}")
                    time.sleep(wait_time)
                else:
                    logger.error(f"LLM API error ({self.provider}): {str(e)}")
                    raise
            except Exception as e:
                logger.error(f"LLM API error ({self.provider}): {str(e)}")
                raise

        # If we exhausted all retries
        logger.error(f"Failed after {self.max_retries} retries")
        raise last_error

    def generate_sql(self, question: str, context: str) -> tuple[str, str]:
        """
        STAGE 1: Generate SQL from question (combines refinement + SQL generation)
        Returns: (refined_question, sql_query)
        """
        system_prompt = """You are a SQL expert for a business analytics system. Your task is to:
1. First, refine the user's question into a clear business question
2. Then generate a safe, read-only SQL query to answer it
3. Use ONLY the tables and columns mentioned in the provided context
4. Apply all business rules and metric definitions from the context

STRICT RULES:
- ONLY use SELECT statements
- NEVER use INSERT, UPDATE, DELETE, DROP, ALTER, CREATE, TRUNCATE
- Use SQLite date functions: date('now'), date('now', '-1 day'), date('now', 'start of month')
- Always filter by status = 'COMPLETED' for sales/revenue calculations
- Use clear column aliases
- Use LIMIT 10 for list queries

OUTPUT FORMAT (exactly as shown):
REFINED: <the refined question>
SQL: <the SQL query>"""

        user_prompt = f"""CONTEXT:
{context}

USER QUESTION: {question}

Generate the refined question and SQL:"""

        response = self._call_llm(system_prompt, user_prompt, temperature=0.1)

        # Parse response
        refined_question = question  # default
        sql = ""

        lines = response.strip().split('\n')
        for i, line in enumerate(lines):
            if line.startswith('REFINED:'):
                refined_question = line[8:].strip()
            elif line.startswith('SQL:'):
                # Get SQL which may span multiple lines
                sql = line[4:].strip()
                # Append remaining lines as part of SQL
                sql += '\n' + '\n'.join(lines[i+1:])
                break

        # Clean up SQL
        sql = sql.strip()
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()

        return refined_question, sql

    def compose_answer(
        self,
        refined_question: str,
        sql_results: list
    ) -> str:
        """
        STAGE 2: Compose a polished answer from SQL results
        """
        system_prompt = """You are a business analyst assistant. Generate a clear, professional, business-friendly answer.

Guidelines:
- Use the exact numbers from the SQL results
- Format large numbers with comma separators (e.g., 12,45,000 BDT)
- Be concise but informative
- Highlight key insights, top performers, or trends
- Use BDT as the currency unit
- Do NOT show SQL or technical details
- Make the response conversational and easy to understand"""

        results_str = json.dumps(sql_results, indent=2, default=str)

        user_prompt = f"""QUESTION: {refined_question}

DATA:
{results_str}

Write a clear, professional answer:"""

        return self._call_llm(system_prompt, user_prompt, temperature=0.4)


# Singleton instance
_llm_service: Optional[LLMService] = None


def get_llm_service() -> LLMService:
    global _llm_service
    if _llm_service is None:
        _llm_service = LLMService()
    return _llm_service
