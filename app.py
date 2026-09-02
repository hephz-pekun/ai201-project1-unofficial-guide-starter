"""Milestone 5 — grounded generation and query interface.

Answers questions about the ten-book corpus using only the passages retrieved
from ChromaDB, with a book-and-chapter citation for every claim.

Grounding is enforced by three mechanisms, not just by asking the model nicely:

  1. The model never sees the corpus. Only the top-k retrieved chunks go into
     the prompt, so there is nothing else for it to draw on.
  2. The distance threshold measured in embed.py rejects queries whose best
     match is too far away. For an out-of-scope question the model is never
     called at all, so it has no opportunity to invent an answer.
  3. The system prompt requires a [n] citation on every claim, and requires the
     model to say so when the passages do not contain the answer.

    python app.py                       # launch the Gradio interface
    python app.py --ask "..."           # answer one question in the terminal
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time

from dotenv import load_dotenv

# The corpus is full of curly quotes and em dashes, and the model's answers
# quote them back. The Windows console defaults to cp1252, which cannot encode
# them, so printing an answer would raise UnicodeEncodeError.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

from embed import (
    COLLECTION_NAME,
    DISTANCE_THRESHOLD,
    TOP_K,
    citation,
    get_client,
    load_model,
    retrieve,
)

MODEL = "openai/gpt-oss-120b"
# Zero, not a low non-zero value. At 0.1 borderline questions flipped between
# answering and refusing across runs, which makes the README transcripts
# irreproducible. Grounded QA wants the model repeating the passages anyway.
TEMPERATURE = 0.0

# Groq's free tier allows 8,000 tokens per minute, so a run of questions has to
# wait for the window to reset rather than erroring out.
RATE_LIMIT_RETRIES = 3
RATE_LIMIT_WAIT = 35

BOOKS_BLURB = (
    "Pride and Prejudice, The Adventures of Sherlock Holmes, The Art of War, "
    "Alice's Adventures in Wonderland, Moby-Dick, Frankenstein, "
    "A Tale of Two Cities, The Picture of Dorian Gray, Dracula, and "
    "Adventures of Huckleberry Finn"
)

SYSTEM_PROMPT = """You answer questions about classic literature using ONLY the numbered passages supplied in each request.

Rules you must follow:

1. Use only information contained in the supplied passages. Do not use anything you know about these books from other sources, even if you recognise the work and are confident of the answer.
2. Cite the passage number in square brackets after every claim, like [2]. A claim with no citation is not allowed.
3. If the passages do not contain enough information to answer, say so plainly: "The retrieved passages don't contain the answer to that." Do not fill the gap from memory.
4. If the passages describe a similar but different event from the one asked about, say so rather than answering as though they matched. Two scenes can look alike without being the same scene.
5. Quote the text directly where a quotation settles the question.
6. Keep the answer to a few sentences unless the question genuinely needs more.

