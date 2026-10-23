"""DealScope Flask application: routes, error handling, logging. Logic lives in dealscope/."""

import json
import logging
import re
import sys
import time
import traceback
import uuid
from typing import Any, Dict, Optional

from flask import Flask, g, jsonify, render_template, request
from flask_cors import CORS
from werkzeug.exceptions import HTTPException

from dealscope import validation as V
from dealscope.config import Config
from dealscope.errors import (
    DealScopeError,
    InvalidRequest,
    MethodNotAllowed,
    NotFound,
    RateLimited,
)
from dealscope.forms import form_to_payload
from dealscope.provider import PropertyProvider, build_provider
from dealscope.ratelimit import RateLimiter, parse_rate
from dealscope.service import run_analysis

log = logging.getLogger("dealscope")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,64}$")
_LIMITED_ENDPOINTS = {"analyze_route", "index"}


def _configure_logging(level: str) -> None:
    numeric = logging.getLevelName(level)
    log.setLevel(numeric if isinstance(numeric, int) else logging.INFO)
    if not log.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter("%(message)s"))
        log.addHandler(handler)


def _form_defaults() -> Dict[str, Any]:
    return {
        "address": "",
        "down_payment_pct": V.DEFAULT_DOWN_PCT,
        "annual_interest_rate_pct": V.DEFAULT_RATE,
        "loan_term_years": V.DEFAULT_TERM,
    }


def create_app(
    config: Optional[Config] = None, provider: Optional[PropertyProvider] = None
) -> Flask:
    config = config or Config.from_env()
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = config.max_body_bytes
    _configure_logging(config.log_level)
    provider = provider or build_provider(
        config.property_provider, config.connect_timeout_s, config.read_timeout_s
    )
    parsed_rate = parse_rate(config.rate_limit)
    limiter = RateLimiter(*parsed_rate) if parsed_rate else None

    if config.cors_origins:
        CORS(
            app,
            resources={r"/analyze": {"origins": list(config.cors_origins)}},
            methods=["POST", "OPTIONS"],
            allow_headers=["Content-Type"],
        )

    # ── request lifecycle ────────────────────────────────────────────────────
    @app.before_request
    def _begin():
        incoming = request.headers.get("X-Request-ID", "")
        g.request_id = incoming if _REQUEST_ID.match(incoming) else uuid.uuid4().hex
        g.started = time.monotonic()
        g.error_code = None
        if limiter and request.method == "POST" and request.endpoint in _LIMITED_ENDPOINTS:
            forwarded = request.headers.get("X-Forwarded-For", "").split(",")[0].strip()
            if not limiter.allow(forwarded or request.remote_addr or "unknown"):
                raise RateLimited()

    @app.after_request
    def _end(response):
        response.headers["X-Request-ID"] = getattr(g, "request_id", "")
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        response.headers.setdefault("Referrer-Policy", "no-referrer")
        if request.endpoint != "healthz":
            # Deliberately excludes addresses, bodies, query strings, and upstream payloads.
            log.info(
                json.dumps(
                    {
                        "event": "request",
                        "request_id": getattr(g, "request_id", None),
                        "method": request.method,
                        "route": request.url_rule.rule if request.url_rule else "unmatched",
                        "status": response.status_code,
                        "latency_ms": round(
                            (time.monotonic() - getattr(g, "started", time.monotonic())) * 1000
                        ),
                        "error_code": getattr(g, "error_code", None),
                    }
                )
            )
        return response

    # ── errors ───────────────────────────────────────────────────────────────
    def _error_body(err: DealScopeError) -> Dict[str, Any]:
        body = err.to_dict()
        body["request_id"] = getattr(g, "request_id", None)
        return {"success": False, "error": body}

    @app.errorhandler(DealScopeError)
    def _domain_error(err: DealScopeError):
        g.error_code = err.code
        return jsonify(_error_body(err)), err.status

    @app.errorhandler(HTTPException)
    def _http_error(err: HTTPException):
        if err.code == 404:
            domain: DealScopeError = NotFound()
        elif err.code == 405:
            domain = MethodNotAllowed()
        else:
            domain = InvalidRequest(
                "The request was too large." if err.code == 413 else "The request was not valid."
            )
            domain.status = err.code if err.code and 400 <= err.code < 500 else 400
        return _domain_error(domain)

    @app.errorhandler(Exception)
    def _unexpected(err: Exception):
        frame = traceback.extract_tb(err.__traceback__)[-1] if err.__traceback__ else None
        log.error(
            json.dumps(
                {
                    "event": "unhandled_error",
                    "request_id": getattr(g, "request_id", None),
                    "type": type(err).__name__,
                    "where": f"{frame.filename.rsplit('/', 1)[-1]}:{frame.lineno}"
                    if frame
                    else None,
                }
            )
        )
        return _domain_error(DealScopeError())

    # ── routes ───────────────────────────────────────────────────────────────
    def _page(status: int = 200, **ctx):
        ctx.setdefault("form", _form_defaults())
        return (
            render_template(
                "index.html",
                provider_enabled=provider.enabled,
                bounds=V,
                version=config.app_version,
                **ctx,
            ),
            status,
        )

    @app.route("/", methods=["GET", "POST"])
    def index():
        if request.method == "GET":
            return _page()
        form = request.form.to_dict()
        try:
            result = run_analysis(form_to_payload(form), provider, config.request_budget_s)
        except DealScopeError as err:
            g.error_code = err.code
            return _page(err.status, form=form, error=_error_body(err)["error"])
        except Exception as err:  # noqa: BLE001 - same safe handling as the JSON API
            body = _unexpected(err)[0].get_json()
            return _page(500, form=form, error=body["error"])
        return _page(form=form, analysis=result["analysis"])

    @app.route("/analyze", methods=["POST"])
    def analyze_route():
        payload = request.get_json(silent=True)
        if payload is None:
            raise InvalidRequest(
                "The request body must be JSON with a Content-Type of application/json."
            )
        return jsonify(run_analysis(payload, provider, config.request_budget_s))

    @app.route("/healthz")
    def healthz():
        # Liveness only (spec FR-21): must never call the property provider.
        return jsonify({"status": "ok", "version": config.app_version})

    @app.template_filter("usd")
    def _usd(value, cents=True):
        if value is None:
            return ""
        text = f"{abs(value):,.2f}" if cents else f"{abs(value):,.0f}"
        return f"−${text}" if value < 0 else f"${text}"

    @app.template_filter("pct")
    def _pct(value):
        if value is None:
            return ""
        return f"−{abs(value):,.2f}%" if value < 0 else f"{value:,.2f}%"

    return app


app = create_app()

if __name__ == "__main__":
    import os

    # Local development server only. Production runs under Gunicorn or the host's runtime.
    app.run(host=os.environ.get("HOST", "127.0.0.1"), port=int(os.environ.get("PORT", 5000)))
