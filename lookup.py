"""Robin's look-up (RAG): the corpus, the content store, and the search in it.

The steps follow the course slide "from question to answer":

    Ingestion pipeline    ingestion/ingest_source_docs.py: read the source documents, preprocess
                          them, cut them into chunks, turn every chunk into an embedding, and store
                          the lot. It runs separately from Robin, whenever the documents change.
    Question recognition  robin.py: a small model rewrites the customer's message into a search query
    Information retrieval search() below: the query becomes an embedding, and the store returns the
                          chunks whose embeddings are closest to it
    Response generation   robin.py: Robin answers with those chunks as its context

Robin never reads the source documents itself: it only searches the store.

**The corpus is source-docs/**, the same markdown the help centre publishes at /help. Editing a
document there and re-running the ingestion is the whole content workflow - no database admin, and
git keeps the history. Not every file has to be published: `help_pages.py` decides that separately,
so Robin can be given a document the website does not show.

**Two stores, one code path.** Which one is used depends only on whether DATABASE_URL is set:

    file (no DATABASE_URL)   data/chunks.json, committed to the repo. The student set-up: no
                             database to pay for, nothing to provision, and the chunks travel with
                             a clone. Searching 60-odd chunks in Python is instant.
    Postgres (DATABASE_URL)  pgvector, as before. The instructor-hosted Robin runs this, so the
                             course can point at a real vector database.

Both return the same `Hit` objects and produce the same trace, so an exercise about reading a
retrieval span works the same either way.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "text-embedding-3-small")
TABLE = "handbook_chunks"
MAX_RESULTS_CHOICES = (1, 3, 5)
DEFAULT_MAX_RESULTS = 3

SOURCE_DOCS = Path(__file__).parent / "source-docs"
CHUNKS_FILE = Path(__file__).parent / "data" / "chunks.json"

SCHEMA = f"""
CREATE EXTENSION IF NOT EXISTS vector;
CREATE TABLE IF NOT EXISTS {TABLE} (
    id               serial PRIMARY KEY,
    document_code    text NOT NULL,
    document_version text NOT NULL,
    chunk_number     integer NOT NULL,
    section          text NOT NULL,
    content          text NOT NULL,
    embedding        vector NOT NULL,
    embedding_model  text NOT NULL,
    ingested_at      timestamptz NOT NULL DEFAULT now()
);
"""


class LookUpError(Exception):
    """The look-up can't run: nothing ingested yet, or the store can't be reached."""


@dataclass
class Chunk:
    section: str           # the heading, for example "Delivery"
    text: str              # the heading plus everything under it
    document: str = ""     # which source document it came from, for example "handbook"
    version: str = "unknown"


@dataclass
class Hit:
    section: str
    text: str
    similarity: float      # 1 means the same meaning, 0 means unrelated
    document_version: str
    ingested_at: str
    document: str = ""


# ---------------------------------------------------------------------------
# The corpus (used by the ingestion pipeline)
# ---------------------------------------------------------------------------

def read_source_docs() -> list[tuple[str, str]]:
    """Every markdown file in source-docs/, as (document name, text), in a stable order.

    Adding a document to the corpus is adding a file here - which is also an exercise: drop in a
    document that disagrees with the others and watch which chunk the look-up returns.
    """
    return [(path.stem, path.read_text(encoding="utf-8")) for path in sorted(SOURCE_DOCS.glob("*.md"))]


def corpus_fingerprint(documents: list[tuple[str, str]]) -> str:
    """A short hash of the source documents, stored with the chunks.

    It answers a question a version number can't: were these chunks built from the text that is in
    the repo now? If someone edits a document and forgets to re-run the ingestion, the fingerprint
    stops matching and the trace says so.
    """
    digest = hashlib.sha256()
    for name, text in documents:
        digest.update(name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(text.replace("\r\n", "\n").encode("utf-8"))
        digest.update(b"\0")
    return digest.hexdigest()[:12]


def split_into_chunks(text: str, document: str = "", version: str = "unknown") -> list[Chunk]:
    """One chunk per '## ' section. The title and document information before the first section
    become a chunk of their own, called 'Document information'."""
    chunks: list[Chunk] = []
    section, lines = "Document information", []
    for line in text.splitlines():
        if line.startswith("## "):
            if "".join(lines).strip():
                chunks.append(Chunk(section, "\n".join(lines).strip(), document, version))
            section, lines = line[3:].strip(), [line]
        else:
            lines.append(line)
    if "".join(lines).strip():
        chunks.append(Chunk(section, "\n".join(lines).strip(), document, version))
    return chunks


def document_info(text: str) -> tuple[str, str]:
    """The document code and version from a document's metadata table, where it has one."""
    def field(name: str, default: str) -> str:
        match = re.search(rf"\*\*{name}\*\*\s*\|\s*([^|\n]+)", text)
        return match.group(1).strip() if match else default
    return field("Document code", "unknown"), field("Version", "unknown")