You are judged on whether every statement is traceable to the passages, not on how complete or confident the answer sounds."""

REFUSAL = (
    "That question doesn't appear to be covered by the ten books in this "
    "collection, so there are no relevant passages to answer from.\n\n"
    f"The collection is: {BOOKS_BLURB}."
)


def format_passages(hits: list[dict]) -> str:
    """Number each passage and label it with its source, so it can be cited."""
    return "\n\n".join(
        f"[{number}] {citation(hit)}\n{hit['text']}"
        for number, hit in enumerate(hits, 1)
    )


def format_sources(hits: list[dict]) -> str:
    return "\n".join(
        f"[{number}] {citation(hit)}  ·  distance {hit['distance']:.3f}"
        for number, hit in enumerate(hits, 1)
    )


def cited_numbers(reply: str) -> list[int]:
    """Passage numbers the model actually cited, in order of first appearance."""
    seen: list[int] = []
    for match in re.finditer(r"\[(\d+)\]", reply):
        number = int(match.group(1))
        if number not in seen:
            seen.append(number)
    return seen


def attribution_block(reply: str, hits: list[dict]) -> str:
    """Resolve the [n] citations to real sources, appended to the answer.

    The README requires source attribution as part of the response, so the
    answer has to stand on its own when copied out of the interface rather
    than relying on a separate panel.
    """
    numbers = [n for n in cited_numbers(reply) if 1 <= n <= len(hits)]
    if not numbers:
        return ""
    return "\n\nSources:\n" + "\n".join(
        f"[{n}] {citation(hits[n - 1])}" for n in numbers
    )


def normalize_citations(text: str) -> str:
    """Normalise the several citation shapes gpt-oss produces down to [n].

    Observed in practice: CJK brackets (【1】) and an annotated form carrying
    line ranges ([12†L1-L5]). Both have to collapse to [12], or the source
    attribution below silently comes out empty.
    """
    text = text.replace("【", "[").replace("】", "]")
    return re.sub(r"\[(\d+)†[^\]]*\]", r"[\1]", text)


def call_groq(question: str, passages: str) -> str:
    from groq import Groq

    load_dotenv()
    if not os.environ.get("GROQ_API_KEY"):
        return "GROQ_API_KEY is not set. Copy .env.example to .env and add your key."

    client = Groq()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": f"Passages:\n\n{passages}\n\nQuestion: {question}"},
    ]

    # gpt-oss models emit chain-of-thought. Keep the effort low, since this task
    # is quotation rather than deliberation, and keep the reasoning out of the
    # visible answer. Retry without those parameters if the API rejects them.
    for extras in ({"reasoning_effort": "low", "reasoning_format": "hidden"}, {}):
        for attempt in range(RATE_LIMIT_RETRIES):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    temperature=TEMPERATURE,
                    **extras,
                )
                return normalize_citations(
                    (response.choices[0].message.content or "").strip()
                )
            except Exception as error:
                text = str(error)
                # The free tier allows 8,000 tokens per minute. Asking several
                # questions in a row trips it, so wait for the window to reset
                # rather than failing the run.
                if "rate_limit" in text or "429" in text:
                    if attempt < RATE_LIMIT_RETRIES - 1:
                        time.sleep(RATE_LIMIT_WAIT)
                        continue
                    return (
                        "Groq rate limit reached (free tier allows 8,000 tokens "
                        "per minute). Wait a minute and ask again."
                    )
                if extras:
                    break  # retry without the reasoning parameters
                return f"Groq request failed: {error}"
    return ""


def answer(question: str, k: int = TOP_K, model=None, collection=None) -> tuple[str, str]:
    """Return (answer, sources) for a question, refusing when out of scope."""
    question = (question or "").strip()
    if not question:
        return "Ask a question about one of the ten books.", ""

    hits = retrieve(question, k=k, model=model, collection=collection)

    if not hits or hits[0]["distance"] > DISTANCE_THRESHOLD:
        best = f"{hits[0]['distance']:.3f}" if hits else "n/a"
        return (
            REFUSAL,
            f"Refused before calling the model: no passage scored below the "
            f"{DISTANCE_THRESHOLD} distance threshold (closest was {best}).",
        )

    reply = call_groq(question, format_passages(hits))
    # Source attribution is part of the response, not a separate panel, so the
    # answer stands alone when copied out.
    return reply + attribution_block(reply, hits), format_sources(hits)


EXAMPLES = [
    "In Pride and Prejudice, why does Elizabeth reject Darcy's first proposal?",
    "In Frankenstein, how does Victor react when the creature comes to life?",
    "Who is Irene Adler, and why is she important to Sherlock Holmes?",
    "Who is Renfield in Dracula?",
    "Why does Huck decide not to betray Jim in Huckleberry Finn?",
    "What is the best pizza restaurant in Chicago?",
]


def launch() -> None:
    import gradio as gr

    # Load the model and collection once, so each question does not reload them.
    model = load_model()
    collection = get_client().get_collection(COLLECTION_NAME)

    def respond(question, k):
        return answer(question, k=int(k), model=model, collection=collection)

    with gr.Blocks(title="The Unofficial Guide to Ten Classics") as demo:
        gr.Markdown(
            "# The Unofficial Guide to Ten Classics\n"
            "Ask about a scene or character you half-remember. Every answer is "
            "drawn only from retrieved passages and carries a chapter citation; "
            "questions outside these ten books are refused.\n\n"
            f"*{BOOKS_BLURB}*"
        )
        with gr.Row():
            question = gr.Textbox(
                label="Your question",
                placeholder="Who is Renfield in Dracula?",
                lines=2,
                scale=4,
            )
            # Upper bound is 20, not 12: about 215 tokens per passage against
            # Groq's 8,000 tokens-per-minute free tier leaves headroom there.
            k = gr.Slider(1, 20, value=TOP_K, step=1,
                          label="Passages to retrieve", scale=1)
        ask = gr.Button("Ask", variant="primary")
        reply = gr.Textbox(label="Answer", lines=8)
        sources = gr.Textbox(label="Sources retrieved", lines=6)

        gr.Examples(examples=[[e] for e in EXAMPLES], inputs=question)

        ask.click(respond, inputs=[question, k], outputs=[reply, sources])
        question.submit(respond, inputs=[question, k], outputs=[reply, sources])

    demo.launch()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--ask", help="answer one question in the terminal")
    parser.add_argument("--k", type=int, default=TOP_K)
    args = parser.parse_args()

    if args.ask:
        reply, sources = answer(args.ask, k=args.k)
        print(f"\nQUESTION: {args.ask}\n")
        print(f"ANSWER:\n{reply}\n")
        print(f"SOURCES:\n{sources}")
    else:
        launch()


if __name__ == "__main__":
    main()
