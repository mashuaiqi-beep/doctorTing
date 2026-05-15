"""文本工具函数。

`utils/` 目录放的是通用小工具，不放业务主逻辑。
"""


def normalize_text(text: str) -> str:
    """做最基础的文本清洗。"""
    return text.strip()
