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
    contacts,
    devices,
    email,
    expenses,
    health,
    home_assistant,
    lists,
    memory,
    notifications,
    push,
    reminders,
    timer,
    vision,
    voice,
    weather,
)
from app.config import get_settings
from app.errors import APIError
from app.services.scheduler import start_scheduler, stop_scheduler

settings = get_settings()


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
async def api_error_handler(_request: Request, exc: APIError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"error": {"code": exc.code, "message": exc.message}})


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
    health.router,
)
for router in api_v1_routers:
    app.include_router(router, prefix="/api/v1")
