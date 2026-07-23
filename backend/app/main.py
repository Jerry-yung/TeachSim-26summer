from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import asr, asr_debug, auth, history, inclass, lesson, report, tts, visual
from app.core.config import get_settings
from app.services.storage import ensure_upload_root


@asynccontextmanager
async def lifespan(_app: FastAPI):
    ensure_upload_root()
    yield


app = FastAPI(title="TeachSim API", lifespan=lifespan)

_settings = get_settings()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(HTTPException)
async def http_exception_handler(_request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={"code": exc.status_code, "message": str(exc.detail)},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request, exc: RequestValidationError):
    errs = exc.errors()
    msg = errs[0].get("msg", "参数错误") if errs else "参数错误"
    return JSONResponse(
        status_code=400,
        content={"code": 400, "message": msg},
    )


app.include_router(auth.router, prefix="/api")
app.include_router(lesson.router, prefix="/api")
app.include_router(asr.router, prefix="/api")
app.include_router(asr_debug.router, prefix="/api/debug")
app.include_router(inclass.router, prefix="/api")
app.include_router(report.router, prefix="/api")
app.include_router(history.router, prefix="/api")
app.include_router(tts.router, prefix="/api")
app.include_router(visual.router, prefix="/api")


@app.get("/health")
def health():
    return {"status": "ok"}
