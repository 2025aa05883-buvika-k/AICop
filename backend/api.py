import logging
import sqlite3
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

from agents.modules import DeploymentModuleOrchestrator, ReliabilityModuleOrchestrator, SecurityModuleOrchestrator
from agents.state import DeploymentState, ReliabilityState, SecurityState
from backend.config import settings
from database.db import AICopDatabase
from reports.pdf_generator import PDFReportGenerator

logger = logging.getLogger("aicop.api")
router = APIRouter()


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.db = AICopDatabase()
    app.state.orchestrators = {
        "security": SecurityModuleOrchestrator(),
        "reliability": ReliabilityModuleOrchestrator(),
        "deployment": DeploymentModuleOrchestrator(),
    }
    app.state.report_generator = PDFReportGenerator()
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
    response: str = Field(default="")
    conversation_history: str = Field(default="")


class InvestigationResponse(BaseModel):
    case_id: str
    status: str
    module: str
    report: str
    pdf_path: str | None = None
    summary: str | None = None
    recommendations: list[str] | None = None
    score: float | None = None
    risk: str | None = None
    verdict: str | None = None
    evidence: dict[str, object] | None = None
    agent_results: list[dict[str, object]] | None = None
    jury_result: dict[str, object] | None = None
    logs: list[str] | None = None
    started_time: str | None = None
    completed_time: str | None = None


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


def persist_investigation_result(db: AICopDatabase, state: object) -> None:
    payload: dict[str, object] = {
        "case_id": getattr(state, "case_id", ""),
        "timestamp": datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
        "prompt": getattr(state, "prompt", ""),
        "response": getattr(state, "response", ""),
        "security_score": None,
        "reliability_score": None,
        "overall_score": None,
        "overall_risk": None,
        "recommendations": [],
        "report": getattr(state, "report", ""),
    }
    if getattr(state, "module", "") == "security":
        payload["security_score"] = state.jury_result.get("security_score")
        payload["overall_score"] = state.jury_result.get("security_score")
        payload["overall_risk"] = state.jury_result.get("security_risk")
        payload["recommendations"] = state.jury_result.get("recommendations", [])
    elif getattr(state, "module", "") == "reliability":
        payload["reliability_score"] = state.jury_result.get("reliability_score")
        payload["overall_score"] = state.jury_result.get("reliability_score")
        payload["overall_risk"] = state.jury_result.get("risk")
        payload["recommendations"] = state.jury_result.get("recommendations", [])
    elif getattr(state, "module", "") == "deployment":
        payload["overall_score"] = state.jury_result.get("overall_score")
        payload["overall_risk"] = state.jury_result.get("deployment_risk")
        payload["recommendations"] = state.jury_result.get("recommendations", [])
    db.save_case(payload)


@router.get("/", response_model=RootResponse, tags=["health"], summary="Root endpoint", description="Returns basic API information.")
def read_root() -> RootResponse:
    return RootResponse(message="AICop AI Investigation Platform")


@router.get("/health", response_model=HealthResponse, tags=["health"], summary="Health check", description="Returns the service health status.")
def health() -> HealthResponse:
    return HealthResponse(status="ok")


