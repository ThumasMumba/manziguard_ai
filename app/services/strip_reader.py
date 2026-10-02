"""Read pad colours from a photo of a K5 strip using OpenCV.

PIPELINE
    bytes -> decode_image -> resize to a standard height -> isolate_strip_region
          -> slice into reference patch + pads -> white-balance against the
          reference patch (in linear light) -> median colour per pad -> CIELAB

ASSUMPTIONS (v1)
    * The strip is photographed vertically inside the guide frame shown by the
      web app, with a white/grey reference patch at one end.
    * Pad layout comes from data/k5_reference_chart.json -> "layout":

        {
          "pad_order": ["nitrate", "ph", "bacteria"],   # listed starting NEXT TO
                                                         # the reference patch
          "reference_patch": "top",                      # or "bottom"

          # OPTIONAL, recommended once you have measured a real strip.
          # Fractions (0..1) of the strip height, measured from the TOP:
          "reference_bounds": [0.00, 0.18],
          "pad_bounds": {"nitrate": [0.22, 0.38], "ph": [0.42, 0.58], "bacteria": [0.62, 0.78]}
        }

      Without the optional bounds, the strip is cut into equal slices.

ERROR CODES (map each to an i18n `err_*` key in English, Bemba and Nyanja)
    no_image_data, image_too_large, not_an_image, image_too_small,
    strip_not_found, strip_too_small, invalid_segment_size, too_dark,
    overexposed, reference_uneven, colour_cast_too_strong, invalid_layout
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any
import cv2
import numpy as np

log = logging.getLogger(__name__)

MAX_IMAGE_BYTES = 5 * 1024 * 1024   # reject huge uploads before decoding (server safety)
MIN_IMAGE_SIDE_PX = 200              # smaller photos cannot resolve the pads
NORMALISED_HEIGHT_PX = 900           # every photo is resized to this height
MIN_STRIP_HEIGHT_PX = 360            # strip crop must be at least this tall after resizing
MIN_STRIP_HEIGHT_FRAC = 0.4          # strip must span >= 40% of the photo height
MIN_STRIP_ASPECT = 2.0               # height/width of the strip bounding box
CORE_FRACTION = 0.5                  # central share of each pad that is sampled
MIN_REF_BRIGHTNESS = 60.0            # reference patch mean (0-255) below this = too dark
SATURATION_LEVEL = 250.0             # any reference channel above this = clipped
MAX_REF_SPREAD = 20.0                # reference patch unevenness (shadow / glare)
MAX_GAIN = 2.5                       # strongest allowed per-channel correction


class StripReadError(ValueError):
    """Raised with a short machine-readable code (see i18n `err_*` keys).

    The code is what the web layer translates for the user; the message is for
    developers and logs.
    """
    
    #Initialize the StripReadError class with a code and an optional message.
    def __init__(self, code: str, message: str | None = None):
        #Call the superclass constructor with the message or code.
        super().__init__(message or code)
        self.code = code


@dataclass(frozen=True)
class PadReading:
    """Parsed colour data for a single reagent pad.

    lab    -- CIELAB (L 0-100, a/b roughly -128..127) after white balancing
    bgr    -- white-balanced 8-bit BGR (handy for drawing swatches in the UI)
    spread -- how uneven the pad was inside the sampled core (mean absolute
              deviation, 8-bit units). A large value means a blotchy pad,
              glare or a shadow, so downstream code should trust it less.
    """

    name: str
    lab: tuple[float, float, float]
    bgr: tuple[int, int, int]
    spread: float = 0.0


# ---------------------------------------------------------------------------
# Layout handling
# ---------------------------------------------------------------------------
def load_layout(path: str | Path) -> dict[str, Any]:
    """Load data/k5_reference_chart.json and return its validated "layout"."""
    with open(path, encoding="utf-8") as fh:
        layout = json.load(fh)["layout"]
    validate_layout(layout)
    return layout


def validate_layout(layout: dict[str, Any]) -> None:
    """Fail early (and clearly) if the chart JSON is malformed."""
    order = layout.get("pad_order")
    if not isinstance(order, list) or not order or len(set(order)) != len(order):
        raise StripReadError("invalid_layout", "pad_order must be a non-empty list of unique names")
    if layout.get("reference_patch", "top") not in ("top", "bottom"):
        raise StripReadError("invalid_layout", "reference_patch must be 'top' or 'bottom'")

    explicit = [k for k in ("reference_bounds", "pad_bounds") if k in layout]
    if explicit and len(explicit) != 2:
        raise StripReadError("invalid_layout", "give both reference_bounds and pad_bounds, or neither")
    if explicit:
        bounds = [layout["reference_bounds"], *layout["pad_bounds"].values()]
        if set(layout["pad_bounds"]) != set(order):
            raise StripReadError("invalid_layout", "pad_bounds keys must match pad_order")
        for lo, hi in bounds:
            if not (0.0 <= lo < hi <= 1.0):
                raise StripReadError("invalid_layout", f"bad bounds [{lo}, {hi}]")


def _segment_bounds(layout: dict[str, Any], strip_h: int) -> tuple[tuple[int, int], dict[str, tuple[int, int]]]:
    """Return (reference_rows, {pad_name: rows}) as pixel row ranges in the strip crop."""
    order = list(layout["pad_order"])

    if "pad_bounds" in layout:  # explicit, measured positions (best)
        def to_px(frac: list[float]) -> tuple[int, int]:
            y0 = int(frac[0] * strip_h)
            y1 = max(y0 + 1, int(frac[1] * strip_h))
            return y0, y1

        return to_px(layout["reference_bounds"]), {n: to_px(layout["pad_bounds"][n]) for n in order}

    # Fallback: equal slices. Slice 0 is the reference patch, then the pads in
    # pad_order. If the reference is at the bottom, the physical order is
    # flipped so pad_order still reads outward from the reference patch.
    n_segments = len(order) + 1
    seg_h = strip_h // n_segments
    at_bottom = layout.get("reference_patch", "top") == "bottom"

    def rows(i: int) -> tuple[int, int]:
        k = (n_segments - 1 - i) if at_bottom else i
        return k * seg_h, (k + 1) * seg_h

    return rows(0), {name: rows(i + 1) for i, name in enumerate(order)}


# ---------------------------------------------------------------------------
# Image decoding and strip detection
# ---------------------------------------------------------------------------
def decode_image(data: bytes) -> np.ndarray:
    """Decode uploaded bytes into a BGR image, rejecting unusable input."""
    if not data:
        log.warning("No image data provided")
        raise StripReadError("no_image_data")
    if len(data) > MAX_IMAGE_BYTES:
        log.warning("Image upload too large: %d bytes", len(data))
        raise StripReadError("image_too_large")

    img = cv2.imdecode(np.frombuffer(data, np.uint8), cv2.IMREAD_COLOR)
    if img is None:
        log.warning("Failed to decode image")
        raise StripReadError("not_an_image")

    h, w = img.shape[:2]
    if min(h, w) < MIN_IMAGE_SIDE_PX:
        log.warning("Image too small: %dx%d", w, h)
        raise StripReadError("image_too_small")
    return img


def isolate_strip_region(img: np.ndarray, allow_fallback: bool = False) -> np.ndarray:
    """Locate and crop the vertical test strip.

    Otsu thresholding separates strip from background, but we do not know
    whether the strip is lighter or darker than the table it lies on, so BOTH
    polarities are tried. A morphological close then glues the strip back
    together, because coloured pads would otherwise split it into blobs.

    If nothing strip-shaped is found we raise `strip_not_found` (the user
    retakes the photo) rather than silently reading background colours.
    `allow_fallback=True` restores the old centre-crop for debugging only.
    """
    h, w = img.shape[:2]
    gray = cv2.GaussianBlur(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), (5, 5), 0)
    kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (15, 41))

    best: tuple[int, int, int, int] | None = None
    for mode in (cv2.THRESH_BINARY, cv2.THRESH_BINARY_INV):
        _, thresh = cv2.threshold(gray, 0, 255, mode + cv2.THRESH_OTSU)
        thresh = cv2.morphologyEx(thresh, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        for c in contours:
            x, y, cw, ch = cv2.boundingRect(c)
            if cw == 0:
                continue
            centred = 0.2 * w < x + cw / 2 < 0.8 * w
            tall_enough = ch >= MIN_STRIP_HEIGHT_FRAC * h
            if ch / cw >= MIN_STRIP_ASPECT and centred and tall_enough:
                if best is None or cw * ch > best[2] * best[3]:
                    best = (x, y, cw, ch)

    if best is None:
        log.warning("No strip-shaped contour found")
        if allow_fallback:
            return img[:, int(w * 0.35): int(w * 0.65)]
        raise StripReadError("strip_not_found")

    x, y, cw, ch = best
    log.info("Isolated strip at x=%d y=%d w=%d h=%d", x, y, cw, ch)
    return img[y: y + ch, x: x + cw]


# ---------------------------------------------------------------------------
# Colour maths
# ---------------------------------------------------------------------------
def core_pixels(segment: np.ndarray) -> np.ndarray:
    """Return the central CORE_FRACTION of a segment as an (N, 3) float array.

    Sampling only the core avoids edge bleed, pad borders and glints.
    """
    h, w = segment.shape[:2]
    if h == 0 or w == 0:
        raise StripReadError("invalid_segment_size", "Segment dimension collapsed to zero")

    m = (1.0 - CORE_FRACTION) / 2.0
    core = segment[int(h * m): int(h * (1 - m)), int(w * m): int(w * (1 - m))]
    if core.size == 0:
        core = segment  # tiny segment: use all of it
    return core.reshape(-1, 3).astype(np.float64)


def median_bgr(segment: np.ndarray) -> np.ndarray:
    """Median BGR of the segment's core (median ignores specular outliers)."""
    return np.median(core_pixels(segment), axis=0)


