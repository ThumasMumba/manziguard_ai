"""POST /api/analyze: strip photo in, water-safety assessment out.

REQUEST   multipart/form-data
            photo  (required) JPEG, PNG or WebP image of the strip
            lang   (optional) en | bem | nya   (falls back to Accept-Language, then en)

RESPONSE  200 {"ok": true, "verdict": "safe|risky|unsafe|retake", ...}
          4xx {"ok": false, "error": {"code": "...", "message": "..."}}

    400 no_image_data      415 unsupported_type     413 image_too_large
    422 <strip_reader code> (retake the photo)      429 rate_limited
    500 server_error

WIRING (in the app factory, after extensions are created):

    from app.blueprints.analysis import analysis_bp, init_analysis
    limiter.init_app(app)
    init_analysis(app)                 # loads and validates the chart ONCE
    app.register_blueprint(analysis_bp)

SECURITY NOTES
    * The photo is processed in memory and never written to disk.
    * File type is decided by the file's first bytes, not by its name or the
      client-supplied Content-Type.
    * The upload is size-limited twice: by Flask (MAX_CONTENT_LENGTH) and again
      while reading, so a lying Content-Length cannot get past it.
    * Internal exception text is logged but never returned to the client.
    * If you use Flask-WTF CSRFProtect, send the token in an X-CSRFToken header
      from your page's JavaScript (preferred), or exempt this view knowingly.
"""
from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from flask import Blueprint, Flask, current_app, jsonify, request

from app.extension import limiter
from app.services import classifier as C
from app.services.messages import normalise_language, t
from app.services.strip_reader import MAX_IMAGE_BYTES, StripReadError

log = logging.getLogger(__name__)

analysis_bp = Blueprint("analysis", __name__, url_prefix="/api")

DEFAULT_RATE_LIMIT = "10 per minute;100 per day"
MULTIPART_OVERHEAD_BYTES = 1024 * 1024   # form fields and boundaries around the photo
EXTENSION_KEY = "manziguard_chart"
SUPPORTED_LANGUAGES = ("en", "bem", "nya")


# ---------------------------------------------------------------------------
# Start-up: load the chart once
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class ChartHolder:
    chart: C.Chart
    placeholder: bool      # True while the chart still carries the "_WARNING" key


def init_analysis(app: Flask, chart_path: str | Path | None = None) -> ChartHolder:
    """Load and validate the chart once, and set the upload size limit.

    A chart that still has the "_WARNING" key holds placeholder colours. The
    app refuses to start with one in production unless ALLOW_PLACEHOLDER_CHART
    is set (use that only for a clearly labelled prototype or staging demo).
    """
    path = Path(chart_path
                or app.config.get("K5_CHART_PATH")
                or Path(app.root_path).parent / "data" / "k5_reference_chart.json")
    raw = json.loads(path.read_text(encoding="utf-8"))
    chart = C.parse_chart(raw)           # raises ClassificationError if malformed

    placeholder = "_WARNING" in raw
    is_production = not (app.debug or app.testing)
    if placeholder and is_production and not app.config.get("ALLOW_PLACEHOLDER_CHART"):
        raise RuntimeError(
            f"{path.name} still contains placeholder colours (_WARNING key). "
            "Calibrate it, or set ALLOW_PLACEHOLDER_CHART=True for a prototype demo.")
    if placeholder:
        log.warning("Analysis API is running with a PLACEHOLDER chart; results are demo-only.")

    cap = MAX_IMAGE_BYTES + MULTIPART_OVERHEAD_BYTES
    current = app.config.get("MAX_CONTENT_LENGTH")
    app.config["MAX_CONTENT_LENGTH"] = min(current, cap) if current else cap

    holder = ChartHolder(chart=chart, placeholder=placeholder)
    app.extensions[EXTENSION_KEY] = holder
    return holder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def pick_language(read_form: bool = True) -> str:
    """lang field/query > Accept-Language > English.

    `read_form=False` is used inside error handlers, because touching
    request.form after a 413 would raise the same error again.
    """
    candidate = request.args.get("lang")
    if read_form and not candidate:
        candidate = request.form.get("lang")
    lang = normalise_language(candidate)
    if lang:
        return lang
    best = request.accept_languages.best_match(SUPPORTED_LANGUAGES)
    return best or "en"


