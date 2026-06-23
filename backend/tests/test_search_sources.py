"""Regression tests for the source/citation path (area of recent churn).

Covers CourseSearchTool formatting + de-duplication and ToolManager source
round-tripping, against the real seeded vector store plus crafted results.
"""

from search_tools import CourseSearchTool, ToolManager
from vector_store import SearchResults


def test_execute_returns_context_and_records_sources(seeded_vector_store):
    tool = CourseSearchTool(seeded_vector_store)

    out = tool.execute(query="what is a widget")

    assert "Test Course on Widgets" in out
    assert tool.last_sources, "execute should populate last_sources"
    labels = [s["label"] for s in tool.last_sources]
    assert any("Test Course on Widgets" in label for label in labels)


def test_sources_carry_resolved_lesson_url(seeded_vector_store):
    tool = CourseSearchTool(seeded_vector_store)

    tool.execute(query="introduction to widgets", lesson_number=0)

    lesson0 = next(s for s in tool.last_sources if "Lesson 0" in s["label"])
    assert lesson0["url"] == "https://example.com/widgets/lesson0"


def test_format_results_deduplicates_same_course_lesson(seeded_vector_store):
    # Two chunks from the same course+lesson must collapse to a single source.
    tool = CourseSearchTool(seeded_vector_store)
    results = SearchResults(
        documents=["chunk one text", "chunk two text"],
        metadata=[
            {"course_title": "Test Course on Widgets", "lesson_number": 0},
            {"course_title": "Test Course on Widgets", "lesson_number": 0},
        ],
        distances=[0.1, 0.2],
    )

    formatted = tool._format_results(results)

    # Both chunks appear in the context...
    assert "chunk one text" in formatted and "chunk two text" in formatted
    # ...but only one source entry is emitted.
    assert len(tool.last_sources) == 1
    assert tool.last_sources[0]["label"] == "Test Course on Widgets - Lesson 0"


def test_distinct_lessons_produce_distinct_sources(seeded_vector_store):
    tool = CourseSearchTool(seeded_vector_store)
    results = SearchResults(
        documents=["a", "b"],
        metadata=[
            {"course_title": "Test Course on Widgets", "lesson_number": 0},
            {"course_title": "Test Course on Widgets", "lesson_number": 1},
        ],
        distances=[0.1, 0.2],
    )

    tool._format_results(results)

    assert len(tool.last_sources) == 2


def test_tool_manager_get_and_reset_sources(seeded_vector_store):
    manager = ToolManager()
    manager.register_tool(CourseSearchTool(seeded_vector_store))

    manager.execute_tool("search_course_content", query="widget composition")
    assert manager.get_last_sources(), "sources should be available after a search"

    manager.reset_sources()
    assert manager.get_last_sources() == []
