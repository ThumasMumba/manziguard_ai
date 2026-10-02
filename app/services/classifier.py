"""Classify K5 strip pad colours into a water-safety verdict.

INPUT   {pad_name: PadReading} from strip_reader.read_pad_colours (white-balanced LAB)
OUTPUT  Assessment: SAFE / RISKY / UNSAFE / RETAKE, per-pad detail, i18n advice keys

HOW IT DECIDES
    1. Each pad's colour is compared with that pad's reference swatches using
       CIEDE2000 (a distance that tracks how different two colours *look*).
    2. The nearest swatch gives the pad's risk level.
    3. Uncertainty always resolves toward caution, never toward "Safe":
         * nearest two swatches have different risks and are almost equally
           close  -> take the MORE severe risk, confidence LOW
         * no swatch is close enough          -> pad is unreadable
         * blotchy pad (glare, shadow, bad dip) -> confidence LOW
    4. The overall verdict is the worst pad, with these rules:
         * any readable pad UNSAFE            -> UNSAFE (a missing pad cannot cancel it)
         * otherwise any unreadable pad       -> RETAKE (we cannot certify Safe)
         * otherwise any LOW-confidence Safe  -> RETAKE
         * otherwise worst of RISKY / SAFE

CHART FILE (data/k5_reference_chart.json), see k5_reference_chart.example.json
    {
      "layout": {...as strip_reader...},
      "pads": {
        "nitrate": {
          "label": "Nitrate", "unit": "mg/L NO3",
          "max_match_de": 15.0,                         # optional per-pad override
          "advice": {"risky": "advice_nitrate_risky",   # optional i18n keys
                     "unsafe": "advice_nitrate_unsafe"},
          "swatches": [{"label": "0", "lab": [94, 2, 4], "risk": "safe"}, ...]
        }
      }
    }

IMPORTANT: swatch LAB values must come from YOUR pipeline (photograph strips
dipped in known standards and run them through strip_reader), not from
eyeballing the printed chart. See `median_lab` below.
"""
from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from pathlib import Path
from typing import Any, Mapping, Sequence

from app.services.strip_reader import PadReading, read_strip

log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tunables (calibrate with real photos; see the notes delivered with this file)
# ---------------------------------------------------------------------------
DEFAULT_MAX_MATCH_DE = 15.0   # beyond this from every swatch, the pad is unreadable
GOOD_MATCH_DE = 6.0           # at or below this (and unambiguous) -> HIGH confidence
AMBIGUITY_MARGIN = 3.0        # nearest different-risk swatch closer than best+this -> ambiguous
MAX_PAD_SPREAD = 20.0         # PadReading.spread above this -> blotchy -> LOW confidence
K_L = 1.0                     # CIEDE2000 lightness weight; raise (e.g. 2.0) if phone exposure varies a lot


class ClassificationError(ValueError):
    """Bad chart or mismatch between chart and readings. `code` is machine-readable."""

    def __init__(self, code: str, message: str | None = None):
        super().__init__(message or code)
        self.code = code


class Risk(IntEnum):
    """Ordered so that max() gives the most severe risk."""
    SAFE = 0
    RISKY = 1
    UNSAFE = 2


class Confidence(IntEnum):
    LOW = 0
    MEDIUM = 1
    HIGH = 2


class Verdict(str, Enum):
    """Values double as i18n keys: verdict_safe, verdict_risky, ..."""
    SAFE = "safe"
    RISKY = "risky"
    UNSAFE = "unsafe"
    RETAKE = "retake"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Swatch:
    label: str
    lab: tuple[float, float, float]
    risk: Risk


