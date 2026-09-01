# Project 1 Planning: The Unofficial Guide

> Write this document before you write any pipeline code.
> Your spec and architecture diagram are what you'll use to direct AI tools (Claude, Copilot, etc.) to generate your implementation — the more specific they are, the more useful the generated code will be.
> Update the Retrieval Approach and Chunking Strategy sections if you change your approach during implementation.
> Update this file before starting any stretch features.

---

## Domain
[What domain did you choose? Why is this knowledge valuable and hard to find through official channels?]
Domain: A searchable library of 10 public-domain classic books.

= This knowledge is valuable because readers often remember a scene, character, or event from a book but cannot remember the exact words or where it appeared. This system helps them quickly find specific passages and understand what happened without rereading the entire book. It is hard to find through official channels because books usually only include a table of contents, not detailed indexes of events or scenes. Search engines, study guides, and summaries focus on major plot points and often cannot answer specific questions about lesser-known moments. If a reader does not remember the exact wording kind of like the Ctrl + F function, traditional text search is often ineffective. This project makes those hidden details easy to find using natural language questions.

## Documents
[List your specific sources: URLs, subreddit names, forum threads, or file descriptions. Aim for variety — sources that together cover different subtopics or perspectives within your domain.]

I used 10 public-domain books from Project Gutenberg, downloaded as plain text (.txt) files and stored locally in the documents/ folder.

The sources are:

Pride and Prejudice by Jane Austen
 https://www.gutenberg.org/ebooks/1342

The Adventures of Sherlock Holmes by Arthur Conan Doyle
 https://www.gutenberg.org/ebooks/1661

The Art of War by Sun Tzu
 https://www.gutenberg.org/ebooks/132

Alice's Adventures in Wonderland by Lewis Carroll
 https://www.gutenberg.org/ebooks/11

Moby-Dick by Herman Melville
 https://www.gutenberg.org/ebooks/2701

Frankenstein by Mary Shelley
 https://www.gutenberg.org/ebooks/84

A Tale of Two Cities by Charles Dickens
 https://www.gutenberg.org/ebooks/98

The Picture of Dorian Gray by Oscar Wilde
 https://www.gutenberg.org/ebooks/174

Dracula by Bram Stoker
 https://www.gutenberg.org/ebooks/345

Adventures of Huckleberry Finn by Mark Twain
 https://www.gutenberg.org/ebooks/76

Why these sources?
 They provide a diverse collection of classic literature, including romance, detective fiction, fantasy, horror, historical fiction, adventure, and military strategy. This variety helps test whether the system can accurately retrieve information from different books and distinguish between similar characters, themes, and events across multiple works.

## Chunking Strategy
[How will you split documents into chunks? State your chunk size (in tokens or characters), overlap size, and explain why those numbers fit the structure of your documents. A review-heavy corpus warrants different chunking than a long FAQ.]

Chunk size: ~800 characters (maximum 1,000 characters)
Overlap: 150 characters

Before chunking:

- Remove Project Gutenberg headers, footers, and license text.
Removed tables of contents to avoid duplicate chapter entries.
-Rejoine hard-wrapped lines into normal paragraphs.
-Detect chapter boundaries for each book.
- Will apply extra cleaning to The Art of War by removing editor introductions and annotations.

Documents will be split using paragraph-based, chapter-bounded approach. So, whole paragraphs are grouped until a chunk reaches about 800 characters. Chunks should never cross chapter boundaries. If a paragraph is too long, it is split at sentence boundaries. Each new chunk includes a 150-character overlap from the previous chunk.

For each chunk include:

Book title
Author
Gutenberg ID
Chapter number/title
Chunk index

I also prepend the book and chapter title to the chunk before embedding to provide additional context.

Why this approach? This is because novels are organized around chapters and paragraphs, which naturally represent scenes and ideas. Using paragraph-based chunks preserves context better than splitting text at fixed character counts. The 150-character overlap helps keep related events together and improves retrieval when characters are referenced by pronouns such as "he" or "she." Limiting chunks to about 800 characters also ensures they fit within the embedding model's input limits, making retrieval more accurate.

