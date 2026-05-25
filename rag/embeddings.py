"""
rag/embeddings.py

ChromaDB vector store + sentence-transformers embeddings for GenEV RAG.

Functions
---------
- build_index()     — load knowledge base, chunk, embed, store in ChromaDB
- load_index()      — load existing ChromaDB collection
- retrieve()        — semantic search over knowledge base
- get_or_build()    — load if exists, build if not (main entry point)
"""

import os
import re
from pathlib import Path
from typing import List

import chromadb
from chromadb.utils import embedding_functions
from sentence_transformers import SentenceTransformer

from config import CHROMA_PERSIST_DIR, RAG_CHUNK_SIZE, RAG_CHUNK_OVERLAP, RAG_TOP_K


# ─────────────────────────────────────────────────────────────────────────────
# Constants
# ─────────────────────────────────────────────────────────────────────────────

KNOWLEDGE_BASE_DIR = Path("rag/knowledge_base")
COLLECTION_NAME    = "genev_knowledge"
EMBEDDING_MODEL    = "all-MiniLM-L6-v2"   # fast, lightweight, good quality


# ─────────────────────────────────────────────────────────────────────────────
# Embedding model (singleton)
# ─────────────────────────────────────────────────────────────────────────────

_model: SentenceTransformer = None


def _get_model() -> SentenceTransformer:
    """Load sentence transformer model (cached after first load)."""
    global _model
    if _model is None:
        print("[embeddings] Loading sentence transformer model...")
        _model = SentenceTransformer(EMBEDDING_MODEL)
        print("[embeddings] Model loaded.")
    return _model


# ─────────────────────────────────────────────────────────────────────────────
# ChromaDB client (singleton)
# ─────────────────────────────────────────────────────────────────────────────

_chroma_client: chromadb.PersistentClient = None


def _get_chroma_client() -> chromadb.PersistentClient:
    """Get or create ChromaDB persistent client."""
    global _chroma_client
    if _chroma_client is None:
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        _chroma_client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
    return _chroma_client


# ─────────────────────────────────────────────────────────────────────────────
# Document loading
# ─────────────────────────────────────────────────────────────────────────────

def _load_knowledge_files() -> list[dict]:
    """
    Load all .txt files from knowledge base directory.

    Returns
    -------
    List of dicts with keys: text, source, filename
    """
    documents = []

    if not KNOWLEDGE_BASE_DIR.exists():
        print(f"[embeddings] Knowledge base dir not found: {KNOWLEDGE_BASE_DIR}")
        return documents

    for filepath in sorted(KNOWLEDGE_BASE_DIR.glob("*.txt")):
        try:
            text = filepath.read_text(encoding="utf-8")
            documents.append({
                "text":     text,
                "source":   filepath.stem,
                "filename": filepath.name,
            })
            print(f"[embeddings] Loaded: {filepath.name} ({len(text)} chars)")
        except Exception as e:
            print(f"[embeddings] Failed to load {filepath.name}: {e}")

    return documents


# ─────────────────────────────────────────────────────────────────────────────
# Text chunking
# ─────────────────────────────────────────────────────────────────────────────

def _chunk_text(
    text: str,
    source: str,
    chunk_size: int = RAG_CHUNK_SIZE,
    overlap: int = RAG_CHUNK_OVERLAP,
) -> list[dict]:
    """
    Split text into overlapping chunks for embedding.

    Strategy
    --------
    1. Split on section headers (=== lines) first
    2. Then split long sections by sentence
    3. Apply overlap between chunks

    Returns
    -------
    List of dicts with keys: text, source, chunk_id
    """
    chunks = []

    # Split on major section dividers first
    sections = re.split(r"={3,}", text)

    for section in sections:
        section = section.strip()
        if not section or len(section) < 50:
            continue

        # If section is short enough, keep as one chunk
        if len(section) <= chunk_size:
            chunks.append({
                "text":     section,
                "source":   source,
                "chunk_id": f"{source}_{len(chunks)}",
            })
            continue

        # Split longer sections into overlapping word-based chunks
        words  = section.split()
        start  = 0
        words_per_chunk = chunk_size // 5  # ~5 chars per word average
        overlap_words   = overlap // 5

        while start < len(words):
            end        = min(start + words_per_chunk, len(words))
            chunk_text = " ".join(words[start:end])

            if len(chunk_text.strip()) > 30:
                chunks.append({
                    "text":     chunk_text,
                    "source":   source,
                    "chunk_id": f"{source}_{len(chunks)}",
                })

            if end == len(words):
                break
            start = end - overlap_words

    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Build index
# ─────────────────────────────────────────────────────────────────────────────

