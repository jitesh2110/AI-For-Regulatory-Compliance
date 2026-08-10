import os
import re
import ollama
import chromadb
from chromadb.utils.embedding_functions import SentenceTransformerEmbeddingFunction
from collections import deque
from concurrent.futures import ThreadPoolExecutor

# ── DB setup ─────────────────────────────────────────────────────────────────

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Zomato_DB')

try:
    chroma_client = chromadb.PersistentClient(path=DB_PATH)
    embedding_func = SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-large-en-v1.5")
    collection = chroma_client.get_or_create_collection(
        name="Zomato",
        embedding_function=embedding_func
    )
except Exception as e:
    print(f"Error initializing ChromaDB: {e}")
    collection = None

# ── Conversation memory ───────────────────────────────────────────────────────

MEMORY_WINDOW = 3
_memory: deque = deque(maxlen=MEMORY_WINDOW * 2)


def _memory_as_messages() -> list[dict]:
    return list(_memory)


def _add_to_memory(role: str, content: str):
    _memory.append({"role": role, "content": content})


def clear_memory():
    """Call this to start a fresh conversation session."""
    _memory.clear()


# ── Core LLM helper ───────────────────────────────────────────────────────────

def _strip_think(text: str) -> str:
    """Strip DeepSeek <think>…</think> reasoning blocks from any LLM output."""
    return re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()


def _llm(prompt: str, system: str = "", temperature: float = 0.0) -> str:
    """Single-turn LLM call. Always strips <think> blocks before returning."""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    try:
        resp = ollama.chat(
            model="deepseek-r1",
            messages=messages,
            options={"temperature": temperature}
        )
        return _strip_think(resp["message"]["content"])
    except Exception as e:
        print(f"LLM call failed: {e}")
        return ""


# ── Stage 1: Query expansion ──────────────────────────────────────────────────
# Runs in parallel with Stage 2 (HyDE) via ThreadPoolExecutor.

REWRITE_SYSTEM = (
    "You are a search query expert. Given a user question and recent chat history, "
    "produce EXACTLY 3 alternative search queries that capture the same intent from "
    "different angles. Return them as a numbered list (1. 2. 3.) and nothing else."
)

def _expand_queries(user_query: str) -> list[str]:
    history_str = "".join(
        f"{m['role'].upper()}: {m['content']}\n"
        for m in _memory_as_messages()
    )
    prompt = (
        f"Chat history:\n{history_str}\n"
        f"Current question: {user_query}\n\n"
        "Generate 3 alternative search queries."
    )
    raw = _llm(prompt, system=REWRITE_SYSTEM, temperature=0.3)
    # Defensive strip — this output feeds the next stage
    raw = _strip_think(raw)

    queries = []
    for line in raw.splitlines():
        line = re.sub(r"^\d+[\.\)]\s*", "", line).strip()
        if line:
            queries.append(line)

    queries.insert(0, user_query)   # always keep the original
    return queries[:4]


# ── Stage 2: HyDE passage ─────────────────────────────────────────────────────
# Runs in parallel with Stage 1 (query expansion) via ThreadPoolExecutor.

HYDE_SYSTEM = (
    "You are a corporate policy analyst. Given a question, write a short 2-3 sentence "
    "passage that looks like it came directly from a corporate policy document. "
    "This is used for semantic search — do NOT answer the question, just write "
    "policy-sounding text that would be relevant to it."
)

def _generate_hyde_passage(user_query: str) -> str:
    result = _llm(user_query, system=HYDE_SYSTEM, temperature=0.2)
    # Defensive strip — this output goes directly into ChromaDB query_texts
    result = _strip_think(result)
    return result if result else user_query


# ── Parallel pre-processing ───────────────────────────────────────────────────
# Stages 1 and 2 are fully independent — fire them together, wait for both.
# ThreadPoolExecutor is appropriate here because ollama.chat is a blocking
# HTTP call that releases the GIL, so both threads make real parallel progress.