## Retrieval Approach
[Which embedding model are you using (e.g., all-MiniLM-L6-v2 via sentence-transformers)? How many chunks will you retrieve per query (top-k)? If you were deploying this for real users and cost wasn't a constraint, what tradeoffs would you weigh in choosing a different embedding model — context length, multilingual support, accuracy on domain-specific text, latency?]

Embedding model: all-MiniLM-L6-v2 from the sentence-transformers library.

Top-k retrieval: 5 chunks per query, with a similarity threshold to filter out weak matches.

Vector database: ChromaDB (chroma_db/).

Why I chose it:
 I selected all-MiniLM-L6-v2 because it is free, runs locally on a CPU, and can efficiently embed the entire collection of about 9,200 text chunks. Retrieving the top 5 chunks provides enough context to answer questions accurately without overwhelming the language model with irrelevant passages. The similarity threshold also helps the system avoid answering questions that are not supported by the book collection.

Tradeoffs for a production system:
 If cost were not a concern, I would primarily consider:

Context length: Larger embedding models can encode much longer passages, allowing entire scenes or chapters to be embedded together rather than splitting them into smaller chunks. This would preserve more context and improve retrieval quality.
Accuracy on literary text: A more advanced model may better understand older writing styles, dialects, historical language, and literary references found in books such as Moby-Dick, Pride and Prejudice, and Huckleberry Finn.
Latency: Larger models generally provide better retrieval accuracy but increase processing time and infrastructure requirements compared to a lightweight model like MiniLM.
Multilingual support: While not important for this project because all sources are in English, multilingual models would be valuable if the collection included books in multiple languages.

For this project, all-MiniLM-L6-v2 offers the best balance of speed, simplicity, and retrieval performance.

## Evaluation Plan
[List your 5 test questions with their expected correct answers. Questions should be specific enough that you can judge whether the system's response is right or wrong — "What are good dining halls?" is too vague; "What do students say about wait times at the [dining hall name] during lunch?" is testable.]]
Test Questions and Expected Answers

I selected five questions that test different retrieval abilities, including finding specific passages, summarizing information across multiple passages, and handling older literary language.

In Pride and Prejudice, why does Elizabeth reject Darcy's first proposal?
 Expected answer: Elizabeth refuses because she believes Darcy separated Bingley from Jane, treated Wickham unfairly, and proposed in a way that insulted her family and social status.

In Frankenstein, how does Victor react when the creature comes to life?
 Expected answer: Instead of feeling proud, Victor is horrified by what he has created. He feels disgust and fear, leaves the room, and abandons the creature.

Who is Irene Adler, and why is she important to Sherlock Holmes?
 Expected answer: Irene Adler is the woman who successfully outsmarts Holmes in A Scandal in Bohemia. Holmes respects her greatly and refers to her as "the woman" because she defeated him.

Who is Renfield in Dracula?
 Expected answer: Renfield is a patient in Dr. Seward's asylum who has a strange obsession with consuming living creatures. He is connected to Dracula and plays an important role in revealing Dracula's influence.

Why does Huck decide not to betray Jim in Huckleberry Finn?
 Expected answer: Huck chooses friendship and loyalty over society's expectations. He tears up the letter that would reveal Jim's location and decides to help him, even believing he may be doing something wrong.

Negative query:
 "What is the best pizza restaurant in Chicago?"

Expected behavior:
 The system should refuse to answer or redirect the question because the question is unrelated to any of the books.

## Anticipated Challenges
[What could go wrong? Consider: noisy or inconsistent documents, missing source attribution, off-topic retrieval, chunks that split key information across boundaries. Name at least two specific risks.]

Potential Risks and Challenges

Coreference and character references
 In novels, characters are often introduced by name and then referred to only as "he," "she," or similar pronouns. If a chunk contains only pronouns and not the character's name, the retrieval system may struggle to connect the query with the correct passage.

Possible solution: Add book and chapter information to each chunk and use overlapping text between chunks to preserve context.

Cross-book confusion
 Some books in the collection share similar themes, settings, or writing styles. For example, Dracula, Frankenstein, and The Picture of Dorian Gray all contain gothic elements. The system may retrieve passages from the wrong book when a query is vague or ambiguous.

Possible solution: Store and display source information (book title, chapter, author) with every retrieved result and optionally allow users to filter by book.

Questions that require information from many parts of a book
 Some questions, such as "Who is Renfield?" require details gathered from multiple chapters rather than a single passage. Retrieving only a few top chunks may produce an incomplete answer.

Possible Solution: Retrieve multiple relevant chunks and combine evidence from different locations before generating a response.

Chunk boundary issues
 Important information may be split across two chunks, causing the system to miss key context or retrieve only part of an event.

Possible Solution: Use overlapping chunks and split text at paragraph or sentence boundaries instead of fixed positions.

Differences in document structure
 The corpus contains many types of texts, including novels, short-story collections, and The Art of War, which is a collection of short aphorisms. A chunking strategy that works well for novels may not be ideal for every source.

Possible Solution: Apply source-specific preprocessing and adjust chunking rules when needed for different document types.

## Architecture

The system would have two phases: Indexing (performed once to build the database) and Querying (performed each time a user asks a question).

Indexing Phase

```mermaid
flowchart LR
    A[Book .txt Files] --> B[Document Ingestion<br/>Python]
    B --> C["Chunking<br/>Custom chunk_text()"]
    C --> D[Embedding<br/>all-MiniLM-L6-v2]
    D --> E[(ChromaDB)]
```

Querying Phase

```mermaid
flowchart LR
    A[User Question] --> B[Embed Query<br/>all-MiniLM-L6-v2]
    B --> C[Retrieve Top 5 Chunks<br/>ChromaDB]
    C --> D[Generate Answer<br/>openai/gpt-oss-120b via Groq]
    D --> E[Answer with Source Citation]
```

Tools Used

| Stage | Tool / Library |
|---|---|
| Document Ingestion | Python (`pathlib`, `re`) |
| Chunking | Custom `chunk_text()` function |
| Embedding | sentence-transformers (all-MiniLM-L6-v2) |
| Vector Store | ChromaDB |
| Retrieval | ChromaDB similarity search |
| Generation | `openai/gpt-oss-120b` via Groq API |
| Interface | Gradio |

Overview: The books are cleaned, split into chunks, embedded, and stored in ChromaDB. When a user asks a question, the question is embedded, the top 5 relevant chunks are retrieved, and `openai/gpt-oss-120b` generates an answer using only those retrieved passages, along with the book and chapter source information.

## AI Tool Plan
[Which parts of the pipeline do you plan to use AI tools (Claude, Copilot, ChatGPT, etc.) to help you implement? For each part, describe what you'll give the AI as input — which sections of this planning.md, which requirements from the instructions — and what you expect it to produce. Be specific: "I'll prompt Claude with my chunking strategy section and ask it to implement the chunk_text() function" is a plan. "I'll use AI to help me code" is not.]

I am using **Claude (Claude Code in VS Code)** as the primary tool, because it can read the actual corpus files while generating code rather than working from my description of them. That already changed this plan: I asked it to inspect the ten files before writing the Chunking Strategy, and it found the duplicated table of contents (TOC) problem and the Lionel Giles issue in *The Art of War*, neither of which I knew about. Both are now preprocessing steps.

