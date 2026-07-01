import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from agents.orchestrator import InvestigationOrchestrator
from agents.state import InvestigationState
from backend.config import settings
from database.db import AICopDatabase

logger = logging.getLogger("aicop.api")
router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = AICopDatabase()
    app.state.orchestrator = InvestigationOrchestrator()
    app.state.logger = logger
    app.state.db._initialize()
    logger.info("application_started", extra={"event": "application_started"})
    yield
    logger.info("application_shutdown", extra={"event": "application_shutdown"})


def create_app() -> FastAPI:
    app = FastAPI(title="AICop API", version=settings.app_version, lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()


class RootResponse(BaseModel):
    message: str


class HealthResponse(BaseModel):
    status: str


class InvestigationRequest(BaseModel):
    prompt: str = Field(..., min_length=3)
    response: str = Field(..., min_length=3)
    conversation_history: str = Field(default="")


class InvestigationResponse(BaseModel):
    case_id: str
    overall_score: float
    overall_risk: str
    recommendations: list[str]
    report: str


class CaseRecordResponse(BaseModel):
    case_id: str
    timestamp: str
    prompt: str
    response: str
    security_score: float | None = None
    reliability_score: float | None = None
    overall_score: float | None = None
    overall_risk: str | None = None
    recommendations: str | None = None
    report: str | None = None


class CaseReportResponse(BaseModel):
    case_id: str
    report: str


def persist_investigation_result(db: AICopDatabase, state: InvestigationState) -> None:
    db.save_case(
        {
            "case_id": state.case_id,
            "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "prompt": state.prompt,
            "response": state.response,
            "security_score": state.security_result.get("score"),
            "reliability_score": state.reliability_result.get("score"),
            "overall_score": state.overall_score,
            "overall_risk": state.overall_risk,
            "recommendations": state.recommendations,
            "report": state.report,
        }
    )


@router.get("/", response_model=RootResponse, tags=["health"], summary="Root endpoint", description="Returns basic API information.")
def read_root() -> RootResponse:
    return RootResponse(message="AICop AI Investigation Platform")


@router.get("/health", response_model=HealthResponse, tags=["health"], summary="Health check", description="Returns the service health status.")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


def _run_investigation(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    if not hasattr(request.app.state, "db"):
        request.app.state.db = AICopDatabase()
        request.app.state.orchestrator = InvestigationOrchestrator()
        request.app.state.logger = logger
        request.app.state.db._initialize()

    db: AICopDatabase = request.app.state.db
    orchestrator: InvestigationOrchestrator = request.app.state.orchestrator
    app_logger = request.app.state.logger

    app_logger.info(
        "investigation_started",
        extra={
            "event": "investigation_started",
            "prompt_length": len(payload.prompt),
            "response_length": len(payload.response),
            "conversation_history_length": len(payload.conversation_history),
        },
    )

    state = InvestigationState(
        prompt=payload.prompt,
        response=payload.response,
        conversation_history=payload.conversation_history,
    )

    try:
        state = orchestrator.run(state)
        persist_investigation_result(db, state)
    except ValueError as exc:
        app_logger.warning(
            "investigation_validation_error",
            extra={"event": "investigation_validation_error", "error": str(exc)},
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except sqlite3.Error as exc:
        app_logger.exception(
            "investigation_db_error",
            extra={"event": "investigation_db_error"},
        )
        raise HTTPException(status_code=500, detail="Unable to save investigation result") from exc
    except Exception as exc:  # pragma: no cover - defensive fallback
        app_logger.exception(
            "investigation_failed",
            extra={"event": "investigation_failed", "error": str(exc)},
        )
        raise HTTPException(status_code=500, detail="Investigation failed") from exc

    app_logger.info(
        "investigation_completed",
        extra={
            "event": "investigation_completed",
            "case_id": state.case_id,
            "overall_score": state.overall_score,
            "overall_risk": state.overall_risk,
        },
    )

    return InvestigationResponse(
        case_id=state.case_id,
        overall_score=state.overall_score,
        overall_risk=state.overall_risk,
        recommendations=state.recommendations,
        report=state.report,
    )


@router.post(
    "/investigate",
    response_model=InvestigationResponse,
    tags=["investigation"],
    summary="Run an investigation",
    description="Runs the investigation workflow for a prompt and model response.",
)
def investigate(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    return _run_investigation(payload, request)


@router.post(
    "/cases",
    response_model=InvestigationResponse,
    tags=["investigation"],
    summary="Create a case",
    description="Creates a new investigation case and returns the result.",
)
def create_case(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    return _run_investigation(payload, request)


@router.get("/cases", response_model=list[CaseRecordResponse], tags=["investigation"], summary="List cases", description="Returns the stored investigation cases.")
def cases(request: Request) -> list[CaseRecordResponse]:
    db: AICopDatabase = request.app.state.db
    return [CaseRecordResponse(**record) for record in db.list_cases()]


@router.get("/cases/{case_id}", response_model=CaseRecordResponse, tags=["investigation"], summary="Get a case", description="Returns the stored investigation case details.")
def get_case(case_id: str, request: Request) -> CaseRecordResponse:
    db: AICopDatabase = request.app.state.db
    record = db.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseRecordResponse(**record)


@router.get("/cases/{case_id}/report", response_model=CaseReportResponse, tags=["investigation"], summary="Get a case report", description="Returns the report for a stored investigation case.")
def get_report(case_id: str, request: Request) -> CaseReportResponse:
    db: AICopDatabase = request.app.state.db
    record = db.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    return CaseReportResponse(case_id=case_id, report=record.get("report", ""))


@router.get("/report/{case_id}", response_model=CaseReportResponse, tags=["investigation"], summary="Get a case report (legacy)", description="Backward-compatible alias for /cases/{id}/report.")
def get_report_legacy(case_id: str, request: Request) -> CaseReportResponse:
    return get_report(case_id, request)
