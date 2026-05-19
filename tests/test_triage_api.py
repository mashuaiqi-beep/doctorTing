from fastapi.testclient import TestClient

import app.api.triage_api as triage_api
from app.main import app
from app.service.triage_service import TriageService


class FakeLLMService:
    def extract_triage_info(self, user_input: str) -> dict:
        return {
            "symptoms": ["发热", "咳嗽"],
            "missing_fields": ["最高体温", "是否呼吸困难"],
            "next_question": "请问最高体温是多少？有没有呼吸困难？",
        }

    def continue_triage_info(self, session: dict, user_input: str) -> dict:
        return {
            "updated_summary": "发热 2 天，最高 38.5 度，伴咳嗽，否认呼吸困难。",
            "symptoms": ["发热", "咳嗽"],
            "missing_fields": ["是否有基础疾病"],
            "next_question": "请问是否有基础疾病？",
            "need_more_info": True,
        }

    def evaluate_triage(self, session: dict) -> dict:
        return {
            "summary": session.get("summary", "发热伴咳嗽。"),
            "department": "呼吸内科",
            "advice": "建议线下就诊；如症状加重请及时急诊。",
            "references": [],
        }

    def detect_red_flags(self, user_input: str, symptoms: list[str]) -> dict:
        if "喘不上气" in user_input:
            return {
                "has_red_flags": True,
                "red_flags": ["呼吸困难"],
                "risk_level": "high",
                "reason": "用户描述喘不上气。",
            }

        return {
            "has_red_flags": False,
            "red_flags": [],
            "risk_level": "low",
            "reason": "未发现明确红旗症状。",
        }


def build_test_service() -> TriageService:
    service = TriageService()
    service.llm_service = FakeLLMService()
    return service


def test_full_triage_flow(monkeypatch):
    service = build_test_service()
    monkeypatch.setattr(triage_api, "triage_service", service)
    client = TestClient(app)

    start_response = client.post(
        "/triage/start",
        json={"user_input": "我发热两天了，还一直咳嗽"},
    )
    assert start_response.status_code == 200
    start_payload = start_response.json()
    assert start_payload["symptoms"] == ["发热", "咳嗽"]
    assert start_payload["risk_level"] == "low"
    assert start_payload["red_flags"] == []
    assert start_payload["session_id"]

    continue_response = client.post(
        "/triage/continue",
        json={
            "session_id": start_payload["session_id"],
            "user_input": "最高 38.5 度，没有呼吸困难",
        },
    )
    assert continue_response.status_code == 200
    continue_payload = continue_response.json()
    assert continue_payload["session_id"] == start_payload["session_id"]
    assert continue_payload["need_more_info"] is True
    assert "38.5" in continue_payload["updated_summary"]
    assert continue_payload["symptoms"] == ["发热", "咳嗽"]
    assert continue_payload["missing_fields"] == ["是否有基础疾病"]
    assert continue_payload["risk_level"] == "low"
    assert continue_payload["red_flags"] == []

    evaluate_response = client.post(
        "/triage/evaluate",
        json={"session_id": start_payload["session_id"]},
    )
    assert evaluate_response.status_code == 200
    evaluate_payload = evaluate_response.json()
    assert evaluate_payload["risk_level"] == "low"
    assert evaluate_payload["department"] == "呼吸内科"
    assert evaluate_payload["references"] == []


def test_start_triage_elevates_red_flag_risk(monkeypatch):
    service = build_test_service()
    monkeypatch.setattr(triage_api, "triage_service", service)
    client = TestClient(app)

    response = client.post(
        "/triage/start",
        json={"user_input": "我胸痛，而且有点喘不上气"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["risk_level"] == "high"
    assert "胸痛" in payload["red_flags"]
    assert "呼吸困难" in payload["red_flags"]


def test_continue_and_evaluate_return_404_for_unknown_session(monkeypatch):
    service = build_test_service()
    monkeypatch.setattr(triage_api, "triage_service", service)
    client = TestClient(app)

    continue_response = client.post(
        "/triage/continue",
        json={"session_id": "missing", "user_input": "补充信息"},
    )
    assert continue_response.status_code == 404

    evaluate_response = client.post(
        "/triage/evaluate",
        json={"session_id": "missing"},
    )
    assert evaluate_response.status_code == 404
