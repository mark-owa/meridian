"""Text chunking strategies for the embedding pipeline.

Token-based chunking (rather than character-based) matters because OpenAI's
embedding models have token limits, not character limits. Overlap between
adjacent chunks prevents a fact from being split across a chunk boundary
and losing retrievability.
"""


import tiktoken


def get_tokenizer(model: str = "text-embedding-3-small") -> tiktoken.Encoding:
    try:
        return tiktoken.encoding_for_model(model)
    except KeyError:
        return tiktoken.get_encoding("cl100k_base")


def count_tokens(text: str, model: str = "text-embedding-3-small") -> int:
    return len(get_tokenizer(model).encode(text, disallowed_special=()))


def chunk_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    model: str = "text-embedding-3-small",
) -> list[tuple[str, int, int]]:
    """Split text into overlapping token-based chunks.

    Returns (chunk_text, start_token_idx, end_token_idx) tuples; the indices
    let a caller reconstruct where in the source document a chunk came from.
    """
    if chunk_size <= 0 or not 0 <= chunk_overlap < chunk_size:
        raise ValueError("Require chunk_size > 0 and 0 <= chunk_overlap < chunk_size")
    enc = get_tokenizer(model)
    tokens = enc.encode(text, disallowed_special=())

    chunks = []
    start = 0
    total_tokens = len(tokens)

    while start < total_tokens:
        end = min(start + chunk_size, total_tokens)
        chunk_content = enc.decode(tokens[start:end]).strip()
        if chunk_content:
            chunks.append((chunk_content, start, end))

        if end == total_tokens:
            break
        start += chunk_size - chunk_overlap

    return chunks


def chunk_by_paragraphs(
    text: str,
    max_chunk_size: int = 800,
    chunk_overlap: int = 100,
    model: str = "text-embedding-3-small",
) -> list[str]:
    """Chunk on paragraph boundaries first, falling back to token-based
    splitting for any single paragraph that exceeds max_chunk_size.
    Better suited to prose than chunk_text, since it avoids cutting an
    argument or clause in half.
    """
    if max_chunk_size <= 0 or not 0 <= chunk_overlap < max_chunk_size:
        raise ValueError("Require max_chunk_size > 0 and 0 <= chunk_overlap < max_chunk_size")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    enc = get_tokenizer(model)

    chunks = []
    current_chunk: list[str] = []

    for para in paragraphs:
        para_tokens = len(enc.encode(para, disallowed_special=()))

        if para_tokens > max_chunk_size:
            if current_chunk:
                chunks.append(" ".join(current_chunk))
                current_chunk = []
            chunks.extend(c[0] for c in chunk_text(para, max_chunk_size, chunk_overlap, model))
            continue

        candidate = " ".join([*current_chunk, para])
        if len(enc.encode(candidate, disallowed_special=())) > max_chunk_size and current_chunk:
            chunks.append(" ".join(current_chunk))
            overlap_para = current_chunk[-1]
            # Keep a whole-paragraph overlap only when both budgets allow it.
            if (
                len(enc.encode(overlap_para, disallowed_special=())) <= chunk_overlap
                and len(enc.encode(f"{overlap_para} {para}", disallowed_special=())) <= max_chunk_size
            ):
                current_chunk = [overlap_para, para]
            else:
                current_chunk = [para]
        else:
            current_chunk.append(para)

    if current_chunk:
        chunks.append(" ".join(current_chunk))

    return chunks


def smart_chunk(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
    document_type: str = "general",
) -> list[str]:
    """Pick a chunking strategy based on document type: uniform token
    chunks for structured documents, paragraph-aware chunks for prose."""
    if document_type in ("invoice", "receipt"):
        return [c[0] for c in chunk_text(text, chunk_size, chunk_overlap)]
    elif document_type in ("contract", "report", "general"):
        return chunk_by_paragraphs(text, chunk_size, chunk_overlap)
    return [c[0] for c in chunk_text(text, chunk_size, chunk_overlap)]
