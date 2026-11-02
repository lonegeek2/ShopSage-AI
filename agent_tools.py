"""Real Python tools exposed to the local LLM agent."""
import os
import pandas as pd
from dotenv import load_dotenv

load_dotenv()
CSV_PATH = os.getenv("PRODUCTS_CSV", "./data/products.csv")

def load_products():
    return pd.read_csv(CSV_PATH).fillna("")

def search_products(query: str, category: str = "", max_price: float = 0, in_stock_only: bool = False):
    """Search the catalog using keyword/category matching and optional constraints."""
    df = load_products()
    terms = [t.lower() for t in query.split() if len(t) > 2]
    if terms:
        searchable = (df["name"].astype(str) + " " + df["description"].astype(str) +
                      " " + df["brand"].astype(str) + " " + df["category"].astype(str)).str.lower()
        mask = searchable.apply(lambda s: sum(term in s for term in terms) > 0)
        df = df[mask]
    if category:
        df = df[df["category"].str.lower() == category.lower()]
    if max_price and max_price > 0:
        df = df[df["price"] <= max_price]
    if in_stock_only:
        df = df[df["stock_quantity"] > 0]
    return df.sort_values(["rating", "price"], ascending=[False, True]).head(10).to_dict(orient="records")

def filter_products(max_price: float = 0, min_rating: float = 0, brand: str = "", category: str = "", in_stock_only: bool = True):
    """Filter the product catalog using explicit shopping constraints."""
    df = load_products()
    if max_price and max_price > 0:
        df = df[df["price"] <= max_price]
    if min_rating and min_rating > 0:
        df = df[df["rating"] >= min_rating]
    if brand:
        df = df[df["brand"].str.lower() == brand.lower()]
    if category:
        df = df[df["category"].str.lower() == category.lower()]
    if in_stock_only:
        df = df[df["stock_quantity"] > 0]
    return df.sort_values(["rating", "price"], ascending=[False, True]).head(10).to_dict(orient="records")

def compare_products(product_ids: list):
    """Compare products by IDs and return their specifications side by side."""
    df = load_products()
    selected = df[df["product_id"].isin(product_ids)]
    cols = ["product_id", "name", "brand", "category", "price", "rating",
            "stock_quantity", "ram", "storage", "battery", "camera", "processor"]
    return selected[cols].to_dict(orient="records")

def check_stock(product_id: str):
    """Check current stock quantity for one product ID."""
    df = load_products()
    row = df[df["product_id"].str.upper() == product_id.upper()]
    if row.empty:
        return {"found": False, "message": "Product ID not found"}
    p = row.iloc[0]
    return {"found": True, "product_id": product_id, "name": p["name"],
            "stock_quantity": int(p["stock_quantity"]),
            "available": bool(p["stock_quantity"] > 0)}
