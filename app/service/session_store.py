from datetime import datetime
from uuid import uuid4


class SessionStore:
    """简单的内存会话存储，用于当前 Demo。"""

    def __init__(self):
        self.sessions = {}

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
