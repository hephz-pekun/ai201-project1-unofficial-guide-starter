"""Print representative chunks from chunks.json for inspection.

Five books are chosen to cover the structurally different source types in the
corpus: dialogue-heavy prose, non-narrative aphorisms, epistolary journal
entries, phonetic dialect, and long-form narrative. Selection is deterministic,
so re-running gives the same chunks and they can be pasted into README.md.

    python sample_chunks.py              # 5 representative chunks
    python sample_chunks.py --embed      # also show the embedded text
    python sample_chunks.py --book Moby  # every sample from one book
"""

import argparse
import json
import sys
from pathlib import Path

CHUNKS_FILE = Path(__file__).parent / "chunks.json"

# (book title prefix, why this book is here)
REPRESENTATIVE = [
    ("Pride and Prejudice", "dialogue-heavy Regency prose"),
    ("The Art of War", "non-narrative numbered aphorisms"),
    ("Dracula", "epistolary journal entry"),
    ("Adventures of Huckleberry Finn", "phonetic vernacular dialect"),
    ("Moby-Dick", "long-form narrative and digression"),
]


def load_chunks():
    if not CHUNKS_FILE.exists():
        sys.exit(f"{CHUNKS_FILE.name} not found — run `python ingest.py` first.")
    return json.loads(CHUNKS_FILE.read_text(encoding="utf-8"))


def pick(chunks, prefix):
    """Choose one full-length chunk from a book, deterministically."""
    pool = [c for c in chunks if c["book_title"].startswith(prefix)]
    if not pool:
        return None
    # Prefer chunks near the target size so samples are not runt end-of-chapter
    # fragments, and take one a third of the way in to avoid front matter.
    full = [c for c in pool if 700 <= len(c["text"]) <= 900] or pool
    return full[len(full) // 3]


def show(chunk, note, show_embed):
    title = chunk["chapter_title"]
    heading = chunk["chapter_label"] + (f": {title}" if title else "")
    print("=" * 78)
    print(f"SOURCE   {chunk['book_title']} — {chunk['author']}")
    print(f"CHAPTER  {heading}")
    print(f"CHUNK    index {chunk['chunk_index']} · {len(chunk['text'])} chars · {note}")
    print("-" * 78)
    print(chunk["text"])
    if show_embed:
        print("-" * 78)
        print("EMBEDDED AS:")
        print(chunk["embed_text"][:200] + " ...")
    print()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--embed", action="store_true", help="show the embedded text too")
    parser.add_argument("--book", help="show 5 chunks from one book instead")
    args = parser.parse_args()

    chunks = load_chunks()

    if args.book:
        pool = [c for c in chunks if args.book.lower() in c["book_title"].lower()]
        if not pool:
            sys.exit(f"No book matching {args.book!r}.")
        step = max(1, len(pool) // 6)
        for chunk in pool[step::step][:5]:
            show(chunk, "sampled", args.embed)
        return

    for prefix, note in REPRESENTATIVE:
        chunk = pick(chunks, prefix)
        if chunk:
            show(chunk, note, args.embed)


if __name__ == "__main__":
    main()
