import os
import uuid
from pathlib import Path
from typing import Optional

import pandas as pd
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from agent import run_agent
from agent_tools import load_products

load_dotenv()

ROOT = Path(__file__).resolve().parent
STATIC_DIR = ROOT / "static"

app = FastAPI(
    title="ShopSage AI",
    description="Local RAG + LLM + Tool-Use shopping agent",
    version="1.0.0",
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# In-memory conversation store for this single-user/local prototype.
# Restarting the server clears sessions.
SESSIONS: dict[str, list] = {}


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: Optional[str] = None


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health():
    return {
        "status": "ok",
        "app": "ShopSage AI",
        "chat_model": os.getenv("CHAT_MODEL", "qwen3:4b"),
        "embedding_model": os.getenv("EMBED_MODEL", "nomic-embed-text"),
    }


@app.get("/api/categories")
def categories():
    try:
        df = load_products()
        return {"categories": sorted(df["category"].dropna().unique().tolist())}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not load catalog: {exc}")


@app.get("/api/products")
def products(
    q: str = "",
    category: str = "All",
    max_price: float = 0,
    in_stock: bool = False,
    sort: str = "recommended",
):
    try:
        df = load_products()
        if q.strip():
            terms = [t.lower() for t in q.strip().split() if len(t) > 1]
            searchable = (
                df["name"].astype(str) + " " +
                df["brand"].astype(str) + " " +
                df["category"].astype(str) + " " +
                df["description"].astype(str)
            ).str.lower()
            df = df[searchable.apply(lambda value: all(term in value for term in terms))]
        if category and category != "All":
            df = df[df["category"].str.lower() == category.lower()]
        if max_price and max_price > 0:
            df = df[df["price"] <= max_price]
        if in_stock:
            df = df[df["stock_quantity"] > 0]

        if sort == "price_low":
            df = df.sort_values("price", ascending=True)
        elif sort == "price_high":
            df = df.sort_values("price", ascending=False)
        elif sort == "rating":
            df = df.sort_values("rating", ascending=False)
        else:
            df = df.sort_values(["rating", "price"], ascending=[False, True])

        items = df.to_dict(orient="records")
        return {"products": items, "total": len(items)}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Could not retrieve products: {exc}")


@app.post("/api/chat")
def chat(request: ChatRequest):
    message = request.message.strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    session_id = request.session_id or str(uuid.uuid4())
    history = SESSIONS.get(session_id, [])

    try:
        result = run_agent(message, history)
        answer = result.get("answer", "I couldn't complete that request.")
        SESSIONS[session_id] = result.get("history", history)

        # Return concise execution metadata for optional UI diagnostics.
        return {
            "session_id": session_id,
            "answer": answer,
            "trace": result.get("trace", []),
            "rag_count": len(result.get("rag_hits", [])),
        }
    except Exception as exc:
        raise HTTPException(
            status_code=503,
            detail=(
                "The local shopping agent could not complete the request. "
                "Check that Ollama is running, the models are installed, "
                "and the product RAG index has been built."
            ),
        ) from exc


@app.delete("/api/session/{session_id}")
def clear_session(session_id: str):
    SESSIONS.pop(session_id, None)
    return {"cleared": True}
