import logging
import os
import sys
import time
import uuid

from flask import Response, g, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, Gauge, Summary, Info, generate_latest


# ============= HTTP Request Metrics ============
REQUESTS_TOTAL = Counter(
    "goalixa_http_requests_total",
    "Total number of HTTP requests.",
    ["method", "route", "status_code"],
)

REQUEST_DURATION_SECONDS = Histogram(
    "goalixa_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)

REQUEST_SIZE_BYTES = Summary(
    "goalixa_http_request_size_bytes",
    "HTTP request size in bytes.",
    ["method", "route"]
)

RESPONSE_SIZE_BYTES = Summary(
    "goalixa_http_response_size_bytes",
    "HTTP response size in bytes.",
    ["method", "route", "status_code"]
)

REQUEST_EXCEPTIONS_TOTAL = Counter(
    "goalixa_http_request_exceptions_total",
    "Total number of request exceptions.",
    ["method", "route", "exception_type"],
)

ACTIVE_REQUESTS = Gauge(
    "goalixa_http_active_requests",
    "Number of active HTTP requests.",
)


# ============= Database Metrics =============
DB_QUERY_DURATION_SECONDS = Histogram(
    "goalixa_db_query_duration_seconds",
    "Database query duration in seconds.",
    ["operation", "table"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5),
)

DB_QUERY_TOTAL = Counter(
    "goalixa_db_queries_total",
    "Total number of database queries.",
    ["operation", "table", "status"],
)

DB_CONNECTION_POOL_SIZE = Gauge(
    "goalixa_db_connection_pool_size",
    "Database connection pool size.",
)

DB_CONNECTIONS_ACTIVE = Gauge(
    "goalixa_db_connections_active",
    "Number of active database connections.",
)


# ============= Authentication Metrics =============
AUTH_VALIDATION_TOTAL = Counter(
    "goalixa_auth_validation_total",
    "Total number of authentication validations.",
    ["validation_type", "status"],  # validation_type: jwt, session, oauth
)

AUTH_SESSION_DURATION_SECONDS = Histogram(
    "goalixa_auth_session_duration_seconds",
    "User session duration in seconds.",
    buckets=(60, 300, 600, 1800, 3600, 7200, 14400, 28800, 43200, 86400),
)

AUTH_ACTIVE_SESSIONS = Gauge(
    "goalixa_auth_active_sessions",
    "Number of active user sessions.",
)


# ============= Business Logic Metrics =============
TASK_OPERATIONS_TOTAL = Counter(
    "goalixa_task_operations_total",
    "Total number of task operations.",
    ["operation", "status"],  # operation: create, update, delete, complete
)

GOAL_OPERATIONS_TOTAL = Counter(
    "goalixa_goal_operations_total",
    "Total number of goal operations.",
    ["operation", "status"],
)

HABIT_OPERATIONS_TOTAL = Counter(
    "goalixa_habit_operations_total",
    "Total number of habit operations.",
    ["operation", "status"],
)

TIMER_OPERATIONS_TOTAL = Counter(
    "goalixa_timer_operations_total",
    "Total number of timer operations.",
    ["operation", "status"],  # operation: start, stop, complete
)

PROJECT_OPERATIONS_TOTAL = Counter(
    "goalixa_project_operations_total",
    "Total number of project operations.",
    ["operation", "status"],
)


# ============= Cache Metrics =============
CACHE_OPERATIONS_TOTAL = Counter(
    "goalixa_cache_operations_total",
    "Total number of cache operations.",
    ["operation", "status"],  # operation: hit, miss, set, delete
)

CACHE_DURATION_SECONDS = Histogram(
    "goalixa_cache_operation_duration_seconds",
    "Cache operation duration in seconds.",
    ["operation"],
    buckets=(0.0001, 0.0005, 0.001, 0.005, 0.01, 0.025, 0.05, 0.1),
)


# ============= External Service Metrics =============
EXTERNAL_SERVICE_REQUESTS_TOTAL = Counter(
    "goalixa_external_service_requests_total",
    "Total number of external service requests.",
    ["service", "operation", "status"],
)

EXTERNAL_SERVICE_DURATION_SECONDS = Histogram(
    "goalixa_external_service_duration_seconds",
    "External service request duration in seconds.",
    ["service", "operation"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)


# ============= Application Info =============
APP_INFO = Info(
    "goalixa_app_info",
    "Goalixa application information"
)


# ============= Error Metrics =============
ERRORS_TOTAL = Counter(
    "goalixa_errors_total",
    "Total number of application errors.",
    ["error_type", "component"],
)


def configure_logging():
    level_name = os.getenv("LOG_LEVEL", "INFO").strip().upper()
    level = getattr(logging, level_name, logging.INFO)
    log_format = os.getenv(
        "LOG_FORMAT",
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    date_format = os.getenv("LOG_DATE_FORMAT", "%Y-%m-%dT%H:%M:%S%z")

    logging.basicConfig(
        level=level,
        format=log_format,
        datefmt=date_format,
        stream=sys.stdout,
        force=True,
    )
    logging.getLogger("werkzeug").setLevel(level)


def register_observability(app):
    log_requests_enabled = os.getenv("LOG_REQUESTS_ENABLED", "1") == "1"

    # Initialize application info
    APP_INFO.info({
        'version': os.getenv('APP_VERSION', '1.0.0'),
        'environment': os.getenv('ENVIRONMENT', 'development'),
        'service': 'goalixa-app'
    })

    @app.route("/metrics", methods=["GET"])
    def prometheus_metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    @app.before_request
    def start_request_tracking():
        ACTIVE_REQUESTS.inc()
        g.request_started_at = time.perf_counter()
        incoming_request_id = (request.headers.get("X-Request-ID") or "").strip()
        g.request_id = incoming_request_id or uuid.uuid4().hex

        # Track request size
        if request.content_length:
            REQUEST_SIZE_BYTES.labels(
                method=request.method,
                route=request.endpoint or "unknown"
            ).observe(request.content_length)

    @app.after_request
    def complete_request_tracking(response):
        ACTIVE_REQUESTS.dec()
        route = _route_label()
        method = request.method
        status_code = str(response.status_code)
        elapsed_seconds = max(
            0.0,
            time.perf_counter() - getattr(g, "request_started_at", time.perf_counter()),
        )

        REQUESTS_TOTAL.labels(method=method, route=route, status_code=status_code).inc()
        REQUEST_DURATION_SECONDS.labels(method=method, route=route).observe(
            elapsed_seconds
        )

        # Track response size
        if response.content_length:
            RESPONSE_SIZE_BYTES.labels(
                method=method,
                route=route,
                status_code=status_code
            ).observe(response.content_length)

        request_id = getattr(g, "request_id", "")
        if request_id:
            response.headers.setdefault("X-Request-ID", request_id)

        if log_requests_enabled:
            app.logger.info(
                "request completed request_id=%s method=%s route=%s status=%s duration_ms=%.2f",
                request_id or "-",
                method,
                route,
                status_code,
                elapsed_seconds * 1000.0,
            )
        return response

    @app.teardown_request
    def track_request_exception(error):
        ACTIVE_REQUESTS.dec()
        if error is None:
            return
        route = _route_label()
        REQUEST_EXCEPTIONS_TOTAL.labels(
            method=request.method,
            route=route,
            exception_type=error.__class__.__name__,
        ).inc()
        app.logger.error(
            "request failed request_id=%s method=%s route=%s error=%s",
            getattr(g, "request_id", "-"),
            request.method,
            route,
            error.__class__.__name__,
            exc_info=(type(error), error, error.__traceback__),
        )


def _route_label():
    if request.url_rule and request.url_rule.rule:
        return request.url_rule.rule
    return "unmatched"
