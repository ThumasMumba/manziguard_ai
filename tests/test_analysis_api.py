"""Tests for the /api/analyze blueprint.  Run from the project root: python -m pytest -q

Photos are synthetic strips painted with the chart's own swatch colours, so the
tests keep working when you swap in a calibrated chart, provided the labels
used below ("0", "7.0", "absent", "present") still exist and the layout uses
equal slicing (no pad_bounds). If you add pad_bounds, paint the pads there.
"""
import io
import json
from pathlib import Path

import cv2
import numpy as np
import pytest
from flask import Flask

from app.services.analysis import analysis_bp, init_analysis
from app.extension import limiter
from app.services import classifier as C
from app.services.messages import MESSAGES, missing_translations, t
from app.services.strip_reader import MAX_IMAGE_BYTES

ROOT = Path(__file__).resolve().parent.parent          # tests/ -> project root
CHART_PATH = ROOT / "data" / "k5_reference_chart.json"
CHART = C.load_chart(CHART_PATH)
RAW_CHART = json.loads(CHART_PATH.read_text(encoding="utf-8"))


# --- helpers ------------------------------------------------------------------
def swatch_lab(pad: str, label: str):
    return next(s.lab for s in CHART.pads[pad].swatches if s.label == label)


def lab_to_bgr(lab) -> tuple[int, int, int]:
    px = np.float32([[lab]])                                   # float32 LAB: L 0-100
    bgr = np.clip(cv2.cvtColor(px, cv2.COLOR_LAB2BGR)[0, 0], 0, 1)
    return tuple(int(round(v * 255)) for v in bgr)


def make_photo(nitrate="0", ph="7.0", bacteria="absent") -> bytes:
    """White strip: reference patch on top, then one pad per segment, as a JPEG."""
    img = np.full((900, 500, 3), 90, np.uint8)
    x0, x1, y0, seg = 210, 290, 50, 200
    img[y0: y0 + 4 * seg, x0:x1] = 200
    for i, (pad, label) in enumerate((("nitrate", nitrate), ("ph", ph), ("bacteria", bacteria)), start=1):
        img[y0 + i * seg: y0 + (i + 1) * seg, x0 + 10: x1 - 10] = lab_to_bgr(swatch_lab(pad, label))
    return cv2.imencode(".jpg", img, [cv2.IMWRITE_JPEG_QUALITY, 95])[1].tobytes()


def post(client, data: bytes | None, filename="strip.jpg", **form):
    fields = dict(form)
    if data is not None:
        fields["photo"] = (io.BytesIO(data), filename)
    return client.post("/api/analyze", data=fields, content_type="multipart/form-data")


@pytest.fixture()
def client():
    app = Flask(__name__)
    app.config.update(TESTING=True, RATELIMIT_STORAGE_URI="memory://")
    limiter.init_app(app)
    init_analysis(app, CHART_PATH)
    app.register_blueprint(analysis_bp)
    limiter.reset()
    return app.test_client()


# --- happy paths --------------------------------------------------------------
def test_clean_strip_is_safe(client):
    r = post(client, make_photo())
    body = r.get_json()
    assert r.status_code == 200 and body["ok"] and body["verdict"] == "safe"
    assert body["alert"] is False and body["advice"] == []
    assert {p["name"]: p["result"] for p in body["pads"]} == {"nitrate": "0", "ph": "7.0", "bacteria": "absent"}
    assert r.headers["Cache-Control"] == "no-store"


def test_bacteria_present_is_unsafe_with_alert_and_advice(client):
    body = post(client, make_photo(bacteria="present")).get_json()
    assert body["verdict"] == "unsafe" and body["alert"] is True
    assert [a["key"] for a in body["advice"]] == ["advice_bacteria_unsafe"]
    assert body["advice"][0]["text"] != "advice_bacteria_unsafe"      # translated, not a raw key


def test_placeholder_chart_is_flagged_as_prototype(client):
    body = post(client, make_photo()).get_json()
    assert body["prototype"] == ("_WARNING" in RAW_CHART)


def test_untranslated_language_falls_back_to_english(client):
    english = post(client, make_photo(bacteria="present")).get_json()
    bemba = post(client, make_photo(bacteria="present"), lang="bem").get_json()
    if not MESSAGES["bem"]:
        assert bemba["verdict_text"] == english["verdict_text"]


# --- bad uploads --------------------------------------------------------------
def test_missing_photo_is_400(client):
    r = post(client, None)
    assert r.status_code == 400 and r.get_json()["error"]["code"] == "no_image_data"


def test_empty_file_is_400(client):
    assert post(client, b"").status_code == 400


def test_wrong_file_type_is_415_even_if_named_jpg(client):
    r = post(client, b"GIF89a" + b"\x00" * 100, filename="strip.jpg")
    assert r.status_code == 415 and r.get_json()["error"]["code"] == "unsupported_type"


def test_corrupt_image_with_valid_header_is_422(client):
    r = post(client, b"\xff\xd8\xff" + b"not really a jpeg" * 20)
    assert r.status_code == 422 and r.get_json()["error"]["code"] == "not_an_image"


def test_photo_without_a_strip_asks_for_retake(client):
    blank = cv2.imencode(".jpg", np.full((900, 500, 3), 120, np.uint8))[1].tobytes()
    r = post(client, blank)
    err = r.get_json()["error"]
    assert r.status_code == 422 and err["code"] == "strip_not_found" and err["message"]


def test_oversized_upload_is_413_json(client):
    r = post(client, b"\xff\xd8\xff" + b"0" * (MAX_IMAGE_BYTES + 2 * 1024 * 1024))
    assert r.status_code == 413 and r.get_json()["error"]["code"] == "image_too_large"


# --- rate limiting ------------------------------------------------------------
def test_rate_limit_returns_json_429(client):
    client.application.config["ANALYZE_RATE_LIMIT"] = "2 per minute"
    photo = make_photo()
    assert post(client, photo).status_code == 200
    assert post(client, photo).status_code == 200
    r = post(client, photo)
    assert r.status_code == 429 and r.get_json()["error"]["code"] == "rate_limited"


# --- start-up safety ----------------------------------------------------------
@pytest.mark.skipif("_WARNING" not in RAW_CHART, reason="chart is already calibrated")
def test_placeholder_chart_refused_in_production():
    app = Flask(__name__)                       # not debug, not testing = production
    with pytest.raises(RuntimeError):
        init_analysis(app, CHART_PATH)
    app.config["ALLOW_PLACEHOLDER_CHART"] = True
    assert init_analysis(app, CHART_PATH).placeholder is True


# --- message catalogue --------------------------------------------------------
STRIP_ERROR_CODES = ["no_image_data", "image_too_large", "not_an_image", "image_too_small",
                     "strip_not_found", "strip_too_small", "invalid_segment_size", "too_dark",
                     "overexposed", "reference_uneven", "colour_cast_too_strong"]


@pytest.mark.parametrize("code", STRIP_ERROR_CODES)
def test_every_strip_error_code_has_an_english_message(code):
    assert f"err_{code}" in MESSAGES["en"]


def test_every_chart_advice_key_has_an_english_text():
    for pad in CHART.pads.values():
        for key in pad.advice.values():
            assert key in MESSAGES["en"], key


def test_translation_gap_report_is_available():
    assert isinstance(missing_translations("bem"), list)
    assert t("no_such_key", "nya", "fallback") == "fallback"
