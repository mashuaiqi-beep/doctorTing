"""问诊相关 HTTP 接口。"""

from fastapi import APIRouter, HTTPException

from app.schema.triage_schema import (
    TriageContinueRequest,
    TriageContinueResponse,
    TriageEvaluateRequest,
    TriageEvaluateResponse,
    TriageStartRequest,
    TriageStartResponse,
)
from app.service.triage_service import TriageService

router = APIRouter(prefix="/triage", tags=["triage"])

triage_service = TriageService()


@router.post("/start", response_model=TriageStartResponse)
def start_triage(payload: TriageStartRequest) -> TriageStartResponse:
    """开始一轮问诊。"""

    result = triage_service.start_triage(payload.user_input)
    return TriageStartResponse(**result)


@router.post("/continue", response_model=TriageContinueResponse)
def continue_triage(payload: TriageContinueRequest) -> TriageContinueResponse:
    """继续已有问诊会话。"""

    try:
        result = triage_service.continue_triage(
            session_id=payload.session_id,
            user_input=payload.user_input,
        )
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return TriageContinueResponse(**result)


@router.post("/evaluate", response_model=TriageEvaluateResponse)
def evaluate_triage(payload: TriageEvaluateRequest) -> TriageEvaluateResponse:
    """生成最终分诊建议。"""
    try:
        result = triage_service.evaluate_triage(payload.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    return TriageEvaluateResponse(**result)
