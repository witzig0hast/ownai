import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import (
    admin,
    agent_bus,
    auth,
    automations,
    calendar,
    chat,
    clipper,
    contacts,
    devices,
    email,
    expenses,
    health,
    home_assistant,
    lists,
    logs,
    memory,
    notifications,
    onboarding,
    pending_actions,
    permanent_agents,
    push,
    reminders,
    rss,
    searxng,
    sso,
    timer,
    tts,
    vision,
    voice,
    weather,
)
from app.config import get_settings
from app.errors import APIError
from app.services.scheduler import start_scheduler, stop_scheduler

settings = get_settings()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    start_scheduler()
    try:
        yield
    finally:
        stop_scheduler()


app = FastAPI(title="OwnAI Backend", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(APIError)
async def api_error_handler(request: Request, exc: APIError) -> JSONResponse:
    if exc.status_code >= 500:
        # A 4xx APIError (wrong password, not found, ...) is routine and already visible to the
        # caller via the JSON body - a 5xx one means something OwnAI itself depends on (an
        # external provider, typically) failed, which is worth `docker compose logs backend`
        # showing directly. Without this, diagnosing e.g. an SSO callback failure meant digging
        # the JSON error body out of a browser's redirect chain instead of just reading the logs.
        logger.warning("%s %s -> %s %s: %s", request.method, request.url.path, exc.status_code, exc.code, exc.message)
    retry_after = getattr(exc, "retry_after_seconds", None)
    headers = {"Retry-After": str(retry_after)} if retry_after is not None else None
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": exc.code, "message": exc.message}},
        headers=headers,
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(_request: Request, exc: HTTPException) -> JSONResponse:
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": {"code": "http_error", "message": str(exc.detail)}},
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={"error": {"code": "validation_error", "message": str(exc.errors())}},
    )


api_v1_routers = (
    auth.router,
    sso.router,
    devices.router,
    chat.router,
    calendar.router,
    notifications.router,
    voice.router,
    home_assistant.router,
    timer.router,
    admin.router,
    email.router,
    vision.router,
    push.router,
    agent_bus.router,
    memory.router,
    contacts.router,
    reminders.router,
    automations.router,
    lists.router,
    expenses.router,
    weather.router,
    searxng.router,
    rss.router,
    clipper.router,
    permanent_agents.router,
    tts.router,
    logs.router,
    pending_actions.router,
    onboarding.router,
    health.router,
)
for router in api_v1_routers:
    app.include_router(router, prefix="/api/v1")
