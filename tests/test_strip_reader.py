"""Tests for strip_reader using synthetic strips (no real photos needed).

Run:  python -m pytest test_strip_reader.py -v     (or: python test_strip_reader.py)
"""
import cv2
import numpy as np

from app.services import strip_reader as sr

PADS = {  # BGR colours of the three synthetic pads
    "nitrate": (60, 60, 200),
    "ph": (60, 180, 60),
    "bacteria": (200, 120, 40),
}
LAYOUT = {"pad_order": list(PADS), "reference_patch": "top"}
WHITE = (200, 200, 200)  # not too bright, so a 1.2x linear tint stays below clipping


def make_photo(bg=90, reference=WHITE, bgcolour=None, h=900, w=500) -> np.ndarray:
    """White strip with a reference patch on top and 3 pads below it."""
    img = np.full((h, w, 3), bg if bgcolour is None else bgcolour, np.uint8)
    x0, x1, y0, seg = 210, 290, 50, 200
    img[y0: y0 + 4 * seg, x0:x1] = WHITE            # strip body
    img[y0: y0 + seg, x0:x1] = reference            # reference patch
    for i, bgr in enumerate(PADS.values(), start=1):
        img[y0 + i * seg: y0 + (i + 1) * seg, x0 + 10: x1 - 10] = bgr
    return img


def lin_tint(img: np.ndarray, tint=(0.8, 1.0, 1.2)) -> np.ndarray:
    """Apply a colour cast the physically correct way: multiply in linear light."""
    lin = sr.srgb_to_linear(img.astype(np.float64)) * np.array(tint)
    return np.round(sr.linear_to_srgb(lin)).astype(np.uint8)


def delta_e(a, b) -> float:
    return float(np.linalg.norm(np.subtract(a, b)))


def png(img: np.ndarray) -> bytes:
    return cv2.imencode(".png", img)[1].tobytes()


def expected_lab() -> dict:
    return {k: sr.bgr_to_lab(np.array(v)) for k, v in PADS.items()}


def test_nominal_read_matches_truth():
    got = sr.read_strip(png(make_photo()), LAYOUT)
    for name, lab in expected_lab().items():
        assert delta_e(got[name].lab, lab) < 3.0, name


def test_dark_background():
    got = sr.read_strip(png(make_photo(bg=25)), LAYOUT)
    assert set(got) == set(PADS)


def test_colour_cast_is_corrected():
    plain = sr.read_strip(png(make_photo()), LAYOUT)
    cast = sr.read_strip(png(lin_tint(make_photo())), LAYOUT)
    for name in PADS:
        assert delta_e(plain[name].lab, cast[name].lab) < 4.0, name


def test_reference_at_bottom_reads_outward_from_reference():
    flipped = make_photo()[::-1].copy()
    layout = {"pad_order": list(PADS), "reference_patch": "bottom"}
    got = sr.read_strip(png(flipped), layout)
    for name, lab in expected_lab().items():
        assert delta_e(got[name].lab, lab) < 3.0, name


def test_explicit_bounds_layout():
    # strip occupies rows 50..850 of 900; segments are 25% each of strip height
    layout = {
        "pad_order": list(PADS),
        "reference_patch": "top",
        "reference_bounds": [0.0, 0.25],
        "pad_bounds": {"nitrate": [0.25, 0.5], "ph": [0.5, 0.75], "bacteria": [0.75, 1.0]},
    }
    got = sr.read_strip(png(make_photo()), layout)
    for name, lab in expected_lab().items():
        assert delta_e(got[name].lab, lab) < 3.0, name


def _code(fn) -> str:
    try:
        fn()
    except sr.StripReadError as exc:
        return exc.code
    return "no_error"


def test_error_codes():
    assert _code(lambda: sr.decode_image(b"")) == "no_image_data"
    assert _code(lambda: sr.decode_image(b"not an image")) == "not_an_image"
    assert _code(lambda: sr.decode_image(png(np.zeros((100, 100, 3), np.uint8)))) == "image_too_small"
    dim = (make_photo().astype(np.float64) * 0.25).astype(np.uint8)  # whole photo underexposed
    assert _code(lambda: sr.read_strip(png(dim), LAYOUT)) == "too_dark"
    assert _code(lambda: sr.read_strip(png(make_photo(reference=(255, 255, 255))), LAYOUT)) == "overexposed"
    blank = np.full((900, 500, 3), 120, np.uint8)
    assert _code(lambda: sr.read_strip(png(blank), LAYOUT)) == "strip_not_found"
    assert _code(lambda: sr.validate_layout({"pad_order": []})) == "invalid_layout"


def test_strong_colour_cast_rejected():
    ref = (235, 235, 40)  # reference patch is nowhere near neutral
    assert _code(lambda: sr.read_strip(png(make_photo(reference=ref)), LAYOUT)) == "colour_cast_too_strong"


if __name__ == "__main__":
    for name, fn in sorted(globals().items()):
        if name.startswith("test_"):
            fn()
            print("[OK] ", name)
