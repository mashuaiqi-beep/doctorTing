from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

from app.core.config import settings

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class VectorKnowledgeService:
    """基于 ChromaDB 的本地向量知识库服务。"""

    def __init__(self):
        # PersistentClient 表示“本地持久化客户端”。
        # Chroma 会把向量数据库文件保存到 settings.CHROMA_PERSIST_DIR。
        self.client = chromadb.PersistentClient(
            path=str(PROJECT_ROOT / settings.CHROMA_PERSIST_DIR)
        )

        # collection 可以理解成一张“向量表”。
        # 类比数据库里的 table。
        #显式调用embedding方法
        self.embedding_function = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name="shibing624/text2vec-base-chinese"
        )

        self.collection = self.client.get_or_create_collection(
            name="medical_knowledge",
            embedding_function=self.embedding_function,
        )

        self.knowledge_dir = Path(__file__).resolve().parents[2] / "data" / "knowledge"

    def rebuild_index(self) -> dict:
        """重建知识库索引。

        做的事：
        1. 删除旧 collection
        2. 重新读取 Markdown
        3. 切 chunk
        4. 写入 Chroma
        """

        try:
            self.client.delete_collection(name="medical_knowledge")
        except Exception:
            pass

        self.collection = self.client.get_or_create_collection(
            name="medical_knowledge",
            embedding_function = self.embedding_function
        )

        documents = []
        metadatas = []
        ids = []

        for path in sorted(self.knowledge_dir.glob("*.md")):
            content = path.read_text(encoding="utf-8")
            chunks = self._split_markdown_to_chunks(content)

            for index, chunk in enumerate(chunks):
                doc_id = f"{path.stem}-{index}"
                documents.append(chunk)
                ids.append(doc_id)
                metadatas.append(
                    {
                        "source": path.name,
                        "title": self._extract_title(content, path.stem),
                        "chunk_index": index,
                    }
                )

        if documents:
            self.collection.add(
                ids=ids,
                documents=documents,
                metadatas=metadatas,
            )

        return {
            "indexed_chunks": len(documents),
            "collection": "medical_knowledge",
        }

    def search(self, query: str, top_k: int = 3) -> dict:
        """用向量相似度检索知识库。"""

        if self.collection.count() == 0:
            self.rebuild_index()

        result = self.collection.query(
            query_texts=[query],
            n_results=top_k,
        )

        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        results = []

        for index, document in enumerate(documents):
            metadata = metadatas[index]
            distance = distances[index] if index < len(distances) else None

            results.append(
                {
                    "keyword": metadata.get("title", ""),
                    "content": document,
                    "source": metadata.get("source", ""),
                    "score": distance,
                }
            )

        return {
            "query": query,
            "results": results,
            "references": self._extract_references(results),
        }

    def _split_markdown_to_chunks(self, content: str) -> list[str]:
        """把 Markdown 按段落切成 chunks。"""

        chunks = []
        raw_chunks = content.split("\n\n")

        for raw_chunk in raw_chunks:
            chunk = self._remove_markdown_heading_lines(raw_chunk)

            if not chunk:
                continue

            chunks.append(chunk)

        return chunks

    def _remove_markdown_heading_lines(self, text: str) -> str:
        """去掉 Markdown 标题行，保留标题下面的正文。

        以前的逻辑是：只要一个块以 # 开头，就把整个块跳过。
        但很多新知识文档是这种格式：

        ## 常见症状
        这里是一大段正文...

        如果直接跳过，就会把正文也丢掉。
        所以这里改成“只删除 # 开头的标题行，保留其他行”。
        """

        cleaned_lines = []

        for line in text.splitlines():
            cleaned = line.strip()

            if not cleaned:
                continue

            if cleaned.startswith("#"):
                continue

            cleaned_lines.append(cleaned)

        return "\n".join(cleaned_lines).strip()

    def _extract_title(self, content: str, default: str) -> str:
        """提取 Markdown 标题。"""

        for line in content.splitlines():
            if line.startswith("# "):
                return line.lstrip("#").strip()

        return default

    def _extract_references(self, results: list[dict]) -> list[str]:
        """提取去重后的来源文件名。"""

        references = []

        for item in results:
            source = item.get("source", "")
            if source and source not in references:
                references.append(source)

        return references
