"""Regression tests for real ChromaDB search + filtering.

Runs against the actual seeded vector store (no mocks): semantic search,
course-name resolution, lesson filtering, and the empty/no-match paths.
"""

from search_tools import CourseSearchTool


def test_plain_query_returns_relevant_chunks(seeded_vector_store):
    results = seeded_vector_store.search(query="reusable components")

    assert results.error is None
    assert not results.is_empty()
    assert all(
        m["course_title"] == "Test Course on Widgets" for m in results.metadata
    )


def test_course_name_partial_match_resolves(seeded_vector_store):
    results = seeded_vector_store.search(query="widgets", course_name="Widgets")

    assert results.error is None
    assert not results.is_empty()


def test_unknown_course_name_resolves_to_nearest_when_catalog_nonempty(
    seeded_vector_store,
):
    # NOTE: pins CURRENT behaviour. _resolve_course_name does a top-1 vector
    # search with no distance threshold, so any course_name resolves to the
    # nearest catalog entry — "No course found" is unreachable while the
    # catalog is non-empty. (Latent issue: course filtering can silently fall
    # back to the closest course.)
    results = seeded_vector_store.search(
        query="widgets", course_name="Nonexistent Course"
    )

    assert results.error is None
    assert not results.is_empty()
    assert all(
        m["course_title"] == "Test Course on Widgets" for m in results.metadata
    )


def test_unknown_course_name_errors_on_empty_catalog(empty_vector_store):
    # The genuine "No course found" path: an empty catalog resolves to nothing.
    results = empty_vector_store.search(query="widgets", course_name="Anything")

    assert results.error is not None
    assert "No course found" in results.error
    assert results.is_empty()


def test_lesson_number_filter_restricts_results(seeded_vector_store):
    results = seeded_vector_store.search(query="composition", lesson_number=1)

    assert results.error is None
    assert not results.is_empty()
    assert all(m["lesson_number"] == 1 for m in results.metadata)


def test_no_match_course_surfaces_through_tool(empty_vector_store):
    # Against an empty catalog the tool reports the resolution error verbatim.
    tool = CourseSearchTool(empty_vector_store)

    out = tool.execute(query="anything", course_name="Totally Missing")

    assert "No course found" in out
