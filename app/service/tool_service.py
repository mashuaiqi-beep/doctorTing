import json
import logging

from openai import OpenAI
from app.core.config import settings
from app.service.vector_knowledge_service import VectorKnowledgeService
from app.tools.book_appointment import book_appointment
from app.tools.search_knowledge import load_knowledge_by_references


logger = logging.getLogger(__name__)


class ToolService:
    """Tool Calling 服务层，负责所有 Function Call 模式的 LLM 调用。"""

    def __init__(self):
        self.client = OpenAI(
            api_key=settings.OPENAI_API_KEY,
            base_url=settings.OPENAI_BASE_URL,
        )
        self.model = settings.OPENAI_MODEL
        self.vector_knowledge_service = VectorKnowledgeService()

    def extract_symptoms(self, user_input: str) -> dict:
        """用 Function Call 方式从用户描述中提取症状列表。"""

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "extract_symptoms",
                    "description": "从用户描述中提取症状列表",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "symptoms": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "识别到的症状列表，例如：['发热', '咳嗽']",
                            }
                        },
                        "required": ["symptoms"],
                    },
                },
            }
        ]

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                tools=tools,
                tool_choice="required",
                messages=[
                    {"role": "system", "content": "你是一个医疗问诊助手，请从用户描述中提取症状。"},
                    {"role": "user", "content": user_input},
                ],
            )

            tool_call = response.choices[0].message.tool_calls[0]
            return json.loads(tool_call.function.arguments)

        except Exception as exc:
            logger.exception("extract_symptoms tool call 失败：%s", repr(exc))
            return {"symptoms": []}

    def check_red_flags(self, user_input: str, symptoms: list[str]) -> dict:
        """用 Function Call 方式判断是否存在红旗症状。"""

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "check_red_flags",
                    "description": "判断症状描述中是否存在需要紧急处理的红旗症状",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "has_red_flags": {
                                "type": "boolean",
                                "description": "是否存在红旗症状",
                            },
                            "red_flags": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "具体的红旗症状列表",
                            },
                            "risk_level": {
                                "type": "string",
                                "enum": ["low", "medium", "high"],
                                "description": "风险等级",
                            },
                            "reason": {
                                "type": "string",
                                "description": "判断理由，一句话说明",
                            },
                        },
                        "required": ["has_red_flags", "red_flags", "risk_level", "reason"],
                    },
                },
            }
        ]

        symptom_text = "、".join(symptoms) if symptoms else "无"

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                temperature=0,
                tools=tools,
                tool_choice="required",
                messages=[
                    {"role": "system", "content": "你是一个医疗安全评估助手，判断症状风险等级。"},
                    {"role": "user", "content": f"用户描述：{user_input}\n已识别症状：{symptom_text}"},
                ],
            )

            tool_call = response.choices[0].message.tool_calls[0]
            return json.loads(tool_call.function.arguments)

        except Exception as exc:
            logger.exception("check_red_flags tool call 失败：%s", repr(exc))
            return {
                "has_red_flags": False,
                "red_flags": [],
                "risk_level": "unknown",
                "reason": "LLM 判断失败，已回退到规则判断。",
            }

    def search_knowledge(self, query: str, top_k: int = 3) -> dict:
        """检索医疗知识。当前是本地 stub，后续可替换为 RAG。"""

        return self.vector_knowledge_service.search(query=query, top_k=top_k)

    def book_appointment(self, symptoms: list[str], risk_level: str) -> dict:
        """推荐科室并返回模拟挂号结果。"""

        return book_appointment(symptoms=symptoms, risk_level=risk_level)

    def load_knowledge_by_references(self, references: list[str]) -> list[dict]:
        """根据 references 读取完整知识文档。"""

        return load_knowledge_by_references(references)