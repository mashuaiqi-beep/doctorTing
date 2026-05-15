"""用于后续 Tool Calling 工作流的简单症状抽取工具。"""


def extract_symptoms(text: str) -> dict:
    """使用最小关键词匹配抽取症状。"""

    symptoms = []
    for keyword in ["发热", "咳嗽", "胸闷", "胸痛", "腹痛", "呼吸困难"]:
        if keyword in text:
            symptoms.append(keyword)

    return {"symptoms": symptoms}
