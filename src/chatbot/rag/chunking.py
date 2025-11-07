"""Semantic-aware text chunking utilities."""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from textwrap import dedent
from uuid import uuid4


@dataclass(slots=True, frozen=True)
class ChunkingConfig:
    """Configuration parameters controlling chunk sizes and overlap."""

    chunk_size: int = 800
    overlap: int = 120
    min_chunk_size: int = 120

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            msg = "chunk_size must be greater than zero"
            raise ValueError(msg)
        if self.overlap < 0:
            msg = "overlap must be non-negative"
            raise ValueError(msg)
        if self.overlap >= self.chunk_size:
            msg = "overlap must be smaller than chunk_size"
            raise ValueError(msg)
        if self.min_chunk_size <= 0:
            msg = "min_chunk_size must be greater than zero"
            raise ValueError(msg)


@dataclass(slots=True, frozen=True)
class Chunk:
    """Represents a chunk of text derived from a larger document."""

    id: str
    content: str
    metadata: dict[str, str] = field(default_factory=dict)


_HEADING_PATTERN = re.compile(r"^#{1,6}\s+.+$", flags=re.MULTILINE)
_FAQ_PATTERN = re.compile(
    r"^\s*\|\s*Question\s*\|\s*Answer\s*\|",
    flags=re.IGNORECASE | re.MULTILINE,
)
_TABLE_ROW_PATTERN = re.compile(r"^\s*\|.*\|$", flags=re.MULTILINE)


def chunk_markdown(
    text: str, config: ChunkingConfig | None = None, *, metadata: dict[str, str] | None = None
) -> list[Chunk]:
    """Split markdown into semantically coherent chunks.

    Headings delineate major sections, FAQ tables are split row-by-row, and long
    bodies are further divided while keeping overlap for context preservation.
    """

    if not text.strip():
        return []

    config = config or ChunkingConfig()
    chunks: list[Chunk] = []

    for heading, body in _iter_sections(text):
        section_metadata = dict(metadata or {})
        has_faq = _FAQ_PATTERN.search(body) is not None
        heading_chunk: Chunk | None = None
        if heading:
            clean_heading = heading.lstrip("# ").strip()
            section_metadata["section"] = clean_heading
            if not has_faq:
                heading_chunk = Chunk(
                    id=str(uuid4()),
                    content=clean_heading,
                    metadata={**section_metadata, "format": "heading"},
                )

        if has_faq:
            chunks.extend(_chunk_faq_table(body, section_metadata))
        else:
            chunks.extend(_chunk_body(body, config, section_metadata))
        if heading_chunk is not None:
            chunks.append(heading_chunk)

    return chunks


def _iter_sections(text: str) -> Iterator[tuple[str, str]]:
    """Yield heading/body tuples for the markdown document."""

    matches = list(_HEADING_PATTERN.finditer(text))
    if not matches:
        yield ("", text)
        return

    first_start = matches[0].start()
    if first_start > 0:
        intro = text[:first_start].strip()
        if intro:
            yield ("", intro)

    for index, current in enumerate(matches):
        heading = current.group(0)
        start = current.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        yield (heading, text[start:end].strip())


def _chunk_body(body: str, config: ChunkingConfig, metadata: dict[str, str]) -> list[Chunk]:
    """Chunk a text body by paragraphs with overlap."""

    paragraphs = [dedent(p).strip() for p in re.split(r"\n{2,}", body) if p.strip()]
    if not paragraphs:
        return []

    assembled: list[str] = []
    current = ""
    for paragraph in paragraphs:
        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= config.chunk_size:
            current = candidate
            continue

        if current:
            assembled.append(current)
        current = paragraph

    if current:
        assembled.append(current)

    chunks: list[Chunk] = []
    for segment in assembled:
        chunks.extend(_split_segment(segment, config, metadata))
    return chunks


def _chunk_faq_table(body: str, metadata: dict[str, str]) -> list[Chunk]:
    """Split FAQ markdown tables into individual rows."""

    rows = [row.strip() for row in _TABLE_ROW_PATTERN.findall(body)]
    chunks: list[Chunk] = []
    for row in rows:
        clean = row.strip("| ").lower()
        condensed = clean.replace("-", "").replace("|", "").strip()
        if not condensed or clean.startswith("question"):
            continue

        cells = [cell.strip() for cell in row.strip("|").split("|")]
        if len(cells) >= 2:
            question, answer = cells[0], cells[1]
            formatted = f"Q: {question}\nA: {answer}"
            chunks.append(
                Chunk(
                    id=str(uuid4()),
                    content=formatted.strip(),
                    metadata={**metadata, "format": "faq"},
                )
            )
    return chunks


def _split_segment(segment: str, config: ChunkingConfig, metadata: dict[str, str]) -> list[Chunk]:
    """Split a long segment into overlapping windows."""

    if len(segment) <= config.chunk_size or len(segment) <= config.min_chunk_size:
        return [Chunk(id=str(uuid4()), content=segment.strip(), metadata={**metadata})]

    chunk_size = config.chunk_size
    overlap = config.overlap
    start = 0
    length = len(segment)
    chunks: list[Chunk] = []

    while start < length:
        end = min(start + chunk_size, length)
        chunk_text = segment[start:end].strip()
        chunks.append(
            Chunk(
                id=str(uuid4()),
                content=chunk_text,
                metadata={**metadata, "index": str(len(chunks))},
            )
        )
        if end == length:
            break
        start = end - overlap

    return chunks
