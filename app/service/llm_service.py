import logging

from openai import OpenAI

from app.core.config import settings
from app.core.prompt_manager import (
    build_red_flag_detection_prompt,
    build_triage_continue_prompt,
    build_triage_evaluate_prompt,
    build_triage_start_prompt,
)
from app.utils.json_util import parse_json_object

logger = logging.getLogger(__name__)


class LLMService:
    """大模型服务层，封装 OpenAI 兼容聊天补全接口。"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model = settings.OPENAI_MODEL

    def extract_triage_info(self, user_input: str) -> dict:
        """提取首轮问诊信息。"""

        prompt = build_triage_start_prompt(user_input)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": "你是一个严谨的医疗问诊助手，只返回 JSON。"},
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            return parse_json_object(content)

        except Exception as exc:
            logger.exception("首轮问诊 LLM 调用失败：%s", repr(exc))
            return {
                "symptoms": [],
                "missing_fields": ["体温", "症状持续时间", "是否呼吸困难"],
                "next_question": "请问最高体温是多少？症状持续了多久？有没有呼吸困难？",
            }

    def continue_triage_info(self, session: dict, user_input: str) -> dict:
        """根据会话历史和用户补充回答更新问诊信息。"""

        prompt = build_triage_continue_prompt(session, user_input)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": "你是一个严谨的医疗问诊助手，只返回 JSON。"},
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            return parse_json_object(content)

        except Exception as exc:
            logger.exception("继续问诊 LLM 调用失败：%s", repr(exc))
            return {
                "updated_summary": session.get("summary", ""),
                "symptoms": session.get("symptoms", []),
                "missing_fields": session.get("missing_fields", []),
                "next_question": "请继续补充症状持续时间、严重程度和伴随症状。",
                "need_more_info": True,
            }

    def evaluate_triage(self, session: dict) -> dict:
        """根据完整会话生成最终分诊建议。"""

        prompt = build_triage_evaluate_prompt(session)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": "你是一个严谨的医疗分诊助手，只返回 JSON。"},
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            return parse_json_object(content)

        except Exception as exc:
            logger.exception("最终分诊 LLM 调用失败：%s", repr(exc))
            return {
                "summary": session.get("summary", ""),
                "department": "全科医学科",
                "advice": "建议结合症状变化线下就诊；如出现明显加重或高风险症状，请及时急诊。",
                "references": [],
            }

    def detect_red_flags(self, user_input: str, symptoms: list[str]) -> dict:
        """使用 LLM 判断语义层面的红旗症状。"""

        prompt = build_red_flag_detection_prompt(user_input, symptoms)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                messages=[
                    {"role": "system", "content": "你是一个医疗分诊安全检查助手，只返回 JSON。"},
                    {"role": "user", "content": prompt},
                ],
            )

            content = response.choices[0].message.content
            return parse_json_object(content)

        except Exception as exc:
            logger.exception("红旗症状 LLM 判断失败：%s", repr(exc))
            return {
                "has_red_flags": False,
                "red_flags": [],
                "risk_level": "unknown",
                "reason": "LLM 判断失败，已回退到规则判断。",
            }
