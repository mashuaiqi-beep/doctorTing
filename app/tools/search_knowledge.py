"""轻量本地知识检索工具。

这个文件现在做的是“简化版 RAG”：
1. 从 data/knowledge 目录读取 Markdown 医疗知识文档。
2. 根据用户 query 里的关键词，判断哪些文档相关。
3. 返回相关片段和 references。

注意：
- 这不是最终向量 RAG。
- 但函数签名和返回结构会尽量保持稳定。
- 后面接向量数据库时，主要替换 search_medical_knowledge 内部逻辑即可。
"""

from pathlib import Path


# __file__ 表示“当前这个 Python 文件的路径”。
# Path(__file__).resolve() 会拿到当前文件的绝对路径。
# parents[2] 表示向上找两级目录：
#   app/tools/search_knowledge.py
#   parents[0] -> app/tools
#   parents[1] -> app
#   parents[2] -> doctorTing 项目根目录
# 然后拼出 data/knowledge 目录。
#
# 类比 Java：
# 你可以把 Path 理解成 Java 里的 Path / File，用来处理文件路径。
KNOWLEDGE_DIR = Path(__file__).resolve().parents[2] / "data" / "knowledge"


# 每个 Markdown 文件对应一组关键词。
# query 里只要出现这些词，就认为这个文档可能相关。
#
# 类比 Java：
# 这相当于 Map<String, List<String>>。
KEYWORD_ALIASES = {
    "fever.md": ["发热", "发烧", "高热", "体温", "寒战"],
    "cough.md": ["咳嗽", "咳痰", "有痰", "咯血", "呼吸困难", "气促"],
    "chest_pain.md": ["胸痛", "胸闷", "胸口", "心悸", "出汗", "呼吸困难"],
}


def search_medical_knowledge(query: str, top_k: int = 3) -> dict:
    """根据 query 从本地 Markdown 知识库返回相关片段。

    参数：
    - query: 检索词，比如 "发热 咳嗽"、"胸痛 呼吸困难"
    - top_k: 最多返回几条结果

    返回：
    {
        "query": 原始查询,
        "results": 相关知识片段列表,
        "references": 来源文件列表
    }
    """

    documents = _load_knowledge_documents()
    results = []

    # 遍历所有知识文档，给每篇文档打分。
    for document in documents:
        score = _score_document(query=query, document=document)

        # score <= 0 表示这个文档和 query 没有明显关系。
        if score <= 0:
            continue

        result_item = {
            "keyword": document["title"],
            "content": _select_snippet(query=query, content=document["content"]),
            "source": document["source"],
            "score": score,
        }
        results.append(result_item)

    # 按 score 从高到低排序。
    # Python 的 sort 类似 Java 里 Collections.sort(list, comparator)。
    # lambda item: item["score"] 可以理解为“按每个元素的 score 字段排序”。
    results.sort(key=lambda item: item["score"], reverse=True)

    if not results:
        results = [
            {
                "keyword": "general",
                "content": "暂未检索到明确匹配的知识片段，建议结合症状变化线下就诊。",
                "source": "general_triage.md",
                "score": 0,
            }
        ]

    # Python 切片 results[:top_k] 表示取前 top_k 个元素。
    # 类比 Java：list.subList(0, Math.min(topK, list.size()))。
    selected_results = results[:top_k]

    return {
        "query": query,
        "results": selected_results,
        "references": _extract_references(selected_results),
    }


def _load_knowledge_documents() -> list[dict]:
    """读取 data/knowledge 目录下所有 Markdown 文档。"""

    if not KNOWLEDGE_DIR.exists():
        return []

    documents = []

    # glob("*.md") 表示找出目录下所有 .md 文件。
    # sorted(...) 是为了让文件读取顺序稳定，方便测试和调试。
    for path in sorted(KNOWLEDGE_DIR.glob("*.md")):
        # read_text 是 Python 读取文本文件的便捷方法。
        # encoding="utf-8" 是为了正确读取中文。
        content = path.read_text(encoding="utf-8").strip()

        if not content:
            continue

        document = {
            "source": path.name,
            "title": _extract_title(content, path.stem),
            "content": content,
            "aliases": KEYWORD_ALIASES.get(path.name, []),
        }
        documents.append(document)

    return documents


def _extract_title(content: str, default: str) -> str:
    """从 Markdown 第一行标题中提取文档标题。"""

    lines = content.splitlines()
    for line in lines:
        if line.startswith("# "):
            # lstrip("#") 去掉左侧的 #，strip() 去掉两边空格。
            return line.lstrip("#").strip()

    return default


def _score_document(query: str, document: dict) -> int:
    """根据 query 和文档关键词计算相关性分数。"""

    score = 0

    for alias in document["aliases"]:
        # Python 的 "胸痛" in query 类似 Java 里的 query.contains("胸痛")。
        if alias in query:
            score += 3

    if document["title"] in query:
        score += 5

    source_name = document["source"].replace(".md", "")
    if source_name in query:
        score += 2

    return score


def _select_snippet(query: str, content: str) -> str:
    """从文档里选一段最适合返回给 LLM 的内容。"""

    paragraphs = _split_paragraphs(content)

    if not paragraphs:
        # content[:200] 表示取前 200 个字符。
        return content[:200]

    query_terms = _extract_query_terms(query)

    for paragraph in paragraphs:
        for term in query_terms:
            if term in paragraph:
                return paragraph

    # 如果没有段落直接命中关键词，就返回第一段正文。
    return paragraphs[0]


def _split_paragraphs(content: str) -> list[str]:
    """把 Markdown 内容按空行拆成段落，并过滤标题。"""

    paragraphs = []

    # Markdown 里通常用一个空行分隔段落，所以这里用 "\n\n" 拆分。
    raw_paragraphs = content.split("\n\n")

    for paragraph in raw_paragraphs:
        cleaned = paragraph.strip()

        if not cleaned:
            continue

        # 跳过 Markdown 标题行，比如 "# 发热"。
        if cleaned.startswith("#"):
            continue

        paragraphs.append(cleaned)

    return paragraphs


def _extract_query_terms(query: str) -> list[str]:
    """从 query 中提取命中的关键词。"""

    terms = []

    for aliases in KEYWORD_ALIASES.values():
        for alias in aliases:
            if alias in query:
                terms.append(alias)

    return terms


def _extract_references(results: list[dict]) -> list[str]:
    """从检索结果中提取去重后的来源文件名。"""

    references = []

    for item in results:
        source = item["source"]

        # 用 list 做去重：如果没出现过，再 append。
        # 这里不用 set，是为了保持来源出现顺序稳定。
        if source not in references:
            references.append(source)

    return references
