from fastapi import APIRouter, Depends, HTTPException

from app.api.dependencies import get_services
from app.core.container import AppServices
from app.schemas import CopilotChatRequest, CopilotChatResponse


router = APIRouter(tags=["copilot"])


@router.post("/api/copilot/chat", response_model=CopilotChatResponse)
def copilot_chat(payload: CopilotChatRequest, services: AppServices = Depends(get_services)):
    try:
        return CopilotChatResponse(
            **services.copilot_service.chat(
                message=payload.message,
                summary=payload.summary,
                app_context=payload.app_context.model_dump(),
                session_parameters=payload.session_parameters.model_dump() if payload.session_parameters else None,
            )
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
