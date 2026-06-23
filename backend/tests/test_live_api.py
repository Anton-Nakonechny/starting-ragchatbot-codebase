"""Opt-in true end-to-end test against the real Anthropic API.

Deselected by default (``addopts = -m 'not live'``). Run explicitly with:

    ANTHROPIC_API_KEY=sk-... uv run pytest -m live

It drives the real app + real LLM through a seeded store and asserts a
well-formed, non-empty answer — no brittle exact-text assertions.
"""

import dataclasses
import os

import pytest
from fastapi.testclient import TestClient

from rag_system import RAGSystem
from tests.conftest import build_app

pytestmark = pytest.mark.live


@pytest.fixture
def live_client(tmp_config, sample_course_file):
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        pytest.skip("ANTHROPIC_API_KEY not set; skipping live API test")

    # Same wiring as the faked client, but with a real key and the real SDK.
    cfg = dataclasses.replace(tmp_config, ANTHROPIC_API_KEY=api_key)
    rag = RAGSystem(cfg)
    rag.add_course_document(str(sample_course_file))
    with TestClient(build_app(rag)) as c:
        yield c


def test_live_query_returns_well_formed_answer(live_client):
    resp = live_client.post(
        "/api/query", json={"query": "What is a widget according to the course?"}
    )

    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body["answer"], str) and body["answer"].strip()
    assert "session_id" in body
    assert isinstance(body["sources"], list)
