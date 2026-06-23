"""Regression tests for document parsing and chunking (pure, deterministic)."""

from document_processor import DocumentProcessor


def test_parses_course_metadata_and_lessons(document_processor, sample_course_file):
    course, chunks = document_processor.process_course_document(str(sample_course_file))

    assert course.title == "Test Course on Widgets"
    assert course.course_link == "https://example.com/widgets"
    assert course.instructor == "Ada Lovelace"
    assert [l.lesson_number for l in course.lessons] == [0, 1]
    assert course.lessons[0].title == "Introduction to Widgets"
    assert course.lessons[1].lesson_link == "https://example.com/widgets/lesson1"
    assert chunks  # at least one chunk produced


def test_chunk_metadata_and_indices(document_processor, sample_course_file):
    _, chunks = document_processor.process_course_document(str(sample_course_file))

    # All chunks attributed to the course; indices are 0..n-1 in order.
    assert all(c.course_title == "Test Course on Widgets" for c in chunks)
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))
    assert all(c.lesson_number in (0, 1) for c in chunks)


def test_long_lesson_is_split_into_multiple_chunks(document_processor, sample_course_file):
    _, chunks = document_processor.process_course_document(str(sample_course_file))

    lesson0_chunks = [c for c in chunks if c.lesson_number == 0]
    assert len(lesson0_chunks) >= 2, "long lesson 0 should span multiple chunks"
    # The first chunk of a lesson is prefixed with lesson context.
    assert lesson0_chunks[0].content.startswith("Lesson 0 content:")


def test_chunk_text_respects_size_and_overlaps():
    # Sentences (~11 chars) are shorter than the overlap (20), so the overlap
    # window captures whole sentences and they reappear in the next chunk.
    proc = DocumentProcessor(chunk_size=50, chunk_overlap=20)
    sentences = [f"Part {i} end." for i in range(12)]
    text = " ".join(sentences)

    chunks = proc.chunk_text(text)

    assert len(chunks) > 1
    # No chunk grossly exceeds the configured size (sentences are small here).
    assert all(len(c) <= 50 + 20 for c in chunks)
    # Overlap re-emits sentences, so total occurrences exceed the 12 unique ones.
    total_occurrences = sum(c.count("Part ") for c in chunks)
    assert total_occurrences > len(sentences)
