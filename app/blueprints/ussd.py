"""USSD webhook.

Written for the common gateway convention: POST form fields `sessionId`, `phoneNumber`,
`text` (the user's choices joined by '*'); reply body starts with `CON ` (continue) or
`END ` (finish). Adapt field names if the MTN/aggregator format differs.

Privacy: the phone number is never read or stored.
"""
import hmac

from flask import Blueprint, Response, abort, current_app, request

from ..extensions import csrf, limiter
from ..services.i18n import PAD_LABELS, t
from ..services.pipeline import assess_and_record

bp = Blueprint("ussd", __name__, url_prefix="/ussd")
csrf.exempt(bp)  # gateway calls carry no CSRF token; a shared secret is checked instead

LANGS = {"1": "en", "2": "bem", "3": "nya"}


def _check_secret():
    expected = current_app.config["USSD_SHARED_SECRET"]
    if not expected:
        if not current_app.config.get("DEBUG") and not current_app.config.get("TESTING"):
            abort(503)  # refuse to run open in production
        return
    supplied = request.headers.get("X-Webhook-Secret", "") or request.args.get("secret", "")
    if not hmac.compare_digest(supplied, expected):
        abort(403)


def _menu(chart, pad: str, lang: str) -> str:
    levels = chart["pads"][pad]["levels"]
    lines = [t("ussd_pad_prompt", lang, pad=PAD_LABELS[pad])]
    lines += [f"{i}. {lv['label']}" for i, lv in enumerate(levels, 1)]
    return "CON " + "\n".join(lines)


@bp.post("")
@limiter.limit("60 per minute")
def handle():
    _check_secret()
    chart = current_app.extensions["manzi_chart"]
    if current_app.config["REQUIRE_CALIBRATED_CHART"] and not chart.get("calibrated"):
        return Response("END " + t("err_not_calibrated"), mimetype="text/plain")

    steps = [s for s in (request.form.get("text", "") or "").split("*")] if request.form.get("text") else []
    pads = chart["layout"]["pad_order"]

    def bad(lang="en"):
        return Response("END " + t("ussd_invalid", lang), mimetype="text/plain")

    if not steps:
        return Response("CON " + t("ussd_language"), mimetype="text/plain")
    if steps[0] not in LANGS:
        return bad()
    lang = LANGS[steps[0]]

    readings = {}
    for idx, pad in enumerate(pads, start=1):
        if len(steps) <= idx:
            return Response(_menu(chart, pad, lang), mimetype="text/plain")
        levels = chart["pads"][pad]["levels"]
        if not steps[idx].isdigit() or not 1 <= int(steps[idx]) <= len(levels):
            return bad(lang)
        readings[pad] = levels[int(steps[idx]) - 1]["value"]
    readings["bacteria"] = bool(readings.get("bacteria"))

    district_idx = len(pads) + 1
    if len(steps) <= district_idx:
        return Response("CON " + t("ussd_district", lang), mimetype="text/plain")
    district = steps[district_idx].strip()[:64]

    sample, assessment, alert_status = assess_and_record(
        readings, channel="ussd", language=lang, district=district)
    body = t("ussd_result", lang, result=t(f"result_{assessment.level}", lang),
             advice=t(f"advice_{assessment.level}", lang))
    if alert_status:
        body += " " + t({"sent": "alert_sent", "no_responder": "alert_no_responder",
                         "no_location": "alert_no_location", "failed": "alert_failed"}[alert_status], lang)
    return Response("END " + body, mimetype="text/plain")
