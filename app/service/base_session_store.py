from abc import ABC, abstractmethod


class BaseSessionStore(ABC):
    """会话存储的统一接口。"""

    @abstractmethod
    def upsert_session(
            self,
            session_id: str | None,
            user_input: str | None,
            data: dict,
    ) -> str:
        """创建或更新会话，返回 session_id。"""
        ...

    @abstractmethod
    def get_session(self, session_id: str) -> dict | None:
        """根据 session_id 获取会话，不存在时返回 None。"""
        ...

    @abstractmethod
    def append_user_message(self, session_id: str, user_input: str) -> None:
        """向已有会话追加一条用户消息。"""
        ...

    @abstractmethod
    def update_session(self, session_id: str, data: dict) -> None:
        """更新会话的部分字段。"""
        ...

    @abstractmethod
    def health_check(self) -> bool:
        """检查存储后端是否可用。Redis 版 ping，内存版永远返回 True。"""
        ...