def spread(segment: np.ndarray) -> float:
    """Mean absolute deviation of the core around its median (8-bit units)."""
    pix = core_pixels(segment)
    return float(np.median(np.abs(pix - np.median(pix, axis=0)), axis=0).mean())


def srgb_to_linear(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64) / 255.0
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def linear_to_srgb(v: np.ndarray) -> np.ndarray:
    v = np.clip(v, 0.0, 1.0)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * v ** (1 / 2.4) - 0.055) * 255.0


def bgr_to_lab(bgr: np.ndarray) -> tuple[float, float, float]:
    """Convert one 8-bit-range BGR colour to CIELAB.

    A float32 image in 0..1 makes OpenCV return true CIELAB directly (L 0-100),
    so no re-normalizing and no 8-bit rounding.
    """
    pixel = np.float32([[np.clip(np.asarray(bgr, dtype=np.float64), 0, 255) / 255.0]])
    l_val, a_val, b_val = cv2.cvtColor(pixel, cv2.COLOR_BGR2LAB)[0, 0].astype(float)
    return (round(l_val, 2), round(a_val, 2), round(b_val, 2))


# ---------------------------------------------------------------------------
# Main entry points
# ---------------------------------------------------------------------------
def read_pad_colours(img: np.ndarray, layout: dict[str, Any]) -> dict[str, PadReading]:
    """Extract and white-balance the colour of every pad against the reference patch."""
    validate_layout(layout)

    # 1. Standardize height so pixel-based constants mean the same on any phone.
    h, w = img.shape[:2]
    scale = NORMALISED_HEIGHT_PX / h
    resized = cv2.resize(img, (max(1, int(w * scale)), NORMALISED_HEIGHT_PX), interpolation=cv2.INTER_AREA)

    # 2. Find the strip.
    strip = isolate_strip_region(resized)
    strip_h = strip.shape[0]
    if strip_h < MIN_STRIP_HEIGHT_PX:
        raise StripReadError("strip_too_small", f"Strip crop only {strip_h}px tall")

    # 3. Slice into reference patch + pads.
    ref_rows, pad_rows = _segment_bounds(layout, strip_h)
    ref_seg = strip[ref_rows[0]: ref_rows[1]]

    # 4. Quality gates on the reference patch.
    ref_bgr = median_bgr(ref_seg)
    ref_mean = float(ref_bgr.mean())
    if ref_mean < MIN_REF_BRIGHTNESS:
        raise StripReadError("too_dark", f"Reference patch too dark ({ref_mean:.1f})")
    if ref_bgr.max() > SATURATION_LEVEL:
        raise StripReadError("overexposed", "A reference channel is clipped")
    if spread(ref_seg) > MAX_REF_SPREAD:
        raise StripReadError("reference_uneven", "Shadow or glare across the reference patch")

    # 5. White balance in LINEAR light. Light is multiplicative in linear
    #    space, so per-channel gains there remove a colour cast correctly; in
    #    gamma space the same gains would distort mid-tones. The gains map the
    #    reference to neutral grey at its own average brightness.
    ref_lin = np.maximum(srgb_to_linear(ref_bgr), 1e-4)
    gains = ref_lin.mean() / ref_lin
    if gains.max() > MAX_GAIN:
        raise StripReadError("colour_cast_too_strong", f"Gains {np.round(gains, 2)} exceed {MAX_GAIN}")
    log.debug("White-balance gains (BGR): %s", gains)

    # 6. Read each pad.
    results: dict[str, PadReading] = {}
    for name, (y0, y1) in pad_rows.items():
        seg = strip[y0:y1]
        raw_bgr = median_bgr(seg)
        calibrated = linear_to_srgb(srgb_to_linear(raw_bgr) * gains)
        results[name] = PadReading(
            name=name,
            lab=bgr_to_lab(calibrated),
            bgr=tuple(int(round(v)) for v in calibrated),  # type: ignore[arg-type]
            spread=round(spread(seg), 2),
        )
    return results


def read_strip(data: bytes, layout: dict[str, Any]) -> dict[str, PadReading]:
    """Convenience wrapper: uploaded bytes in, pad readings out."""
    return read_pad_colours(decode_image(data), layout)
