from app.service.triage_service import TriageService


class FailingLLMService:
    def extract_triage_info(self, user_input: str) -> dict:
        return {
            "symptoms": [],
            "missing_fields": ["体温", "症状持续时间", "是否呼吸困难"],
            "next_question": "请问最高体温是多少？症状持续了多久？有没有呼吸困难？",
        }

    def continue_triage_info(self, session: dict, user_input: str) -> dict:
        return {
            "updated_summary": session.get("summary", ""),
            "symptoms": session.get("symptoms", []),
            "missing_fields": session.get("missing_fields", []),
            "next_question": "请继续补充症状持续时间、严重程度和伴随症状。",
            "need_more_info": True,
        }

    def evaluate_triage(self, session: dict) -> dict:
        return {
            "summary": session.get("summary", ""),
            "department": "全科医学科",
            "advice": "建议结合症状变化线下就诊；如出现明显加重或高风险症状，请及时急诊。",
            "references": [],
        }

    def detect_red_flags(self, user_input: str, symptoms: list[str]) -> dict:
        return {
            "has_red_flags": False,
            "red_flags": [],
            "risk_level": "unknown",
            "reason": "LLM 判断失败，已回退到规则判断。",
        }


def test_rule_risk_still_works_when_llm_red_flag_detection_is_unknown():
    service = TriageService()
    service.llm_service = FailingLLMService()

    result = service.start_triage("我胸痛，而且越来越严重")

    assert result["risk_level"] == "high"
    assert "胸痛" in result["red_flags"]


def test_high_risk_session_is_not_downgraded_on_follow_up():
    service = TriageService()
    service.llm_service = FailingLLMService()

    started = service.start_triage("我胸痛")
    continued = service.continue_triage(started["session_id"], "现在没有其他症状")
    evaluated = service.evaluate_triage(started["session_id"])

    assert continued["session_id"] == started["session_id"]
    assert evaluated["risk_level"] == "high"
    assert "胸痛" in evaluated["red_flags"]
