import json
from datetime import datetime
from uuid import uuid4

import redis

from app.core.config import settings


class RedisSessionStore:
    """基于 Redis 的问诊会话存储。"""

    def __init__(self):
        self.client = redis.Redis.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
        self.ttl_seconds = 60 * 60 * 24

    def _key(self, session_id: str) -> str:
        return f"triage:session:{session_id}"

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
            "created_at": now,
            "updated_at": now,
        }

        self.client.setex(
            self._key(session_id),
            self.ttl_seconds,
            json.dumps(session, ensure_ascii=False),
        )

        return session_id

    def get_session(self, session_id: str) -> dict | None:
        raw = self.client.get(self._key(session_id))
        if not raw:
            return None

        return json.loads(raw)

    def update_session(self, session_id: str, data: dict) -> None:
        session = self.get_session(session_id)
        if not session:
            return

        session.update(data)
        session["updated_at"] = datetime.now().isoformat()

        self.client.setex(
            self._key(session_id),
            self.ttl_seconds,
            json.dumps(session, ensure_ascii=False),
        )

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

        self.client.setex(
            self._key(session_id),
            self.ttl_seconds,
            json.dumps(session, ensure_ascii=False),
        )
