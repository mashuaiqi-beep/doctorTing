import time

from datetime import datetime
from uuid import uuid4

from app.service.base_session_store import BaseSessionStore

class SessionStore(BaseSessionStore):
    """简单的内存会话存储，用于当前 Demo。"""

    def __init__(self):
        self.sessions = {}

    def upsert_session(
            self,
            session_id: str | None,
            user_input: str | None,
            data: dict,
    ) -> str:
        """存在则更新，不存在则创建。"""
        now = datetime.now().isoformat()

        if session_id:
            session = self.get_session(session_id)
        else:
            session = None

        if not session:
            session_id = str(uuid4())
            session = self._build_default_session(session_id=session_id, now=now)

        if user_input:
            session["messages"].append(
                {"role": "user", "content": user_input, "created_at": now}
            )

        session.update(data)
        session["updated_at"] = now

        # 追加状态快照
        session["state_history"].append({
            "stage": session.get("stage", "started"),
            "symptoms": session.get("symptoms", []),
            "confirmed_facts": session.get("confirmed_facts", {}),
            "uncertain_facts": session.get("uncertain_facts", []),
            "missing_fields": session.get("missing_fields", []),
            "risk_level": session.get("risk_level", "low"),
            "red_flags": session.get("red_flags", []),
            "summary": session.get("summary", ""),
            "retrieval_query": session.get("retrieval_query", ""),
            "needs_human_review": session.get("needs_human_review", False),
            "last_tool_status": session.get("last_tool_status", {}),
            "updated_at": now,
        })
        session["state_history"] = session["state_history"][-20:]

        self.sessions[session_id] = session
        self._evict_expired()

        return session_id

    def get_session(self, session_id: str) -> dict | None:
        """获取会话，自动补全缺失字段。"""
        session = self.sessions.get(session_id)
        if session is None:
            return None

        # 兼容老版本 session 缺少新字段的情况
        session.setdefault("stage", "started")
        session.setdefault("summary", "")
        session.setdefault("symptoms", [])
        session.setdefault("confirmed_facts", {})
        session.setdefault("uncertain_facts", [])
        session.setdefault("missing_fields", [])
        session.setdefault("references", [])
        session.setdefault(
            "last_tool_status",
            {"tool_name": "", "status": "idle", "error": None},
        )
        session.setdefault("needs_human_review", False)
        session.setdefault("state_history", [])
        session.setdefault("messages", [])
        return session

    def append_user_message(self, session_id: str, user_input: str) -> None:
        session = self.get_session(session_id)
        if not session:
            return

        session["messages"].append({
            "role": "user",
            "content": user_input,
            "created_at": datetime.now().isoformat(),
        })
        session["updated_at"] = datetime.now().isoformat()
        self.sessions[session_id] = session

    def update_session(self, session_id: str, data: dict) -> None:
        session = self.get_session(session_id)
        if not session:
            return

        session.update(data)
        session["updated_at"] = datetime.now().isoformat()
        self.sessions[session_id] = session

    def health_check(self) -> bool:
        """内存存储永远可用。"""
        return True

    def create_session(self, user_input: str, triage_result: dict) -> str:
        session_id = str(uuid4())
        now = datetime.now().isoformat()

        self.sessions[session_id] = {
            "session_id": session_id,
            "messages": [
                {
                    "role": "user",
                    "content": user_input,
                    "created_at": now,
                }
            ],
            "symptoms": triage_result.get("symptoms", []),
            "missing_fields": triage_result.get("missing_fields", []),
            "next_question": triage_result.get("next_question", ""),
            "risk_level": triage_result.get("risk_level", "low"),
            "red_flags": triage_result.get("red_flags", []),
            "summary": triage_result.get("summary", ""),
            "created_at": now,
            "updated_at": now,
        }

        return session_id

    def get_session(self, session_id: str) -> dict | None:
        return self.sessions.get(session_id)

    def append_user_message(self, session_id: str, user_input: str) -> None:
        session = self.sessions.get(session_id)
        if not session:
            return

        session["messages"].append(
            {
                "role": "user",
                "content": user_input,
                "created_at": datetime.now().isoformat(),
            }
        )
        session["updated_at"] = datetime.now().isoformat()

    def update_session(self, session_id: str, data: dict) -> None:
        session = self.sessions.get(session_id)
        if not session:
            return

        session.update(data)
        session["updated_at"] = datetime.now().isoformat()

    def _build_default_session(self, session_id: str, now: str) -> dict:
        """新会话的初始骨架，字段和 Redis 版完全对齐。"""
        return {
            "session_id": session_id,
            "stage": "started",
            "messages": [],
            "summary": "",
            "symptoms": [],
            "confirmed_facts": {},
            "uncertain_facts": [],
            "missing_fields": [],
            "risk_level": "low",
            "red_flags": [],
            "retrieval_query": "",
            "references": [],
            "last_tool_status": {
                "tool_name": "",
                "status": "idle",
                "error": None,
            },
            "needs_human_review": False,
            "state_history": [],
            "created_at": now,
            "updated_at": now,
        }

    def _evict_expired(self) -> None:
        """清理过期会话，防止内存无限增长。

        默认 TTL 和 Redis 版一致（24 小时）。
        超过 2 倍 TTL 仍无活动的会话会被清理。
        """
        from app.core.config import settings

        ttl = settings.REDIS_SESSION_TTL_SECONDS
        now_ts = time.time()
        expired_ids = []

        for sid, s in self.sessions.items():
            try:
                updated = datetime.fromisoformat(s.get("updated_at", ""))
                age = now_ts - updated.timestamp()
                if age > ttl * 2:
                    expired_ids.append(sid)
            except (ValueError, OSError):
                expired_ids.append(sid)

        for sid in expired_ids:
            del self.sessions[sid]