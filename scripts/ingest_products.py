"""Build/rebuild the local ChromaDB product knowledge base."""
import os
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from dotenv import load_dotenv
import pandas as pd
import chromadb
import ollama

load_dotenv()
CSV_PATH = os.getenv("PRODUCTS_CSV", "./data/products.csv")
CHROMA_PATH = os.getenv("CHROMA_PATH", "./chroma_db")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
client_ollama = ollama.Client(host=OLLAMA_HOST)

def product_text(row):
    fields = [
        f"Product: {row.get('name','')}",
        f"Category: {row.get('category','')}",
        f"Brand: {row.get('brand','')}",
        f"Price: INR {row.get('price','')}",
        f"Rating: {row.get('rating','')}",
        f"Stock quantity: {row.get('stock_quantity','')}",
        f"Description: {row.get('description','')}",
        f"RAM: {row.get('ram','')}",
        f"Storage: {row.get('storage','')}",
        f"Battery: {row.get('battery','')}",
        f"Camera: {row.get('camera','')}",
        f"Processor: {row.get('processor','')}",
    ]
    return ". ".join(x for x in fields if x.split(": ",1)[-1] not in ("", "nan"))

def main():
    df = pd.read_csv(CSV_PATH).fillna("")
    client = chromadb.PersistentClient(path=CHROMA_PATH)
    try:
        client.delete_collection("products")
    except Exception:
        pass
    collection = client.create_collection(
        name="products",
        metadata={"hnsw:space": "cosine"}
    )
    batch_size = 20
    for start in range(0, len(df), batch_size):
        chunk = df.iloc[start:start+batch_size]
        docs = [product_text(row) for _, row in chunk.iterrows()]
        ids = chunk["product_id"].astype(str).tolist()
        embed_response = client_ollama.embed(model=EMBED_MODEL, input=docs)
        embeddings = embed_response["embeddings"] if isinstance(embed_response, dict) else embed_response.embeddings
        metadatas = []
        for _, row in chunk.iterrows():
            metadatas.append({
                "product_id": str(row["product_id"]),
                "name": str(row["name"]),
                "category": str(row["category"]),
                "brand": str(row["brand"]),
                "price": float(row["price"]),
                "rating": float(row["rating"]),
                "stock_quantity": int(float(row["stock_quantity"] or 0)),
            })
        collection.add(ids=ids, documents=docs, embeddings=embeddings, metadatas=metadatas)
    print(f"Indexed {len(df)} products into {CHROMA_PATH}")

if __name__ == "__main__":
    main()
