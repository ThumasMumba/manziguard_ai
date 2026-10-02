from flask import Blueprint, current_app, render_template, request

from ..extension import limiter
from ..services import calibration, strip_reader
from ..services.il8n import t
from ..services.pipeline import assess_and_record

bp = Blueprint("analysis", __name__)

#If the language is not supported, it defaults to the application's DEFAULT LANGUAGE if it is supported it returns the lang
def _language() -> str:
    lang = request.values.get("lang", current_app.config["DEFAULT_LANGUAGE"])
    if lang in current_app.config["SUPPORTED_LANGUAGES"]:
        return lang
    else:
        return current_app.config["DEFAULT_LANGUAGE"]


def _coord(name: str, low: float, high: float):
    raw = request.form.get(name, "").strip()
    if not raw:
        return None
    try:
        value = float(raw)
    except ValueError:
        return None
    return value if low <= value <= high else None


def _error(code: str, lang: str, status: int, **kw):
    return render_template("index.html", lang=lang, t=t,
                           error=t(f"err_{code}", lang, **kw)), status


@bp.get("/")
def index():
    lang = _language()
    return render_template("index.html", lang=lang, t=t, error=None)


@bp.post("/analyze")
@limiter.limit("20 per hour")
def analyze():
    lang = _language()
    cfg = current_app.config
    chart = current_app.extensions["manzi_chart"]

    if cfg["REQUIRE_CALIBRATED_CHART"] and not chart.get("calibrated"):
        return _error("not_calibrated", lang, 503)

    file = request.files.get("strip_photo")
    if not file or not file.filename:
        return _error("not_an_image", lang, 400)

    lat, lon = _coord("lat", -90, 90), _coord("lon", -180, 180)
    if lat is None or lon is None:
        lat = lon = None

    try:
        img = strip_reader.decode_image(file.read())  # kept in memory, never written to disk
        colours = strip_reader.read_pad_colours(img, chart["layout"])
        readings = calibration.colours_to_readings(colours, chart, cfg["MAX_MATCH_DELTA_E"])
    except strip_reader.StripReadError as exc:
        return _error(str(exc), lang, 400)
    except calibration.LowConfidence as exc:
        return _error("low_confidence", lang, 422, pad=exc.pad)

    sample, assessment, alert_status = assess_and_record(
        readings, channel="web", language=lang, lat=lat, lon=lon)
    
    return render_template("result.html", lang=lang, t=t, sample=sample,assessment=assessment, alert_status=alert_status)
