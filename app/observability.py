import logging
import os
import sys
import time
import uuid

from flask import Response, g, request
from prometheus_client import CONTENT_TYPE_LATEST, Counter, Histogram, generate_latest


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

REQUEST_EXCEPTIONS_TOTAL = Counter(
    "goalixa_http_request_exceptions_total",
    "Total number of request exceptions.",
    ["method", "route", "exception_type"],
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

    @app.route("/metrics", methods=["GET"])
    def prometheus_metrics():
        return Response(generate_latest(), mimetype=CONTENT_TYPE_LATEST)

    @app.before_request
    def start_request_tracking():
        g.request_started_at = time.perf_counter()
        incoming_request_id = (request.headers.get("X-Request-ID") or "").strip()
        g.request_id = incoming_request_id or uuid.uuid4().hex

    @app.after_request
    def complete_request_tracking(response):
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
