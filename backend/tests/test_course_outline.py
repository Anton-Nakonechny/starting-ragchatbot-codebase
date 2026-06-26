"""Tests for CourseOutlineTool — the course-structure/outline tool.

Exercises the tool against the real seeded vector store (sample course
"Test Course on Widgets" with two lessons), plus the ToolManager wiring and
the end-to-end query path with a scripted Anthropic client.
"""

from search_tools import CourseOutlineTool, ToolManager

from tests.conftest import text_response, tool_use_response


def test_definition_exposes_name_and_required_course_name():
    tool = CourseOutlineTool(vector_store=None)

    definition = tool.get_tool_definition()

    assert definition["name"] == "get_course_outline"
    assert definition["input_schema"]["required"] == ["course_name"]
    assert "course_name" in definition["input_schema"]["properties"]


def test_execute_returns_title_link_and_full_lesson_list(seeded_vector_store):
    tool = CourseOutlineTool(seeded_vector_store)

    # Partial / fuzzy name should still resolve to the seeded course.
    out = tool.execute(course_name="Widgets")

    assert "Test Course on Widgets" in out
    assert "https://example.com/widgets" in out
    # Both lessons, with their numbers and titles.
    assert "Lesson 0: Introduction to Widgets" in out
    assert "Lesson 1: Advanced Widget Composition" in out


def test_execute_records_course_source(seeded_vector_store):
    tool = CourseOutlineTool(seeded_vector_store)

    tool.execute(course_name="Widgets")

    assert tool.last_sources, "execute should populate last_sources"
    src = tool.last_sources[0]
    assert src["label"] == "Test Course on Widgets"
    assert src["url"] == "https://example.com/widgets"


def test_execute_no_matching_course_returns_message(empty_vector_store):
    # With an empty catalog, name resolution finds nothing.
    tool = CourseOutlineTool(empty_vector_store)

    out = tool.execute(course_name="Nonexistent Course")

    assert "No course found" in out
    assert tool.last_sources == []


def test_tool_manager_routes_and_surfaces_sources(seeded_vector_store):
    manager = ToolManager()
    manager.register_tool(CourseOutlineTool(seeded_vector_store))

    out = manager.execute_tool("get_course_outline", course_name="Widgets")

    assert "Lesson 1: Advanced Widget Composition" in out
    assert manager.get_last_sources(), "sources should be available after outline"


def test_query_uses_outline_tool_end_to_end(seeded_rag_system):
    fake = seeded_rag_system.ai_generator.client
    fake.responses = [
        tool_use_response("get_course_outline", {"course_name": "Widgets"}),
        text_response("The Widgets course has two lessons."),
    ]

    answer, sources = seeded_rag_system.query("Give me the outline of the Widgets course")

    assert answer == "The Widgets course has two lessons."
    assert sources and sources[0]["label"] == "Test Course on Widgets"
    # The outline tool's definition must have been advertised to Claude.
    tool_names = {t["name"] for t in fake.calls[0]["tools"]}
    assert "get_course_outline" in tool_names
