"""知识检索服务。

这一层负责 RAG 里的“检索”部分。
以后通常会做这些事：
- 读取文档
- 切片
- 生成 embedding
- 去向量库查相似内容
"""
from app.service.vector_knowledge_service import VectorKnowledgeService


class KnowledgeService:
    """知识检索服务类。"""

    def search_medical_knowledge(query: str, top_k: int = 3) -> dict:
        """根据 query 从 ChromaDB 向量知识库返回相关片段。"""

        service = VectorKnowledgeService()
        return service.search(query=query, top_k=top_k)