def _parallel_preprocess(user_query: str) -> tuple[list[str], str]:
    """Returns (expanded_queries, hyde_passage) concurrently."""
    with ThreadPoolExecutor(max_workers=2) as executor:
        future_queries = executor.submit(_expand_queries, user_query)
        future_hyde    = executor.submit(_generate_hyde_passage, user_query)
        expanded_queries = future_queries.result()
        hyde_passage     = future_hyde.result()
    return expanded_queries, hyde_passage


# ── Stage 3: Multi-query retrieval (hard cap = TOP_K_CAP) ────────────────────
# Merge results from all queries, deduplicate by chunk ID, return the TOP_K_CAP
# best matches only. Keeping the batch small is what makes the Batch Judge fast.

SEARCH_PREFIX = "Represent this sentence for searching relevant passages: "
TOP_K_CAP = 4


def _retrieve_chunks(queries: list[str], hyde_passage: str,
                     n_per_query: int = 3) -> list[tuple[str, float, str]]:
    """
    Returns at most TOP_K_CAP deduplicated (chunk_text, distance, source) tuples,
    sorted by cosine distance ascending (lower = more relevant).
    """
    if not collection:
        return []

    all_queries = [hyde_passage] + [SEARCH_PREFIX + q for q in queries]
    seen_ids: dict[str, tuple[str, float, str]] = {}

    for q in all_queries:
        try:
            results = collection.query(
                query_texts=[q],
                n_results=n_per_query,
                include=["documents", "distances", "metadatas"]
            )
            if not results["documents"] or not results["documents"][0]:
                continue

            for doc, dist, meta, cid in zip(
                results["documents"][0],
                results["distances"][0],
                results["metadatas"][0],
                results["ids"][0],
            ):
                source = meta.get("source", "unknown") if meta else "unknown"
                if cid not in seen_ids or dist < seen_ids[cid][1]:
                    seen_ids[cid] = (doc, dist, source)

        except Exception as e:
            print(f"Retrieval error for query '{q[:60]}': {e}")

    ranked = sorted(seen_ids.values(), key=lambda x: x[1])
    # Hard cap — only the mathematically best TOP_K_CAP chunks go to the judge
    return ranked[:TOP_K_CAP]


# ── Stage 4: Batch Judge ──────────────────────────────────────────────────────
# ALL chunks are graded in ONE single LLM call.
# The model returns a comma-separated score list; we parse it positionally.
# This replaces the old per-chunk loop (N LLM calls → 1 LLM call).

BATCH_JUDGE_SYSTEM = (
    "You are a strict relevance judge. You will be given a question and a numbered "
    "list of policy text chunks. Score EACH chunk from 0 to 10 for how directly it "
    "helps answer the question. 0 = completely irrelevant, 10 = directly answers it.\n"
    "Respond with ONLY a comma-separated list of integers, one per chunk, in order. "
    "Example for 4 chunks: 8, 2, 0, 9\n"
    "No explanation. No extra text. Just the numbers."
)

RELEVANCE_THRESHOLD = 4


def _batch_judge(
    chunks: list[tuple[str, float, str]],
    user_query: str,
) -> list[tuple[str, str]]:
    """
    Grades all chunks in a single LLM call.
    Returns (chunk_text, source) pairs that pass RELEVANCE_THRESHOLD,
    ordered by score descending.
    """
    if not chunks:
        return []

    chunk_lines = "\n\n".join(
        f"[{i+1}] (Source: {src})\n{text}"
        for i, (text, _dist, src) in enumerate(chunks)
    )
    prompt = (
        f"Question: {user_query}\n\n"
        f"Policy chunks:\n{chunk_lines}\n\n"
        f"Scores (comma-separated, {len(chunks)} numbers):"
    )

    raw = _llm(prompt, system=BATCH_JUDGE_SYSTEM, temperature=0.0)
    # Defensive strip — model might wrap scores in a <think> block
    raw = _strip_think(raw)

    # Parse comma-separated scores robustly
    scores: list[int] = []
    for token in re.split(r"[,\s]+", raw.strip()):
        try:
            scores.append(int(re.search(r"\d+", token).group()))
        except (AttributeError, ValueError):
            scores.append(0)

    # Pad with zeros if the model returned fewer scores than expected
    while len(scores) < len(chunks):
        scores.append(0)

    print(f"[BatchJudge] Scores: {scores[:len(chunks)]}")

    scored = [
        (chunks[i][0], chunks[i][2], scores[i])
        for i in range(len(chunks))
        if scores[i] >= RELEVANCE_THRESHOLD
    ]
    scored.sort(key=lambda x: x[2], reverse=True)
    return [(text, src) for text, src, _ in scored]


