"""doctorTing 的 LangGraph 编排层。

这个文件不要理解成普通的 service，也不要理解成 HTTP API。

它的职责是：
- 定义 Agent 流程中的 State，也就是每个节点之间传递的数据包。
- 定义一个个节点函数，每个节点只负责流程中的一个步骤。
- 使用 LangGraph 把节点连接成一张可执行的图。

在当前项目里，`start_triage` 的真实业务能力仍然来自这些对象：
- `LLMService`：负责调用大模型提取首轮问诊信息。
- `RiskControlService`：负责用确定性规则检查红旗症状。
- `ToolService`：负责工具调用，比如 LLM function calling 风险判断。
- `SessionStore` / `RedisSessionStore`：负责保存问诊 session。

LangGraph 做的是“流程编排”：
用户输入 -> 提取信息 -> 规则风险判断 -> LLM 风险判断 -> 合并风险 -> 保存 session -> 组装响应
"""

from typing import TypedDict

from langgraph.graph import END, StateGraph


class StartTriageState(TypedDict, total=False):
    """`/triage/start` 这条 LangGraph 流程里流动的状态对象。

    LangGraph 的核心概念之一就是 State。

    你可以把 State 理解成一张“流程工作台”：
    - 第一个节点从 State 里拿 `user_input`。
    - 它把 `llm_result` 和 `symptoms` 写回 State。
    - 后面的节点继续读取前面节点写入的字段。
    - 最后一个节点把接口需要返回的内容写到 `response`。

    `total=False` 的意思是：
    这些字段不要求一开始全部存在。刚进入图时，通常只有 `user_input`。
    后续字段会被各个 node 一步步补齐。
    """

    # 图的初始输入：来自 TriageService.start_triage(user_input)。
    user_input: str

    # LLM 首轮抽取结果，比如症状、缺失字段、下一轮追问、检索 query。
    llm_result: dict
    symptoms: list[str]

    # 两层风险判断结果：
    # rule_risk 来自确定性关键词规则，llm_risk 来自 ToolService 的 LLM function calling。
    rule_risk: dict
    llm_risk: dict
    risk_result: dict

    # triage_data 是准备写入 session 的结构化问诊数据。
    triage_data: dict
    session_id: str

    # response 是最终返回给 API 层的结构。
    response: dict

class ContinueTriageState(TypedDict, total=False):
    session_id: str
    user_input: str
    session: dict
    llm_result: dict
    symptoms: list[str]
    rule_risk: dict
    llm_risk: dict
    risk_result: dict
    update_data: dict
    response: dict


class EvaluateTriageState(TypedDict, total=False):
    session_id: str
    session: dict
    query: str
    knowledge_result: dict
    references: list[str]
    full_knowledge: list[dict]
    appointment_result: dict
    session_for_evaluation: dict
    llm_result: dict
    response: dict

def dedupe_flags(flags: list[str]) -> list[str]:
    """
    对红旗症状去重，并保留原顺序。

    例如：
    ["胸痛", "呼吸困难", "胸痛"]
    -> ["胸痛", "呼吸困难"]
    """
    return list(dict.fromkeys(flag for flag in flags if flag))


