"""Black-box end-to-end tests of the HTTP contract via TestClient.

The whole stack is real except the Anthropic client (faked). These tests
pin the user-facing API: query flow, sources shape, sessions, and errors.
"""

from fastapi.testclient import TestClient

from tests.conftest import build_app, text_response, tool_use_response


def test_query_creates_session_when_missing(client, fake_anthropic):
    fake_anthropic.responses = [text_response("Hello, I can help with courses.")]

    resp = client.post("/api/query", json={"query": "hi"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Hello, I can help with courses."
    assert body["session_id"]  # a session was created
    assert body["sources"] == []


def test_query_with_tool_use_populates_sources(client, fake_anthropic):
    # Claude asks to search, then answers from the tool results.
    fake_anthropic.responses = [
        tool_use_response("search_course_content", {"query": "widgets"}),
        text_response("Widgets are small reusable components."),
    ]

    resp = client.post("/api/query", json={"query": "what is a widget?"})

    assert resp.status_code == 200
    body = resp.json()
    assert body["answer"] == "Widgets are small reusable components."
    assert len(body["sources"]) >= 1
    # Sources match the SourceCitation shape and point at the seeded course.
    first = body["sources"][0]
    assert set(first.keys()) == {"label", "url"}
    assert "Test Course on Widgets" in first["label"]


def test_query_general_knowledge_has_no_sources(client, fake_anthropic):
    fake_anthropic.responses = [text_response("Paris is the capital of France.")]

    resp = client.post("/api/query", json={"query": "capital of France?"})

    assert resp.status_code == 200
    assert resp.json()["sources"] == []


def test_query_reuses_existing_session_and_records_history(
    client, fake_anthropic, seeded_rag_system
):
    fake_anthropic.responses = [
        text_response("First answer."),
        text_response("Second answer."),
    ]

    first = client.post("/api/query", json={"query": "first question"}).json()
    session_id = first["session_id"]

    second = client.post(
        "/api/query", json={"query": "second question", "session_id": session_id}
    )

    assert second.status_code == 200
    assert second.json()["session_id"] == session_id
    # The session now holds both exchanges (2 user + 2 assistant messages).
    history = seeded_rag_system.session_manager.sessions[session_id]
    assert len(history) == 4
    assert history[0].content == "first question"


def test_query_propagates_errors_as_500(client, fake_anthropic):
    fake_anthropic.error = RuntimeError("upstream boom")

    resp = client.post("/api/query", json={"query": "anything"})

    assert resp.status_code == 500
    assert "upstream boom" in resp.json()["detail"]


def test_courses_endpoint_reports_seeded_catalog(client):
    resp = client.get("/api/courses")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_courses"] == 1
    assert "Test Course on Widgets" in body["course_titles"]


def test_courses_endpoint_empty_store(unseeded_rag_system):
    with TestClient(build_app(unseeded_rag_system)) as c:
        resp = c.get("/api/courses")

    assert resp.status_code == 200
    body = resp.json()
    assert body["total_courses"] == 0
    assert body["course_titles"] == []


def test_clear_session(client, fake_anthropic, seeded_rag_system):
    sessions = seeded_rag_system.session_manager
    fake_anthropic.responses = [text_response("answer")]
    session_id = client.post("/api/query", json={"query": "q"}).json()["session_id"]
    assert sessions.get_conversation_history(session_id) is not None

    resp = client.delete(f"/api/session/{session_id}")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
    assert sessions.get_conversation_history(session_id) is None
