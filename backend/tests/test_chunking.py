"""Tests for the token-based and paragraph-based chunking utilities."""

import pytest

from utils.chunking import chunk_by_paragraphs, chunk_text, count_tokens, smart_chunk


def test_count_tokens_nonzero_for_text():
    assert count_tokens("hello world") > 0


def test_count_tokens_empty_string_is_zero():
    assert count_tokens("") == 0


def test_chunk_text_respects_overlap():
    text = " ".join(f"word{i}" for i in range(500))
    chunks = chunk_text(text, chunk_size=50, chunk_overlap=10)

    assert len(chunks) > 1
    # Every chunk after the first should share its start with the previous
    # chunk's tail, which is what the overlap is for.
    for previous, current in zip(chunks, chunks[1:], strict=False):
        assert previous[2] - current[1] == 10


def test_chunk_text_single_short_text_returns_one_chunk():
    chunks = chunk_text("just a few words here", chunk_size=800, chunk_overlap=100)
    assert len(chunks) == 1


@pytest.mark.parametrize("size,overlap", [(50, 50), (0, 0), (50, -1)])
def test_chunk_text_rejects_invalid_chunk_budgets(size, overlap):
    with pytest.raises(ValueError):
        chunk_text("word " * 200, chunk_size=size, chunk_overlap=overlap)


def test_chunk_by_paragraphs_keeps_short_document_whole():
    text = "This is one short paragraph.\n\nAnd a second short paragraph."
    chunks = chunk_by_paragraphs(text, max_chunk_size=800)
    assert len(chunks) == 1


def test_chunk_by_paragraphs_splits_long_document():
    paragraph = "This sentence repeats to build up token count. " * 40
    text = "\n\n".join([paragraph] * 10)
    chunks = chunk_by_paragraphs(text, max_chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1


def test_smart_chunk_general_uses_paragraph_strategy():
    text = "Paragraph one.\n\nParagraph two.\n\nParagraph three."
    chunks = smart_chunk(text, document_type="general")
    assert len(chunks) >= 1
    assert all(isinstance(c, str) for c in chunks)


def test_smart_chunk_invoice_uses_token_strategy():
    text = "Invoice line items and totals go here. " * 20
    chunks = smart_chunk(text, document_type="invoice")
    assert len(chunks) >= 1


def test_paragraph_chunks_respect_budget_and_keep_content():
    paragraphs = ["alpha " * 60, "bravo " * 60, "charlie " * 30]
    budget = max(count_tokens(paragraph.strip()) for paragraph in paragraphs) + 10
    chunks = chunk_by_paragraphs("\n\n".join(paragraphs), max_chunk_size=budget, chunk_overlap=5)
    assert all(count_tokens(chunk) <= budget for chunk in chunks)
    for paragraph in paragraphs:
        assert any(paragraph.strip() in chunk for chunk in chunks)


def test_document_text_can_contain_tokenizer_special_marker():
    text = "Document describes <|endoftext|> as a literal marker."
    assert smart_chunk(text) == [text]
