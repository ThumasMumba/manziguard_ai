"""Tests for classifier.py.  Run: python -m pytest test_classifier.py -v  (or python test_classifier.py)

Swatch colours are read from the example chart, so these tests check the LOGIC
and keep working when you replace the placeholder values with calibrated ones
(provided you keep the same pad names and at least one safe + one unsafe swatch
on nitrate and bacteria).
"""
from pathlib import Path

from flask import json
import pytest

from app.services import classifier as C
from app.services.strip_reader import PadReading
from pathlib import Path

# def get_data_file_path(filename: str) -> Path:
#     """Finds a file inside the root data/ folder regardless of current working directory."""
#     # Start from current file location and traverse up to project root
#     current = Path(__file__).resolve()
#     for parent in [current] + list(current.parents):
#         data_dir = parent / "data"
#         if data_dir.is_dir():
#             target = data_dir / filename
#             if target.exists():
#                 return target
    
#     raise FileNotFoundError(f"Could not locate '{filename}' in project data/ directory.")

ROOT = Path(__file__).resolve().parent.parent
# Usage
CHART_PATH = ROOT / "data" / "k5_reference_chart.json" # or "k5_reference_chart.json"
CHART = C.load_chart(CHART_PATH)


def swatch_lab(pad: str, label: str):
    return next(s.lab for s in CHART.pads[pad].swatches if s.label == label)


def reading(pad: str, lab, spread: float = 0.0) -> PadReading:
    return PadReading(name=pad, lab=tuple(lab), bgr=(0, 0, 0), spread=spread)


def readings(nitrate="0", ph="7.0", bacteria="absent", over=None):
    out = {
        "nitrate": reading("nitrate", swatch_lab("nitrate", nitrate)),
        "ph": reading("ph", swatch_lab("ph", ph)),
        "bacteria": reading("bacteria", swatch_lab("bacteria", bacteria)),
    }
    out.update(over or {})
    return out


# --- colour-difference maths -------------------------------------------------
@pytest.mark.parametrize("lab1, lab2, expected", [
    # Published CIEDE2000 test pairs (Sharma, Wu & Dalal 2005)
    ((50.0, 2.6772, -79.7751), (50.0, 0.0, -82.7485), 2.0425),
    ((50.0, 3.1571, -77.2803), (50.0, 0.0, -82.7485), 2.8615),
    ((50.0, 2.5, 0.0), (50.0, 0.0, -2.5), 4.3065),
    ((60.2574, -34.0099, 36.2677), (60.4626, -34.1751, 39.4387), 1.2644),
])
def test_ciede2000_matches_published_values(lab1, lab2, expected):
    assert C.delta_e_2000(lab1, lab2) == pytest.approx(expected, abs=1e-4)


def test_delta_e_is_zero_for_identical_and_symmetric():
    a, b = (70.0, 20.0, -10.0), (65.0, 25.0, 0.0)
    assert C.delta_e_2000(a, a) == pytest.approx(0.0)
    assert C.delta_e_2000(a, b) == pytest.approx(C.delta_e_2000(b, a))


# --- single pad --------------------------------------------------------------
def test_exact_swatch_is_high_confidence():
    r = C.classify_pad(reading("nitrate", swatch_lab("nitrate", "100")), CHART.pads["nitrate"])
    assert (r.swatch_label, r.risk, r.confidence) == ("100", C.Risk.UNSAFE, C.Confidence.HIGH)


def test_far_from_everything_is_unreadable():
    r = C.classify_pad(reading("nitrate", (20, -100, 100)), CHART.pads["nitrate"])
    assert not r.readable and "no_match" in r.flags


def test_boundary_colour_resolves_to_the_more_severe_risk():
    lo, hi = swatch_lab("nitrate", "25"), swatch_lab("nitrate", "50")   # safe | risky
    mid = tuple((a + b) / 2 for a, b in zip(lo, hi))
    r = C.classify_pad(reading("nitrate", mid), CHART.pads["nitrate"])
    assert r.risk == C.Risk.RISKY and "ambiguous" in r.flags and r.confidence == C.Confidence.LOW


