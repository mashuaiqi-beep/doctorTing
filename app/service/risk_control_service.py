"""基于规则的风险控制服务。"""

from app.core.risk_rules import RED_FLAG_KEYWORDS


class RiskControlService:
    """使用确定性规则识别明显红旗症状。"""

    def check_risk(self, text: str, symptoms: list[str]) -> dict:
        """检查用户原文和已抽取症状中是否包含红旗关键词。"""

        matched_flags = []

        for flag in RED_FLAG_KEYWORDS:
            if flag in text:
                matched_flags.append(flag)

        for symptom in symptoms:
            if symptom in RED_FLAG_KEYWORDS and symptom not in matched_flags:
                matched_flags.append(symptom)

        return {
            "risk_level": "high" if matched_flags else "low",
            "red_flags": matched_flags,
        }
