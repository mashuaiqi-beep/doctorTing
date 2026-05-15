"""问诊 Agent 的工作流。

这里未来会放 LangGraph 的主流程。

你可以把 LangGraph 理解成：
- 把一个复杂任务拆成多个节点
- 每个节点只处理一步
- 节点之间按顺序流转

对于这个项目，建议流程是：
1. collect_info
2. check_risk
3. retrieve_knowledge
4. generate_advice
"""

from typing import TypedDict


class TriageState(TypedDict, total=False):
    """工作流里流动的状态对象。

    LangGraph 通常会让你定义一个 state，
    每个节点从 state 里读取数据，再往里面写回结果。
    """

    user_input: str
    symptom_summary: str
    risk_level: str
    retrieved_docs: list[str]
    final_advice: str


def collect_info_node(state: TriageState) -> TriageState:
    """信息收集节点。

    现在先做一个最小示例：
    - 读取用户输入
    - 生成一个简单摘要
    """
    user_input = state.get("user_input", "")
    return {
        **state,
        "symptom_summary": f"已收到用户描述：{user_input}",
    }


def check_risk_node(state: TriageState) -> TriageState:
    """风险判断节点。

    后续可以在这里调用：
    - 红旗症状规则
    - 大模型风险分类
    """
    return {
        **state,
        "risk_level": "medium",
    }


def retrieve_knowledge_node(state: TriageState) -> TriageState:
    """知识检索节点。

    后续这里会接 RAG：
    - 把用户症状转成查询
    - 去向量库检索相关知识
    """
    return {
        **state,
        "retrieved_docs": ["发热处理建议", "呼吸道症状分诊说明"],
    }


def generate_advice_node(state: TriageState) -> TriageState:
    """生成建议节点。

    最终把前面的信息汇总，形成建议。
    """
    return {
        **state,
        "final_advice": "建议尽快线下就诊，如症状加重请及时急诊。",
    }