def _run_investigation(payload: InvestigationRequest, request: Request, module: str) -> InvestigationResponse:
    if not hasattr(request.app.state, "db"):
        request.app.state.db = AICopDatabase()
        request.app.state.orchestrators = {
            "security": SecurityModuleOrchestrator(),
            "reliability": ReliabilityModuleOrchestrator(),
            "deployment": DeploymentModuleOrchestrator(),
        }
        request.app.state.report_generator = PDFReportGenerator()
        request.app.state.logger = logger
        request.app.state.db._initialize()

    db: AICopDatabase = request.app.state.db
    orchestrator = request.app.state.orchestrators[module]
    app_logger = request.app.state.logger

    app_logger.info(
        "investigation_started",
        extra={
            "event": "investigation_started",
            "module_name": module,
            "prompt_length": len(payload.prompt),
            "response_length": len(payload.response),
            "conversation_history_length": len(payload.conversation_history),
        },
    )

    if module == "security":
        state = SecurityState(prompt=payload.prompt, response=payload.response, conversation_history=payload.conversation_history)
    elif module == "reliability":
        state = ReliabilityState(prompt=payload.prompt, response=payload.response, conversation_history=payload.conversation_history)
    else:
        state = DeploymentState(prompt=payload.prompt, response=payload.response, conversation_history=payload.conversation_history)

    try:
        state = orchestrator.run(state)
        pdf_path = request.app.state.report_generator.generate(state.case_id, state.report)
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
        extra={"event": "investigation_completed", "module_name": module, "case_id": state.case_id},
    )

    if module == "security":
        summary = state.jury_result.get("summary")
        recommendations = state.jury_result.get("recommendations", [])
        score = state.jury_result.get("security_score")
        risk = state.jury_result.get("security_risk")
    elif module == "reliability":
        summary = state.jury_result.get("summary")
        recommendations = state.jury_result.get("recommendations", [])
        score = state.jury_result.get("reliability_score")
        risk = state.jury_result.get("risk")
    else:
        summary = state.jury_result.get("summary")
        recommendations = state.jury_result.get("recommendations", [])
        score = state.jury_result.get("overall_score")
        risk = state.jury_result.get("deployment_risk")
    verdict = state.jury_result.get("deployment_verdict")

    return InvestigationResponse(
        case_id=state.case_id,
        status=state.status,
        module=module,
        report=state.report,
        pdf_path=pdf_path,
        summary=summary,
        recommendations=recommendations,
        score=score,
        risk=risk,
        verdict=verdict,
        evidence=state.evidence,
        agent_results=state.agent_results,
        jury_result=state.jury_result,
        logs=state.logs,
        started_time=state.started_time,
        completed_time=state.completed_time,
    )


@router.post(
    "/investigate/security",
    response_model=InvestigationResponse,
    tags=["investigation"],
    summary="Run a security investigation",
    description="Runs the security investigation workflow for a prompt and optional context.",
)
def investigate_security(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    return _run_investigation(payload, request, "security")


@router.post(
    "/investigate/reliability",
    response_model=InvestigationResponse,
    tags=["investigation"],
    summary="Run a reliability investigation",
    description="Runs the reliability investigation workflow for prompt, response, and context.",
)
def investigate_reliability(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    return _run_investigation(payload, request, "reliability")


@router.post(
    "/investigate/deployment",
    response_model=InvestigationResponse,
    tags=["investigation"],
    summary="Run a deployment readiness assessment",
    description="Runs the deployment readiness assessment for a prompt and response.",
)
def investigate_deployment(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    return _run_investigation(payload, request, "deployment")


@router.post(
    "/investigate",
    response_model=InvestigationResponse,
    tags=["investigation"],
    summary="Run a generic investigation (legacy)",
    description="Backward-compatible alias for the security workflow.",
)
def investigate(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    return _run_investigation(payload, request, "security")


@router.post(
    "/cases",
    response_model=InvestigationResponse,
    tags=["investigation"],
    summary="Create a case",
    description="Creates a new investigation case and returns the result.",
)
def create_case(payload: InvestigationRequest, request: Request) -> InvestigationResponse:
    return _run_investigation(payload, request, "security")


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


@router.get("/report/{case_id}/pdf", tags=["investigation"], summary="Download a PDF report", description="Returns a generated PDF report for a stored case.")
def download_report_pdf(case_id: str, request: Request) -> FileResponse:
    db: AICopDatabase = request.app.state.db
    record = db.get_case(case_id)
    if not record:
        raise HTTPException(status_code=404, detail="Case not found")
    generator = getattr(request.app.state, "report_generator", PDFReportGenerator())
    pdf_path = Path(generator.generate(case_id, record.get("report", "")))
    if not pdf_path.exists():
        raise HTTPException(status_code=404, detail="Report PDF not found")
    return FileResponse(str(pdf_path), media_type="application/pdf", filename=f"{case_id}.pdf")
