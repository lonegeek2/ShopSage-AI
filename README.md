# ShopSage AI — Full Website Edition

A complete local e-commerce shopping-agent project with a custom HTML/CSS/JavaScript frontend and a Python FastAPI backend.

## Architecture

**RAG + LLM + Tool Use**

* Frontend: HTML5, CSS3, vanilla JavaScript
* Backend: FastAPI
* LLM: Qwen3 4B through Ollama
* Embeddings: nomic-embed-text through Ollama
* Vector database: ChromaDB
* Product catalog: local CSV + Pandas
* Agent tools: search, filter, compare, stock check

No paid AI API keys are required.

## Requirements

* Windows 10/11
* Python 3.10+
* Ollama installed and running
* 16 GB RAM recommended
* Internet only for initial downloads

## 1\. Pull the models

Open PowerShell:

```powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
ollama list
```

Keep Ollama running. Default local endpoint: `http://localhost:11434`.

## 2\. Set up Python

Open PowerShell in the extracted `ShopSage-Web` folder:

```powershell
python -m venv venv
venv\\Scripts\\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

## 3\. Configure environment

```powershell
copy .env.example .env
```

Defaults work for a local Ollama installation. If Ollama uses a different host, update `OLLAMA\_HOST` in `.env`.

## 4\. Build the RAG index

```powershell
python scripts/ingest\_products.py
```

Expected output:

```text
Indexed 17 products into ./chroma\_db
```

Run ingestion again whenever `data/products.csv` changes.

## 5\. Start the website and backend

```powershell
uvicorn server:app --host 127.0.0.1 --port 8000 --reload
```

Open:

http://127.0.0.1:8000

The same FastAPI server serves the website and its API. Do not open `index.html` directly from File Explorer.

## Website features

* Responsive dark minimalistic shopping interface
* AI shopping chat with session context
* Suggested shopping prompts
* Product catalog cards
* Search by product name, brand or description
* Category, budget and stock filters
* Sorting by recommendation, price and rating
* Local connection status

## API routes

* `GET /api/health`
* `GET /api/categories`
* `GET /api/products`
* `POST /api/chat`
* `DELETE /api/session/{session\_id}`

## Troubleshooting

### Ollama connection issue

Start the Ollama desktop app or run `ollama serve` in a separate terminal. Check `ollama list`.

### Model missing

```powershell
ollama pull qwen3:4b
ollama pull nomic-embed-text
```

### Empty RAG index

```powershell
python scripts/ingest\_products.py
```

### Port already in use

```powershell
uvicorn server:app --host 127.0.0.1 --port 8001
```

Then open `http://127.0.0.1:8001`.

### Slow responses on 16 GB RAM

Close other memory-heavy applications. If needed, change `CHAT\_MODEL=qwen3:1.7b` in `.env`, run `ollama pull qwen3:1.7b`, and restart the server.

## Notes

* Included products are synthetic demo catalog records.
* Product prices, ratings and stock are only as current as the CSV file.
* The agent does not make purchases or payments.
* Session history is held in server memory and is cleared when the server restarts.
* This is a local prototype, not a production deployment with authentication or persistent user accounts.



🎥 Project Demonstration



Watch the complete demonstration of ShopSage AI:



\[▶ Watch ShopSage AI Demo](demo/ShopSage-AI-Demo.mp4)

