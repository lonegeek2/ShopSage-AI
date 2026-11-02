"""Local retrieval-augmented generation using Ollama embeddings + ChromaDB."""
import os
from pathlib import Path
from dotenv import load_dotenv
import chromadb
import ollama
from scripts.ingest_products import product_text
import pandas as pd

load_dotenv()
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
CSV_PATH = os.getenv("PRODUCTS_CSV", "./data/products.csv")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
client_ollama = ollama.Client(host=OLLAMA_HOST)

def get_collection():
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    return client.get_or_create_collection("products", metadata={"hnsw:space": "cosine"})

def retrieve_products(query: str, n_results: int = 5):
    collection = get_collection()
    if collection.count() == 0:
        return []
    embed_response = client_ollama.embed(model=EMBED_MODEL, input=query)
    embeddings = embed_response["embeddings"] if isinstance(embed_response, dict) else embed_response.embeddings
    embedding = embeddings[0]
    result = collection.query(query_embeddings=[embedding], n_results=min(n_results, collection.count()))
    hits = []
    for i, doc in enumerate(result.get("documents", [[]])[0]):
        hits.append({
            "product_id": result["ids"][0][i],
            "document": doc,
            "distance": result["distances"][0][i],
            "metadata": result["metadatas"][0][i]
        })
    return hits
