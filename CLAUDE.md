# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Course Materials RAG System** — A full-stack web application that answers questions about course materials using Retrieval-Augmented Generation (RAG). Users submit queries through a web interface; the system retrieves relevant course content via semantic search and generates context-aware responses using Anthropic's Claude API.

## Architecture

### High-Level Flow

1. **Frontend** (HTML/JS) → sends query to **Backend API**
2. **FastAPI app** (app.py) → delegates to **RAGSystem** orchestrator
3. **RAGSystem** coordinates:
   - **DocumentProcessor**: Parses course files (PDF/DOCX/TXT) into chunks with metadata
   - **VectorStore** (ChromaDB): Stores embeddings; performs semantic search
   - **AIGenerator**: Calls Claude API with search results + conversation history
   - **SessionManager**: Maintains per-user conversation context (last 2 exchanges)
   - **ToolManager**: Manages Claude's tool use (search tool for retrieval)
4. Response streams back to frontend

### Key Design Patterns

- **Tool-based RAG**: Claude uses a `CourseSearchTool` to retrieve relevant documents as needed (vs. pre-retrieving before calling Claude)
- **Session-scoped history**: Each session stores up to `MAX_HISTORY` (2) prior user/assistant exchanges for context
- **Course deduplication**: On startup/folder load, system checks existing course titles to avoid re-processing
- **No-cache frontend**: Static assets have cache-control headers disabled for development; remove these before production

### Configuration

All settings via `config.py`, which loads from `.env`:
- `ANTHROPIC_API_KEY` — Required; no default
- `ANTHROPIC_MODEL` — Claude model ID (currently `claude-sonnet-4-20250514`)
- `CHUNK_SIZE` (800) — Document chunk size in characters
- `CHUNK_OVERLAP` (100) — Character overlap between chunks
- `MAX_RESULTS` (5) — Max semantic search results per query
- `MAX_HISTORY` (2) — Conversation turns to store per session
- `CHROMA_PATH` — Vector DB storage location (`./chroma_db`)
- `EMBEDDING_MODEL` — Sentence transformer (`all-MiniLM-L6-v2`)

## Development Commands

### Setup
```bash
uv sync                    # Install dependencies
pip install pre-commit     # Install pre-commit for secret scanning
pre-commit install         # Register git hooks
cp .env.example .env       # Create .env with your ANTHROPIC_API_KEY
```

### Run
```bash
./run.sh                              # Start backend + static server
# Or manually:
cd backend && uv run uvicorn app:app --reload --port 8000
```

Access app at `http://localhost:8000` and API docs at `http://localhost:8000/docs`.

### Pre-commit Hooks

This project uses `detect-secrets` + Black + Ruff via `.pre-commit-config.yaml`:
- Blocks commits with API keys/tokens
- Prevents `.env` files from being committed
- Auto-formats Python code (Black)
- Lints with Ruff

Hooks run automatically on `git commit`. To run manually:
```bash
pre-commit run --all-files
```

## File Organization

```
backend/
  app.py                    # FastAPI entry point, routes, models
  rag_system.py             # RAG orchestrator, main query flow
  config.py                 # Configuration from environment
  vector_store.py           # ChromaDB wrapper, embedding + search
  ai_generator.py           # Claude API client, tool handling
  document_processor.py     # Parse docs (PDF/DOCX/TXT) → chunks + metadata
  session_manager.py        # Per-session conversation history
  search_tools.py           # Tool definitions for Claude; CourseSearchTool
  models.py                 # Pydantic models: Course, Lesson, CourseChunk

frontend/
  index.html                # UI layout
  script.js                 # Query submission, response rendering
  style.css                 # Styling

docs/                       # Course documents (loaded on startup)
.pre-commit-config.yaml     # Secret detection, formatting, linting
```

## Adding Course Materials

Place course files (`.pdf`, `.docx`, `.txt`) in the `docs/` folder. On backend startup, the system automatically:
1. Detects new documents
2. Processes them into chunks
3. Generates embeddings via Sentence Transformers
4. Stores in ChromaDB

To reload documents during development, restart the backend.

## Important Notes

- **Secrets**: `.env` is git-ignored and pre-commit blocked; never commit `ANTHROPIC_API_KEY`
- **Frontend caching**: Development has no-cache headers; remove from `app.py` line 112 before production
- **CORS**: Currently allows all origins (`["*"]`) for development; restrict before production
- **Tool use**: Claude makes decisions about when to call the search tool; it always has access via `tools` parameter in `ai_generator.py`