# ---------------------------------------------------------------------------
# Embeddings
# ---------------------------------------------------------------------------

def embed(client, texts: list[str]) -> tuple[list[list[float]], int]:
    """Turn texts into embeddings. Returns the embeddings and the number of tokens used.

    This is the one step that is not Claude: Anthropic has no embeddings model, so Robin uses
    OpenAI here and Claude everywhere else.
    """
    response = client.embeddings.create(model=EMBEDDING_MODEL, input=texts)
    usage = getattr(response, "usage", None)
    return [item.embedding for item in response.data], getattr(usage, "total_tokens", 0) or 0


def as_vector(embedding: list[float]) -> str:
    """pgvector's text format: [0.1,0.2,...]"""
    return "[" + ",".join(f"{x:.8f}" for x in embedding) + "]"


# ---------------------------------------------------------------------------
# Which store is in use
# ---------------------------------------------------------------------------

def using_database() -> bool:
    """Postgres when DATABASE_URL is set, the committed file otherwise."""
    return bool(os.getenv("DATABASE_URL", ""))


def store_name() -> str:
    return "postgres (pgvector)" if using_database() else f"file ({CHUNKS_FILE.name})"


def connect():
    url = os.getenv("DATABASE_URL", "")
    if not url:
        raise LookUpError("No content database: the environment variable DATABASE_URL is not set.")
    import psycopg  # only needed when the database store is used

    return psycopg.connect(url, connect_timeout=5)


# ---------------------------------------------------------------------------
# Storing
# ---------------------------------------------------------------------------

def store(chunks: list[Chunk], embeddings: list[list[float]], corpus_version: str) -> int:
    """Replace everything in the store with these chunks. One transaction, or one file write."""
    if using_database():
        return _store_postgres(chunks, embeddings)
    return _store_file(chunks, embeddings, corpus_version)


def _store_postgres(chunks: list[Chunk], embeddings: list[list[float]]) -> int:
    with connect() as conn, conn.transaction():
        conn.execute(SCHEMA)
        conn.execute(f"DELETE FROM {TABLE}")  # the ingestion always writes the whole corpus
        for number, (chunk, embedding) in enumerate(zip(chunks, embeddings), start=1):
            conn.execute(
                f"INSERT INTO {TABLE} (document_code, document_version, chunk_number, section, content, "
                f"embedding, embedding_model) VALUES (%s, %s, %s, %s, %s, %s::vector, %s)",
                (chunk.document or "unknown", chunk.version, number, chunk.section, chunk.text,
                 as_vector(embedding), EMBEDDING_MODEL),
            )
    return len(chunks)


def _store_file(chunks: list[Chunk], embeddings: list[list[float]], corpus_version: str) -> int:
    payload = {
        "embedding_model": EMBEDDING_MODEL,
        "corpus_version": corpus_version,
        "ingested_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "chunks": [
            {"document": chunk.document, "version": chunk.version, "section": chunk.section,
             "text": chunk.text, "embedding": [round(x, 6) for x in embedding]}
            for chunk, embedding in zip(chunks, embeddings)
        ],
    }
    CHUNKS_FILE.parent.mkdir(parents=True, exist_ok=True)
    CHUNKS_FILE.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return len(chunks)


# ---------------------------------------------------------------------------
# Searching
# ---------------------------------------------------------------------------

def _load_file() -> dict:
    if not CHUNKS_FILE.exists():
        raise LookUpError(f"Nothing to search: {CHUNKS_FILE.name} is missing. "
                          f"Run the ingestion (python ingestion/ingest_source_docs.py).")
    try:
        payload = json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise LookUpError(f"{CHUNKS_FILE.name} could not be read: {error}") from error
    if not payload.get("chunks"):
        raise LookUpError(f"{CHUNKS_FILE.name} holds no chunks. Run the ingestion again.")
    return payload


def _cosine(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    size = math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(y * y for y in b))
    return dot / size if size else 0.0


def search(query_embedding: list[float], limit: int) -> list[Hit]:
    """The chunks closest in meaning to the query."""
    if using_database():
        return _search_postgres(query_embedding, limit)
    return _search_file(query_embedding, limit)


def _search_file(query_embedding: list[float], limit: int) -> list[Hit]:
    payload = _load_file()
    ingested_at = payload.get("ingested_at", "unknown")
    scored = sorted(
        ((_cosine(query_embedding, chunk["embedding"]), chunk) for chunk in payload["chunks"]),
        key=lambda pair: pair[0], reverse=True,
    )
    return [Hit(chunk["section"], chunk["text"], float(score), chunk.get("version", "unknown"),
                ingested_at, chunk.get("document", ""))
            for score, chunk in scored[:limit]]