def _error(code: str, status: int, lang: str, message_key: str | None = None):
    body = {"ok": False, "error": {"code": code, "message": t(message_key or f"err_{code}", lang, "err_server")}}
    resp = jsonify(body)
    resp.status_code = status
    resp.headers["Cache-Control"] = "no-store"
    return resp


def looks_like_supported_image(data: bytes) -> bool:
    """Decide the type from magic bytes: JPEG, PNG or WebP only."""
    return (data[:3] == b"\xff\xd8\xff"
            or data[:8] == b"\x89PNG\r\n\x1a\n"
            or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"))


def serialise(assessment: C.Assessment, holder: ChartHolder, lang: str, request_id: str) -> dict[str, Any]:
    verdict = assessment.verdict.value
    pads, hints = [], []
    for name, res in assessment.pads.items():
        pad_chart = holder.chart.pads[name]
        pads.append({
            "name": name,
            "label": pad_chart.label,
            "unit": pad_chart.unit,
            "readable": res.readable,
            "result": res.swatch_label,
            "risk": res.risk.name.lower() if res.risk is not None else None,
            "confidence": res.confidence.name.lower(),
            "flags": list(res.flags),
        })
        for flag in res.flags:
            text = t(f"hint_{flag}", lang, "")
            if text and text not in hints:
                hints.append(text)

    body: dict[str, Any] = {
        "ok": True,
        "request_id": request_id,
        "verdict": verdict,
        "verdict_text": t(f"verdict_{verdict}", lang),
        "detail": t(f"verdict_{verdict}_detail", lang),
        "alert": assessment.alert,
        "low_confidence": assessment.low_confidence,
        "pads": pads,
        "hints": hints,
        "advice": [{"key": k, "text": t(k, lang)} for k in assessment.advice_keys],
        "prototype": holder.placeholder,
    }
    if holder.placeholder:
        body["prototype_notice"] = t("prototype_notice", lang)
    return body


def rate_limit() -> str:
    return current_app.config.get("ANALYZE_RATE_LIMIT", DEFAULT_RATE_LIMIT)


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------
@analysis_bp.post("/analyze")
@limiter.limit(rate_limit)
def analyze():
    request_id = uuid.uuid4().hex[:12]
    lang = pick_language()

    photo = request.files.get("photo")
    if photo is None:
        return _error("no_image_data", 400, lang)

    # Read at most limit+1 bytes: enough to know it is too big, never more.
    data = photo.stream.read(MAX_IMAGE_BYTES + 1)
    if not data:
        return _error("no_image_data", 400, lang)
    if len(data) > MAX_IMAGE_BYTES:
        return _error("image_too_large", 413, lang)
    if not looks_like_supported_image(data):
        return _error("unsupported_type", 415, lang)

    holder: ChartHolder = current_app.extensions[EXTENSION_KEY]
    try:
        assessment = C.assess_photo(data, holder.chart)
    except StripReadError as exc:                       # the photo is the problem: ask for a retake
        log.info("req=%s strip read failed: %s", request_id, exc.code)
        return _error(exc.code, 422, lang, message_key=f"err_{exc.code}")
    except C.ClassificationError:                       # our chart/config is the problem
        log.exception("req=%s classification/chart error", request_id)
        return _error("server_error", 500, lang, message_key="err_server")
    except Exception:                                   # never leak internals
        log.exception("req=%s unexpected failure", request_id)
        return _error("server_error", 500, lang, message_key="err_server")

    log.info("req=%s verdict=%s low_confidence=%s reasons=%s", request_id,
             assessment.verdict.value, assessment.low_confidence, list(assessment.reasons))
    resp = jsonify(serialise(assessment, holder, lang, request_id))
    resp.headers["Cache-Control"] = "no-store"
    return resp


# ---------------------------------------------------------------------------
# JSON errors for the framework's own failures, limited to /api/ so the
# rest of the site keeps its normal HTML error pages.
# ---------------------------------------------------------------------------
@analysis_bp.app_errorhandler(413)
def too_large(exc):
    if not request.path.startswith("/api/"):
        return exc
    return _error("image_too_large", 413, pick_language(read_form=False))


@analysis_bp.app_errorhandler(429)
def rate_limited(exc):
    if not request.path.startswith("/api/"):
        return exc
    resp = _error("rate_limited", 429, pick_language(read_form=False))
    headers = dict(exc.get_headers()) if hasattr(exc, "get_headers") else {}
    if "Retry-After" in headers:          # keep the standard hint for well-behaved clients
        resp.headers["Retry-After"] = headers["Retry-After"]
    return resp
