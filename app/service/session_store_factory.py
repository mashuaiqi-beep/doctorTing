"""会话存储工厂。

负责在启动时选择可用的存储后端：
- Redis 可用 → RedisSessionStore（生产模式）
- Redis 不可用 → MemorySessionStore（降级模式）
"""

import logging

from app.service.base_session_store import BaseSessionStore
from app.service.redis_session_store import RedisSessionStore

logger = logging.getLogger(__name__)


def create_session_store() -> BaseSessionStore:
    """创建会话存储实例，自动处理 Redis 不可用的降级。

    返回：
        BaseSessionStore —— Redis 或内存实现。
    """

    # 1. 先试 Redis
    try:
        store = RedisSessionStore()
        if store.health_check():
            logger.info("--会话存储：Redis（生产模式）--")
            return store
        else:
            logger.warning("⚠️ Redis ping 失败，降级为内存存储")
    except Exception:
        logger.warning("⚠️ Redis 连接失败，降级为内存存储")

    # 2. 兜底
    from app.service.session_store import SessionStore

    logger.info("--会话存储：内存（降级模式，重启后数据丢失）--")
    return SessionStore()
