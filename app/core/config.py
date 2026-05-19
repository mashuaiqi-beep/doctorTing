"""项目配置。

统一管理运行时配置，避免在业务代码里写死模型、数据库或缓存连接信息。
"""

import os


class Settings:
    """从环境变量读取的应用配置。"""

    OPENAI_API_KEY: str = "sk-12ff9e3dc09847ecba964d7143d74a6a"
    OPENAI_BASE_URL: str = "https://api.deepseek.com"
    OPENAI_MODEL: str = "deepseek-chat"

    APP_NAME: str = "Medical Triage Agent"
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://:123456@localhost:6379/0")
    REDIS_SESSION_TTL_SECONDS: int = int(
        os.getenv("REDIS_SESSION_TTL_SECONDS", "86400")
    )

    CHROMA_PERSIST_DIR: str = os.getenv("CHROMA_PERSIST_DIR", "data/chroma")


settings = Settings()
