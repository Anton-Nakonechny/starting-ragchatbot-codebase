"""Shared fixtures for the backend regression suite.

Design: the *entire* owned stack runs for real — FastAPI routes, RAGSystem,
ChromaDB (in a tmp dir), document parsing, sessions. The only external
dependency, the Anthropic API, is replaced at its network boundary by
``FakeAnthropic`` so the suite is deterministic, free, and fast. A separate
opt-in live suite (``-m live``) exercises the real API.
"""

import dataclasses

import pytest
from fastapi.testclient import TestClient

from config import Config
from rag_system import RAGSystem
from vector_store import VectorStore
from document_processor import DocumentProcessor
from app import create_app


# --------------------------------------------------------------------------- #
# Fake Anthropic client — a scripted stand-in shaped like the real SDK.
# --------------------------------------------------------------------------- #

class FakeContentBlock:
    """Mimics an Anthropic content block (text or tool_use)."""

    def __init__(self, type, text=None, name=None, input=None, id=None):
        self.type = type
        self.text = text
        self.name = name
        self.input = input or {}
        self.id = id


class FakeResponse:
    """Mimics an Anthropic Message response."""

    def __init__(self, content, stop_reason):
        self.content = content
        self.stop_reason = stop_reason


def text_response(text):
    """A plain text answer (end_turn, no tool use)."""
    return FakeResponse([FakeContentBlock("text", text=text)], stop_reason="end_turn")


def tool_use_response(tool_name, tool_input, block_id="tool_1"):
    """A response asking to invoke a tool."""
    return FakeResponse(
        [FakeContentBlock("tool_use", name=tool_name, input=tool_input, id=block_id)],
        stop_reason="tool_use",
    )


class _FakeMessages:
    def __init__(self, parent):
        self._parent = parent

    def create(self, **kwargs):
        # Record the call so tests can assert on what was sent (tools, system…).
        self._parent.calls.append(kwargs)
        if self._parent.error is not None:
            raise self._parent.error
        if not self._parent.responses:
            # Sensible default so unscripted calls don't explode.
            return text_response("(no scripted response)")
        nxt = self._parent.responses.pop(0)
        if isinstance(nxt, Exception):
            raise nxt
        return nxt


class FakeAnthropic:
    """Drop-in replacement for ``anthropic.Anthropic``.

    Configure ``responses`` (consumed FIFO across ``messages.create`` calls)
    or ``error`` (raised on the next call) to script a scenario.
    """

    def __init__(self, responses=None, error=None):
        self.responses = list(responses or [])
        self.error = error
        self.calls = []
        self.messages = _FakeMessages(self)


# --------------------------------------------------------------------------- #
# A small, well-formed course document used to seed the real vector store.
# Lesson 0 is intentionally long so it produces multiple chunks (exercises
# source de-duplication); lesson 1 is short.
# --------------------------------------------------------------------------- #

SAMPLE_COURSE_TEXT = """Course Title: Test Course on Widgets
Course Link: https://example.com/widgets
Course Instructor: Ada Lovelace

Lesson 0: Introduction to Widgets
Lesson Link: https://example.com/widgets/lesson0
Widgets are small reusable components used throughout modern software systems. \
A widget encapsulates both appearance and behaviour so that it can be dropped \
into many different screens without modification. The earliest widgets were \
simple buttons and labels, but the idea quickly grew to cover sliders, menus, \
and entire panels. Understanding widgets is the foundation for everything that \
follows in this course. We will look at what a widget is, why widgets matter, \
and how a well designed widget improves both developer productivity and the end \
user experience. A good widget hides its internal complexity behind a clean \
interface. It exposes only the properties and events that callers actually need. \
This separation of concerns is what lets large teams build complex interfaces \
without stepping on each other. Throughout this lesson we emphasise that widgets \
should be small, focused, and composable so that they can be combined into \
larger structures later on in the course material.

Lesson 1: Advanced Widget Composition
Lesson Link: https://example.com/widgets/lesson1
Advanced widgets support composition. You can nest widgets inside other widgets \
to build complex interfaces from simple parts. Composition is the most powerful \
technique covered in this course.
"""


@pytest.fixture
def tmp_config(tmp_path):
    """A Config pointing at an isolated tmp ChromaDB and a dummy API key."""
    return dataclasses.replace(
        Config(),
        ANTHROPIC_API_KEY="test-key-not-used",
        CHROMA_PATH=str(tmp_path / "chroma_db"),
    )


@pytest.fixture
def sample_course_file(tmp_path):
    """Write the sample course to a temp .txt file and return its path."""
    path = tmp_path / "test_course.txt"
    path.write_text(SAMPLE_COURSE_TEXT, encoding="utf-8")
    return path


def build_app(rag_system):
    """Build a test app over ``rag_system`` (no frontend mount, no doc load)."""
    return create_app(rag_system, serve_frontend=False, load_docs_on_startup=False)


@pytest.fixture
def document_processor(tmp_config):
    """A DocumentProcessor using the configured chunk size/overlap."""
    return DocumentProcessor(tmp_config.CHUNK_SIZE, tmp_config.CHUNK_OVERLAP)


@pytest.fixture
def empty_vector_store(tmp_config):
    """A real, empty VectorStore backed by the tmp ChromaDB."""
    return VectorStore(
        tmp_config.CHROMA_PATH, tmp_config.EMBEDDING_MODEL, tmp_config.MAX_RESULTS
    )


@pytest.fixture
def seeded_vector_store(empty_vector_store, document_processor, sample_course_file):
    """A real VectorStore seeded with the sample course via the real path."""
    course, chunks = document_processor.process_course_document(str(sample_course_file))
    empty_vector_store.add_course_metadata(course)
    empty_vector_store.add_course_content(chunks)
    return empty_vector_store


@pytest.fixture
def fake_anthropic():
    """A fresh FakeAnthropic; tests assign ``.responses`` / ``.error``."""
    return FakeAnthropic()


@pytest.fixture
def unseeded_rag_system(tmp_config, fake_anthropic):
    """A real RAGSystem with no courses, LLM boundary faked."""
    rag = RAGSystem(tmp_config)
    rag.ai_generator.client = fake_anthropic
    return rag


@pytest.fixture
def seeded_rag_system(unseeded_rag_system, sample_course_file):
    """A real RAGSystem seeded with the sample course, LLM boundary faked."""
    unseeded_rag_system.add_course_document(str(sample_course_file))
    return unseeded_rag_system


@pytest.fixture
def client(seeded_rag_system):
    """TestClient over the real app, no frontend mount, no startup doc load."""
    with TestClient(build_app(seeded_rag_system)) as test_client:
        yield test_client
