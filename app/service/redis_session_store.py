import json
from datetime import datetime
from uuid import uuid4

import redis

from app.core.config import settings


class RedisSessionStore:
    """基于 Redis 的问诊 session 存储。"""

    def __init__(self):
        self.client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        self.ttl_seconds = settings.REDIS_SESSION_TTL_SECONDS

    def upsert_session(
            self,
            session_id: str | None,
            user_input: str | None,
            data: dict,
    ) -> str:
        """存在则更新 session，不存在则创建 session。

        参数：
        - session_id: 已有会话 ID；如果是 None 或找不到，就创建新 session
        - user_input: 当前用户输入；如果有值，会追加到 messages
        - data: 要写入/更新的结构化状态
        """

        now = datetime.now().isoformat()

        if session_id:
            session = self.get_session(session_id)
        else:
            session = None

        if not session:
            session_id = str(uuid4())
            session = {
                "session_id": session_id,
                "messages": [],
                "symptoms": [],
                "missing_fields": [],
                "next_question": "",
                "risk_level": "low",
                "red_flags": [],
                "summary": "",
                "retrieval_query": "",
                "state_history": [],
                "created_at": now,
                "updated_at": now,
            }

        if user_input:
            session["messages"].append(
                {
                    "role": "user",
                    "content": user_input,
                    "created_at": now,
                }
            )

        session.update(data)
        session["updated_at"] = now

        session["state_history"].append(
            {
                "symptoms": session.get("symptoms", []),
                "missing_fields": session.get("missing_fields", []),
                "risk_level": session.get("risk_level", "low"),
                "red_flags": session.get("red_flags", []),
                "summary": session.get("summary", ""),
                "retrieval_query": session.get("retrieval_query", ""),
                "updated_at": now,
            }
        )
        session["state_history"] = session["state_history"][-20:]

        self._save_session(session_id, session)

        return session_id


    def create_session(self, user_input: str, triage_result: dict) -> str:
        session_id = str(uuid4())
        now = datetime.now().isoformat()

        session = {
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
            "retrieval_query": triage_result.get("retrieval_query", ""),
            "created_at": now,
            "updated_at": now,
        }

        self._save_session(session_id, session)

        return session_id

    def get_session(self, session_id: str) -> dict | None:
        raw = self.client.get(self._key(session_id))

        if not raw:
            return None

        return json.loads(raw)

    def append_user_message(self, session_id: str, user_input: str) -> None:
        session = self.get_session(session_id)

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

        self._save_session(session_id, session)

    def update_session(self, session_id: str, data: dict) -> None:
        session = self.get_session(session_id)

        if not session:
            return

        session.update(data)
        session["updated_at"] = datetime.now().isoformat()

        self._save_session(session_id, session)

    def _save_session(self, session_id: str, session: dict) -> None:
        self.client.setex(
            self._key(session_id),
            self.ttl_seconds,
            json.dumps(session, ensure_ascii=False),
        )

    def _key(self, session_id: str) -> str:
        return f"triage:session:{session_id}"
