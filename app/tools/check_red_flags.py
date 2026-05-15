"""用于确定性红旗症状检查的工具函数。"""

from app.core.risk_rules import RED_FLAG_KEYWORDS


def check_red_flags(text: str) -> dict:
    """检查输入文本中是否包含红旗关键词。"""

    matched = [word for word in RED_FLAG_KEYWORDS if word in text]
    return {
        "has_red_flags": bool(matched),
        "red_flags": matched,
    }
