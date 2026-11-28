"""Loopback workbench: catalog fixtures and explicitly trusted local pasted Python."""
import ast
import os
import secrets
from pathlib import Path
from tempfile import TemporaryDirectory
from importlib.metadata import version
import json
import threading
from typing import Literal
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, model_validator
from starlette.middleware.trustedhost import TrustedHostMiddleware

from . import __version__
from .engine import Options, analyze
from .paths import RESULTS, ROOT, WEB
from .problems import InvalidCase
from .problem_registry import REGISTRY
from .package_review import review_package
from .registry import fixture_cards, get_submission, local_submission


class AnalysisOptions(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    seed: int = Field(default=2026, ge=0, le=2**32 - 1)
    strategy: Literal["hypothesis", "random"] = "hypothesis"
    max_examples: int = Field(default=100, ge=1, le=500)
    max_seconds: float = Field(default=10.0, ge=0.05, le=30)
    per_case_seconds: float = Field(default=1.0, ge=0.01, le=3)
    shrink: bool = True
    max_reduction_calls: int = Field(default=150, ge=1, le=500)
    reduction_seconds: float = Field(default=5.0, ge=0.05, le=10)
    include_trace: bool = True
    trace_limit: int = Field(default=2000, ge=1, le=2000)
    replay_count: int = Field(default=3, ge=2, le=5)
    fresh_process: bool = False
    diagnostic_samples: int = Field(default=0, ge=0, le=4)


class PackageReviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    problem_id: str = Field(min_length=1, max_length=100)
    controls: list[dict] = Field(min_length=1, max_length=20)
    seed: int = Field(default=2026, ge=0, le=2**32-1)
    sample_count: int = Field(default=12, ge=1, le=40)


class AnalyzeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    problem_id: str = Field(min_length=1, max_length=100)
    fixture_id: str | None = Field(default=None, min_length=1, max_length=100, pattern=r"^[a-z0-9_]+$")
    source: str | None = Field(default=None, min_length=1, max_length=32768)
    trusted_local_code: bool = False
    options: AnalysisOptions = Field(default_factory=AnalysisOptions)
    case: dict | None = None
    analysis_id: str | None = Field(default=None, pattern=r'^[a-f0-9]{32}$')

    @model_validator(mode="after")
    def exactly_one_source(self):
        if self.problem_id not in REGISTRY:
            raise ValueError('Unknown problem')
        if (self.fixture_id is None) == (self.source is None):
            raise ValueError("Choose exactly one of fixture_id or source")
        return self


def validate_source(source):
    if len(source.encode("utf-8")) > 32768:
        raise HTTPException(422, {"kind": "source_size", "message": "حجم الكود الأقصى 32 KiB."})
    try:
        syntax_source = source.removeprefix("\ufeff")
        tree = ast.parse(syntax_source, filename="submission.py")
        compile(tree, "submission.py", "exec")
    except SyntaxError as exc:
        raise HTTPException(422, {"kind": "syntax_error", "message": "خطأ في صياغة Python: " + exc.msg,
                                  "line": exc.lineno, "column": exc.offset}) from exc
    except (ValueError, RecursionError) as exc:
        raise HTTPException(422, {"kind": "invalid_source", "message": "تعذر قراءة بنية الكود."}) from exc
    solve = next((n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "solve"), None)
    if solve is None or len(solve.args.posonlyargs + solve.args.args) != 1 or any(v is None for v in solve.args.kw_defaults):
        raise HTTPException(422, {"kind": "missing_solve", "message": "عرّف دالة solve(payload) تستقبل مدخل المسألة وتعيد النتيجة باستخدام return."})
    return tree


CUSTOM_CODE_ENABLED = os.getenv("ALGOXRAY_CUSTOM_CODE", "1") == "1"
ALLOWED_HOSTS = [h.strip() for h in os.getenv("ALGOXRAY_ALLOWED_HOSTS", "127.0.0.1,localhost,[::1],testserver").split(",") if h.strip()]

def require_loopback(request):
    if not CUSTOM_CODE_ENABLED:
        raise HTTPException(403, "Custom code is disabled in this deployment")
    if not request.client or request.client.host not in {"127.0.0.1", "::1", "testclient"}:
        raise HTTPException(403, "Custom code is restricted to this local computer")


app = FastAPI(title="AlgoX-Ray", version=__version__, docs_url=None, redoc_url=None)
app.add_middleware(TrustedHostMiddleware, allowed_hosts=ALLOWED_HOSTS)
analysis_lock = threading.Lock()
active_lock = threading.Lock()
active_analyses = {}
custom_code_token = secrets.token_urlsafe(32)


@app.middleware("http")
async def local_boundary(request: Request, call_next):
    if request.method == "POST":
        origin = request.headers.get("origin")
        if origin and (urlsplit(origin).scheme not in ("http", "https") or urlsplit(origin).netloc != request.headers.get("host")):
            return JSONResponse({"detail": "Cross-origin analysis is disabled"}, status_code=403)
        try:
            content_length = int(request.headers.get("content-length", "0"))
        except ValueError:
            return JSONResponse({"detail": "Invalid Content-Length"}, status_code=400)
        if content_length < 0 or content_length > 65536:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
        body = await request.body()
        if len(body) > 65536:
            return JSONResponse({"detail": "Request too large"}, status_code=413)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
    response.headers["Cache-Control"] = "no-store" if request.url.path.startswith("/api") else "no-cache"
    return response


@app.get("/api/health")
def health():
    return {"status": "ready", "version": __version__, "execution_mode": "local_trusted" if CUSTOM_CODE_ENABLED else "catalog_only",
            "problems": len(REGISTRY), "custom_code": CUSTOM_CODE_ENABLED, "hypothesis": version("hypothesis"), "networkx": version("networkx")}


@app.get("/api/problems")
def problems():
    return [spec.public_metadata() for spec in REGISTRY.values()]


@app.post("/api/packages/review")
def package_review(body: PackageReviewRequest, request: Request):
    require_loopback(request)
    if not secrets.compare_digest(request.headers.get("x-algoxray-token",""),custom_code_token):
        raise HTTPException(403, "Local author session required")
    try:
        return review_package(body.problem_id,body.controls,body.seed,body.sample_count)
    except ValueError as exc:
        raise HTTPException(422,str(exc)) from exc


@app.get("/api/fixtures")
def fixtures(problem_id: str | None = None):
    return fixture_cards(problem_id)


@app.get("/api/session")
def local_session(request: Request):
    require_loopback(request)
    return {"custom_code_token": custom_code_token, "max_source_bytes": 32768}


@app.post("/api/analysis/{analysis_id}/cancel")
def cancel_analysis(analysis_id: str):
    with active_lock:
        token = active_analyses.get(analysis_id)
        if token is None:
            raise HTTPException(404, "No active analysis with this identifier")
        token.set()
    return {"status": "cancellation_requested"}


@app.post("/api/analyze")
def analyze_request(body: AnalyzeRequest, request: Request):
    if body.source is not None:
        require_loopback(request)
        token = request.headers.get("x-algoxray-token", "")
        if not body.trusted_local_code or not secrets.compare_digest(token, custom_code_token):
            raise HTTPException(403, "Confirm your local code and refresh the page before running it")
        if request.headers.get("sec-fetch-site") == "cross-site":
            raise HTTPException(403, "Cross-site custom code is disabled")
        if request.headers.get("content-type", "").split(";")[0].strip() != "application/json":
            raise HTTPException(415, "Custom code requires application/json")
        validate_source(body.source)
    if not analysis_lock.acquire(blocking=False):
        raise HTTPException(409, "An analysis is already running")
    cancel = threading.Event()
    if body.analysis_id:
        with active_lock:
            active_analyses[body.analysis_id] = cancel
    try:
        if body.source is not None:
            with TemporaryDirectory(prefix="algoxray_code_") as directory:
                path = Path(directory) / "submission.py"
                path.write_bytes(body.source.encode("utf-8"))
                submission = local_submission(body.problem_id, path)
                return analyze(submission, Options(**body.options.model_dump()), case=body.case, cancel=cancel)
        submission = get_submission(body.fixture_id)
        if submission.problem_id != body.problem_id:
            raise ValueError("Fixture does not belong to the requested problem")
        return analyze(submission, Options(**body.options.model_dump()), case=body.case, cancel=cancel)
    except (ValueError, InvalidCase) as exc:
        raise HTTPException(422, str(exc)) from exc
    finally:
        if body.analysis_id:
            with active_lock:
                active_analyses.pop(body.analysis_id, None)
        analysis_lock.release()


@app.get("/api/benchmark-summary")
def benchmark_summary():
    path = RESULTS / "core-release" / "summary.json"
    if path.is_file():
        return json.loads(path.read_text(encoding="utf-8"))
    path = RESULTS / "summary.json"
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else {"status": "not_run", "rows": []}


@app.get("/api/option-b/benchmark-summary")
def option_b_benchmark_summary(revision: Literal["v1","v2"] = "v1"):
    path = RESULTS / ("option-b-new" if revision=="v1" else "option-b-v2") / "summary.json"
    result = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {"status": "not_run", "rows": []}
    return {**result,"revision":revision}


@app.get("/api/contract")
def evidence_contract():
    return json.loads((ROOT / "contracts" / "evidence.schema.json").read_text(encoding="utf-8"))


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/docs", include_in_schema=False)
def docs():
    return FileResponse(WEB / "docs.html")


@app.get("/poster", include_in_schema=False)
def poster():
    path = ROOT / "docs" / "poster.html"
    if not path.exists():
        raise HTTPException(404, "Poster has not been generated")
    return FileResponse(path)


from .v4_api import router_for
app.include_router(router_for(require_loopback,custom_code_token))

@app.get("/v4",include_in_schema=False)
def v4_page():
    return FileResponse(WEB / "v4.html")

@app.get("/v4/catalog", include_in_schema=False)
def v4_catalog_page(request: Request):
    require_loopback(request)
    return FileResponse(WEB / "v4-catalog.html")


app.mount("/static", StaticFiles(directory=WEB / "static"), name="static")
