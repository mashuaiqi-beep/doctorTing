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

KEYWORD_ALIASES: dict[str, list[str]] = {
    "fever.md": ["发热", "发烧", "体温高", "高热", "体温"],
    "cough.md": ["咳嗽", "咳", "干咳", "咳痰"],
    "chest_pain.md": ["胸痛", "胸闷", "胸口疼", "胸口痛"],
    "社区获得性肺炎.md": ["社区获得性肺炎", "肺炎", "CAP"],
    "支气管哮喘.md": ["支气管哮喘", "哮喘", "气喘"],
    "慢性阻塞性肺疾病.md": ["慢性阻塞性肺疾病", "慢阻肺", "COPD"],
    "支气管扩张.md": ["支气管扩张", "支扩"],
    "肺血栓栓塞症.md": ["肺血栓栓塞症", "肺栓塞", "PE", "PTE"],
    "支原体肺炎.md": ["支原体肺炎", "MP肺炎"],
    "自发性气胸.md": ["自发性气胸", "气胸"],
    "原发性高血压.md": ["原发性高血压", "高血压", "血压高", "血压"],
    "冠心病.md": ["冠心病", "冠状动脉粥样硬化性心脏病", "CHD", "心绞痛"],
    "心力衰竭.md": ["心力衰竭", "心衰", "HF"],
    "心房颤动.md": ["心房颤动", "房颤", "AF"],
    "病毒性心肌炎.md": ["病毒性心肌炎", "心肌炎"],
    "胃食管反流病.md": ["胃食管反流病", "胃食管反流", "GERD", "反流性食管炎"],
    "消化性溃疡.md": ["消化性溃疡", "胃溃疡", "十二指肠溃疡", "PU"],
    "急性阑尾炎.md": ["急性阑尾炎", "阑尾炎", "右下腹痛"],
    "胆囊结石伴胆囊炎.md": ["胆囊结石伴胆囊炎", "胆囊结石", "胆囊炎", "胆结石"],
    "急性胰腺炎.md": ["急性胰腺炎", "胰腺炎", "AP"],
    "肠梗阻.md": ["肠梗阻", "IO"],
    "结肠息肉.md": ["结肠息肉", "肠息肉"],
    "肝硬化.md": ["肝硬化"],
    "脑梗死.md": ["脑梗死", "脑梗", "脑梗塞", "缺血性脑卒中", "中风"],
    "脑出血.md": ["脑出血", "脑溢血", "出血性脑卒中"],
    "短暂性脑缺血发作.md": ["短暂性脑缺血发作", "TIA", "小中风"],
    "癫痫.md": ["癫痫", "EP", "抽风", "羊癫疯"],
    "偏头痛.md": ["偏头痛", "头痛", "头疼"],
    "三叉神经痛.md": ["三叉神经痛", "面部疼痛"],
    "面神经麻痹.md": ["面神经麻痹", "面瘫", "面神经炎"],
    "2型糖尿病.md": ["2型糖尿病", "二型糖尿病", "糖尿病", "T2DM", "血糖高"],
    "1型糖尿病.md": ["1型糖尿病", "一型糖尿病", "T1DM"],
    "甲状腺功能亢进.md": ["甲状腺功能亢进", "甲亢"],
    "甲状腺功能减退.md": ["甲状腺功能减退", "甲减"],
    "泌尿系结石.md": ["泌尿系结石", "肾结石", "输尿管结石", "尿结石", "尿路结石"],
    "前列腺增生.md": ["前列腺增生", "BPH", "前列腺肥大"],
    "尿路感染.md": ["尿路感染", "UTI", "尿道炎", "膀胱炎"],
    "慢性肾炎.md": ["慢性肾炎", "慢性肾小球肾炎", "肾炎"],
    "子宫肌瘤.md": ["子宫肌瘤"],
    "卵巢囊肿.md": ["卵巢囊肿"],
    "宫颈炎.md": ["宫颈炎", "宫颈炎症"],
    "腰椎间盘突出.md": ["腰椎间盘突出", "腰突", "腰痛", "腰疼"],
    "颈椎病.md": ["颈椎病", "颈椎", "脖子疼"],
    "骨质疏松.md": ["骨质疏松", "OP"],
    "骨关节炎.md": ["骨关节炎", "OA", "关节炎"],
    "荨麻疹.md": ["荨麻疹", "风团", "风疹块", "过敏"],
    "带状疱疹.md": ["带状疱疹", "HZ", "缠腰龙"],
    "慢性鼻窦炎.md": ["慢性鼻窦炎", "鼻窦炎"],
    "扁桃体炎.md": ["扁桃体炎", "扁桃体", "嗓子疼", "喉咙痛"],
    "过敏性鼻炎.md": ["过敏性鼻炎", "鼻炎", "鼻过敏", "花粉症"],
    "急性结膜炎.md": ["急性结膜炎", "结膜炎", "红眼病", "红眼"],
    "白内障.md": ["白内障", "视力模糊"],
    "缺铁性贫血.md": ["缺铁性贫血", "贫血", "IDA"],
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

def search_medical_knowledge(query: str, top_k: int = 3) -> dict:
    """根据 query 检索医疗知识，返回相关片段和来源。

    这是模块对外暴露的唯一入口。
    返回结构保持稳定，后续接向量数据库时只替换内部逻辑。
    """

    documents = _load_knowledge_documents()

    scored: list[tuple[int, dict]] = []
    for doc in documents:
        score = _score_document(query, doc)
        snippet = _select_snippet(query, doc["content"])
        scored.append((score, {
            "source": doc["source"],
            "content": snippet,
        }))

    scored.sort(key=lambda item: item[0], reverse=True)
    results = [item for _, item in scored[:top_k]]

    if not results or scored[0][0] == 0:
        results = [{
            "source": "general_triage.md",
            "content": "请详细描述您的症状、持续时间和严重程度，以便为您提供更准确的分诊建议。",
            "keyword": "general",
        }]

    matched = [r for s, r in scored if s > 0]
    if not matched:
        references = [results[0]["source"]]
    else:
        references = _extract_references(matched[:top_k])

    return {
        "query": query,
        "results": results,
        "references": references,
    }


def load_knowledge_by_references(references: list[str]) -> list[dict]:
    """根据 references 读取完整 Markdown 文件内容。

    参数：
    - references: 例如 ["偏头痛.md", "cough.md"]

    返回：
    [
        {
            "source": "偏头痛.md",
            "content": "整篇 markdown 内容..."
        }
    ]
    """

    documents = []

    for source in references:
        path = KNOWLEDGE_DIR / source

        # 防止传入不存在的文件名。
        if not path.exists():
            continue

        content = path.read_text(encoding="utf-8").strip()

        if not content:
            continue

        documents.append(
            {
                "source": source,
                "content": content,
            }
        )

    return documents