def merge_risk(rule_risk: dict, llm_risk: dict) -> dict:
    """
    合并规则层和 LLM 层的风险判断。

    当前采用保守策略：
    1. 规则命中 high，则最终 high
    2. LLM 命中 high，则最终 high
    3. LLM 如果失败返回 unknown，则回退到规则结果
    4. 否则默认为 low

    这是医疗分诊场景里非常典型的“宁可保守”的设计。
    """
    red_flags = dedupe_flags(
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


def build_confirmed_facts(
    session: dict | None,
    symptoms: list[str],
    user_input: str,
) -> dict:
    """
    构建 working memory 里的 confirmed_facts。

    这个字段的目标不是保存原始对话，
    而是保存“系统已经确认的事实”。

    这里先做一个简单版本：
    - main_symptoms
    - max_temperature
    - dyspnea

    后面你可以继续扩：
    - duration
    - underlying_disease
    - pregnancy
    - drug_allergy
    """
    existing = (session or {}).get("confirmed_facts", {}).copy()

    # 只要本轮识别到了症状，就更新主症状
    if symptoms:
        existing["main_symptoms"] = symptoms

    # 这里先用非常简单的字符串规则做演示
    # 后续可以改成 LLM 或结构化抽取
    if "38.5" in user_input:
        existing["max_temperature"] = "38.5C"

    if "没有呼吸困难" in user_input or "无呼吸困难" in user_input:
        existing["dyspnea"] = False
    elif "呼吸困难" in user_input or "喘不上气" in user_input:
        existing["dyspnea"] = True

    return existing


def build_uncertain_facts(missing_fields: list[str]) -> list[str]:
    """
    把 LLM 识别出的 missing_fields 转成 uncertain_facts。

    目前先简单等价处理：
    missing_fields 里缺什么，就认为 uncertain_facts 里有什么。

    后面你可以把它做成标准 key，例如：
    “是否有基础疾病” -> “underlying_disease”
    """
    return list(dict.fromkeys(item for item in missing_fields if item))


def decide_stage(risk_level: str, need_more_info: bool) -> str:
    """
    根据当前风险等级和信息是否足够，决定 session 所处阶段。

    这就是 working memory 里 stage 的核心来源。
    """
    if risk_level == "high":
        return "high_risk_alerted"
    if need_more_info:
        return "collecting_info"
    return "ready_for_evaluation"


# -----------------------------
# 3. start 图
# -----------------------------
# start 图负责首轮问诊：
# 用户输入 -> LLM 抽取 -> 双层风控 -> 写 session -> 返回响应


def build_start_triage_graph(
    llm_service,
    risk_control_service,
    tool_service,
    session_store,
):
    """
    构建 /triage/start 对应的 LangGraph。

    传入的四个参数本质上是依赖注入：
    - llm_service: 调大模型
    - risk_control_service: 规则风控
    - tool_service: 工具调用
    - session_store: Redis 会话存储
    """

    def extract_info_node(state: StartTriageState) -> dict:
        """
        节点 1：从用户首轮描述中抽取关键信息。

        这里调用的是 LLMService.extract_triage_info，
        典型输出包括：
        - symptoms
        - missing_fields
        - retrieval_query
        - next_question
        - need_more_info
        """
        user_input = state["user_input"]
        llm_result = llm_service.extract_triage_info(user_input)

        return {
            "llm_result": llm_result,
            "symptoms": llm_result.get("symptoms", []),
        }

    def check_rule_risk_node(state: StartTriageState) -> dict:
        """
        节点 2：规则层风险检查。

        规则层适合做兜底，例如：
        - 胸痛
        - 呼吸困难
        - 昏迷
        - 咯血

        这种节点的优点是稳定、可解释、可控。
        """
        rule_risk = risk_control_service.check_risk(
            text=state["user_input"],
            symptoms=state.get("symptoms", []),
        )
        return {"rule_risk": rule_risk}

    def check_llm_risk_node(state: StartTriageState) -> dict:
        """
        节点 3：LLM 语义层风险检查。

        这里主要处理口语化表达，比如：
        - “喘不上气”
        - “胸口压得难受”
        - “人有点迷糊”

        它和规则层形成双保险。
        """
        llm_risk = tool_service.check_red_flags(
            user_input=state["user_input"],
            symptoms=state.get("symptoms", []),
        )
        return {"llm_risk": llm_risk}

    def merge_risk_node(state: StartTriageState) -> dict:
        """
        节点 4：合并两层风险结果。
        """
        risk_result = merge_risk(
            rule_risk=state.get("rule_risk", {}),
            llm_risk=state.get("llm_risk", {}),
        )
        return {"risk_result": risk_result}

    def save_session_node(state: StartTriageState) -> dict:
        """
        节点 5：把首轮结果写入 Redis session。

        这是结构化 working memory 真正落地的关键节点。
        我们在这里写入：
        - stage
        - confirmed_facts
        - uncertain_facts
        - risk_level
        - red_flags
        - retrieval_query
        - last_tool_status
        """
        llm_result = state.get("llm_result", {})
        symptoms = state.get("symptoms", [])
        risk_result = state.get("risk_result", {})

        missing_fields = llm_result.get("missing_fields", [])
        confirmed_facts = build_confirmed_facts(
            session=None,
            symptoms=symptoms,
            user_input=state["user_input"],
        )
        uncertain_facts = build_uncertain_facts(missing_fields)
        stage = decide_stage(
            risk_level=risk_result.get("risk_level", "low"),
            need_more_info=llm_result.get("need_more_info", True),
        )

        triage_data = {
            "stage": stage,
            "symptoms": symptoms,
            "confirmed_facts": confirmed_facts,
            "uncertain_facts": uncertain_facts,
            "missing_fields": missing_fields,
            "next_question": llm_result.get(
                "next_question",
                "请补充更多症状信息，例如持续时间、严重程度和伴随症状。",
            ),
            "risk_level": risk_result.get("risk_level", "low"),
            "red_flags": risk_result.get("red_flags", []),
            "summary": llm_result.get("summary", ""),
            "retrieval_query": llm_result.get("retrieval_query", " ".join(symptoms)),
            "last_tool_status": {
                "tool_name": "check_red_flags",
                "status": "success",
                "error": None,
            },
            "needs_human_review": risk_result.get("risk_level") == "high",
        }

        session_id = session_store.upsert_session(
            session_id=None,
            user_input=state["user_input"],
            data=triage_data,
        )

        return {
            "triage_data": triage_data,
            "session_id": session_id,
        }

    def build_response_node(state: StartTriageState) -> dict:
        """
        节点 6：组装 API 返回值。

        注意：
        graph 内部 state 很丰富，
        但接口不一定要把所有字段都暴露出去。
        """
        triage_data = state["triage_data"]

        return {
            "response": {
                "session_id": state["session_id"],
                "symptoms": triage_data["symptoms"],
                "missing_fields": triage_data["missing_fields"],
                "next_question": triage_data["next_question"],
                "risk_level": triage_data["risk_level"],
                "red_flags": triage_data["red_flags"],
                "stage": triage_data["stage"],
            }
        }

    graph = StateGraph(StartTriageState)

    graph.add_node("extract_info", extract_info_node)
    graph.add_node("check_rule_risk", check_rule_risk_node)
    graph.add_node("check_llm_risk", check_llm_risk_node)
    graph.add_node("merge_risk", merge_risk_node)
    graph.add_node("save_session", save_session_node)
    graph.add_node("build_response", build_response_node)

    graph.set_entry_point("extract_info")

    graph.add_edge("extract_info", "check_rule_risk")
    graph.add_edge("check_rule_risk", "check_llm_risk")
    graph.add_edge("check_llm_risk", "merge_risk")
    graph.add_edge("merge_risk", "save_session")
    graph.add_edge("save_session", "build_response")
    graph.add_edge("build_response", END)

    return graph.compile()


# -----------------------------
# 4. continue 图
# -----------------------------
# continue 图负责：
# 读取旧 session -> 处理本轮补充信息 -> 更新 working memory -> 返回结果


def build_continue_triage_graph(
    llm_service,
    risk_control_service,
    tool_service,
    session_store,
):
    def load_session_node(state: ContinueTriageState) -> dict:
        """
        节点 1：先根据 session_id 读取旧会话。

        如果读不到，直接报错。
        这和现在 service 里的判断逻辑一致，只是迁进图里了。
        """
        session = session_store.get_session(state["session_id"])
        if not session:
            raise ValueError("session_id 不存在")
        return {"session": session}

    def continue_extract_info_node(state: ContinueTriageState) -> dict:
        """
        节点 2：结合旧 session 和本轮用户补充，更新问诊状态。

        这里 LLM 会做的事包括：
        - 更新 summary
        - 更新 symptoms
        - 更新 missing_fields
        - 更新 retrieval_query
        - 判断 need_more_info
        """
        llm_result = llm_service.continue_triage_info(
            session=state["session"],
            user_input=state["user_input"],
        )
        symptoms = llm_result.get("symptoms", state["session"].get("symptoms", []))

        return {
            "llm_result": llm_result,
            "symptoms": symptoms,
        }

    def continue_check_rule_risk_node(state: ContinueTriageState) -> dict:
        """
        节点 3：继续问诊时再次跑规则风险检查。
        """
        rule_risk = risk_control_service.check_risk(
            text=state["user_input"],
            symptoms=state.get("symptoms", []),
        )
        return {"rule_risk": rule_risk}

    def continue_check_llm_risk_node(state: ContinueTriageState) -> dict:
        """
        节点 4：继续问诊时再次跑 LLM 风险检查。
        """
        llm_risk = tool_service.check_red_flags(
            user_input=state["user_input"],
            symptoms=state.get("symptoms", []),
        )
        return {"llm_risk": llm_risk}

    def continue_merge_risk_node(state: ContinueTriageState) -> dict:
        """
        节点 5：合并本轮风险判断。
        """
        risk_result = merge_risk(
            rule_risk=state.get("rule_risk", {}),
            llm_risk=state.get("llm_risk", {}),
        )
        return {"risk_result": risk_result}

    def update_session_node(state: ContinueTriageState) -> dict:
        """
        节点 6：把本轮更新写回 Redis session。

        这是 continue 链路里 working memory 的核心更新点。
        """
        session = state["session"]
        llm_result = state.get("llm_result", {})
        symptoms = state.get("symptoms", [])
        risk_result = state.get("risk_result", {})

        # 把旧的 red_flags 和本轮新命中的 red_flags 合并
        existing_red_flags = session.get("red_flags", [])
        red_flags = dedupe_flags(existing_red_flags + risk_result.get("red_flags", []))

        # 一旦历史上已经 high，则后续不允许降级
        risk_level = (
            "high"
            if session.get("risk_level") == "high"
            or risk_result.get("risk_level") == "high"
            else risk_result.get("risk_level", "low")
        )

        missing_fields = llm_result.get("missing_fields", [])
        confirmed_facts = build_confirmed_facts(
            session=session,
            symptoms=symptoms,
            user_input=state["user_input"],
        )
        uncertain_facts = build_uncertain_facts(missing_fields)
        need_more_info = llm_result.get("need_more_info", True)
        stage = decide_stage(risk_level=risk_level, need_more_info=need_more_info)

        update_data = {
            "stage": stage,
            "symptoms": symptoms,
            "confirmed_facts": confirmed_facts,
            "uncertain_facts": uncertain_facts,
            "missing_fields": missing_fields,
            "next_question": llm_result.get("next_question", ""),
            "risk_level": risk_level,
            "red_flags": red_flags,
            "summary": llm_result.get("updated_summary", session.get("summary", "")),
            "retrieval_query": llm_result.get(
                "retrieval_query",
                session.get("retrieval_query", " ".join(symptoms)),
            ),
            "last_tool_status": {
                "tool_name": "check_red_flags",
                "status": "success",
                "error": None,
            },
            "needs_human_review": risk_level == "high",
        }

        session_store.upsert_session(
            session_id=state["session_id"],
            user_input=state["user_input"],
            data=update_data,
        )

        return {"update_data": update_data}

    def continue_response_node(state: ContinueTriageState) -> dict:
        """
        节点 7：把 continue 接口需要的结果返回给 API。
        """
        update_data = state["update_data"]
        need_more_info = state["llm_result"].get("need_more_info", True)

        return {
            "response": {
                "session_id": state["session_id"],
                "updated_summary": update_data["summary"],
                "symptoms": update_data["symptoms"],
                "missing_fields": update_data["missing_fields"],
                "next_question": update_data["next_question"],
                "risk_level": update_data["risk_level"],
                "red_flags": update_data["red_flags"],
                "need_more_info": need_more_info,
                "stage": update_data["stage"],
                "confirmed_facts": update_data["confirmed_facts"],
                "uncertain_facts": update_data["uncertain_facts"],
            }
        }

    graph = StateGraph(ContinueTriageState)

    graph.add_node("load_session", load_session_node)
    graph.add_node("continue_extract_info", continue_extract_info_node)
    graph.add_node("continue_check_rule_risk", continue_check_rule_risk_node)
    graph.add_node("continue_check_llm_risk", continue_check_llm_risk_node)
    graph.add_node("continue_merge_risk", continue_merge_risk_node)
    graph.add_node("update_session", update_session_node)
    graph.add_node("continue_response", continue_response_node)

    graph.set_entry_point("load_session")

    graph.add_edge("load_session", "continue_extract_info")
    graph.add_edge("continue_extract_info", "continue_check_rule_risk")
    graph.add_edge("continue_check_rule_risk", "continue_check_llm_risk")
    graph.add_edge("continue_check_llm_risk", "continue_merge_risk")
    graph.add_edge("continue_merge_risk", "update_session")
    graph.add_edge("update_session", "continue_response")
    graph.add_edge("continue_response", END)

    return graph.compile()


# -----------------------------
# 5. evaluate 图
# -----------------------------
# evaluate 图负责：
# 读取 session -> 检索知识 -> 加载知识全文 -> 推荐科室 -> LLM 最终评估 -> 写回 completed


def build_evaluate_triage_graph(
    llm_service,
    tool_service,
    session_store,
):
    def load_session_node(state: EvaluateTriageState) -> dict:
        """
        节点 1：先读 session。
        """
        session = session_store.get_session(state["session_id"])
        if not session:
            raise ValueError("session_id 不存在")
        return {"session": session}

    def prepare_query_node(state: EvaluateTriageState) -> dict:
        """
        节点 2：准备 RAG 检索 query。

        优先级：
        1. retrieval_query
        2. 症状拼接
        3. summary
        """
        session = state["session"]
        symptoms = session.get("symptoms", [])

        query = (
            session.get("retrieval_query")
            or " ".join(symptoms)
            or session.get("summary", "")
        )

        return {"query": query}

    def search_knowledge_node(state: EvaluateTriageState) -> dict:
        """
        节点 3：向量检索知识库。
        """
        knowledge_result = tool_service.search_knowledge(
            query=state["query"],
            top_k=3,
        )
        return {
            "knowledge_result": knowledge_result,
            "references": knowledge_result.get("references", []),
        }

    def load_knowledge_node(state: EvaluateTriageState) -> dict:
        """
        节点 4：根据 references 读取完整知识文档。

        这里的目的是给最终 LLM 更多完整上下文，
        不只依赖 chunk 摘要。
        """
        full_knowledge = tool_service.load_knowledge_by_references(
            references=state.get("references", []),
        )
        return {"full_knowledge": full_knowledge}

    def book_appointment_node(state: EvaluateTriageState) -> dict:
        """
        节点 5：根据症状和风险给出推荐科室/挂号结果。

        当前还是模拟能力，但保留了执行型工具入口。
        """
        session = state["session"]
        appointment_result = tool_service.book_appointment(
            symptoms=session.get("symptoms", []),
            risk_level=session.get("risk_level", "low"),
        )
        return {"appointment_result": appointment_result}

    def assemble_evaluation_context_node(state: EvaluateTriageState) -> dict:
        """
        节点 6：把最终评估需要的上下文拼起来给 LLM。

        包括：
        - 原 session
        - knowledge
        - knowledge_chunks
        - references
        - appointment
        """
        session_for_evaluation = {
            **state["session"],
            "knowledge": state.get("full_knowledge", []),
            "knowledge_chunks": state.get("knowledge_result", {}).get("results", []),
            "references": state.get("references", []),
            "appointment": state.get("appointment_result", {}),
        }
        return {"session_for_evaluation": session_for_evaluation}

    def evaluate_with_llm_node(state: EvaluateTriageState) -> dict:
        """
        节点 7：调用 LLM 生成最终分诊建议。
        """
        llm_result = llm_service.evaluate_triage(state["session_for_evaluation"])
        return {"llm_result": llm_result}

    def save_evaluation_node(state: EvaluateTriageState) -> dict:
        """
        节点 8：把最终结果写回 session。

        这里把 session 的阶段更新为 completed，
        表示这次问诊流程已经结束。
        """
        session_store.update_session(
            state["session_id"],
            {
                "stage": "completed",
                "references": state.get("references", []),
                "department": state.get("appointment_result", {}).get("department", ""),
                "final_advice": state.get("llm_result", {}).get("advice", ""),
                "last_tool_status": {
                    "tool_name": "search_knowledge",
                    "status": "success",
                    "error": None,
                },
            },
        )
        return {}

    def evaluate_response_node(state: EvaluateTriageState) -> dict:
        """
        节点 9：组装 evaluate 接口返回值。
        """
        session = state["session"]
        llm_result = state.get("llm_result", {})
        appointment_result = state.get("appointment_result", {})
        knowledge_result = state.get("knowledge_result", {})

        return {
            "response": {
                "summary": llm_result.get("summary", session.get("summary", "")),
                "risk_level": session.get("risk_level", "low"),
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
        }

    graph = StateGraph(EvaluateTriageState)

    graph.add_node("load_session", load_session_node)
    graph.add_node("prepare_query", prepare_query_node)
    graph.add_node("search_knowledge", search_knowledge_node)
    graph.add_node("load_knowledge", load_knowledge_node)
    graph.add_node("book_appointment", book_appointment_node)
    graph.add_node("assemble_evaluation_context", assemble_evaluation_context_node)
    graph.add_node("evaluate_with_llm", evaluate_with_llm_node)
    graph.add_node("save_evaluation", save_evaluation_node)
    graph.add_node("evaluate_response", evaluate_response_node)

    graph.set_entry_point("load_session")

    graph.add_edge("load_session", "prepare_query")
    graph.add_edge("prepare_query", "search_knowledge")
    graph.add_edge("search_knowledge", "load_knowledge")
    graph.add_edge("load_knowledge", "book_appointment")
    graph.add_edge("book_appointment", "assemble_evaluation_context")
    graph.add_edge("assemble_evaluation_context", "evaluate_with_llm")
    graph.add_edge("evaluate_with_llm", "save_evaluation")
    graph.add_edge("save_evaluation", "evaluate_response")
    graph.add_edge("evaluate_response", END)

    return graph.compile()