def test_blotchy_pad_drops_to_low_confidence():
    r = C.classify_pad(reading("ph", swatch_lab("ph", "7.0"), spread=C.MAX_PAD_SPREAD + 5), CHART.pads["ph"])
    assert "blotchy" in r.flags and r.confidence == C.Confidence.LOW


# --- overall verdict ---------------------------------------------------------
def test_all_clear_is_safe_with_no_alert():
    a = C.classify(readings(), CHART)
    assert a.verdict == C.Verdict.SAFE and not a.alert and a.advice_keys == ()


def test_bacteria_present_is_unsafe_and_alerts():
    a = C.classify(readings(bacteria="present"), CHART)
    assert a.verdict == C.Verdict.UNSAFE and a.alert
    assert a.advice_keys == ("advice_bacteria_unsafe",)


def test_risky_nitrate_gives_risky_with_nitrate_advice():
    a = C.classify(readings(nitrate="50"), CHART)
    assert a.verdict == C.Verdict.RISKY and a.advice_keys == ("advice_nitrate_risky",)


def test_worst_pad_wins_and_advice_lists_each_faulty_pad():
    a = C.classify(readings(nitrate="100", ph="9.0"), CHART)
    assert a.verdict == C.Verdict.UNSAFE
    assert a.advice_keys == ("advice_nitrate_unsafe", "advice_ph_risky")


def test_unreadable_pad_cannot_certify_safe():
    bad = {"ph": reading("ph", (20, -100, 100))}
    a = C.classify(readings(over=bad), CHART)
    assert a.verdict == C.Verdict.RETAKE and not a.alert


def test_unsafe_pad_is_not_cancelled_by_an_unreadable_pad():
    bad = {"ph": reading("ph", (20, -100, 100))}
    a = C.classify(readings(bacteria="present", over=bad), CHART)
    assert a.verdict == C.Verdict.UNSAFE and "ph:no_match" in a.reasons


def test_low_confidence_safe_becomes_retake():
    blotchy = {"ph": reading("ph", swatch_lab("ph", "7.0"), spread=C.MAX_PAD_SPREAD + 5)}
    assert C.classify(readings(over=blotchy), CHART).verdict == C.Verdict.RETAKE


def test_missing_pad_reading_raises():
    r = readings()
    del r["bacteria"]
    with pytest.raises(C.ClassificationError) as exc:
        C.classify(r, CHART)
    assert exc.value.code == "missing_pad"


# --- chart validation --------------------------------------------------------
def _raw():
    return json.loads(CHART_PATH.read_text(encoding="utf-8"))

@pytest.mark.parametrize("mutate", [
    lambda raw: raw["pads"].pop("ph"),                                          # pads != layout.pad_order
    lambda raw: raw["pads"]["nitrate"]["swatches"][0].update(risk="fine"),      # unknown risk name
    lambda raw: raw["pads"]["nitrate"]["swatches"][0].update(lab=[500, 0, 0]),  # LAB out of range
    lambda raw: raw["pads"]["nitrate"].update(swatches=raw["pads"]["nitrate"]["swatches"][:1]),  # < 2 swatches
    lambda raw: raw["pads"]["nitrate"]["swatches"][1].update(
        label=raw["pads"]["nitrate"]["swatches"][0]["label"]),                  # duplicate label
])
def test_invalid_charts_are_rejected(mutate):
    raw = _raw()
    mutate(raw)
    with pytest.raises(C.ClassificationError) as exc:
        C.parse_chart(raw)
    assert exc.value.code == "invalid_chart"


def test_median_lab():
    assert C.median_lab([(50, 0, 0), (60, 10, 10), (55, 5, 5)]) == (55, 5, 5)
    assert C.median_lab([(50, 0, 0), (60, 10, 10)]) == (55, 5, 5)


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
