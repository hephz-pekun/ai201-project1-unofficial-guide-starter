# The Unofficial Guide — Project 1

A retrieval-augmented question answering system over ten public-domain classic books. Ask about a scene or character you half-remember, and get an answer drawn only from the retrieved passages, with a chapter citation for every claim.

---

## Domain

**Passage-level recall across a personal library of ten classic books.**

This system answers the question a reader actually has weeks after finishing a book: *there was a scene where someone did something — where was it, and what happened?* You remember a character existed, or that a moment mattered, but not the words. Ctrl-F cannot help, because it needs the exact phrase you have forgotten. The alternative is rereading 130,000 words to find one paragraph.

This knowledge is not secret, but it is **inaccessible**, and that is the gap the project fills. A published novel ships with a table of contents and nothing else: no index of events, no record of who did what to whom, no way to ask a question in the words you happen to remember. The official channels fail in specific ways:

- **Publishers** provide chapter numbers. There is no official "what happened in chapter 12" lookup for any book in this corpus.
- **Search engines** answer only the famous questions. "Why does Elizabeth refuse Darcy?" is answerable; "the bit where the sister writes home about the officers" is not, because it was never notable enough for anyone to write about.
- **Study guides** such as SparkNotes work at chapter-summary altitude. They confirm a plot beat existed; they cannot show the passage, quote what a character said, or tell you which of three similar scenes you are thinking of.
- **Fan wikis** are spoiler-soaked by design and, for older literary fiction, thin or absent.

The corpus deliberately spreads across authors, genres and centuries rather than staying in one series: Regency social comedy, detective short stories, gothic horror, American vernacular satire, a whaling epic and a classical military treatise. That tests something a single-series corpus cannot — whether retrieval can keep ten distinct worlds apart when several of them share vocabulary and register.

---

## Document Sources

All ten sources are Project Gutenberg plain-text files, public domain, stored in `documents/`. Total corpus: **1,119,924 words**, about 6.3 MB.

