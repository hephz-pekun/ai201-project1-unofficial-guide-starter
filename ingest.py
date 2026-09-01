"""Milestone 3 — document ingestion and chunking.

Implements the Chunking Strategy section of planning.md:

  * ~800 character chunks, 1,000 character hard maximum
  * 150 character overlap between consecutive chunks
  * paragraph-based and chapter-bounded: whole paragraphs are packed together
    and a chunk never crosses a chapter boundary
  * oversized paragraphs are split at sentence boundaries
  * metadata per chunk: book title, author, Gutenberg ID, chapter number,
    chapter title, chunk index
  * the book and chapter title are prepended to the text before embedding

Run it directly to build chunks.json and print verification statistics:

    python ingest.py
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, asdict, field
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).parent / "documents"
OUTPUT_FILE = Path(__file__).parent / "chunks.json"

TARGET_CHARS = 800
MAX_CHARS = 1000
OVERLAP_CHARS = 150


# --------------------------------------------------------------------------
# Per-book configuration
# --------------------------------------------------------------------------
# Every book formats its chapter headings differently, so each one gets its own
# pattern. Each pattern must expose two named groups:
#   num   - the chapter identifier (roman numerals, digits, or a word)
#   title - the chapter title, which may be empty in the book's body
#
# expected_chapters is ground truth used by verify() to catch silent breakage.


@dataclass
class BookConfig:
    filename: str
    title: str
    author: str
    gutenberg_id: int
    heading: str
    expected_chapters: int
    # Some books mark sections with a keyword ("Letter 1" vs "Chapter 1"), which
    # must be part of the identity or the two collide.
    keyed_by_kind: bool = False
    # The Art of War carries the translator's commentary in square brackets.
    strip_brackets: bool = False
    # A Tale of Two Cities restarts its chapter numbering inside each "Book",
    # so the enclosing section has to be part of the chapter's identity.
    section: str | None = None


BOOKS: list[BookConfig] = [
    BookConfig(
        filename="pride-and-prejudice.txt",
        title="Pride and Prejudice",
        author="Jane Austen",
        gutenberg_id=1342,
        # Chapter I appears only as "Chapter I.]", closing an illustration
        # caption, so both the mixed case and the trailing bracket are optional.
        heading=r"^[ \t]*(?:CHAPTER|Chapter)[ \t]+(?P<num>[IVXLC]+)\.?\]?[ \t]*(?P<title>)$",
        expected_chapters=61,
    ),
    BookConfig(
        filename="adventures-of-sherlock-holmes.txt",
        title="The Adventures of Sherlock Holmes",
        author="Arthur Conan Doyle",
        gutenberg_id=1661,
        # A short story collection: no CHAPTER keyword, just a roman numeral.
        heading=r"^[ \t]*(?P<num>[IVXLC]+)\.[ \t]+(?P<title>\S.*?)[ \t]*$",
        expected_chapters=12,
    ),
    BookConfig(
        filename="the-art-of-war.txt",
        title="The Art of War",
        author="Sun Tzu (translated by Lionel Giles)",
        gutenberg_id=132,
        heading=r"^[ \t]*Chapter[ \t]+(?P<num>[IVXLC]+)\.?[ \t]*(?P<title>.*?)[ \t]*$",
        expected_chapters=13,
        strip_brackets=True,
    ),
    BookConfig(
        filename="alices-adventures-in-wonderland.txt",
        title="Alice's Adventures in Wonderland",
        author="Lewis Carroll",
        gutenberg_id=11,
        heading=r"^[ \t]*CHAPTER[ \t]+(?P<num>[IVXLC]+)\.[ \t]*(?P<title>.*?)[ \t]*$",
        expected_chapters=12,
    ),
    BookConfig(
        filename="moby-dick.txt",
        title="Moby-Dick; or, The Whale",
        author="Herman Melville",
        gutenberg_id=2701,
        heading=r"^[ \t]*CHAPTER[ \t]+(?P<num>\d+)\.[ \t]*(?P<title>.*?)[ \t]*$",
        expected_chapters=135,
    ),
    BookConfig(
        filename="frankenstein.txt",
        title="Frankenstein; or, The Modern Prometheus",
        author="Mary Wollstonecraft Shelley",
        gutenberg_id=84,
        # Four opening letters, then twenty-four chapters, both Arabic.
        heading=r"^[ \t]*(?P<kind>Letter|Chapter)[ \t]+(?P<num>\d+)[ \t]*(?P<title>)$",
        expected_chapters=28,
        keyed_by_kind=True,
    ),
    BookConfig(
        filename="a-tale-of-two-cities.txt",
        title="A Tale of Two Cities",
        author="Charles Dickens",
        gutenberg_id=98,
        # Chapter numbers restart in each of the three Books, so the roman
        # numeral alone is not unique and the section must key it too.
        heading=r"^[ \t]*CHAPTER[ \t]+(?P<num>[IVXLC]+)\.?[ \t]*(?P<title>.*?)[ \t]*$",
        expected_chapters=45,
        section=r"^[ \t]*(?P<name>Book the [A-Za-z]+)",
    ),
    BookConfig(
        filename="the-picture-of-dorian-gray.txt",
        title="The Picture of Dorian Gray",
        author="Oscar Wilde",
        gutenberg_id=174,
        heading=r"^[ \t]*CHAPTER[ \t]+(?P<num>[IVXLC]+)\.?[ \t]*(?P<title>.*?)[ \t]*$",
        expected_chapters=20,
    ),
    BookConfig(
        filename="dracula.txt",
        title="Dracula",
        author="Bram Stoker",
        gutenberg_id=345,
        heading=r"^[ \t]*CHAPTER[ \t]+(?P<num>[IVXLC]+)\.?[ \t]*(?P<title>.*?)[ \t]*$",
        expected_chapters=27,
    ),
    BookConfig(
        filename="adventures-of-huckleberry-finn.txt",
        title="Adventures of Huckleberry Finn",
        author="Mark Twain",
        gutenberg_id=76,
        # The final chapter is "CHAPTER THE LAST" rather than a numeral.
        heading=r"^[ \t]*CHAPTER[ \t]+(?P<num>[IVXLC]+|THE LAST)\.?[ \t]*(?P<title>.*?)[ \t]*$",
        expected_chapters=43,
    ),
]


# --------------------------------------------------------------------------
# Preprocessing
# --------------------------------------------------------------------------

_START_MARKER = re.compile(r"^\*\*\* START OF THE PROJECT GUTENBERG EBOOK.*$", re.M)
_END_MARKER = re.compile(r"^\*\*\* END OF THE PROJECT GUTENBERG EBOOK.*$", re.M)
_ILLUSTRATION = re.compile(r"\[Illustration(?::.*?)?\]", re.S)
# Pride and Prejudice hides its Chapter I heading at the end of an illustration
# caption, so the marker must be rescued before captions are stripped.
_CAPTION_CHAPTER = re.compile(
    r"\[Illustration:(?:(?!\[Illustration:).)*?\bChapter[ \t]+(?P<num>[IVXLC]+)\.\]",
    re.S,
)
_BRACKETED = re.compile(r"\[[^\[\]]*\]", re.S)
_SENTENCE_END = re.compile(r'(?<=[.!?])["”’\')\]]*\s+')


def strip_boilerplate(text: str) -> str:
    """Drop the Gutenberg header, footer, and trailing licence block.

    Verified present and identically formatted in all ten source files.
    """
    start = _START_MARKER.search(text)
    end = _END_MARKER.search(text)
    if not start or not end:
        raise ValueError("Gutenberg START/END markers not found")
    return text[start.end():end.start()]


def normalize_paragraphs(text: str) -> list[str]:
    """Rejoin hard-wrapped lines into continuous paragraphs.

    Gutenberg files wrap at roughly 72 characters mid-sentence. Paragraphs are
    separated by blank lines, so split on those and join the lines within.
    """
    paragraphs = []
    for block in re.split(r"\n[ \t]*\n+", text):
        joined = " ".join(line.strip() for line in block.splitlines())
        joined = re.sub(r"\s+", " ", joined).strip()
        if joined:
            paragraphs.append(joined)
    return paragraphs


ROMAN_VALUES = {"I": 1, "V": 5, "X": 10, "L": 50, "C": 100, "D": 500, "M": 1000}


def roman_to_int(numeral: str) -> int | None:
    total = 0
    previous = 0
    for char in reversed(numeral.upper()):
        value = ROMAN_VALUES.get(char)
        if value is None:
            return None
        total = total - value if value < previous else total + value
        previous = max(previous, value)
    return total


@dataclass
class Chapter:
    number: int
    label: str
    title: str
    text: str


def find_chapters(text: str, config: BookConfig) -> list[Chapter]:
    """Locate chapter bodies, discarding the table of contents.

    Every book repeats its chapter headings in a TOC before the body, so each
    heading matches at least twice. The body is always the *last* occurrence.
    Chapter titles, however, usually appear only in the TOC - the body heading
    is often bare - so the title is taken from the *first* occurrence. Slicing
    from the first body heading also discards front matter such as Pride and
    Prejudice's list of illustrations and The Art of War's translator preface.
    """
    pattern = re.compile(config.heading, re.M)

    # Sections ("Book the First") scope the chapter numbering in some books.
    sections: list[tuple[int, str]] = []
    if config.section:
        for match in re.finditer(config.section, text, re.M):
            sections.append((match.start(), match.group("name").strip()))

    def section_at(position: int) -> str:
        label = ""
        for start, name in sections:
            if start <= position:
                label = name
            else:
                break
        return label

    occurrences: dict[str, dict] = {}
    order: list[str] = []
    for match in pattern.finditer(text):
        num = match.group("num").strip()
        kind = match.groupdict().get("kind") or ""
        section = section_at(match.start())

        key = f"{kind}:{num}" if config.keyed_by_kind else num
        if section:
            key = f"{section}:{key}"

        title = (match.groupdict().get("title") or "").strip()
        title = title.rstrip(".").strip()

        if key not in occurrences:
            occurrences[key] = {
                "title": "", "start": None, "end": None,
                "num": num, "kind": kind, "section": section,
            }
            order.append(key)
        record = occurrences[key]
        # First occurrence wins for the title, last wins for the position.
        if title and not record["title"]:
            record["title"] = title
        record["start"] = match.start()
        record["end"] = match.end()

    if not occurrences:
        return []

    starts = sorted((rec["start"], key) for key, rec in occurrences.items())

    chapters: list[Chapter] = []
    for position, (start, key) in enumerate(starts):
        record = occurrences[key]
        stop = starts[position + 1][0] if position + 1 < len(starts) else len(text)
        body = text[record["end"]:stop]

        number = roman_to_int(record["num"])
        if number is None:
            number = int(record["num"]) if record["num"].isdigit() else position + 1

        kind = record["kind"] or "Chapter"
        label = f"{kind} {record['num']}"
        if record["section"]:
            label = f"{record['section']}, {label}"

        chapters.append(
            Chapter(
                number=position + 1,
                label=label,
                title=record["title"],
                text=body,
            )
        )
    return chapters


# --------------------------------------------------------------------------
# Chunking
# --------------------------------------------------------------------------


def split_long_paragraph(paragraph: str, limit: int) -> list[str]:
    """Split an oversized paragraph at sentence boundaries."""
    sentences = _SENTENCE_END.split(paragraph)
    pieces: list[str] = []
    current = ""
    for sentence in sentences:
        if not sentence:
            continue
        candidate = f"{current} {sentence}".strip() if current else sentence
        if len(candidate) <= limit:
            current = candidate
            continue
        if current:
            pieces.append(current)
        # A single sentence longer than the limit is split on whitespace.
        while len(sentence) > limit:
            cut = sentence.rfind(" ", 0, limit)
            cut = cut if cut > 0 else limit
            pieces.append(sentence[:cut].strip())
            sentence = sentence[cut:].strip()
        current = sentence
    if current:
        pieces.append(current)
    return pieces


def tail_overlap(text: str, size: int) -> str:
    """Take the last `size` characters, trimmed forward to a word boundary."""
    if len(text) <= size:
        return text
    tail = text[-size:]
    space = tail.find(" ")
    return tail[space + 1:] if space != -1 else tail


def chunk_paragraphs(
    paragraphs: list[str],
    target: int = TARGET_CHARS,
    maximum: int = MAX_CHARS,
    overlap: int = OVERLAP_CHARS,
) -> list[str]:
    """Pack whole paragraphs into chunks of roughly `target` characters.

    Paragraphs are kept intact wherever possible. The overlap budget is
    reserved up front so that adding it can never push a chunk past `maximum`:
    a carried overlap of `overlap` chars, plus the two-character paragraph
    separator, plus one unit must all fit inside `maximum`.
    """
    budget = maximum - overlap - 2
    units: list[str] = []
    for paragraph in paragraphs:
        if len(paragraph) > budget:
            units.extend(split_long_paragraph(paragraph, budget))
        else:
            units.append(paragraph)

    chunks: list[str] = []
    current = ""
    for unit in units:
        candidate = f"{current}\n\n{unit}" if current else unit
        if current and len(candidate) > target:
            chunks.append(current)
            carry = tail_overlap(current, overlap)
            current = f"{carry}\n\n{unit}" if carry else unit
        else:
            current = candidate
    if current.strip():
        chunks.append(current)
    return chunks


# --------------------------------------------------------------------------
# Assembly
# --------------------------------------------------------------------------


@dataclass
class Chunk:
    book_title: str
    author: str
    gutenberg_id: int
    chapter_number: int
    chapter_label: str
    chapter_title: str
    chunk_index: int
    text: str
    embed_text: str = field(default="")


def build_embed_text(chunk_text: str, book_title: str, chapter_label: str, chapter_title: str) -> str:
    """Prepend book and chapter context, per the Chunking Strategy section.

    Kept separate from `text` so responses can quote the passage itself without
    the synthetic header appearing in the citation.
    """
    heading = f"{book_title} — {chapter_label}"
    if chapter_title:
        heading = f"{heading}: {chapter_title}"
    return f"{heading}\n\n{chunk_text}"


def ingest_book(config: BookConfig) -> tuple[list[Chunk], list[Chapter]]:
    path = DOCUMENTS_DIR / config.filename
    text = path.read_text(encoding="utf-8")

    text = strip_boilerplate(text)
    text = _CAPTION_CHAPTER.sub(lambda m: f"\n\nCHAPTER {m.group('num')}.\n\n", text)
    text = _ILLUSTRATION.sub(" ", text)
    if config.strip_brackets:
        # The Giles edition interleaves ~45% commentary in square brackets.
        text = _BRACKETED.sub(" ", text)

    chapters = find_chapters(text, config)

    chunks: list[Chunk] = []
    index = 0
    for chapter in chapters:
        paragraphs = normalize_paragraphs(chapter.text)
        for chunk_text in chunk_paragraphs(paragraphs):
            chunks.append(
                Chunk(
                    book_title=config.title,
                    author=config.author,
                    gutenberg_id=config.gutenberg_id,
                    chapter_number=chapter.number,
                    chapter_label=chapter.label,
                    chapter_title=chapter.title,
                    chunk_index=index,
                    text=chunk_text,
                    embed_text=build_embed_text(
                        chunk_text, config.title, chapter.label, chapter.title
                    ),
                )
            )
            index += 1
    return chunks, chapters


def main() -> None:
    all_chunks: list[Chunk] = []
    problems: list[str] = []

    print(f"{'book':<42}{'chapters':>10}{'expected':>10}{'chunks':>9}{'avg':>7}{'max':>7}")
    print("-" * 85)

    for config in BOOKS:
        chunks, chapters = ingest_book(config)
        all_chunks.extend(chunks)

        lengths = [len(c.text) for c in chunks] or [0]
        average = sum(lengths) // len(lengths)
        longest = max(lengths)

        flag = "" if len(chapters) == config.expected_chapters else "  <-- MISMATCH"
        if flag:
            problems.append(
                f"{config.title}: found {len(chapters)} chapters, expected {config.expected_chapters}"
            )
        if longest > MAX_CHARS:
            problems.append(f"{config.title}: chunk of {longest} chars exceeds {MAX_CHARS}")

        print(
            f"{config.title[:40]:<42}{len(chapters):>10}{config.expected_chapters:>10}"
            f"{len(chunks):>9}{average:>7}{longest:>7}{flag}"
        )

    lengths = [len(c.text) for c in all_chunks]
    print("-" * 85)
    print(f"{'TOTAL':<42}{'':>10}{'':>10}{len(all_chunks):>9}"
          f"{sum(lengths) // len(lengths):>7}{max(lengths):>7}")

    OUTPUT_FILE.write_text(
        json.dumps([asdict(c) for c in all_chunks], ensure_ascii=False, indent=1),
        encoding="utf-8",
    )
    print(f"\nWrote {len(all_chunks):,} chunks to {OUTPUT_FILE.name}")

    if problems:
        print("\nPROBLEMS:")
        for problem in problems:
            print(f"  - {problem}")
    else:
        print("All chapter counts match and no chunk exceeds the maximum.")


if __name__ == "__main__":
    main()
