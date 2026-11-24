"""The ingestion pipeline: put the Nest & Co source documents into Robin's content store.

This is the bottom row of the course slide "from question to answer":

    1. Read the documents     every markdown file in source-docs/ - the same files the help centre
                              publishes at /help
    2. Preprocess             tidy the text: line endings, trailing spaces, extra blank lines
    3. Chunk                  cut each document into chunks: one per section (## heading)
    4. Embed                  turn every chunk into an embedding with OpenAI
    5. Store                  replace everything in the content store

It runs separately from Robin, whenever a document changes. Robin itself only searches the store.
The run shows up in Langfuse as one trace, "Ingestion - source documents", in the environment
"ingestion".

Where it stores depends on DATABASE_URL (see lookup.py): Postgres with pgvector when it is set,
and the committed file data/chunks.json when it is not. The file is the student set-up - commit it
and a clone can search straight away, with no database.

Run it locally with:  python ingestion/ingest_source_docs.py
It needs OPENAI_API_KEY for the embeddings, DATABASE_URL only if you want the database store, and
the Langfuse keys only to trace the run.
"""

from __future__ import annotations

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from dotenv import load_dotenv  # noqa: E402

load_dotenv()
os.environ.setdefault("LANGFUSE_TRACING_ENVIRONMENT", "ingestion")

from langfuse import get_client  # noqa: E402
from openai import OpenAI  # noqa: E402

import lookup  # noqa: E402


def preprocess(text: str) -> str:
    text = text.replace("\r\n", "\n")
    text = "\n".join(line.rstrip() for line in text.split("\n"))
    return re.sub(r"\n{3,}", "\n\n", text).strip() + "\n"


def main(client=None) -> int:
    client = client or OpenAI()
    langfuse = get_client()
    with langfuse.start_as_current_observation(as_type="chain", name="Ingestion - source documents") as run:
        with langfuse.start_as_current_observation(as_type="span", name="1. Read the documents") as step:
            documents = lookup.read_source_docs()
            if not documents:
                raise SystemExit(f"No markdown files in {lookup.SOURCE_DOCS}.")
            step.update(output=[{"document": name, "characters": len(text)} for name, text in documents],
                        metadata={"folder": "source-docs/", "documents": len(documents)})
        print(f"1. Read {len(documents)} documents: " + ", ".join(name for name, _ in documents) + ".")

        with langfuse.start_as_current_observation(as_type="span", name="2. Preprocess") as step:
            documents = [(name, preprocess(text)) for name, text in documents]
            corpus_version = lookup.corpus_fingerprint(documents)
            info = {name: lookup.document_info(text) for name, text in documents}
            step.update(output={name: {"code": code, "version": version} for name, (code, version) in info.items()},
                        metadata={"corpus_version": corpus_version})
        print("2. Preprocessed. Corpus fingerprint " + corpus_version + ".")

        with langfuse.start_as_current_observation(as_type="span", name="3. Chunk") as step:
            chunks: list[lookup.Chunk] = []
            for name, text in documents:
                chunks.extend(lookup.split_into_chunks(text, document=name, version=info[name][1]))
            step.update(output=[{"chunk": n, "document": c.document, "section": c.section,
                                 "characters": len(c.text), "text": c.text}
                                for n, c in enumerate(chunks, start=1)],
                        metadata={"rule": "one chunk per section (## heading)", "chunks": len(chunks),
                                  "per_document": {name: sum(1 for c in chunks if c.document == name)
                                                   for name, _ in documents}})
        print(f"3. Cut them into {len(chunks)} chunks.")

        with langfuse.start_as_current_observation(as_type="embedding", name="4. Embed",
                                                   model=lookup.EMBEDDING_MODEL,
                                                   input=[f"{c.document}: {c.section}" for c in chunks]) as step:
            embeddings, tokens = lookup.embed(client, [c.text for c in chunks])
            step.update(output=f"{len(embeddings)} embeddings of {len(embeddings[0])} numbers each",
                        usage_details={"input_tokens": tokens})
        print(f"4. Made {len(embeddings)} embeddings with {lookup.EMBEDDING_MODEL} ({tokens} tokens).")

        with langfuse.start_as_current_observation(as_type="span", name="5. Store") as step:
            stored = lookup.store(chunks, embeddings, corpus_version)
            step.update(output=f"{stored} chunks stored in {lookup.store_name()}",
                        metadata={"store": lookup.store_name(), "corpus_version": corpus_version})
        print(f"5. Stored {stored} chunks in {lookup.store_name()}, replacing what was there.")
        run.update(output=f"corpus {corpus_version}: {stored} chunks from {len(documents)} documents")
    langfuse.flush()
    return stored


if __name__ == "__main__":
    main()
