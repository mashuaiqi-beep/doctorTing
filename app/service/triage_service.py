"""医疗问诊分诊业务逻辑。"""
from app.service import redis_session_store, session_store_factory
from app.service.llm_service import LLMService
from app.service.risk_control_service import RiskControlService
from app.service.tool_service import ToolService
from app.agent.triage_graph import build_start_triage_graph, build_continue_triage_graph, build_evaluate_triage_graph


class TriageService:
    """编排 LLM 抽取、风险控制和会话状态。"""

    def __init__(self):
        # 1. 初始化所有依赖服务
        # 这些对象后面会被注入到 LangGraph 里。
        self.llm_service = LLMService()
        self.risk_control_service = RiskControlService()
        self.session_store = session_store_factory.create_session_store()
        self.tool_service = ToolService()

        # 2. 构建 start 图
        self.start_graph = build_start_triage_graph(
            llm_service=self.llm_service,
            risk_control_service=self.risk_control_service,
            tool_service=self.tool_service,
            session_store=self.session_store,
        )

        # 3. 构建 continue 图
        self.continue_graph = build_continue_triage_graph(
            llm_service=self.llm_service,
            risk_control_service=self.risk_control_service,
            tool_service=self.tool_service,
            session_store=self.session_store,
        )

        # 4. 构建 evaluate 图
        self.evaluate_graph = build_evaluate_triage_graph(
            llm_service=self.llm_service,
            tool_service=self.tool_service,
            session_store=self.session_store,
        )

    def start_triage(self, user_input: str) -> dict:
        """根据用户首轮症状描述开始问诊。"""

        final_state = self.start_graph.invoke(
            {
                "user_input": user_input,
            }
        )

        return final_state["response"]

    def continue_triage(self, session_id: str, user_input: str) -> dict:
        """
        调用 continue 图。
        """
        final_state = self.continue_graph.invoke(
            {
                "session_id": session_id,
                "user_input": user_input,
            }
        )
        return final_state["response"]

    def evaluate_triage(self, session_id: str) -> dict:
        """
        调用 evaluate 图。
        """
        final_state = self.evaluate_graph.invoke(
            {
                "session_id": session_id,
            }
        )
        return final_state["response"]