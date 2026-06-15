"""问诊接口使用的 Pydantic 数据模型。"""

from pydantic import BaseModel, Field


class TriageStartRequest(BaseModel):
    """开始问诊时的请求体。"""

    user_input: str = Field(..., description="用户首轮输入的症状描述")


class TriageStartResponse(BaseModel):
    """开始问诊后的响应体。"""

    session_id: str = Field(..., description="问诊会话 ID")
    symptoms: list[str] = Field(default_factory=list, description="已识别的症状")
    missing_fields: list[str] = Field(
        default_factory=list,
        description="当前缺失的重要信息",
    )
    next_question: str = Field(..., description="系统下一步要追问的问题")
    risk_level: str = Field(..., description="风险等级")
    red_flags: list[str] = Field(default_factory=list, description="命中的红旗症状")


class TriageContinueRequest(BaseModel):
    """继续问诊时的请求体。"""

    session_id: str = Field(..., description="问诊会话 ID")
    user_input: str = Field(..., description="用户补充回答")


class TriageContinueResponse(BaseModel):
    session_id: str = Field(..., description="问诊会话 ID")
    updated_summary: str = Field(..., description="更新后的病情摘要")
    symptoms: list[str] = Field(default_factory=list, description="当前已识别的症状")
    missing_fields: list[str] = Field(
        default_factory=list,
        description="当前仍缺失的重要信息",
    )
    next_question: str = Field(..., description="下一轮追问内容")
    risk_level: str = Field(..., description="当前风险等级")
    red_flags: list[str] = Field(default_factory=list, description="当前命中的红旗症状")
    need_more_info: bool = Field(..., description="是否还需要继续追问")
    stage: str = Field(..., description="当前问诊阶段")
    confirmed_facts: dict = Field(default_factory=dict, description="已确认事实")
    uncertain_facts: list[str] = Field(default_factory=list, description="待确认事实")

class TriageEvaluateRequest(BaseModel):
    """生成最终分诊结果时的请求体。"""

    session_id: str = Field(..., description="问诊会话 ID")


class TriageEvaluateResponse(BaseModel):
    """最终分诊结果响应体。"""

    summary: str = Field(..., description="病情摘要")
    risk_level: str = Field(..., description="风险等级")
    red_flags: list[str] = Field(default_factory=list, description="命中的红旗症状")
    department: str = Field(..., description="建议就诊科室")
    advice: str = Field(..., description="分诊建议")
    references: list[str] = Field(default_factory=list, description="知识来源")
