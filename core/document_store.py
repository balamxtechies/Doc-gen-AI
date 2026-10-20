import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any
from .config import DOCUMENTS_FILE

logger = logging.getLogger(__name__)

class DocumentStore:
    def __init__(self):
        self._ensure_file()

    def _ensure_file(self):
        if not DOCUMENTS_FILE.exists():
            with open(DOCUMENTS_FILE, "w", encoding="utf-8") as f:
                json.dump([], f, indent=2)

    def _load_all(self) -> List[Dict[str, Any]]:
        try:
            with open(DOCUMENTS_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading documents.json: {e}")
            return []

    def _save_all(self, docs: List[Dict[str, Any]]):
        with open(DOCUMENTS_FILE, "w", encoding="utf-8") as f:
            json.dump(docs, f, indent=2)

    def list_all(self) -> List[Dict[str, Any]]:
        return self._load_all()

    def get_by_slug(self, slug: str) -> Optional[Dict[str, Any]]:
        slug = slug.strip().lower()
        for doc in self._load_all():
            if doc.get("slug", "").lower() == slug:
                return doc
        return None

    def get_by_id(self, doc_id: str) -> Optional[Dict[str, Any]]:
        for doc in self._load_all():
            if doc.get("id") == doc_id:
                return doc
        return None

    def save(self, doc_data: Dict[str, Any]) -> Dict[str, Any]:
        docs = self._load_all()
        now = datetime.now().isoformat()
        
        # Check if updating existing by id or slug
        existing_idx = None
        for i, d in enumerate(docs):
            if d.get("id") == doc_data.get("id") or d.get("slug") == doc_data.get("slug"):
                existing_idx = i
                break

        if existing_idx is not None:
            doc_data["updated_at"] = now
            if "created_at" not in doc_data:
                doc_data["created_at"] = docs[existing_idx].get("created_at", now)
            doc_data["call_count"] = docs[existing_idx].get("call_count", 0)
            docs[existing_idx] = doc_data
        else:
            doc_data["created_at"] = now
            doc_data["updated_at"] = now
            doc_data["call_count"] = 0
            docs.append(doc_data)

        self._save_all(docs)
        return doc_data

    def delete(self, doc_id: str) -> bool:
        docs = self._load_all()
        new_docs = [d for d in docs if d.get("id") != doc_id and d.get("slug") != doc_id]
        if len(new_docs) < len(docs):
            self._save_all(new_docs)
            return True
        return False

    def increment_call_count(self, slug: str):
        docs = self._load_all()
        for doc in docs:
            if doc.get("slug", "").lower() == slug.lower():
                doc["call_count"] = doc.get("call_count", 0) + 1
                doc["last_called_at"] = datetime.now().isoformat()
                self._save_all(docs)
                break

doc_store = DocumentStore()