@dataclass(frozen=True)
class PadChart:
    name: str
    label: str
    unit: str
    swatches: tuple[Swatch, ...]
    max_match_de: float = DEFAULT_MAX_MATCH_DE
    advice: Mapping[Risk, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Chart:
    layout: dict[str, Any]
    pads: dict[str, PadChart]


@dataclass(frozen=True)
class PadResult:
    name: str
    readable: bool
    swatch_label: str | None
    risk: Risk | None
    delta_e: float
    margin: float | None            # gap to the nearest different-risk swatch (None = none exists)
    confidence: Confidence
    flags: tuple[str, ...] = ()     # "no_match", "ambiguous", "blotchy"


@dataclass(frozen=True)
class Assessment:
    verdict: Verdict
    pads: dict[str, PadResult]
    advice_keys: tuple[str, ...]    # i18n keys for the pads that triggered advice
    alert: bool                     # True -> send the CHW / WASH officer SMS
    low_confidence: bool            # True -> UI should recommend re-testing to confirm
    reasons: tuple[str, ...]        # e.g. "nitrate:no_match" for logs and the dashboard


# ---------------------------------------------------------------------------
# CIEDE2000 (Sharma, Wu & Dalal 2005), implemented directly to avoid a
# scikit-image dependency on the server.
# ---------------------------------------------------------------------------
def delta_e_2000(lab1: Sequence[float], lab2: Sequence[float],
                 k_l: float = 1.0, k_c: float = 1.0, k_h: float = 1.0) -> float:
    L1, a1, b1 = lab1
    L2, a2, b2 = lab2

    c1, c2 = math.hypot(a1, b1), math.hypot(a2, b2)
    c_bar7 = ((c1 + c2) / 2.0) ** 7
    g = 0.5 * (1.0 - math.sqrt(c_bar7 / (c_bar7 + 25.0 ** 7)))
    a1p, a2p = (1.0 + g) * a1, (1.0 + g) * a2
    c1p, c2p = math.hypot(a1p, b1), math.hypot(a2p, b2)

    def hue(b: float, ap: float) -> float:
        return math.degrees(math.atan2(b, ap)) % 360.0 if (b or ap) else 0.0

    h1p, h2p = hue(b1, a1p), hue(b2, a2p)

    d_lp = L2 - L1
    d_cp = c2p - c1p
    if c1p * c2p == 0.0:
        d_hp_deg = 0.0
    else:
        d_hp_deg = h2p - h1p
        if d_hp_deg > 180.0:
            d_hp_deg -= 360.0
        elif d_hp_deg < -180.0:
            d_hp_deg += 360.0
    d_hp = 2.0 * math.sqrt(c1p * c2p) * math.sin(math.radians(d_hp_deg) / 2.0)

    l_bar = (L1 + L2) / 2.0
    c_barp = (c1p + c2p) / 2.0
    if c1p * c2p == 0.0:
        h_barp = h1p + h2p
    elif abs(h1p - h2p) <= 180.0:
        h_barp = (h1p + h2p) / 2.0
    elif h1p + h2p < 360.0:
        h_barp = (h1p + h2p + 360.0) / 2.0
    else:
        h_barp = (h1p + h2p - 360.0) / 2.0

    t = (1.0
         - 0.17 * math.cos(math.radians(h_barp - 30.0))
         + 0.24 * math.cos(math.radians(2.0 * h_barp))
         + 0.32 * math.cos(math.radians(3.0 * h_barp + 6.0))
         - 0.20 * math.cos(math.radians(4.0 * h_barp - 63.0)))
    d_theta = 30.0 * math.exp(-(((h_barp - 275.0) / 25.0) ** 2))
    r_c = 2.0 * math.sqrt(c_barp ** 7 / (c_barp ** 7 + 25.0 ** 7))
    s_l = 1.0 + 0.015 * (l_bar - 50.0) ** 2 / math.sqrt(20.0 + (l_bar - 50.0) ** 2)
    s_c = 1.0 + 0.045 * c_barp
    s_h = 1.0 + 0.015 * c_barp * t
    r_t = -math.sin(math.radians(2.0 * d_theta)) * r_c

    tl, tc, th = d_lp / (k_l * s_l), d_cp / (k_c * s_c), d_hp / (k_h * s_h)
    return math.sqrt(tl * tl + tc * tc + th * th + r_t * tc * th)


# ---------------------------------------------------------------------------
# Chart loading and validation
# ---------------------------------------------------------------------------
def _parse_risk(value: Any, where: str) -> Risk:
    try:
        return Risk[str(value).upper()]
    except KeyError:
        raise ClassificationError("invalid_chart", f"{where}: risk must be safe/risky/unsafe, got {value!r}") from None


def parse_chart(raw: dict[str, Any]) -> Chart:
    """Validate a decoded chart JSON and convert it to typed objects."""
    layout, raw_pads = raw.get("layout"), raw.get("pads")
    if not isinstance(layout, dict) or not isinstance(raw_pads, dict) or not raw_pads:
        raise ClassificationError("invalid_chart", "chart needs 'layout' and a non-empty 'pads'")
    if set(raw_pads) != set(layout.get("pad_order", [])):
        raise ClassificationError("invalid_chart", "pads must match layout.pad_order exactly")

    pads: dict[str, PadChart] = {}
    for name, p in raw_pads.items():
        swatches: list[Swatch] = []
        seen: set[str] = set()
        for s in p.get("swatches", []):
            label = str(s.get("label", ""))
            lab = tuple(float(v) for v in s.get("lab", ()))
            if not label or label in seen:
                raise ClassificationError("invalid_chart", f"{name}: swatch labels must be unique and non-empty")
            if len(lab) != 3 or not (0 <= lab[0] <= 100 and all(-128 <= v <= 127 for v in lab[1:])):
                raise ClassificationError("invalid_chart", f"{name}/{label}: bad LAB {lab}")
            seen.add(label)
            swatches.append(Swatch(label, lab, _parse_risk(s.get("risk"), f"{name}/{label}")))  # type: ignore[arg-type]
        if len(swatches) < 2:
            raise ClassificationError("invalid_chart", f"{name}: need at least 2 swatches")

        advice = {_parse_risk(k, f"{name}.advice"): str(v) for k, v in p.get("advice", {}).items()}
        pads[name] = PadChart(
            name=name,
            label=str(p.get("label", name)),
            unit=str(p.get("unit", "")),
            swatches=tuple(swatches),
            max_match_de=float(p.get("max_match_de", DEFAULT_MAX_MATCH_DE)),
            advice=advice,
        )
    return Chart(layout=layout, pads=pads)


def load_chart(path: str | Path) -> Chart:
    with open(path, encoding="utf-8") as fh:
        return parse_chart(json.load(fh))


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------
def classify_pad(reading: PadReading, pad: PadChart) -> PadResult:
    """Compare one pad's colour with its reference swatches."""
    scored = sorted(((delta_e_2000(reading.lab, s.lab, k_l=K_L), s) for s in pad.swatches),
                    key=lambda t: t[0])
    best_de, best = scored[0]

    if best_de > pad.max_match_de:
        log.warning("Pad %s matches no swatch (best dE=%.1f)", pad.name, best_de)
        return PadResult(pad.name, False, None, None, round(best_de, 2), None,
                         Confidence.LOW, ("no_match",))

    flags: list[str] = []
    risk = best.risk

    # Nearest swatch whose RISK differs: only those make a decision uncertain.
    rival = next(((d, s) for d, s in scored[1:] if s.risk != best.risk), None)
    margin = (rival[0] - best_de) if rival else None

    if rival and margin < AMBIGUITY_MARGIN:
        risk = max(best.risk, rival[1].risk)      # resolve toward caution
        flags.append("ambiguous")
        confidence = Confidence.LOW
    elif best_de <= GOOD_MATCH_DE:
        confidence = Confidence.HIGH
    else:
        confidence = Confidence.MEDIUM

    if reading.spread > MAX_PAD_SPREAD:
        flags.append("blotchy")
        confidence = Confidence.LOW

    return PadResult(pad.name, True, best.label, risk, round(best_de, 2),
                     None if margin is None else round(margin, 2), confidence, tuple(flags))


def classify(readings: Mapping[str, PadReading], chart: Chart) -> Assessment:
    """Combine all pads into one verdict (see module docstring for the rules)."""
    missing = set(chart.pads) - set(readings)
    if missing:
        raise ClassificationError("missing_pad", f"no reading for: {sorted(missing)}")

    results = {name: classify_pad(readings[name], pad) for name, pad in chart.pads.items()}
    readable = [r for r in results.values() if r.readable]
    unreadable = [r for r in results.values() if not r.readable]
    worst = max((r.risk for r in readable), default=None)

    reasons = tuple(f"{r.name}:{f}" for r in results.values() for f in r.flags)

    if worst == Risk.UNSAFE:
        verdict = Verdict.UNSAFE
    elif unreadable or worst is None:
        verdict = Verdict.RETAKE
    elif worst == Risk.SAFE and any(r.confidence == Confidence.LOW for r in readable):
        verdict = Verdict.RETAKE
    elif worst == Risk.RISKY:
        verdict = Verdict.RISKY
    else:
        verdict = Verdict.SAFE

    # Advice comes from the pads that are actually at fault, because the right
    # action differs by hazard (e.g. boiling does not remove nitrate).
    advice: list[str] = []
    if verdict in (Verdict.RISKY, Verdict.UNSAFE):
        for r in readable:
            key = chart.pads[r.name].advice.get(r.risk) if r.risk and r.risk > Risk.SAFE else None
            if key and key not in advice:
                advice.append(key)

    driving = [r for r in readable if r.risk == worst]
    low_conf = verdict == Verdict.RETAKE or any(r.confidence == Confidence.LOW for r in driving)

    return Assessment(verdict=verdict, pads=results, advice_keys=tuple(advice),
                      alert=verdict == Verdict.UNSAFE, low_confidence=low_conf, reasons=reasons)


def assess_photo(data: bytes, chart: Chart) -> Assessment:
    """Uploaded photo bytes in, Assessment out. StripReadError means: ask for a retake."""
    return classify(read_strip(data, chart.layout), chart)


# ---------------------------------------------------------------------------
# Calibration helper
# ---------------------------------------------------------------------------
def median_lab(labs: Sequence[Sequence[float]]) -> tuple[float, float, float]:
    """Median LAB over many readings of ONE standard (different photos/phones/light).

    Photograph a strip dipped in each known standard 20+ times, run every photo
    through strip_reader, collect each pad's `lab`, and pass them here. Paste the
    result into the chart JSON as that swatch's LAB. Also look at the spread of
    the inputs: it tells you how far apart two swatches must be to be separable.
    """
    if not labs:
        raise ValueError("no readings supplied")
    cols = list(zip(*labs))
    mid = [sorted(c)[len(c) // 2] if len(c) % 2 else sum(sorted(c)[len(c) // 2 - 1: len(c) // 2 + 1]) / 2
           for c in cols]
    return (round(mid[0], 2), round(mid[1], 2), round(mid[2], 2))
