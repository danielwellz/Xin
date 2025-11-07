from __future__ import annotations

import pytest

from chatbot.rag.chunking import ChunkingConfig, chunk_markdown

pytestmark = pytest.mark.unit


def test_default_chunking_config_matches_reference() -> None:
    config = ChunkingConfig()
    assert config.chunk_size == 512
    assert config.overlap == 64
    assert config.min_chunk_size == 128


def test_chunk_markdown_splits_faq_rows() -> None:
    markdown = """
    # FAQ

    | Question | Answer |
    | --- | --- |
    | What is your return policy? | Returns accepted within 30 days. |
    | How do I track my order? | Use the tracking link emailed after shipping. |
    """

    chunks = chunk_markdown(markdown)

    assert len(chunks) == 2
    assert all(chunk.metadata.get("format") == "faq" for chunk in chunks)
    assert "return policy" in chunks[0].content.lower()


def test_chunk_markdown_applies_overlap() -> None:
    long_paragraph = (
        "This is a very long paragraph designed to test overlap handling. "
        "It should be split into multiple chunks while preserving context for "
        "the reader across boundaries. "
    )
    markdown = f"# Intro\n\n{long_paragraph * 5}"
    config = ChunkingConfig(chunk_size=150, overlap=50, min_chunk_size=50)

    chunks = chunk_markdown(markdown, config)

    assert len(chunks) > 1
    # Ensure that the trailing text of the first chunk appears in the next chunk
    first_end = chunks[0].content[-50:]
    assert first_end.strip() in chunks[1].content


def test_chunk_markdown_captures_intro_without_heading() -> None:
    markdown = "Preface paragraph before headings.\n\n# Heading\nContent here."

    chunks = chunk_markdown(markdown)

    assert any("Preface" in chunk.content for chunk in chunks)
