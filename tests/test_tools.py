from app.tools.book_appointment import book_appointment
from app.tools.search_knowledge import search_medical_knowledge


def test_book_appointment_high_risk_goes_to_emergency():
    result = book_appointment(["胸痛", "呼吸困难"], "high")

    assert result["department"] == "急诊科"
    assert result["appointment_type"] == "急诊"
    assert result["success"] is True


def test_book_appointment_low_risk_cough_goes_to_respiratory():
    result = book_appointment(["咳嗽"], "low")

    assert result["department"] == "呼吸内科"
    assert result["appointment_type"] == "普通门诊"


def test_search_knowledge_returns_references_for_chest_pain():
    result = search_medical_knowledge("我胸痛，而且喘不上气", top_k=2)

    assert result["references"] == ["chest_pain.md"]
    assert len(result["results"]) == 2


def test_search_knowledge_returns_general_fallback():
    result = search_medical_knowledge("我有点不舒服", top_k=2)

    assert result["references"] == ["general_triage.md"]
    assert result["results"][0]["keyword"] == "general"