# ── Stage 5: Answer generation ────────────────────────────────────────────────

ANSWER_SYSTEM = (
    "You are the RegAI Policy Bot for Zomato. Answer questions using ONLY the "
    "provided policy context. Rules:\n"
    "1. Keep answers under 4 sentences.\n"
    "2. Be direct and professional.\n"
    "3. If the answer is not in the context, say exactly: "
    "'I cannot find that in our current policies.'\n"
    "4. Never mention 'context', 'chunks', or 'search results'.\n"
    "5. If relevant, cite the policy document name in parentheses."
)


def _build_context_block(relevant_chunks: list[tuple[str, str]]) -> str:
    return "\n\n---\n\n".join(
        f"[Source: {src}]\n{text}"
        for text, src in relevant_chunks
    )


# ── Public entry point ────────────────────────────────────────────────────────

def get_chat_response(user_query: str) -> str:
    """
    Optimized RAG pipeline — LLM call count vs. previous version:

      Previous: 1 (expand) + 1 (HyDE) + N (per-chunk judge) + 1 (answer) = N+3 calls
      Now:      1 (expand) ─┐                                               = 3 calls
                1 (HyDE)   ─┘ [parallel]
                              + 1 (batch judge) + 1 (answer)

      [Parallel]  Stage 1: Query expansion  ─┐
                  Stage 2: HyDE passage      ─┴─► Stage 3: Retrieval (cap=4)
                                                       │
                                             Stage 4: Batch Judge (1 LLM call)
                                                       │
                                             Stage 5: Answer generation
    """
    if not collection:
        return "I'm sorry, my policy database is currently unavailable."

    try:
        print(f"\n[ChatEngine] Query: {user_query}")

        # Stages 1 & 2 — parallel
        expanded_queries, hyde_passage = _parallel_preprocess(user_query)
        print(f"[ChatEngine] Queries : {expanded_queries}")
        print(f"[ChatEngine] HyDE    : {hyde_passage[:80]}…")

        # Stage 3 — retrieve, hard-capped at TOP_K_CAP
        raw_chunks = _retrieve_chunks(expanded_queries, hyde_passage, n_per_query=3)
        print(f"[ChatEngine] Retrieved {len(raw_chunks)} chunks (cap={TOP_K_CAP})")

        if not raw_chunks:
            return "I cannot find that in our current policies."

        # Stage 4 — batch judge (single LLM call for all chunks)
        relevant_chunks = _batch_judge(raw_chunks, user_query)
        print(f"[ChatEngine] {len(relevant_chunks)} chunks passed relevance filter")

        if not relevant_chunks:
            return "I cannot find that in our current policies."

        # Stage 5 — generate answer with conversation memory
        context_block = _build_context_block(relevant_chunks)
        messages = _memory_as_messages() + [{
            "role": "user",
            "content": (
                f"[CORPORATE POLICIES]\n{context_block}\n\n"
                f"[QUESTION]\n{user_query}"
            )
        }]

        resp = ollama.chat(
            model="deepseek-r1",
            messages=[{"role": "system", "content": ANSWER_SYSTEM}] + messages,
            options={"temperature": 0.1}
        )
        answer = _strip_think(resp["message"]["content"])

        _add_to_memory("user", user_query)
        _add_to_memory("assistant", answer)

        return answer

    except Exception as e:
        print(f"[ChatEngine] Fatal error: {e}")
        return "I encountered an error while searching the policies. Please try again later."