def build_index() -> chromadb.Collection:
    """
    Load knowledge base files, chunk them, embed, and store in ChromaDB.
    Returns the ChromaDB collection.
    """
    print("[embeddings] Building knowledge base index...")

    client     = _get_chroma_client()
    model      = _get_model()
    documents  = _load_knowledge_files()

    if not documents:
        raise ValueError("No knowledge base files found. Check rag/knowledge_base/")

    # Delete existing collection if rebuilding
    try:
        client.delete_collection(COLLECTION_NAME)
        print(f"[embeddings] Deleted existing collection: {COLLECTION_NAME}")
    except Exception:
        pass

    # Create fresh collection
    collection = client.create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    # Process all documents
    all_chunks = []
    for doc in documents:
        chunks = _chunk_text(doc["text"], doc["source"])
        all_chunks.extend(chunks)
        print(f"[embeddings] {doc['filename']}: {len(chunks)} chunks")

    print(f"[embeddings] Total chunks: {len(all_chunks)}")

    # Generate embeddings in batches
    batch_size = 50
    for i in range(0, len(all_chunks), batch_size):
        batch      = all_chunks[i:i + batch_size]
        texts      = [c["text"]     for c in batch]
        ids        = [c["chunk_id"] for c in batch]
        metadatas  = [{"source": c["source"]} for c in batch]

        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        collection.add(
            documents=texts,
            embeddings=embeddings,
            ids=ids,
            metadatas=metadatas,
        )

        print(f"[embeddings] Embedded batch {i // batch_size + 1}"
              f"/{(len(all_chunks) + batch_size - 1) // batch_size}")

    print(f"[embeddings] Index built successfully. "
          f"{collection.count()} chunks stored.")

    return collection


# ─────────────────────────────────────────────────────────────────────────────
# Load index
# ─────────────────────────────────────────────────────────────────────────────

def load_index() -> chromadb.Collection:
    """
    Load existing ChromaDB collection.
    Raises ValueError if collection doesn't exist.
    """
    client = _get_chroma_client()

    try:
        collection = client.get_collection(COLLECTION_NAME)
        print(f"[embeddings] Loaded existing index: "
              f"{collection.count()} chunks")
        return collection
    except Exception:
        raise ValueError(
            f"ChromaDB collection '{COLLECTION_NAME}' not found. "
            "Call build_index() first."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Get or build
# ─────────────────────────────────────────────────────────────────────────────

def get_or_build_index() -> chromadb.Collection:
    """
    Main entry point.
    Load existing index if available, build if not.
    """
    try:
        return load_index()
    except ValueError:
        print("[embeddings] No existing index found. Building...")
        return build_index()


# ─────────────────────────────────────────────────────────────────────────────
# Retrieve
# ─────────────────────────────────────────────────────────────────────────────

def retrieve(
    query: str,
    top_k: int = RAG_TOP_K,
    collection: chromadb.Collection = None,
) -> list[dict]:
    """
    Semantic search over the knowledge base.

    Parameters
    ----------
    query      : user's question or search text
    top_k      : number of chunks to retrieve
    collection : ChromaDB collection (loads if not provided)

    Returns
    -------
    List of dicts with keys: text, source, score
    """
    if collection is None:
        collection = get_or_build_index()

    model      = _get_model()
    query_emb  = model.encode([query]).tolist()

    results = collection.query(
        query_embeddings=query_emb,
        n_results=min(top_k, collection.count()),
        include=["documents", "metadatas", "distances"],
    )

    chunks = []
    if results["documents"] and results["documents"][0]:
        for text, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            # Convert cosine distance to similarity score
            similarity = round(1 - dist, 4)
            chunks.append({
                "text":   text,
                "source": meta.get("source", "unknown"),
                "score":  similarity,
            })

    # Sort by relevance score
    chunks.sort(key=lambda x: x["score"], reverse=True)
    return chunks


# ─────────────────────────────────────────────────────────────────────────────
# Rebuild index (utility function)
# ─────────────────────────────────────────────────────────────────────────────

def rebuild_index() -> chromadb.Collection:
    """Force rebuild the index from scratch."""
    print("[embeddings] Force rebuilding index...")
    return build_index()


# ─────────────────────────────────────────────────────────────────────────────
# Index stats (utility function)
# ─────────────────────────────────────────────────────────────────────────────

def get_index_stats() -> dict:
    """Return stats about the current index."""
    try:
        collection = load_index()
        return {
            "status":      "ready",
            "total_chunks": collection.count(),
            "collection":  COLLECTION_NAME,
            "model":       EMBEDDING_MODEL,
            "persist_dir": CHROMA_PERSIST_DIR,
        }
    except ValueError:
        return {
            "status":      "not_built",
            "total_chunks": 0,
            "collection":  COLLECTION_NAME,
            "model":       EMBEDDING_MODEL,
            "persist_dir": CHROMA_PERSIST_DIR,
        }