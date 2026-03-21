from services import rag


def test_extract_pdf_chunks(sample_pdf):
    chunks = rag.extract_pdf_chunks(sample_pdf, chunk_size=40)
    assert len(chunks) >= 2
    assert isinstance(chunks[0][0], str)
    assert isinstance(chunks[0][1], int)


def test_index_pdf(tmp_chroma, sample_pdf, mock_embedder):
    count = rag.index_pdf("u1", "sample.pdf", sample_pdf)
    assert count > 0


def test_query_after_index(tmp_chroma, sample_pdf, mock_embedder):
    rag.index_pdf("u1", "sample.pdf", sample_pdf)
    results = rag.query_documents("u1", "semantic search", top_k=3)
    assert len(results) > 0


def test_query_returns_citations(tmp_chroma, sample_pdf, mock_embedder):
    rag.index_pdf("u1", "sample.pdf", sample_pdf)
    results = rag.query_documents("u1", "WhatsApp files", top_k=2)
    assert len(results) > 0
    first = results[0]
    assert "file_name" in first
    assert "page" in first
    assert "distance" in first


def test_query_different_user_isolation(tmp_chroma, sample_pdf, mock_embedder):
    rag.index_pdf("u1", "sample.pdf", sample_pdf)
    results = rag.query_documents("u2", "WhatsApp files", top_k=5)
    assert results == []


def test_delete_user_docs(tmp_chroma, sample_pdf, mock_embedder):
    rag.index_pdf("u1", "sample.pdf", sample_pdf)
    before = rag.query_documents("u1", "WhatsApp files", top_k=5)
    assert len(before) > 0
    rag.delete_user_docs("u1", "sample.pdf")
    after = rag.query_documents("u1", "WhatsApp files", top_k=5)
    assert after == []
