"""医疗问诊分诊业务逻辑。"""

from app.service.llm_service import LLMService
from app.service.risk_control_service import RiskControlService
from app.service.session_store import SessionStore
from app.service.tool_service import ToolService


class TriageService:
    """编排 LLM 抽取、风险控制和会话状态。"""

    def __init__(self):
        self.llm_service = LLMService()
        self.risk_control_service = RiskControlService()
        self.session_store = SessionStore()
        self.tool_service = ToolService()

    def start_triage(self, user_input: str) -> dict:
        """根据用户首轮症状描述开始问诊。"""

        llm_result = self.llm_service.extract_triage_info(user_input)
        symptoms = llm_result.get("symptoms", [])

        rule_risk = self.risk_control_service.check_risk(
            text=user_input,
            symptoms=symptoms,
        )
        llm_risk = self.tool_service.check_red_flags(
            user_input=user_input,
            symptoms=symptoms,
        )
        risk_result = self._merge_risk(rule_risk, llm_risk)

        result = {
            "symptoms": symptoms,
            "missing_fields": llm_result.get("missing_fields", []),
            "next_question": llm_result.get(
                "next_question",
                "请补充更多症状信息，例如持续时间、严重程度和伴随症状。",
            ),
            "risk_level": risk_result["risk_level"],
            "red_flags": risk_result["red_flags"],
        }

        session_id = self.session_store.create_session(user_input, result)

        return {
            "session_id": session_id,
            **result,
        }

    def continue_triage(self, session_id: str, user_input: str) -> dict:
        """继续已有问诊会话。"""

        session = self.session_store.get_session(session_id)
        if not session:
            raise ValueError("session_id 不存在")

        self.session_store.append_user_message(session_id, user_input)

        llm_result = self.llm_service.continue_triage_info(
            session=session,
            user_input=user_input,
        )
        symptoms = llm_result.get("symptoms", session.get("symptoms", []))

        rule_risk = self.risk_control_service.check_risk(
            text=user_input,
            symptoms=symptoms,
        )
        llm_risk = self.tool_service.check_red_flags(
            user_input=user_input,
            symptoms=symptoms,
        )
        risk_result = self._merge_risk(rule_risk, llm_risk)

        existing_red_flags = session.get("red_flags", [])
        red_flags = self._dedupe_flags(existing_red_flags + risk_result["red_flags"])
        risk_level = (
            "high"
            if session.get("risk_level") == "high" or risk_result["risk_level"] == "high"
            else risk_result["risk_level"]
        )

        update_data = {
            "symptoms": symptoms,
            "missing_fields": llm_result.get("missing_fields", []),
            "next_question": llm_result.get("next_question", ""),
            "risk_level": risk_level,
            "red_flags": red_flags,
            "summary": llm_result.get("updated_summary", ""),
        }

        self.session_store.update_session(session_id, update_data)

        return {
            "session_id": session_id,
            "updated_summary": update_data["summary"],
            "next_question": update_data["next_question"],
            "need_more_info": llm_result.get("need_more_info", True),
        }

    def evaluate_triage(self, session_id: str) -> dict:
        """根据已保存会话生成最终分诊建议。"""

        session = self.session_store.get_session(session_id)
        if not session:
            raise ValueError("session_id 不存在")

        symptoms = session.get("symptoms", [])
        risk_level = session.get("risk_level", "low")
        query = "、".join(symptoms) if symptoms else session.get("summary", "")

        knowledge_result = self.tool_service.search_knowledge(
            query=query,
            top_k=3,
        )

        appointment_result = self.tool_service.book_appointment(
            symptoms=symptoms,
            risk_level=risk_level,
        )
        session_for_evaluation = {
            **session,
            "knowledge": knowledge_result.get("results", []),
            "appointment": appointment_result,
        }

        llm_result = self.llm_service.evaluate_triage(session_for_evaluation)

        return {
            "summary": llm_result.get("summary", session.get("summary", "")),
            "risk_level": risk_level,
            "red_flags": session.get("red_flags", []),
            "department": appointment_result.get(
                "department",
                llm_result.get("department", "全科医学科"),
            ),
            "advice": llm_result.get(
                "advice",
                appointment_result.get(
                    "message",
                    "建议结合症状变化线下就诊；如出现明显加重或高风险症状，请及时急诊。",
                ),
            ),
            "references": knowledge_result.get(
                "references",
                llm_result.get("references", []),
            ),
        }

    def _merge_risk(self, rule_risk: dict, llm_risk: dict) -> dict:
        """保守合并规则风险结果和 LLM 风险结果。"""

        red_flags = self._dedupe_flags(
            rule_risk.get("red_flags", []) + llm_risk.get("red_flags", [])
        )

        if rule_risk.get("risk_level") == "high":
            risk_level = "high"
        elif llm_risk.get("risk_level") == "high":
            risk_level = "high"
        elif llm_risk.get("risk_level") == "unknown":
            risk_level = rule_risk.get("risk_level", "low")
        else:
            risk_level = "low"

        return {
            "risk_level": risk_level,
            "red_flags": red_flags,
        }

    def _dedupe_flags(self, flags: list[str]) -> list[str]:
        return list(dict.fromkeys(flag for flag in flags if flag))
