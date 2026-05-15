import pytest

pytest.importorskip("chromadb")

from app.service.vector_knowledge_service import VectorKnowledgeService
from app.tools.search_knowledge import search_medical_knowledge


def test_vector_knowledge_index_can_be_built():
    """向量知识库能从 data/knowledge 读取 Markdown 并写入 chunk。"""

    service = VectorKnowledgeService()
    result = service.rebuild_index()

    assert result["collection"] == "medical_knowledge"
    assert result["indexed_chunks"] > 0
    assert service.collection.count() == result["indexed_chunks"]


def test_vector_knowledge_search_returns_references():
    """向量检索能返回知识片段和来源文件。"""

    service = VectorKnowledgeService()
    result = service.search("胸口像被压着，还有点喘不上气", top_k=2)

    assert result["query"] == "胸口像被压着，还有点喘不上气"
    assert result["results"]
    assert result["references"]

    first_result = result["results"][0]
    assert first_result["content"]
    assert first_result["source"].endswith(".md")


def test_search_medical_knowledge_public_entry_returns_stable_shape():
    """公开工具入口保持稳定返回结构，方便 evaluate 主链路调用。"""

    result = search_medical_knowledge("我胸痛胸闷，还有点呼吸困难", top_k=2)

    assert set(result.keys()) == {"query", "results", "references"}
    assert result["results"]
    assert result["references"]

    for item in result["results"]:
        assert "content" in item
        assert "source" in item
        assert item["source"].endswith(".md")
