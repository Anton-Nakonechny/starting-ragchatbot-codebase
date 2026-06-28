import warnings
warnings.filterwarnings("ignore", message="resource_tracker: There appear to be.*")

import logging
from pathlib import Path
from typing import List, Optional

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel, field_validator

from config import config
from rag_system import RAGSystem

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


# Pydantic models for request/response

class QueryRequest(BaseModel):
    """Request model for course queries"""
    query: str
    session_id: Optional[str] = None

    @field_validator("query")
    @classmethod
    def query_not_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("query must not be empty or blank")
        return stripped

class SourceCitation(BaseModel):
    """A source citation with optional URL"""
    label: str
    url: Optional[str] = None

class QueryResponse(BaseModel):
    """Response model for course queries"""
    answer: str
    sources: List[SourceCitation]
    session_id: str

class CourseStats(BaseModel):
    """Response model for course statistics"""
    total_courses: int
    course_titles: List[str]


# Default location of the frontend assets, relative to this file (so it
# resolves regardless of the current working directory).
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
DOCS_DIR = Path(__file__).resolve().parent.parent / "docs"


class DevStaticFiles(StaticFiles):
    """Static file handler with no-cache headers for development."""
    async def get_response(self, path: str, scope):
        response = await super().get_response(path, scope)
        if isinstance(response, FileResponse):
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "0"
        return response


def create_app(
    rag_system: Optional[RAGSystem] = None,
    *,
    serve_frontend: bool = True,
    load_docs_on_startup: bool = True,
) -> FastAPI:
    """Build the FastAPI application.

    Args:
        rag_system: RAG orchestrator to use. Defaults to a fresh
            ``RAGSystem(config)`` for production; tests inject a seeded one.
        serve_frontend: Mount the static frontend at ``/``. Disabled in tests
            so the app can be imported/built without the frontend directory.
        load_docs_on_startup: Register the startup hook that loads ``docs/``.
            Disabled in tests to keep the suite fast and isolated.

    Returns:
        A configured FastAPI app.
    """
    if rag_system is None:
        rag_system = RAGSystem(config)

    app = FastAPI(title="Course Materials RAG System", root_path="")

    # Trusted host middleware for proxy
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=["*"])

    # CORS with proper settings for proxy
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        """Process a query and return response with sources"""
        try:
            session_id = request.session_id
            if not session_id:
                session_id = rag_system.session_manager.create_session()

            answer, sources = rag_system.query(request.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id,
            )
        except Exception as e:
            logger.exception("Query failed for request: %r", request.query)
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        """Get course analytics and statistics"""
        try:
            analytics = rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"],
            )
        except Exception as e:
            logger.exception("Failed to get course stats")
            raise HTTPException(status_code=500, detail=str(e))

    @app.delete("/api/session/{session_id}")
    async def clear_session(session_id: str):
        """Release a conversation session from memory"""
        try:
            rag_system.session_manager.clear_session(session_id)
            return {"status": "ok"}
        except Exception as e:
            logger.exception("Failed to clear session %s", session_id)
            raise HTTPException(status_code=500, detail=str(e))

    if load_docs_on_startup:
        @app.on_event("startup")
        async def startup_event():
            """Load initial documents on startup"""
            if DOCS_DIR.exists():
                print("Loading initial documents...")
                try:
                    courses, chunks = rag_system.add_course_folder(
                        str(DOCS_DIR), clear_existing=False
                    )
                    print(f"Loaded {courses} courses with {chunks} chunks")
                except Exception as e:
                    print(f"Error loading documents: {e}")

    # Serve static files for the frontend (development: no-cache headers)
    if serve_frontend and FRONTEND_DIR.exists():
        app.mount("/", DevStaticFiles(directory=str(FRONTEND_DIR), html=True), name="static")

    return app


# Module-level `app` for `uvicorn app:app` and run.sh — built lazily so that
# importing this module (e.g. to reach create_app from tests) has no side
# effects. Accessing `app` triggers production wiring on first use.
_app = None


def __getattr__(name):
    global _app
    if name == "app":
        if _app is None:
            _app = create_app()
        return _app
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
