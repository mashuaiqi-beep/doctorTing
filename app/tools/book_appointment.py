"""模拟挂号工具。

当前只做科室推荐，不对接真实医院系统。
后续可以把这里替换成真实 HIS/挂号系统 API。
"""


DEPARTMENT_RULES = [
    (["胸痛", "胸闷"], "心内科"),
    (["呼吸困难", "咳嗽", "气促"], "呼吸内科"),
    (["发热", "高热"], "发热门诊"),
    (["腹痛", "腹泻", "呕吐"], "消化内科"),
    (["头痛", "头晕"], "神经内科"),
    (["意识模糊", "抽搐", "昏迷"], "急诊科"),
]


def book_appointment(symptoms: list[str], risk_level: str) -> dict:
    """根据症状和风险等级推荐科室，返回模拟挂号结果。"""

    if risk_level == "high":
        return {
            "department": "急诊科",
            "appointment_type": "急诊",
            "message": "检测到高风险信号，建议立即前往急诊科，必要时拨打 120。",
            "success": True,
        }

    department = _match_department(symptoms)

    return {
        "department": department,
        "appointment_type": "普通门诊",
        "message": f"已为您推荐挂号科室：{department}（普通门诊）。",
        "success": True,
    }


def _match_department(symptoms: list[str]) -> str:
    for symptom in symptoms:
        for keywords, department in DEPARTMENT_RULES:
            if any(keyword in symptom for keyword in keywords):
                return department

    return "全科医学科"