| # | Source | Type | URL or file path |
|---|--------|------|-----------------|
| 1 | *Pride and Prejudice* — Jane Austen | Novel, 61 chapters, 130,412 words | [gutenberg.org/ebooks/1342](https://www.gutenberg.org/ebooks/1342) → `documents/pride-and-prejudice.txt` |
| 2 | *The Adventures of Sherlock Holmes* — Arthur Conan Doyle | Short story collection, 12 stories, 107,518 words | [gutenberg.org/ebooks/1661](https://www.gutenberg.org/ebooks/1661) → `documents/adventures-of-sherlock-holmes.txt` |
| 3 | *The Art of War* — Sun Tzu, trans. Lionel Giles | Non-narrative treatise, 13 chapters, 58,075 words | [gutenberg.org/ebooks/132](https://www.gutenberg.org/ebooks/132) → `documents/the-art-of-war.txt` |
| 4 | *Alice's Adventures in Wonderland* — Lewis Carroll | Children's fantasy, 12 chapters, 29,565 words | [gutenberg.org/ebooks/11](https://www.gutenberg.org/ebooks/11) → `documents/alices-adventures-in-wonderland.txt` |
| 5 | *Moby-Dick; or, The Whale* — Herman Melville | Novel, 135 chapters, 215,840 words | [gutenberg.org/ebooks/2701](https://www.gutenberg.org/ebooks/2701) → `documents/moby-dick.txt` |
| 6 | *Frankenstein* — Mary Shelley | Epistolary novel, 4 letters + 24 chapters, 78,101 words | [gutenberg.org/ebooks/84](https://www.gutenberg.org/ebooks/84) → `documents/frankenstein.txt` |
| 7 | *A Tale of Two Cities* — Charles Dickens | Historical novel, 45 chapters in 3 books, 138,930 words | [gutenberg.org/ebooks/98](https://www.gutenberg.org/ebooks/98) → `documents/a-tale-of-two-cities.txt` |
| 8 | *The Picture of Dorian Gray* — Oscar Wilde | Novel, 20 chapters, 82,025 words | [gutenberg.org/ebooks/174](https://www.gutenberg.org/ebooks/174) → `documents/the-picture-of-dorian-gray.txt` |
| 9 | *Dracula* — Bram Stoker | Epistolary novel, 27 chapters, 164,352 words | [gutenberg.org/ebooks/345](https://www.gutenberg.org/ebooks/345) → `documents/dracula.txt` |
| 10 | *Adventures of Huckleberry Finn* — Mark Twain | Novel in vernacular dialect, 43 chapters, 114,126 words | [gutenberg.org/ebooks/76](https://www.gutenberg.org/ebooks/76) → `documents/adventures-of-huckleberry-finn.txt` |

The variety is deliberate. It tests whether the system can distinguish similar characters, themes and events across works — particularly the three gothic-adjacent sources (*Frankenstein*, *Dracula*, *Dorian Gray*), which share register and imagery.

---

## Chunking Strategy

**Chunk size:** 800 characters target, 1,000 hard maximum
**Overlap:** 150 characters
**Final chunk count:** **10,301 chunks** (mean 692 characters, longest 998)

### Preprocessing

Five steps, all driven by things I found by inspecting the actual files rather than assuming.

1. **Strip Gutenberg boilerplate.** Keep only what lies between the `*** START OF THE PROJECT GUTENBERG EBOOK` and `*** END OF` markers, which are identically formatted in all ten files. The trailing licence block is about 350 lines of legal text that would otherwise become chunks matching nothing useful.

2. **Discard the table of contents.** Every book repeats its chapter headings in a TOC, so each heading matches at least twice — Alice matched 24 headings for 12 real chapters, Moby-Dick 276 for 138. Without this the pipeline emits a one-line garbage chunk per TOC entry. The rule is to take the **last** occurrence of each chapter heading as the body, which also discards front matter such as Pride and Prejudice's list of illustrations. Chapter *titles*, however, are taken from the **first** occurrence, because most books have bare headings in the body (`CHAPTER X.`) and carry the title only in the TOC.

3. **Rejoin hard-wrapped lines into paragraphs.** All files wrap at about 72 characters mid-sentence. I split on blank lines to find paragraph boundaries, then join the lines within each.

4. **Detect chapter boundaries per book.** The formats genuinely differ, so this is a configuration table rather than one pattern:

   | Book | Heading format |
   |---|---|
   | Alice, Dorian Gray, Huck Finn | `CHAPTER III.` |
   | Pride and Prejudice | `CHAPTER III.`, but chapter I appears only as `Chapter I.]` inside an illustration caption |
   | Moby-Dick | `CHAPTER 3. The Spouter-Inn.` (Arabic numerals) |
   | Dracula | `CHAPTER III. Jonathan Harker's Journal` |
   | A Tale of Two Cities | `     CHAPTER III    The Night Shadows` (indented; numbering restarts each Book) |
   | Frankenstein | `Letter 1`–`Letter 4`, then `Chapter 1`–`Chapter 24` |
   | Sherlock Holmes | `   III.   A Case of Identity` — no `CHAPTER` keyword at all |
   | The Art of War | `Chapter III. ATTACK BY STRATAGEM` |

5. **Extra cleaning for The Art of War.** The Gutenberg edition is Lionel Giles' 1910 critical edition: only about 10,000 of its 58,075 words are Sun Tzu. Slicing from the first body chapter drops Giles' introduction on manuscript provenance, and a pass over square-bracketed blocks removes his inline annotations.

### Chunking algorithm

Paragraph-packed and chapter-bounded. Whole paragraphs accumulate until adding the next would exceed 800 characters, then the chunk is emitted and the next begins with 150 characters of overlap. A chunk never crosses a chapter boundary. A paragraph too long to fit on its own is split at sentence boundaries.

Every chunk stores `book_title`, `author`, `gutenberg_id`, `chapter_number`, `chapter_label`, `chapter_title` and `chunk_index`. Before embedding, the book and chapter are prepended:

```
Alice's Adventures in Wonderland — Chapter I: Down the Rabbit-Hole

<chunk text>
```

The prefixed version is what gets embedded; the bare passage is what gets stored and quoted, so the synthetic header never leaks into a citation.

### Why these choices fit these documents

**Why 800 characters.** The binding constraint is the embedding model, not the prose. `all-MiniLM-L6-v2` truncates at 256 word-pieces, roughly 1,000 characters of English. Anything past that is *silently* discarded at embedding time — still stored, still returned if retrieved, but contributing nothing to whether the chunk was findable. An 800-character target with a 1,000 cap keeps every chunk inside that window with headroom for the prefix. Narrative prose would prefer larger chunks, and accepting that ceiling has a real cost, discussed in the failure analysis.

**Why paragraphs rather than fixed character splits.** A paragraph is the smallest self-contained unit of narrative prose. A blind character split lands mid-sentence and separates an action from its subject.

**Why 150 characters of overlap.** Scenes are built as setup then payoff, and a hard boundary orphans the payoff from the setup. Overlap also partially addresses pronouns: the carried sentence often contains the proper noun that the next chunk refers to only as "he" or "she".

**Why chapter-bounded.** Chapters are scene units here. Moby-Dick's 135 chapters average under 1,600 words and switch abruptly between narrative and cetological essay, so a chunk spanning a chapter break would fuse two unrelated topics into one unsearchable vector.

---

## Sample Chunks

Five chunks chosen to cover the structurally different source types. Reproducible with `python sample_chunks.py`.

| # | Source document | Chunk text |
|---|----------------|------------|
| 1 | *Pride and Prejudice*, Chapter XX (chunk 364, 721 chars) | "I have much pleasure, indeed, in talking to anybody. People who suffer as I do from nervous complaints can have no great inclination for talking. Nobody can tell what I suffer! But it is always so. Those who do not complain are never pitied." Her daughters listened in silence to this effusion, sensible that any attempt to reason with or soothe her would only increase the irritation. She talked on, therefore, without interruption from any of them till they were joined by Mr. Collins, who entered with an air more stately than usual, and on perceiving whom, she said to the girls,-- "Now, I do insist upon it, that you, all of you, hold your tongues, and let Mr. Collins and me have a little conversation together." |
| 2 | *The Art of War*, Chapter VI: Weak Points and Strong (chunk 47, 736 chars) | Rouse him, and learn the principle of his activity or inactivity. Force him to reveal himself, so as to find out his vulnerable spots. 24. Carefully compare the opposing army with your own, so that you may know where strength is superabundant and where it is deficient. 25. In making tactical dispositions, the highest pitch you can attain is to conceal them; conceal your dispositions, and you will be safe from the prying of the subtlest spies, from the machinations of the wisest brains. 26. How victory may be produced for them out of the enemy's own tactics—that is what the multitude cannot comprehend. 27. All men can see the tactics whereby I conquer, but what none can see is the strategy out of which victory is evolved. |
| 3 | *Dracula*, Chapter XI: Lucy Westenra's Diary (chunk 531, 769 chars) | for all you're worth, and won't git even a growl out of me. Drive along with your questions. I know what yer a-comin' at, that 'ere escaped wolf." "Exactly. I want you to give me your view of it. Just tell me how it happened; and when I know the facts I'll get you to say what you consider was the cause of it, and how you think the whole affair will end." "All right, guv'nor. This 'ere is about the 'ole story. That 'ere wolf what we called Bersicker was one of three grey ones that came from Norway to Jamrach's, which we bought off him four years ago. He was a nice well-behaved wolf, that never gave no trouble to talk of." |
| 4 | *Adventures of Huckleberry Finn*, Chapter XVII (chunk 349, 781 chars) | tell him—oh, here he is himself. Buck, take this little stranger and get the wet clothes off from him and dress him up in some of yours that's dry." Buck looked about as old as me—thirteen or fourteen or along there, though he was a little bigger than me. He hadn't on anything but a shirt, and he was very frowzy-headed. He came in gaping and digging one fist into his eyes, and he was dragging a gun along with the other one. He says: "Ain't they no Shepherdsons around?" They said, no, 'twas a false alarm. "Well," he says, "if they'd a ben some, I reckon I'd a got one." |
| 5 | *Moby-Dick*, Chapter 42: The Whiteness of the Whale (chunk 700, 844 chars) | at all approaching to muteness or universality. What I mean by these two statements may perhaps be respectively elucidated by the following examples. First: The mariner, when drawing nigh the coasts of foreign lands, if by night he hear the roar of breakers, starts to vigilance, and feels just enough of trepidation to sharpen all his faculties; but under precisely similar circumstances, let him be called from his hammock to view his ship sailing through a midnight sea of milky whiteness—as if from encircling headlands shoals of combed white bears were swimming round him, then he feels a silent, superstitious dread. |

Chunks 3, 4 and 5 begin mid-sentence. That is the 150-character overlap being carried in from the previous chunk, working as designed — the overlap is trimmed to a word boundary rather than a sentence boundary, so it starts wherever 150 characters back happens to land.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384 dimensions, 256 word-piece input limit, about 80 MB, running locally on CPU). Vectors are stored in ChromaDB with cosine distance, persisted to `chroma_db/`. Indexing all 10,301 chunks took 12 minutes 29 seconds on CPU.

I chose it because it is free, requires no API key, and embeds the whole corpus in a few minutes on an ordinary laptop, which mattered because I re-indexed several times while tuning.

**Production tradeoff reflection:**

If cost were not a constraint, **context length** is the tradeoff I would weigh first, because it is the constraint actively distorting this design. MiniLM's 256-token window is what forces 800-character chunks, and narrative prose does not divide into 800-character units. Scenes run longer, so the pipeline fragments them and then relies on overlap and a synthetic prefix to patch over the damage. This turned out to be the direct cause of my worst failure, described below: the passage answering a question sat eight to thirteen chunks away from the passage that matched it. An embedding model with an 8,000–32,000 token window, such as `voyage-3` or OpenAI's `text-embedding-3-large`, could hold an entire scene or chapter in one vector and would dissolve that problem rather than mitigate it.

**Accuracy on domain-specific text** is second, and I measured it rather than guessing. MiniLM was trained on modern web text and question-answer pairs, and every source here is out of that distribution differently: Melville's cetology vocabulary, Austen's free indirect discourse, Twain's phonetic dialect where "sivilize" and "civilize" are different tokens, and Giles' romanised Chinese. I tested two stronger models on my hardest question. Where MiniLM ranked the answer-bearing chunks 109th, `all-mpnet-base-v2` ranked them 50th and `BAAI/bge-small-en-v1.5` 54th. Better, but not enough to matter at my token budget.

**Latency and hosting** cut the other way, and are why MiniLM is right for this project: local inference is milliseconds per query, with no network round trip, no key, no per-token cost and no rate limit while iterating.

**Multilingual support** is nearly irrelevant here since all ten sources are English. The exceptions — Moby-Dick's scattered French and Latin, and Sun Tzu's transliterated names — carry too little weight to justify a multilingual model.

---

## Retrieval Test Results

Three queries run through the retrieval system, showing the top 3 chunks with their cosine distances.

**Query 1:** *Who is Renfield in Dracula?*

Top returned chunks:
- `[0.231] Dracula — Chapter XX: Jonathan Harker's Journal` — "…*Dr. Seward's Diary.* *1 October.*--I am puzzled afresh about Renfield. His moods change so rapidly that I find it difficult to keep touch of them, and as they always mean something…"
- `[0.257] Dracula — Chapter XIX: Jonathan Harker's Journal` — "…by the scene with Mr. Renfield. When we came away from his room we were silent till we got back to the study. Then Mr. Morris said to Dr. Seward:-- 'Say, Jack, if that man wasn't attempting a bluff, he is about the sanest lunatic I ever saw…'"
- `[0.257] Dracula — Chapter XXI: Dr. Seward's Diary` — "…Renfield proceeded:-- 'He came up to the window in the mist, as I had seen him often before; but he was solid then--not a ghost, and his eyes were fierce like a man's when angry…'"

Relevance explanation: all three are directly on target, and they come from three different chapters, which is what this question needs — Renfield is described across the whole novel rather than in one place. Each chunk carries a different facet: Seward's clinical assessment of his moods, an outsider's judgement of his sanity, and Renfield's own account of Dracula at his window. This question succeeds because it is a **descriptive** question answered by **descriptive** passages; the text says who Renfield is in roughly the words someone would use to ask.

---

**Query 2:** *What does Sun Tzu say about deception in warfare?*

Top returned chunks:
- `[0.333] The Art of War — Chapter XIII: The Use of Spies` — "If a secret piece of news is divulged by a spy before the time is ripe, he must be put to death together with the man to whom the secret was told…"
- `[0.365] The Art of War — Chapter IV: Tactical Dispositions` — "1. Sun Tzŭ said: The good fighters of old first put themselves beyond the possibility of defeat, and then waited for an opportunity of defeating the enemy…"
- `[0.367] The Art of War — Chapter IV: Tactical Dispositions` — "…and balk his schemes, so that at last the day may be won without shedding a drop of blood…"

Relevance explanation: partially relevant, and instructive about a weakness. All three are correctly from The Art of War and all concern concealment, secrecy and thwarting an enemy's plans. But the single most famous line on this subject — "All warfare is based on deception," in Chapter I — is *not* in the top three, and I checked the full window: it is absent from the top **twelve** as well, despite existing in the corpus and containing the query's exact keyword. The retrieved passages are about the *practice* of deception rather than the *statement* about it, and the vector space cannot tell those apart. Note also the distances: 0.333 to 0.367 against 0.231 for the Dracula query, so the system is measurably less certain here.

---

**Query 3:** *In Pride and Prejudice, why does Elizabeth reject Darcy's first proposal?*

Top returned chunks:
- `[0.214] Pride and Prejudice — Chapter XXXVI` — "Elizabeth, when Mr. Darcy gave her the letter, did not expect it to contain a renewal of his offers…"
- `[0.215] Pride and Prejudice — Chapter X` — "…than Darcy on particular occasions, and in particular places; at his own house especially, and of a Sunday evening…"
- `[0.216] Pride and Prejudice — Chapter XXXIII` — "More than once did Elizabeth, in her ramble within the park, unexpectedly meet Mr. Darcy…"

Relevance explanation: off-target, and this is the system's clearest failure. The proposal happens in Chapter XXXIV, which appears nowhere in the top three — or in the top ten. Book-level routing is perfect (everything is from the right novel), but within-book ranking is not: the three distances span 0.002, meaning the model has almost no basis for preferring one P&P chunk over another once the query names the book. Analysed in full below.

---

## Grounded Generation

The generation model is `openai/gpt-oss-120b` via the Groq API, at temperature 0. I originally planned to use a Llama model, but listing the models available on my Groq account showed no Llama chat model is offered — the only Meta entries are `llama-prompt-guard-2` safety classifiers. I also deliberately avoided Groq's `groq/compound` models, because they have built-in web search, which would let the model answer from the internet instead of my retrieved passages and would silently destroy grounding.

**System prompt grounding instruction:**

```
You answer questions about classic literature using ONLY the numbered passages
supplied in each request.

Rules you must follow:

1. Use only information contained in the supplied passages. Do not use anything
   you know about these books from other sources, even if you recognise the work
   and are confident of the answer.
2. Cite the passage number in square brackets after every claim, like [2]. A
   claim with no citation is not allowed.
3. If the passages do not contain enough information to answer, say so plainly:
   "The retrieved passages don't contain the answer to that." Do not fill the gap
   from memory.
4. If the passages describe a similar but different event from the one asked
   about, say so rather than answering as though they matched. Two scenes can
   look alike without being the same scene.
5. Quote the text directly where a quotation settles the question.
6. Keep the answer to a few sentences unless the question genuinely needs more.

You are judged on whether every statement is traceable to the passages, not on
how complete or confident the answer sounds.
```

Grounding is enforced by three mechanisms, not by the prompt alone:

1. **The model never sees the corpus.** Only the 12 retrieved chunks go into the prompt. There is nothing else for it to draw on.
2. **Out-of-scope questions never reach the model.** If the closest chunk scores worse than a cosine distance of 0.51, the system refuses without making an API call at all. It cannot hallucinate an answer it was never asked to produce.
3. **The prompt demands citations,** and rule 4 specifically targets the failure mode this corpus invites — answering about a similar scene as though it were the right one.

The 0.51 threshold was measured, not guessed. `python embed.py --calibrate` runs the five evaluation questions alongside five clearly out-of-scope questions and reports the closest distance for each. In-scope questions scored 0.214 to 0.337; out-of-scope questions scored 0.684 to 0.821. That is a clean separation gap of 0.348 with no overlap, and 0.51 sits in the middle of it.

**How source attribution is surfaced in the response:**

Each passage is numbered and labelled with its source before being given to the model:

```
[1] Dracula — Chapter XX: Jonathan Harker's Journal
<passage text>
```

The model cites those numbers inline. The system then resolves the numbers it actually used into a `Sources:` block appended to the answer, so a response stands on its own when copied out rather than depending on a separate panel. The full retrieved list with distances is shown separately as diagnostics.

---

## Example Responses

**Grounded response 1**

Query: *Who is Renfield in Dracula?*

Response:

> Renfield is the strange patient in Dr. Seward's asylum who is repeatedly described as a volatile, "lunatic" with shifting moods and a compulsive love of animals. Dr. Seward notes that "His moods change so rapidly" and that Renfield "has certain qualities… selfishness, secrecy, and purpose" while also being "a love of animals" and "catching flies" as a hobby[1][11]. He is seen eating the birds he keeps, "disgorged a whole lot of feathers… he has eaten his birds"[5], and at other times he becomes quiet and murmurs to himself, "Now I can wait; now I can wait"[6]. In the journal entries he is referred to as "the patient" and is treated by Dr. Seward and Van Helsing, confirming his role as an asylum inmate rather than a member of the main vampire cast.

Source attribution:

```
Sources:
[1]  Dracula — Chapter XX: Jonathan Harker's Journal
[11] Dracula — Chapter VI: Mina Murray's Journal
[5]  Dracula — Chapter VI: Mina Murray's Journal
[6]  Dracula — Chapter IX: Mina Murray's Journal
```

---

**Grounded response 2**

Query: *Who is Irene Adler, and why is she important to Sherlock Holmes?*

Response:

> Irene Adler is introduced in the passages as a "well-known adventuress" whom Holmes met during a long visit to Warsaw and whose biography he keeps in his index of people of interest[2]. To Holmes she is "always _the_ woman" – the one woman who eclipses and predominates the whole of her sex in his eyes, admired for her intellect and resolve rather than for any romantic feeling[3]. Her importance to Holmes is shown by the fact that she once possessed a compromising photograph of the King of Bohemia and threatened to use it, a scheme that Holmes had to try to thwart, and by Holmes's continual reference to her as "the woman" whenever he speaks of her later[4][10].

Source attribution:

```
Sources:
[2]  The Adventures of Sherlock Holmes — Chapter I: A Scandal in Bohemia
[3]  The Adventures of Sherlock Holmes — Chapter I: A Scandal in Bohemia
[4]  The Adventures of Sherlock Holmes — Chapter I: A Scandal in Bohemia
[10] The Adventures of Sherlock Holmes — Chapter I: A Scandal in Bohemia
```

---

**Out-of-scope query**

Query: *What is the best pizza restaurant in Chicago?*

System response (refusal):

> That question doesn't appear to be covered by the ten books in this collection, so there are no relevant passages to answer from.
>
> The collection is: Pride and Prejudice, The Adventures of Sherlock Holmes, The Art of War, Alice's Adventures in Wonderland, Moby-Dick, Frankenstein, A Tale of Two Cities, The Picture of Dorian Gray, Dracula, and Adventures of Huckleberry Finn.

Diagnostics:

```
Refused before calling the model: no passage scored below the 0.51 distance
threshold (closest was 0.684).
```

The language model was never invoked for this query. The refusal is structural, not a matter of the model choosing to decline.

---

## Query Interface

Built with Gradio (`python app.py`). A terminal mode is also available for testing and for capturing transcripts: `python app.py --ask "..."`.

**Input fields:**

- **Your question** — a free-text box for a natural-language question about any of the ten books.
- **Passages to retrieve** — a slider from 1 to 20, defaulting to 12, controlling top-k. It is exposed because the retrieval window turned out to be the single most consequential parameter in the system.
- **Ask** — submits; pressing Enter in the question box does the same.
- Six preloaded examples, including the out-of-scope pizza query so the refusal path can be demonstrated in one click.

**Output format:**

- **Answer** — the grounded response with inline `[n]` citations, followed by a `Sources:` block resolving each cited number to its book and chapter.
- **Sources retrieved** — every passage that was retrieved, with its book, chapter and cosine distance, whether or not the model cited it. This makes it possible to see when retrieval succeeded but generation declined.

---

**Sample Interaction Transcript**

> **User:** Who is Renfield in Dracula?

> **System:**
> Renfield is the strange patient in Dr. Seward's asylum who is repeatedly described as a volatile, "lunatic" with shifting moods and a compulsive love of animals. Dr. Seward notes that "His moods change so rapidly" and that Renfield "has certain qualities… selfishness, secrecy, and purpose" while also being "a love of animals" and "catching flies" as a hobby[1][11]. He is seen eating the birds he keeps, "disgorged a whole lot of feathers… he has eaten his birds"[5], and at other times he becomes quiet and murmurs to himself, "Now I can wait; now I can wait"[6].
>
> Sources:
> [1] Dracula — Chapter XX: Jonathan Harker's Journal
> [11] Dracula — Chapter VI: Mina Murray's Journal
> [5] Dracula — Chapter VI: Mina Murray's Journal
> [6] Dracula — Chapter IX: Mina Murray's Journal
>
> **Sources retrieved**
> ```
> [1]  Dracula — Chapter XX: Jonathan Harker's Journal   · distance 0.231
> [2]  Dracula — Chapter XIX: Jonathan Harker's Journal  · distance 0.257
> [3]  Dracula — Chapter XXI: Dr. Seward's Diary         · distance 0.257
> [4]  Dracula — Chapter XX: Jonathan Harker's Journal   · distance 0.262
> [5]  Dracula — Chapter VI: Mina Murray's Journal       · distance 0.283
> [6]  Dracula — Chapter IX: Mina Murray's Journal       · distance 0.295
> [7]  Dracula — Chapter XXI: Dr. Seward's Diary         · distance 0.301
> [8]  Dracula — Chapter XX: Jonathan Harker's Journal   · distance 0.307
> [9]  Dracula — Chapter XX: Jonathan Harker's Journal   · distance 0.312
> [10] Dracula — Chapter VI: Mina Murray's Journal       · distance 0.314
> [11] Dracula — Chapter VI: Mina Murray's Journal       · distance 0.321
> [12] Dracula — Chapter IX: Mina Murray's Journal       · distance 0.321
> ```

---

## Evaluation Report

All five questions from `planning.md`, run at top-k 12.

| # | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
|---|----------|-----------------|------------------------------|-------------------|-------------------|
| 1 | In *Pride and Prejudice*, why does Elizabeth reject Darcy's first proposal? | She believes he separated Bingley from Jane, treated Wickham unfairly, and proposed in a way that insulted her family | Answered, but said she refused because of "family weakness… the deepest disgrace." Its citations lean on Chapter XLVI (Lydia's elopement — her *own* family, and a far later event). One of the three expected reasons survives; the other two never appear | Off-target | **Partially accurate** |
| 2 | In *Frankenstein*, how does Victor react when the creature comes to life? | Horror rather than pride; he flees the room and abandons the creature | Answered correctly, quoting "the wretch—the miserable monster whom I had created," his escape downstairs, and the night in the courtyard "in the greatest agitation" | Relevant | Accurate |
| 3 | Who is Irene Adler, and why is she important to Sherlock Holmes? | The adventuress who outwits Holmes in *A Scandal in Bohemia*; he calls her "*the* woman" | Answered correctly, identifying her as an adventuress in Holmes's index, quoting "always _the_ woman," and citing the photograph of the King of Bohemia | Relevant | Accurate |
| 4 | Who is Renfield in *Dracula*? | Dr. Seward's asylum patient, zoophagous, psychically linked to Dracula | Answered correctly, drawing on four chapters — his shifting moods, "selfishness, secrecy, and purpose," eating his birds, his quiet spells | Relevant | Accurate |
| 5 | Why does Huck decide not to betray Jim in *Huckleberry Finn*? | He tears up the letter to Miss Watson and chooses damnation over betraying Jim | **Refused** — "The retrieved passages don't contain the answer to that." Chapter XXXI *was* retrieved, but the chunk holding the decision was not | Partially relevant | **Inaccurate** (no answer produced) |
| — | *Out of scope:* What is the best pizza restaurant in Chicago? | Should refuse | Refused before any API call; closest distance 0.684 against a 0.51 threshold | n/a | Correct |

**Result: 3 accurate, 1 partially accurate, 1 inaccurate.** The out-of-scope query was correctly refused.

Question 1 is judged partially accurate rather than inaccurate on a technicality worth being precise about. One of the three expected reasons — that Darcy proposed in a way insulting to her family — *is* present in the response, and is correct. But the system supports it with the wrong passage (Chapter 46, about Lydia's elopement, which happens hundreds of pages later and concerns Elizabeth's own family), and it misses the other two reasons entirely. Right conclusion, wrong evidence, incomplete.

Question 5 is judged inaccurate because no answer was produced, even though the refusal was the *correct behaviour* given what retrieval supplied. Those are different things, and collapsing them would flatter the system. The pipeline stage that failed was retrieval, not generation.

The number that matters more than the accuracy rate is this: **in no run, in any configuration, did the model invent an answer.** It demonstrably knows these novels — it could have produced a fluent, confident, uncited account of Elizabeth's reasons from training data. Instead it either refused or answered from what it was given. Retrieval is the weak component; grounding held under exactly the conditions that would expose a weak implementation.

### Verbatim system responses

Captured with `python app.py --ask "..."` at top-k 12, temperature 0. Sources blocks are as the system produced them.

**Question 1 — In *Pride and Prejudice*, why does Elizabeth reject Darcy's first proposal?**

> Elizabeth refuses Mr Darcy's first proposal because his declaration is accompanied by a harsh reminder of her family's disgrace, which she perceives as a proof of his pride and a humiliation of her relatives. She feels "everything must sink under such a proof of family weakness, such an assurance of the deepest disgrace" and cannot accept a marriage that is predicated on that contempt [8]. Her reaction to his offer is one of astonishment and disbelief, showing that she cannot reconcile his love with the insult to her family [12].
>
> Sources:
> [8] Pride and Prejudice — Chapter XLVI
> [12] Pride and Prejudice — Chapter XXXIV

The citation is the tell. Passage [8] is Chapter XLVI, not the proposal chapter, and it is doing most of the work in the answer.

**Question 2 — In *Frankenstein*, how does Victor react when the creature comes to life?**

> Victor is horrified at the instant the creature awakens. He sees the "miserable monster" he has created, watches it lift the curtain and open its jaws, and then he "escaped and rushed downstairs." He takes refuge in the courtyard and spends the night "walking up and down in the greatest agitation, listening attentively, catching and fearing each sound as if it were to announce the approach of the demoniacal corpse" he has brought to life[8].
>
> Sources:
> [8] Frankenstein; or, The Modern Prometheus — Chapter 5

**Question 3 — Who is Irene Adler, and why is she important to Sherlock Holmes?**

> Irene Adler is introduced in the case as "the well-known adventuress" who once crossed paths with Holmes during a long visit to Warsaw [2]. To Holmes she is "always _the_ woman… she eclipses and predominates the whole of her sex" and is the only female figure he ever mentions with such admiration [3]. Her importance to Holmes stems from the fact that she out-witted him and now holds a compromising photograph that could ruin the King of Bohemia, a situation that Holmes is forced to confront [4]; Holmes even refers to her repeatedly as "the woman" when recalling the episode [10].
>
> Sources:
> [2] The Adventures of Sherlock Holmes — Chapter I: A Scandal in Bohemia
> [3] The Adventures of Sherlock Holmes — Chapter I: A Scandal in Bohemia
> [4] The Adventures of Sherlock Holmes — Chapter I: A Scandal in Bohemia
> [10] The Adventures of Sherlock Holmes — Chapter I: A Scandal in Bohemia

**Question 4 — Who is Renfield in *Dracula*?**

> Renfield is the strange patient under Dr. Seward's care – a man whose moods swing wildly and who "does not really care for any of the things of mere earth…[he] was in the clouds" and "commanding destiny" ([1]). He is noted for a compulsive love of animals: he eats the birds he keeps, "disgorged a whole lot of feathers" and "has eaten his birds…raw" ([5]), and later spends his time "catching flies" and even humming while "spreading out his sugar…beginning his fly-catching again" ([10]). His behaviour alternates between violent outbursts and periods of quiet, "murmuring…'Now I can wait…'" ([6]) and, when confronted, he speaks cryptically about "flies…spiders" and stops at the word "drink" ([9]). He is also described as having "selfishness, secrecy, and purpose" and a "love of animals" that can appear "abnormally cruel" ([11]). In short, Renfield is Dr. Seward's disturbed, animal-obsessed patient.
>
> Sources:
> [1] Dracula — Chapter XX: Jonathan Harker's Journal
> [5] Dracula — Chapter VI: Mina Murray's Journal
> [10] Dracula — Chapter VI: Mina Murray's Journal
> [6] Dracula — Chapter IX: Mina Murray's Journal
> [9] Dracula — Chapter XX: Jonathan Harker's Journal
> [11] Dracula — Chapter VI: Mina Murray's Journal

The best answer of the five, drawing on five chapters at once. This is the aggregation case I predicted would be hardest in `planning.md`, and it worked — because Renfield is *described* in the text in roughly the words someone would use to ask about him.

**Question 5 — Why does Huck decide not to betray Jim in *Huckleberry Finn*?**

> The retrieved passages don't contain the answer to that.

**Out-of-scope — What is the best pizza restaurant in Chicago?**

> That question doesn't appear to be covered by the ten books in this collection, so there are no relevant passages to answer from.
>
> The collection is: Pride and Prejudice, The Adventures of Sherlock Holmes, The Art of War, Alice's Adventures in Wonderland, Moby-Dick, Frankenstein, A Tale of Two Cities, The Picture of Dorian Gray, Dracula, and Adventures of Huckleberry Finn.

with the diagnostic line: `Refused before calling the model: no passage scored below the 0.51 distance threshold (closest was 0.684).`

The number that matters more than the accuracy rate is this: **in no run, in any configuration, did the model invent an answer.** It demonstrably knows these novels — it could have produced a fluent, confident, uncited account of Elizabeth's reasons from training data. Instead it either refused or answered from what it was given. Retrieval is the weak component; grounding held under exactly the conditions that would expose a weak implementation.

---

## Failure Case Analysis

**Question that failed:** *In Pride and Prejudice, why does Elizabeth reject Darcy's first proposal?*

**What the system returned:** A fluent answer claiming Elizabeth refused because of "family weakness… the deepest disgrace." Its own citations give the failure away: it leans on passage `[8]`, which is Chapter **XLVI** — Lydia's elopement, several hundred pages later, concerning Elizabeth's own family rather than Darcy's — while Chapter XXXIV, where the proposal actually happens, appears only as `[12]` and contributes just her astonishment. One of her three real reasons (that his manner insulted her family) survives by coincidence, which is why this is graded partially accurate rather than inaccurate; the other two, Jane and Wickham, never appear. Chapter XXXIV ranked 12th, and the chunks in which she states her reasons ranked **109th**.

**Root cause: questions are asked in summary vocabulary, and fiction is written in dramatic vocabulary.**

This is a retrieval-stage failure, and the mechanism is specific. The chunks where Elizabeth gives her reasons contain **none** of the words "refuse", "reject", "proposal", "propose" or "decline". I checked. They are her dialogue:

> "…your manners impressing me with the fullest belief of your arrogance, your conceit, and your selfish disdain…"
> "…I had not known you a month before I felt that you were the last man in the world whom I could ever be prevailed on to marry."

She **enacts** the refusal. No sentence in the novel says "Elizabeth rejected Darcy because X" — the reader infers it from an argument. Meanwhile the passages that *do* carry proposal-and-refusal vocabulary are Chapter XX, which is Mr Collins's proposal, and Chapter XXXVI, which is Darcy's letter. They match the question's register, rank at the top, and are the wrong scene.

Two further measurements support this reading. First, naming the book in the query compresses the top ten distances into a 0.021 band, because the book name matches every P&P chunk equally and swamps the rest of the signal. Second, the same failure recurs in question 5 for the same reason: Chapter XXXI of *Huckleberry Finn* was retrieved, but the decisive passage — "All right, then, I'll *go* to hell"—and tore it up — is eight chunks further on and was never in the window.

This also explains the successes. "Who is Renfield?" and "Who is Irene Adler?" are **descriptive** questions answered by **descriptive** passages: "the sanest lunatic I ever saw", "always *the* woman". Question and source share a register, so the vectors align.

**What I would change to fix it — and what I ruled out by measuring:**

I tried four fixes and none worked within my constraints:

- **Widening top-k.** Raising it from 5 to 12 fixed question 2 (Frankenstein Chapter 5 sits at rank 8) but not this one. Reaching rank 109 would need roughly 23,000 tokens against Groq's free-tier limit of 8,000 tokens per minute.
- **Expanding to neighbouring chunks.** Useless here: the answer is 13 chunks from the match, not 1.
- **Retrieving whole chapters.** Rejected by the API with a 413 error at about 13,000 tokens, which is what revealed the real ceiling is the rate limit, not the model's 131,000-token context window.
- **A stronger embedding model.** `all-mpnet-base-v2` moved those chunks from rank 109 to 50 and `bge-small-en-v1.5` to 54 — roughly twice as good, still far outside any window I can afford.

The fix that would actually work is the one the token budget forbids: an embedding model with a long enough context to hold a whole scene in a single vector, so that a chunk containing Darcy's proposal also contains Elizabeth's answer. Failing that, a hybrid approach — dense retrieval to find the chapter, then a second pass to select within it — would let the system reach passages that rank poorly on their own but sit inside a chapter that ranks well.

---

## Spec Reflection

**One way the spec helped me during implementation:**

Writing concrete numbers into `planning.md` before writing code turned verification into something mechanical rather than a matter of opinion. Because the spec said 800 characters, 1,000 maximum, and a specific chapter count per book, I could assert those and catch four real bugs the moment I ran the pipeline: Pride and Prejudice found 59 of 61 chapters because my pattern was case-sensitive and missed `Chapter I.]`; then 60, because that heading lives inside an illustration caption my cleaning had deleted; A Tale of Two Cities found 24 of 45 because its chapter numbers restart in each of its three Books; and chunks came out at 1,001 characters because I had reserved the overlap budget but forgotten the two-character paragraph separator. None of those would have been visible by reading output and judging whether it "looked right."

The limits of that also became clear. My chapter-count check passed while the data was broken: when a bug removed the body headings for eight Art of War chapters, they silently fell back to their table-of-contents entries. The count still read 13. I only caught it by reading an actual chunk and finding a bibliography of Chinese commentators under the heading "The Attack by Fire." I have since added a check for chapters with almost no body text, and for one chapter that has swallowed far more than the others.

**One way my implementation diverged from the spec, and why:**

I planned top-k of 5 and shipped 12. At 5, only 2 of my 5 evaluation questions could be answered, and all three failures were the same shape: the passage holding the answer had been retrieved reasonably well but sat just outside the window. Frankenstein Chapter 5 ranks 8th and Pride and Prejudice Chapter XXXIV ranks 12th, so a window of 5 excluded both.

What I did not anticipate was where the ceiling on that number would come from. I assumed the model's 131,000-token context was the limit and started building toward whole-chapter retrieval, until the API rejected a request with a 413 at about 13,000 tokens. The real constraint is Groq's free tier: 8,000 tokens per minute. At roughly 215 tokens per passage, 12 passages plus the system prompt is about 3,000 tokens, which fits and leaves room to ask twice a minute. I also had to add retry-with-backoff, because running all five evaluation questions in sequence trips that limit. Both changes are recorded in `planning.md` as updates rather than silently applied.

---

## AI Usage

I used Claude (Claude Code in VS Code) throughout, and the most useful property was that it could read the actual corpus files rather than working from my description of them.

**Instance 1 — Inspecting the sources before writing the chunking spec**

- *What I gave the AI:* the ten Gutenberg files and my draft Chunking Strategy section, and asked it to check my assumptions against the real text before I wrote any code.
- *What it produced:* three findings I did not know about. Every book repeats its chapter headings in a table of contents, so a naive regex doubles the chapter count — Moby-Dick matched 276 headings for 138 chapters. The chapter heading formats differ across all ten books, and Sherlock Holmes has no `CHAPTER` keyword at all, just indented roman numerals. And the Gutenberg edition of *The Art of War* is Lionel Giles' 1910 critical edition, where about 45% of the file is the translator's introduction and bracketed annotations rather than Sun Tzu.
- *What I changed or overrode:* I added all three as explicit preprocessing steps and made chapter detection a per-book configuration table rather than one pattern. I also decided to keep *The Art of War* in the corpus rather than drop it, because being the only non-narrative source makes it a useful contrast — and it did turn out to be the weakest performer.

**Instance 2 — Choosing the refusal threshold by measurement instead of guessing**

- *What I gave the AI:* my Retrieval Approach section, which said only "a similarity threshold to filter out weak matches" without stating a number, and asked for it to be determined rather than picked.
- *What it produced:* a `--calibrate` mode that runs my five evaluation questions alongside five out-of-scope ones and reports the distance distribution. In-scope questions scored 0.214 to 0.337, out-of-scope 0.684 to 0.821, a clean gap of 0.348.
- *What I changed or overrode:* I took 0.51, the midpoint, as the threshold. More importantly I applied the same principle to the rest of the project: when the first draft of the answer to "does the prefix help retrieval?" was a plausible-sounding explanation, I asked for an A/B test instead, which showed the prefix was *not* the cause and sent the investigation in a different direction. Several of my early conclusions were wrong and only measurement caught them — including one where the rank I was tracking belonged to the wrong chunk entirely.
