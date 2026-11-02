"""Qwen3 tool-calling shopping agent. Tools execute locally in Python."""
import json
import os
import ollama
from dotenv import load_dotenv
from agent_tools import search_products, filter_products, compare_products, check_stock
from rag_store import retrieve_products

load_dotenv()
MODEL = os.getenv("CHAT_MODEL", "qwen3:4b")
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
client_ollama = ollama.Client(host=OLLAMA_HOST)

TOOL_DEFS = [
    {"type": "function", "function": {"name": "search_products", "description": "Search products by keywords and optional category, maximum price, and stock constraint.", "parameters": {"type": "object", "properties": {"query": {"type": "string"}, "category": {"type": "string"}, "max_price": {"type": "number"}, "in_stock_only": {"type": "boolean"}}, "required": ["query"]}}},
    {"type": "function", "function": {"name": "filter_products", "description": "Filter products by maximum price, minimum rating, brand, category and stock.", "parameters": {"type": "object", "properties": {"max_price": {"type": "number"}, "min_rating": {"type": "number"}, "brand": {"type": "string"}, "category": {"type": "string"}, "in_stock_only": {"type": "boolean"}}}}},
    {"type": "function", "function": {"name": "compare_products", "description": "Compare products using their product IDs.", "parameters": {"type": "object", "properties": {"product_ids": {"type": "array", "items": {"type": "string"}}}, "required": ["product_ids"]}}},
    {"type": "function", "function": {"name": "check_stock", "description": "Check stock availability using a product ID.", "parameters": {"type": "object", "properties": {"product_id": {"type": "string"}}, "required": ["product_id"]}}}
]
TOOL_MAP = {
    "search_products": search_products,
    "filter_products": filter_products,
    "compare_products": compare_products,
    "check_stock": check_stock,
}

SYSTEM = """You are ShopSage, a helpful e-commerce shopping agent.
You have access to a local product catalog through tools and a RAG knowledge base.
Rules:
- Use tools to retrieve factual product information. Never invent products, prices, ratings, specifications or stock.
- For product-finding requests, call search_products or filter_products.
- For comparison requests, call compare_products after obtaining product IDs.
- For availability questions, call check_stock.
- Use the provided RAG context as additional product knowledge, but verify current price and stock with tools.
- Respect explicit budget/category/brand constraints.
- Recommend only products returned by tools. Explain trade-offs clearly.
- If no products match, say so and suggest relaxing a constraint.
- Prices are in INR (₹). Do not claim that a purchase has been made.
"""

def run_agent(user_message: str, history=None):
    history = history or []
    rag_hits = retrieve_products(user_message, n_results=5)
    rag_context = "\n".join(
        f"- {h['document']} (retrieval distance: {h['distance']:.3f})" for h in rag_hits
    ) or "No relevant RAG documents retrieved."
    messages = [{"role": "system", "content": SYSTEM + "\n\nRAG product context:\n" + rag_context}]
    messages.extend(history[-8:])
    messages.append({"role": "user", "content": user_message})

    trace = [f"RAG retrieved {len(rag_hits)} relevant product records."]
    for _ in range(5):
        response = client_ollama.chat(
            model=MODEL,
            messages=messages,
            tools=TOOL_DEFS,
            options={"temperature": 0.2}
        )
        msg = response.message
        messages.append(msg)
        calls = getattr(msg, "tool_calls", None) or []
        if not calls:
            answer = msg.content or "I couldn't generate a recommendation. Please try again."
            return {"answer": answer, "trace": trace, "rag_hits": rag_hits, "history": messages[1:]}
        for call in calls:
            name = call.function.name
            args = call.function.arguments or {}
            if isinstance(args, str):
                args = json.loads(args)
            trace.append(f"Tool executed: {name}({json.dumps(args, ensure_ascii=False)})")
            try:
                result = TOOL_MAP[name](**args)
            except Exception as exc:
                result = {"error": str(exc)}
            messages.append({
                "role": "tool",
                "name": name,
                "content": json.dumps(result, ensure_ascii=False, default=str)
            })
    return {
        "answer": "I reached the tool-call limit. Please narrow your request and try again.",
        "trace": trace, "rag_hits": rag_hits, "history": messages[1:]
    }
