import sqlite3
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

PROBLEM_JSON = "application/problem+json"
RETRY_AFTER_SECONDS = 30
# Can't open, or locked. Prefix match also covers extended codes (SQLITE_BUSY_TIMEOUT, ...).
RETRYABLE_SQLITE_ERRORS = ("SQLITE_CANTOPEN", "SQLITE_BUSY", "SQLITE_LOCKED")

HTTP_CODES = {404: "NOT_FOUND", 405: "VALIDATION", 409: "CONFLICT", 503: "UNAVAILABLE"}


class ApiError(Exception):
    def __init__(self, status: int, code: str, detail: str, headers: dict[str, str] | None = None):
        super().__init__(detail)
        self.status = status
        self.code = code
        self.detail = detail
        self.headers = headers


def problem(
    status: int, code: str, detail: str, headers: dict[str, str] | None = None
) -> JSONResponse:
    return JSONResponse(
        status_code=status,
        content={
            "type": "about:blank",
            "title": HTTPStatus(status).phrase,
            "status": status,
            "detail": detail,
            "code": code,
        },
        media_type=PROBLEM_JSON,
        headers=headers,
    )


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def api_error_handler(request: Request, exc: ApiError) -> JSONResponse:
        return problem(exc.status, exc.code, exc.detail, exc.headers)

    @app.exception_handler(sqlite3.OperationalError)
    async def sqlite_error_handler(request: Request, exc: sqlite3.OperationalError) -> JSONResponse:
        if (exc.sqlite_errorname or "").startswith(RETRYABLE_SQLITE_ERRORS):
            headers = {"Retry-After": str(RETRY_AFTER_SECONDS)}
            return problem(503, "UNAVAILABLE", "Database unavailable", headers)
        # Any other OperationalError (e.g. "no such table") is a bug; retrying would not help.
        return problem(500, "UNAVAILABLE", "Internal server error")

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
        detail = "; ".join(f"{err['loc'][-1]}: {err['msg']}" for err in exc.errors())
        return problem(422, "VALIDATION", detail)

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
        default = "UNAVAILABLE" if exc.status_code >= 500 else "VALIDATION"
        code = HTTP_CODES.get(exc.status_code, default)
        return problem(exc.status_code, code, str(exc.detail))

    @app.exception_handler(Exception)
    async def unhandled_error_handler(request: Request, exc: Exception) -> JSONResponse:
        return problem(500, "UNAVAILABLE", "Internal server error")
