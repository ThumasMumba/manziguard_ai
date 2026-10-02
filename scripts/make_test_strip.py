"""Create a synthetic K5 strip photo from the chart's own swatch colours.

Use it to try POST /api/analyze before you have real strips. It paints a white
strip with a white reference patch and one coloured pad per chart pad.

USAGE (run from the project root, venv active):
    python scripts/make_test_strip.py test_strip.jpg
    python scripts/make_test_strip.py unsafe.jpg bacteria=present nitrate=0 ph=7.0

Each name=label pair picks which swatch to paint for that pad. Pads you don't
mention use the first swatch marked "safe". Labels must exist in the chart.
"""
import sys
from pathlib import Path

import cv2
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))   # project root

from app.services import classifier as C                           # noqa: E402
from app.services.strip_reader import _segment_bounds              # noqa: E402

CHART_PATH = Path(__file__).resolve().parent.parent / "data" / "k5_reference_chart.json"
STRIP_TOP, STRIP_HEIGHT, STRIP_X0, STRIP_X1 = 50, 800, 210, 290    # in a 500 x 900 photo


def lab_to_bgr(lab) -> tuple[int, int, int]:
    px = np.float32([[lab]])                                       # float32 LAB: L 0-100
    bgr = np.clip(cv2.cvtColor(px, cv2.COLOR_LAB2BGR)[0, 0], 0, 1)
    return tuple(int(round(v * 255)) for v in bgr)


def main(argv: list[str]) -> int:
    if not argv or "=" in argv[0]:
        print(__doc__)
        return 2
    out_path, choices = Path(argv[0]), dict(a.split("=", 1) for a in argv[1:])

    chart = C.load_chart(CHART_PATH)
    unknown = set(choices) - set(chart.pads)
    if unknown:
        print(f"Unknown pad(s): {sorted(unknown)}. Chart pads: {sorted(chart.pads)}")
        return 2

    img = np.full((900, 500, 3), 90, np.uint8)                     # grey background
    img[STRIP_TOP: STRIP_TOP + STRIP_HEIGHT, STRIP_X0:STRIP_X1] = 200   # white strip body
    ref_rows, pad_rows = _segment_bounds(chart.layout, STRIP_HEIGHT)
    r0, r1 = ref_rows
    img[STRIP_TOP + r0: STRIP_TOP + r1, STRIP_X0:STRIP_X1] = 200   # reference patch (white)

    for name, pad in chart.pads.items():
        wanted = choices.get(name)
        swatch = next((s for s in pad.swatches if s.label == wanted), None) if wanted else \
                 next(s for s in pad.swatches if s.risk == C.Risk.SAFE)
        if swatch is None:
            print(f"Pad '{name}' has no swatch '{wanted}'. Options: {[s.label for s in pad.swatches]}")
            return 2
        y0, y1 = pad_rows[name]
        img[STRIP_TOP + y0: STRIP_TOP + y1, STRIP_X0 + 10: STRIP_X1 - 10] = lab_to_bgr(swatch.lab)
        print(f"  {name:10s} -> {swatch.label} ({swatch.risk.name.lower()})")

    cv2.imwrite(str(out_path), img, [cv2.IMWRITE_JPEG_QUALITY, 95])
    print(f"Wrote {out_path.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
