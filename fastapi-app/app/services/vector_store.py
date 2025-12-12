"""
Vector Store Service using ChromaDB for storing and retrieving:
- Data dictionary (table & column descriptions)
- Metric definitions
- Business rules
- Documentation
"""

import chromadb
from typing import List, Dict, Optional, Any
import logging
import json
import os

from app.config import get_settings

logger = logging.getLogger(__name__)


class VectorStoreService:
    def __init__(self, persist_directory: Optional[str] = None):
        settings = get_settings()
        self.persist_directory = persist_directory or settings.chroma_persist_directory

        # Ensure directory exists
        os.makedirs(self.persist_directory, exist_ok=True)

        # Initialize ChromaDB client with persistent storage
        self.client = chromadb.PersistentClient(path=self.persist_directory)

        # Initialize collections
        self._init_collections()

    def _init_collections(self):
        """Initialize all required collections."""
        # Collection for data dictionary (tables and columns)
        self.data_dictionary = self.client.get_or_create_collection(
            name="data_dictionary",
            metadata={"description": "Table and column descriptions"}
        )

        # Collection for metric definitions
        self.metrics = self.client.get_or_create_collection(
            name="metrics",
            metadata={"description": "Business metric definitions and formulas"}
        )

        # Collection for business rules
        self.business_rules = self.client.get_or_create_collection(
            name="business_rules",
            metadata={"description": "Business rules and conditions"}
        )

        # Collection for documentation
        self.documentation = self.client.get_or_create_collection(
            name="documentation",
            metadata={"description": "General documentation and notes"}
        )

    def add_data_dictionary(self, items: List[Dict[str, Any]]):
        """
        Add data dictionary items (table/column descriptions).

        Args:
            items: List of dicts with keys: id, content, metadata
        """
        if not items:
            return

        ids = [item["id"] for item in items]
        documents = [item["content"] for item in items]
        metadatas = [item.get("metadata", {}) for item in items]

        self.data_dictionary.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(items)} items to data dictionary")

    def add_metrics(self, items: List[Dict[str, Any]]):
        """
        Add metric definitions.

        Args:
            items: List of dicts with keys: id, content, metadata
        """
        if not items:
            return

        ids = [item["id"] for item in items]
        documents = [item["content"] for item in items]
        metadatas = [item.get("metadata", {}) for item in items]

        self.metrics.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(items)} metric definitions")

    def add_business_rules(self, items: List[Dict[str, Any]]):
        """
        Add business rules.

        Args:
            items: List of dicts with keys: id, content, metadata
        """
        if not items:
            return

        ids = [item["id"] for item in items]
        documents = [item["content"] for item in items]
        metadatas = [item.get("metadata", {}) for item in items]

        self.business_rules.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(items)} business rules")

    def add_documentation(self, items: List[Dict[str, Any]]):
        """
        Add documentation items.

        Args:
            items: List of dicts with keys: id, content, metadata
        """
        if not items:
            return

        ids = [item["id"] for item in items]
        documents = [item["content"] for item in items]
        metadatas = [item.get("metadata", {}) for item in items]

        self.documentation.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )
        logger.info(f"Added {len(items)} documentation items")

    def search(
        self,
        query: str,
        top_k: int = 5,
        collections: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Search across specified collections for relevant context.

        Args:
            query: The search query
            top_k: Number of results per collection
            collections: List of collection names to search (default: all)

        Returns:
            List of relevant context items with scores
        """
        if collections is None:
            collections = ["data_dictionary", "metrics", "business_rules", "documentation"]

        results = []

        collection_map = {
            "data_dictionary": self.data_dictionary,
            "metrics": self.metrics,
            "business_rules": self.business_rules,
            "documentation": self.documentation,
        }

        for collection_name in collections:
            if collection_name not in collection_map:
                continue

            collection = collection_map[collection_name]

            try:
                # Check if collection has documents
                if collection.count() == 0:
                    continue

                search_results = collection.query(
                    query_texts=[query],
                    n_results=min(top_k, collection.count()),
                )

                if search_results and search_results["documents"]:
                    for i, doc in enumerate(search_results["documents"][0]):
                        results.append({
                            "content": doc,
                            "collection": collection_name,
                            "metadata": search_results["metadatas"][0][i] if search_results["metadatas"] else {},
                            "distance": search_results["distances"][0][i] if search_results.get("distances") else None,
                        })
            except Exception as e:
                logger.error(f"Error searching {collection_name}: {str(e)}")

        # Sort by distance (lower is better)
        results.sort(key=lambda x: x.get("distance", float("inf")) if x.get("distance") is not None else float("inf"))

        return results[:top_k * 2]  # Return top results across all collections

    def get_all_context(self, query: str, top_k: int = 5) -> str:
        """
        Get all relevant context as a formatted string.

        Args:
            query: The search query
            top_k: Number of results

        Returns:
            Formatted context string for LLM
        """
        results = self.search(query, top_k)

        if not results:
            return "No relevant context found."

        context_parts = []

        # Group by collection type
        by_collection = {}
        for item in results:
            collection = item["collection"]
            if collection not in by_collection:
                by_collection[collection] = []
            by_collection[collection].append(item)

        # Format each section
        section_titles = {
            "data_dictionary": "DATA DICTIONARY (Tables & Columns)",
            "metrics": "METRIC DEFINITIONS",
            "business_rules": "BUSINESS RULES",
            "documentation": "DOCUMENTATION",
        }

        for collection, items in by_collection.items():
            title = section_titles.get(collection, collection.upper())
            context_parts.append(f"\n=== {title} ===")
            for item in items:
                context_parts.append(f"\n{item['content']}")

        return "\n".join(context_parts)

    def clear_all(self):
        """Clear all collections."""
        try:
            self.client.delete_collection("data_dictionary")
        except Exception:
            pass
        try:
            self.client.delete_collection("metrics")
        except Exception:
            pass
        try:
            self.client.delete_collection("business_rules")
        except Exception:
            pass
        try:
            self.client.delete_collection("documentation")
        except Exception:
            pass

        self._init_collections()
        logger.info("All collections cleared")


# Singleton instance
_vector_store: Optional[VectorStoreService] = None


def get_vector_store(persist_directory: Optional[str] = None) -> VectorStoreService:
    global _vector_store
    if _vector_store is None:
        _vector_store = VectorStoreService(persist_directory)
    return _vector_store
