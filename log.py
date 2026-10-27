
# AI Generated Code for loggin everything of requested actions

import json
import logging
import threading

from pathlib import Path
from logging.handlers import RotatingFileHandler
from collections import defaultdict
from datetime import datetime, timezone


BASE_DIR = Path(__file__).resolve().parent
LOG_DIR = BASE_DIR / "log"

LOG_DIR.mkdir(parents=True, exist_ok=True)


def create_logger(name, filename):
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    logger.propagate = False

    # Prevent duplicate handlers during reloads
    if not logger.handlers:
        handler = RotatingFileHandler(
            LOG_DIR / filename,
            maxBytes=5 * 1024 * 1024,
            backupCount=5,
            encoding="utf-8"
        )

        handler.setFormatter(logging.Formatter("%(message)s"))
        logger.addHandler(handler)

    return logger


error_logger = create_logger("ams_error", "error.log")
viewer_logger = create_logger("ams_viewer", "viewer.log")
frequency_logger = create_logger(
    "ams_frequency", "viewer_frequency.log"
)
action_logger = create_logger("ams_action", "action.log")

frequency_lock = threading.Lock()
visitor_frequency = defaultdict(int)


def load_previous_frequency():
    """Restore counts from the existing frequency log."""
    log_path = LOG_DIR / "viewer_frequency.log"

    if not log_path.exists():
        return

    try:
        with log_path.open("r", encoding="utf-8") as file:
            for line in file:
                try:
                    record = json.loads(line)
                    key = record.get("frequency_key")

                    if key:
                        visitor_frequency[key] = max(
                            visitor_frequency[key],
                            record.get("visit_count", 0)
                        )
                except (json.JSONDecodeError, TypeError):
                    continue
    except OSError:
        error_logger.exception(
            "Could not load visitor frequency history"
        )


load_previous_frequency()


def current_timestamp():
    return datetime.now(timezone.utc).isoformat()


def write_record(logger, record):
    """Write one structured JSON record per log line."""
    try:
        logger.info(json.dumps(
            record,
            ensure_ascii=False,
            default=str
        ))
    except Exception:
        # Avoid breaking the API if logging itself fails.
        pass


SENSITIVE_KEYS = {
    "password", "passwd", "token", "access_token",
    "refresh_token", "secret", "authorization",
    "cookie", "set-cookie", "api_key", "apikey",
    "email", "phone", "address", "student_name",
    "teacher_name", "full_name"
}


def sanitize(value):
    """Redact sensitive fields before writing request/response data."""
    if isinstance(value, dict):
        cleaned = {}

        for key, item in value.items():
            if key.lower() in SENSITIVE_KEYS:
                cleaned[key] = "[REDACTED]"
            else:
                cleaned[key] = sanitize(item)

        return cleaned

    if isinstance(value, list):
        return [sanitize(item) for item in value]

    return value


def parse_json_body(raw_body):
    """Decode JSON when possible; otherwise log a safe placeholder."""
    if not raw_body:
        return None

    if len(raw_body) > 65536:
        return "[BODY OMITTED: exceeds 64 KB]"

    try:
        parsed = json.loads(raw_body.decode("utf-8"))
        return sanitize(parsed)
    except (ValueError, UnicodeDecodeError):
        return "[NON-JSON BODY OMITTED]"


def log_error(message, **details):
    write_record(error_logger, {
        "timestamp": current_timestamp(),
        "message": message,
        **details
    })


def log_action(
    *,
    client_ip,
    method,
    path,
    query_params=None,
    request_data=None,
    status_code=None,
    outcome=None,
    response_data=None
):
    write_record(action_logger, {
        "timestamp": current_timestamp(),
        "client_ip": client_ip,
        "method": method,
        "path": path,
        "query_params": query_params or {},
        "request_data": request_data,
        "status_code": status_code,
        "outcome": outcome,
        "response_data": response_data
    })


