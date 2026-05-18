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


def dedupe_flags(flags: list[str]) -> list[str]:
    """红旗症状去重。

    这不是 LangGraph 的功能，只是当前业务里用到的一个普通工具函数。
    放在 graph 文件里，是因为 start 流程的风险合并节点会用到它。
    """

    return list(dict.fromkeys(flag for flag in flags if flag))


def merge_risk(rule_risk: dict, llm_risk: dict) -> dict:
    """合并规则风险和 LLM 风险。

    医疗分诊场景里宁可保守一点：
    - 规则命中 high，则最终 high。
    - LLM 判断 high，则最终 high。
    - LLM 调用失败或返回 unknown，则回退到规则判断。
    - 都没有高风险，则 low。
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


def build_start_triage_graph(
    llm_service,
    risk_control_service,
    tool_service,
    session_store,
):
    """构建 `/triage/start` 对应的 LangGraph。

    这里采用“工厂函数”的写法，而不是直接在模块全局创建 graph。

    原因是：
    - graph 节点需要调用 `llm_service`、`tool_service` 等项目内服务。
    - 这些服务是在 `TriageService.__init__` 里创建的。
    - 所以这里把依赖作为参数传进来，再在内部 node 里使用。

    调用关系是：
    `TriageService.__init__`
        -> `build_start_triage_graph(...)`
        -> 返回一个编译后的 graph

    执行关系是：
    `TriageService.start_triage`
        -> `self.start_graph.invoke({"user_input": user_input})`
        -> LangGraph 按下面定义的边依次执行节点
    """

    def extract_info_node(state: StartTriageState) -> dict:
        """节点 1：调用 LLM，抽取首轮问诊信息。

        LangGraph 节点本质上就是一个普通 Python 函数：
        - 入参是当前 State。
        - 返回值是要更新进 State 的字段。

        注意这里返回的是“局部更新”：
        只返回 `llm_result` 和 `symptoms`，LangGraph 会把它们合并回完整 State。
        """

        user_input = state["user_input"]
        llm_result = llm_service.extract_triage_info(user_input)

        return {
            "llm_result": llm_result,
            "symptoms": llm_result.get("symptoms", []),
        }

    def check_rule_risk_node(state: StartTriageState) -> dict:
        """节点 2：用确定性规则判断红旗症状。

        这个节点调用的是 `RiskControlService.check_risk`。

        它不依赖 LLM，所以它适合承担医疗安全里的兜底判断：
        只要用户原文或症状列表里出现明确红旗关键词，就提升风险等级。
        """

        rule_risk = risk_control_service.check_risk(
            text=state["user_input"],
            symptoms=state.get("symptoms", []),
        )

        return {
            "rule_risk": rule_risk,
        }

    def check_llm_risk_node(state: StartTriageState) -> dict:
        """节点 3：用 ToolService 做 LLM 语义层风险判断。

        这个节点调用的是 `ToolService.check_red_flags`。

        在这个项目里，ToolService 内部使用 OpenAI compatible function calling。
        也就是说：
        - graph 负责决定什么时候调用工具。
        - ToolService 负责具体怎么调用工具。

        这也是 LangGraph 很适合 Agent 项目的原因：
        它可以把“是否调用工具、何时调用工具、工具结果流向哪里”显式写在图里。
        """

        llm_risk = tool_service.check_red_flags(
            user_input=state["user_input"],
            symptoms=state.get("symptoms", []),
        )

        return {
            "llm_risk": llm_risk,
        }

    def merge_risk_node(state: StartTriageState) -> dict:
        """节点 4：合并两层风险判断。

        这个节点没有调用外部服务，只处理 State 中已有的数据。

        这类节点在 LangGraph 里很常见：
        它们像流程中的“整理台”，把上游多个节点的结果合并成下游更容易使用的结构。
        """

        risk_result = merge_risk(
            rule_risk=state.get("rule_risk", {}),
            llm_risk=state.get("llm_risk", {}),
        )

        return {
            "risk_result": risk_result,
        }

    def save_session_node(state: StartTriageState) -> dict:
        """节点 5：把首轮问诊结果写入 session。

        这个节点调用的是 `session_store.upsert_session`。

        为什么保存 session 也是一个 graph 节点？
        因为在 Agent 流程里，持久化本身也是流程的一部分。
        后续 `continue` 和 `evaluate` 都要依赖这一步留下的状态。
        """

        llm_result = state.get("llm_result", {})
        symptoms = state.get("symptoms", [])
        risk_result = state.get("risk_result", {})

        triage_data = {
            "symptoms": symptoms,
            "missing_fields": llm_result.get("missing_fields", []),
            "next_question": llm_result.get(
                "next_question",
                "请补充更多症状信息，例如持续时间、严重程度和伴随症状。",
            ),
            "risk_level": risk_result.get("risk_level", "low"),
            "red_flags": risk_result.get("red_flags", []),
            "retrieval_query": llm_result.get("retrieval_query", "。".join(symptoms)),
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
        """节点 6：组装 API 需要返回的 response。

        LangGraph 最终返回的是完整 State，不会自动帮我们变成 FastAPI 的响应体。

        所以这里专门放一个节点，把内部流程字段整理成接口响应字段。
        `TriageService.start_triage` 最后只需要 `return final_state["response"]`。
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
            }
        }

    # LangGraph API 1：StateGraph(...)
    #
    # `StateGraph(StartTriageState)` 创建一张“带状态类型的流程图”。
    # 这一步只是声明图的结构，还没有真正运行。
    #
    # 你可以把它理解成：
    # “我要开始画一张图了，这张图里流动的数据类型叫 StartTriageState。”
    graph = StateGraph(StartTriageState)

    # LangGraph API 2：add_node(name, function)
    #
    # `add_node` 把一个普通 Python 函数注册成图里的节点。
    # name 是节点名，后面连边时会用到。
    # function 是节点实际执行的逻辑。
    graph.add_node("extract_info", extract_info_node)
    graph.add_node("check_rule_risk", check_rule_risk_node)
    graph.add_node("check_llm_risk", check_llm_risk_node)
    graph.add_node("merge_risk", merge_risk_node)
    graph.add_node("save_session", save_session_node)
    graph.add_node("build_response", build_response_node)

    # LangGraph API 3：set_entry_point(name)
    #
    # 设置图从哪个节点开始执行。
    # 对 `/triage/start` 来说，第一步一定是从用户输入里抽取问诊信息。
    graph.set_entry_point("extract_info")

    # LangGraph API 4：add_edge(from_node, to_node)
    #
    # `add_edge` 表示节点之间的执行顺序。
    # 当前 start 流程是线性的，所以每一步都连到下一步。
    #
    # 后面如果要做条件分支，比如：
    # - high risk -> emergency_advice
    # - low risk -> ask_follow_up
    # 就会用 LangGraph 的 `add_conditional_edges`。
    graph.add_edge("extract_info", "check_rule_risk")
    graph.add_edge("check_rule_risk", "check_llm_risk")
    graph.add_edge("check_llm_risk", "merge_risk")
    graph.add_edge("merge_risk", "save_session")
    graph.add_edge("save_session", "build_response")

    # LangGraph API 5：END
    #
    # `END` 是 LangGraph 提供的特殊结束节点。
    # 把最后一个业务节点连到 END，表示流程到这里结束。
    graph.add_edge("build_response", END)

    # LangGraph API 6：compile()
    #
    # `compile()` 会把上面声明的图结构编译成一个可执行对象。
    #
    # 编译之后，业务层可以调用：
    # `self.start_graph.invoke({"user_input": user_input})`
    #
    # `invoke` 不是在这里调用，而是在 `TriageService.start_triage` 里调用。
    # 它的作用是：给图一个初始 State，然后让 LangGraph 按边依次运行所有节点。
    return graph.compile()
