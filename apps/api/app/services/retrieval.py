"""Small-corpus exact pgvector retrieval with explicit manual fallback."""

import asyncio
import hashlib
import json
import httpx
import psycopg
from psycopg.types.json import Jsonb
from app.core.config import API_DIR, Settings
from app.runtime.store import StoreError


def migrate(settings: Settings):
    if not settings.database_url:
        raise ValueError("DATABASE_URL is missing.")
    with psycopg.connect(settings.database_url, connect_timeout=5) as db:
        db.execute((API_DIR / "migrations/001_card_search.sql").read_text())


def text_for(card):
    return json.dumps(
        {
            k: card[k]
            for k in (
                "pattern_name",
                "summary",
                "hook_type",
                "narrative_flow",
                "editing_atoms",
                "reusable_rules",
                "observations",
                "rules",
                "applicability",
                "material_requirements",
            )
            if k in card
        },
        ensure_ascii=False,
        sort_keys=True,
    )


def vector_literal(vector):
    import math

    if len(vector) != 1024 or not all(
        isinstance(x, (int, float)) and math.isfinite(x) for x in vector
    ):
        raise ValueError(
            "Embedding provider returned an invalid 1024-dimensional vector."
        )
    return "[" + ",".join(str(float(x)) for x in vector) + "]"


async def embed(settings: Settings, text: str, client=None):
    own = client is None
    client = client or httpx.AsyncClient(timeout=30)
    try:
        response = await client.post(
            settings.embedding_api_base_url.rstrip("/") + "/embeddings/multimodal",
            headers={"Authorization": f"Bearer {settings.embedding_api_key}"},
            json={
                "model": settings.embedding_model,
                "input": [{"type": "text", "text": text}],
                "dimensions": 1024,
                "encoding_format": "float",
            },
        )
        response.raise_for_status()
        result = response.json()
        vector = result["data"]["embedding"]
        vector_literal(vector)
        return vector, result.get("usage", {})
    finally:
        if own:
            await client.aclose()


def existing_hash(settings, cid):
    with psycopg.connect(settings.database_url, connect_timeout=5) as db:
        row = db.execute(
            "SELECT content_hash,embedding_model FROM viralcraft_cards WHERE id=%s",
            (cid,),
        ).fetchone()
        return row


def upsert(settings, card, owner, vector, content_hash):
    with psycopg.connect(settings.database_url, connect_timeout=5) as db:
        db.execute(
            """INSERT INTO viralcraft_cards VALUES (%s,%s,%s,%s,%s,%s,%s::vector)
        ON CONFLICT(id) DO UPDATE SET content=excluded.content,content_hash=excluded.content_hash,embedding_model=excluded.embedding_model,embedding=excluded.embedding
        WHERE viralcraft_cards.owner_id=excluded.owner_id""",
            (
                card["id"],
                owner,
                owner == "__public__",
                Jsonb(card),
                content_hash,
                settings.embedding_model,
                vector_literal(vector),
            ),
        )


def query(settings, owner, vector):
    with psycopg.connect(settings.database_url, connect_timeout=5) as db:
        rows = db.execute(
            """SELECT content FROM viralcraft_cards WHERE (owner_id=%s OR is_public=true) AND embedding_model=%s ORDER BY embedding <=> %s::vector LIMIT 3""",
            (owner, settings.embedding_model, vector_literal(vector)),
        ).fetchall()
        return [r[0] for r in rows]


async def search_cards(settings, store, user, text):
    owner = user["id"]
    cards = store.resources(owner, "card", True)
    fallback = {
        "mode": "manual",
        "cards": cards,
        "message": "Semantic retrieval is unavailable. Choose reference cards manually.",
    }
    if not settings.capabilities()["retrieval"]["configured"]:
        return fallback
    if settings.embedding_dimensions != 1024:
        return fallback
    try:
        # Explicit migrate command owns DDL; requests never change the database schema.
        for card in cards:
            content = text_for(card)
            hash_ = hashlib.sha256(content.encode()).hexdigest()
            old = await asyncio.to_thread(existing_hash, settings, card["id"])
            if old and old == (hash_, settings.embedding_model):
                continue
            store.reserve(
                owner,
                "embedding",
                user["quota"] * 10,
                settings.global_generation_limit * 10,
            )
            v, usage = await embed(settings, content)
            card_owner = store.card_index_owner(owner, card["id"])
            await asyncio.to_thread(upsert, settings, card, card_owner, v, hash_)
            store.event(
                owner,
                "embedding_usage",
                {"model": settings.embedding_model, "usage": usage},
            )
        store.reserve(
            owner,
            "embedding",
            user["quota"] * 10,
            settings.global_generation_limit * 10,
        )
        v, usage = await embed(settings, text)
        hits = await asyncio.to_thread(query, settings, owner, v)
        # Local ownership is authoritative even if an old search index is stale.
        available = {c["id"]: c for c in cards}
        hits = [available[c["id"]] for c in hits if c["id"] in available]
        store.event(
            owner, "retrieval", {"card_ids": [c["id"] for c in hits], "usage": usage}
        )
        return {"mode": "semantic", "cards": hits, "message": None}
    except StoreError:
        raise
    except Exception:
        store.event(owner, "retrieval_fallback", {})
        return fallback