# ----------------------------------------------------------------------------------------------------
# FASTAPI REQUEST LOGGING MIDDLEWARE
# ----------------------------------------------------------------------------------------------------

class RequestLoggingMiddleware:
    """
    Logs incoming requests and completed responses.

    Works at the ASGI level so the request body can be
    recorded without consuming it before FastAPI receives it.
    """

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        started_at = datetime.now(timezone.utc)

        method = scope.get("method", "UNKNOWN")
        path = scope.get("path", "/")

        query_string = scope.get("query_string", b"")
        try:
            from urllib.parse import parse_qs

            query_params = parse_qs(
                query_string.decode("utf-8"),
                keep_blank_values=True
            )
        except Exception:
            query_params = {}

        client = scope.get("client")
        client_ip = client[0] if client else "unknown"

        request_chunks = []
        response_chunks = []
        status_code = 500

        async def logged_receive():
            message = await receive()

            if message["type"] == "http.request":
                chunk = message.get("body", b"")

                # Bound memory use for logging.
                remaining = 65536 - sum(
                    len(part) for part in request_chunks
                )
                if remaining > 0:
                    request_chunks.append(chunk[:remaining])

            return message

        async def logged_send(message):
            nonlocal status_code

            if message["type"] == "http.response.start":
                status_code = message["status"]

            elif message["type"] == "http.response.body":
                chunk = message.get("body", b"")

                # Only capture a bounded response for logging.
                remaining = 16384 - sum(
                    len(part) for part in response_chunks
                )
                if remaining > 0:
                    response_chunks.append(chunk[:remaining])

            await send(message)

        try:
            await self.app(scope, logged_receive, logged_send)

        except Exception as exc:
            log_error(
                "Unhandled application exception",
                method=method,
                path=path,
                client_ip=client_ip,
                exception_type=type(exc).__name__,
                exception_message=str(exc)
            )
            raise

        finally:
            finished_at = datetime.now(timezone.utc)
            duration_ms = round(
                (finished_at - started_at).total_seconds() * 1000,
                2
            )

            route = scope.get("route")
            route_template = getattr(route, "path", path)

            request_body = parse_json_body(
                b"".join(request_chunks)
            )

            # Viewer log: one entry per request.
            write_record(viewer_logger, {
                "timestamp": finished_at.isoformat(),
                "client_ip": client_ip,
                "method": method,
                "path": path,
                "route": route_template,
                "status_code": status_code,
                "duration_ms": duration_ms
            })

            # Frequency key uses route template, so
            # /course/1 and /course/2 count as one page.
            frequency_key = f"{client_ip}|{method}|{route_template}"

            with frequency_lock:
                visitor_frequency[frequency_key] += 1
                count = visitor_frequency[frequency_key]

                write_record(frequency_logger, {
                    "timestamp": finished_at.isoformat(),
                    "client_ip": client_ip,
                    "method": method,
                    "route": route_template,
                    "frequency_key": frequency_key,
                    "visit_count": count
                })

            # Capture only JSON response details.
            response_data = None
            raw_response = b"".join(response_chunks)

            if raw_response and len(raw_response) <= 16384:
                try:
                    response_data = sanitize(
                        json.loads(raw_response.decode("utf-8"))
                    )
                except (ValueError, UnicodeDecodeError):
                    response_data = "[NON-JSON RESPONSE OMITTED]"
            elif raw_response:
                response_data = "[RESPONSE OMITTED: exceeds 16 KB]"

            # Action log: request, result, and outcome.
            log_action(
                client_ip=client_ip,
                method=method,
                path=path,
                query_params=query_params,
                request_data=request_body,
                status_code=status_code,
                outcome=(
                    "success" if status_code < 400 else "failed"
                ),
                response_data=response_data
            )

            # Error log: client errors and server errors.
            if status_code >= 400:
                log_error(
                    "HTTP request failed",
                    client_ip=client_ip,
                    method=method,
                    path=path,
                    status_code=status_code,
                    duration_ms=duration_ms
                )
