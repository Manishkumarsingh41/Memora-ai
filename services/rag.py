import os
from typing import Any, Dict, List, Optional, Tuple

from config import get_settings
from logging_config import get_logger


settings = get_settings()
logger = get_logger("rag")

_chroma_client: Optional[Any] = None
_embedder: Optional[Any] = None
COLLECTION_NAME = "memora_docs"


def _get_chroma_client() -> Any:
	global _chroma_client
	if _chroma_client is None:
		import chromadb
		from chromadb.config import Settings as ChromaSettings

		os.makedirs(settings.chroma_db_path, exist_ok=True)
		_chroma_client = chromadb.PersistentClient(
			path=settings.chroma_db_path,
			settings=ChromaSettings(anonymized_telemetry=False, allow_reset=True),
		)
	return _chroma_client


def _get_embedder() -> Any:
	global _embedder
	if _embedder is None:
		from sentence_transformers import SentenceTransformer

		_embedder = SentenceTransformer("all-MiniLM-L6-v2")
	return _embedder


def _get_collection():
	client = _get_chroma_client()
	return client.get_or_create_collection(name=COLLECTION_NAME)


def extract_pdf_chunks(pdf_path: str, chunk_size: int = 500) -> List[Tuple[str, int]]:
	import fitz

	chunks: List[Tuple[str, int]] = []
	step = max(1, chunk_size - 50)
	try:
		doc = fitz.open(pdf_path)
		for page_num, page in enumerate(doc, start=1):
			text = (page.get_text("text") or "").strip()
			if not text:
				continue
			words = text.split()
			for i in range(0, len(words), step):
				chunk = " ".join(words[i : i + chunk_size]).strip()
				if chunk:
					chunks.append((chunk, page_num))
		doc.close()
	except Exception as exc:
		logger.error("PDF extraction failed: %s", exc)
	return chunks


def index_pdf(user_id: str, file_name: str, pdf_path: str) -> int:
	chunks = extract_pdf_chunks(pdf_path)
	if not chunks:
		return 0

	embedder = _get_embedder()
	collection = _get_collection()
	total = 0

	for start in range(0, len(chunks), 100):
		batch = chunks[start : start + 100]
		texts = [text for text, _ in batch]
		pages = [page for _, page in batch]
		embeddings = embedder.encode(texts, convert_to_numpy=True).tolist()
		metadatas = [
			{
				"user_id": user_id,
				"file_name": file_name,
				"page": int(page),
			}
			for page in pages
		]
		ids = [f"{user_id}::{file_name}::chunk_{start + idx}" for idx in range(len(batch))]
		collection.upsert(
			ids=ids,
			embeddings=embeddings,
			documents=texts,
			metadatas=metadatas,
		)
		total += len(batch)

	return total


def query_documents(user_id: str, query: str, top_k: int = 5) -> List[Dict]:
	try:
		collection = _get_collection()
		embedder = _get_embedder()
		query_embedding = embedder.encode([query], convert_to_numpy=True).tolist()[0]
		results = collection.query(
			query_embeddings=[query_embedding],
			n_results=top_k,
			where={"user_id": user_id},
		)
		docs = results.get("documents", [[]])[0]
		metas = results.get("metadatas", [[]])[0]
		dists = results.get("distances", [[]])[0]

		formatted: List[Dict] = []
		for idx, text in enumerate(docs):
			meta = metas[idx] if idx < len(metas) else {}
			distance = dists[idx] if idx < len(dists) else 0.0
			formatted.append(
				{
					"text": text,
					"file_name": meta.get("file_name", ""),
					"page": int(meta.get("page", 0)),
					"distance": float(distance),
				}
			)
		return formatted
	except Exception as exc:
		logger.error("RAG query failed: %s", exc)
		return []


def delete_user_docs(user_id: str, file_name: str) -> None:
	try:
		collection = _get_collection()
		collection.delete(where={"$and": [{"user_id": user_id}, {"file_name": file_name}]})
	except Exception as exc:
		logger.warning("Delete user docs failed for %s/%s: %s", user_id, file_name, exc)


def delete_user_all_docs(user_id: str) -> None:
	try:
		collection = _get_collection()
		collection.delete(where={"user_id": user_id})
	except Exception as exc:
		logger.warning("Delete all docs failed for %s: %s", user_id, exc)