def _search_postgres(query_embedding: list[float], limit: int) -> list[Hit]:
    """Cosine distance, `<=>` in pgvector."""
    vector = as_vector(query_embedding)
    try:
        with connect() as conn:
            rows = conn.execute(
                f"SELECT section, content, 1 - (embedding <=> %s::vector) AS similarity, document_version, "
                f"ingested_at, document_code FROM {TABLE} ORDER BY embedding <=> %s::vector LIMIT %s",
                (vector, vector, limit),
            ).fetchall()
    except LookUpError:
        raise
    except Exception as error:
        if "does not exist" in str(error):
            raise LookUpError("The content database is empty: run the ingestion first "
                              "(Actions > \"Ingest the source documents\").") from error
        raise
    if not rows:
        raise LookUpError("The content database is empty: run the ingestion first "
                          "(Actions > \"Ingest the source documents\").")
    return [Hit(section, content, float(similarity), version, str(ingested_at), code)
            for section, content, similarity, version, ingested_at, code in rows]


def corpus_status() -> dict:
    """What the trace says about where the chunks came from, next to the hits themselves.

    `matches_source` is the useful one: False means somebody edited a document in source-docs/ and
    did not re-run the ingestion, so Robin is answering from text the repo no longer holds. The
    database store keeps no fingerprint, so there it is None rather than a guess.
    """
    status = {"store": store_name()}
    if using_database():
        status["matches_source"] = None
        return status
    try:
        payload = _load_file()
    except LookUpError:
        return status
    status["corpus_version"] = payload.get("corpus_version", "unknown")
    status["ingested_at"] = payload.get("ingested_at", "unknown")
    try:
        status["matches_source"] = payload.get("corpus_version") == corpus_fingerprint(read_source_docs())
    except OSError:
        status["matches_source"] = None
    return status


def list_chunks(numbers: int = 8) -> list[dict]:
    """Every chunk in the store, for the 'Content database' page: the text plus the first few
    numbers of its embedding, to show that a chunk really is text plus numbers."""
    if using_database():
        return _list_chunks_postgres(numbers)
    return _list_chunks_file(numbers)


def _list_chunks_file(numbers: int) -> list[dict]:
    try:
        payload = _load_file()
    except LookUpError:
        return []
    listed = []
    for number, chunk in enumerate(payload["chunks"], start=1):
        listed.append({"chunk": number, "section": chunk["section"], "text": chunk["text"],
                       "document_code": chunk.get("document", "unknown"),
                       "document_version": chunk.get("version", "unknown"),
                       "ingested_at": payload.get("ingested_at", "unknown"),
                       "embedding_model": payload.get("embedding_model", EMBEDDING_MODEL),
                       "dimensions": len(chunk["embedding"]),
                       "first_numbers": [round(float(x), 4) for x in chunk["embedding"][:numbers]]})
    return listed


def _list_chunks_postgres(numbers: int) -> list[dict]:
    try:
        with connect() as conn:
            rows = conn.execute(
                f"SELECT chunk_number, section, content, document_code, document_version, ingested_at, "
                f"embedding_model, vector_dims(embedding), embedding::text FROM {TABLE} "
                f"ORDER BY document_code, chunk_number"
            ).fetchall()
    except LookUpError:
        raise
    except Exception as error:
        if "does not exist" in str(error):
            return []
        raise
    chunks = []
    for number, section, content, code, version, ingested_at, model, dims, vector in rows:
        first = [round(float(x), 4) for x in vector.strip("[]").split(",")[:numbers]]
        chunks.append({"chunk": number, "section": section, "text": content, "document_code": code,
                       "document_version": version, "ingested_at": ingested_at.isoformat(timespec="seconds"),
                       "embedding_model": model, "dimensions": dims, "first_numbers": first})
    return chunks


# ---------------------------------------------------------------------------
# Settings and formatting (used by Robin)
# ---------------------------------------------------------------------------

def max_results(value) -> int:
    """The number of chunks to look up: 1, 3 or 5. Anything else becomes the default."""
    try:
        number = int(value)
    except (TypeError, ValueError):
        return DEFAULT_MAX_RESULTS
    return number if number in MAX_RESULTS_CHOICES else DEFAULT_MAX_RESULTS


def format_sources(hits: list[Hit]) -> str:
    """The chunks as Robin sees them in its system prompt.

    The document name travels with the section, because the corpus holds several documents and they
    do not always agree - which document a fact came from is part of the answer.
    """
    if not hits:
        return "(No sections were found.)"
    return "\n\n".join(f"### Section: {hit.section}" + (f" (from {hit.document})" if hit.document else "")
                       + f"\n{_without_heading(hit.text)}" for hit in hits)


def _without_heading(text: str) -> str:
    return re.sub(r"^## .*\n?", "", text, count=1).strip()
