"""User-facing messages for the analysis API, keyed for translation.

HOW TO ADD A LANGUAGE
    Fill the "bem" (Bemba) and "nya" (Nyanja) dictionaries below with the SAME
    keys as "en". Until a key is translated, the English text is shown, so the
    app never displays a raw key.

IMPORTANT
    * Health and safety wording must be written or reviewed by native speakers
      AND a health professional. Do not machine-translate the advice_* and
      verdict_* entries.
    * Every advice_* text below is a DRAFT for review, not approved guidance.
"""
from __future__ import annotations

SUPPORTED_LANGUAGES = ("en", "bem", "nya")
LANGUAGE_ALIASES = {"ny": "nya", "chichewa": "nya"}

MESSAGES: dict[str, dict[str, str]] = {
    "en": {
        # ---- photo / upload problems (user can fix by retaking) -------------
        "err_no_image_data": "No photo was received. Please take a photo of the test strip and try again.",
        "err_unsupported_type": "Please upload a JPEG, PNG or WebP photo.",
        "err_image_too_large": "The photo is too large. Please take it again at a lower quality or resolution.",
        "err_not_an_image": "We could not open this file as a photo. Please take a new photo.",
        "err_image_too_small": "The photo is too small. Move closer so the strip fills the guide frame.",
        "err_strip_not_found": "We could not find the strip. Place it upright inside the guide frame, on a plain surface, and try again.",
        "err_strip_too_small": "The strip looks too small in the photo. Move closer so it fills the guide frame.",
        "err_invalid_segment_size": "The strip could not be read. Please retake the photo with the whole strip in the frame.",
        "err_too_dark": "The photo is too dark. Move somewhere brighter, out of the shade, and try again.",
        "err_overexposed": "The photo is too bright or has glare. Move out of direct sun and avoid shiny reflections.",
        "err_reference_uneven": "There is a shadow or glare on the white patch. Hold the phone steady and keep shadows off the strip.",
        "err_colour_cast_too_strong": "The colour of the light is too strong. Use daylight or plain white light and try again.",
        "err_unreadable": "We could not read this photo. Please retake it.",
        # ---- service problems ------------------------------------------------
        "err_rate_limited": "Too many tests in a short time. Please wait a minute and try again.",
        "err_server": "Something went wrong on our side. Please try again.",
        # ---- verdicts --------------------------------------------------------
        "verdict_safe": "Safe",
        "verdict_risky": "Risky",
        "verdict_unsafe": "Unsafe",
        "verdict_retake": "Please retake the photo",
        "verdict_safe_detail": "No problems were found on this strip. This is a screening test, not a laboratory result.",
        "verdict_risky_detail": "One or more results are outside the recommended range. See the advice below.",
        "verdict_unsafe_detail": "Do not drink this water until a health worker has advised you.",
        "verdict_retake_detail": "We could not read every result clearly, so we cannot say the water is safe. Please retake the photo.",
        # ---- per-pad hints ---------------------------------------------------
        "hint_no_match": "A pad could not be read clearly.",
        "hint_ambiguous": "A result was close to the line between two levels, so the more cautious level was used.",
        "hint_blotchy": "A pad looked uneven (glare, shadow or uneven dipping).",
        # ---- notices ---------------------------------------------------------
        "prototype_notice": "Prototype: results are for demonstration and have not been validated.",
        # ---- advice (DRAFT: needs health-professional review) -----------------
        "advice_nitrate_risky": "Nitrate is higher than recommended. Do not use this water for infant feeding or formula. Boiling does not remove nitrate.",
        "advice_nitrate_unsafe": "Nitrate is too high. Do not give this water to infants or pregnant women, and do not boil it to make it safe, because boiling makes nitrate stronger. Use another water source and tell your health worker.",
        "advice_ph_risky": "The pH is outside the recommended range (6.5 to 8.5). Ask your health or water officer for advice.",
        "advice_bacteria_unsafe": "Germs were detected. Do not drink this water untreated. Bring it to a rolling boil, or treat it with chlorine, and tell your Community Health Worker.",
    },
    "bem": {
                # ---- ifoto / amafya ya upload (umukuta kuti ayalungule ukupitila mukutwala ifoto nakabili) -------------
        "err_no_image_data": "Tatusambilile ifoto. Tafweni ifoto ya strip ya test kabili yesheni nakabili.",
        "err_unsupported_type": "Tafweni ifoto ya JPEG, PNG nangu WebP.",
        "err_image_too_large": "Ifoto ninkalamba sana. Tafweni nakabili na quality nangu resolution ipeela.",
        "err_not_an_image": "Tatuswike ukusegula iyi file ngaifoto. Tafweni ifoto ipeya.",
        "err_image_too_small": "Ifoto ninkache sana. Sendekeni pafupi ukuti strip ikule guide frame.",
        "err_strip_not_found": "Tatuswike ukusanga strip. Ikani strip kwima mukati ka guide frame, pa cintu cisa, kabili yesheni nakabili.",
        "err_strip_too_small": "Strip ilolesha nga nkache mu foto. Sendekeni pafupi ukuti ikule guide frame.",
        "err_invalid_segment_size": "Tatuswike ukubelenga strip. Tafweni nakabili, ukuti strip yonse ibe mukati ka frame.",
        "err_too_dark": "Ifoto ninkati sana. Yendeni pa cifulo ca kuwala, panuma ya mfwili, kabili yesheni nakabili.",
        "err_overexposed": "Ifoto ninkati sana nangu ikalalika. Fumeni pa kuwala kwa direct sun kabili taleni ukulondolola kwa kuwala pa strip.",
        "err_reference_uneven": "Kuli mfwili nangu kuwalilika pa cifulo cisa. Katileni phone bwino kabili taleni mfwili ukwikala pa strip.",
        "err_colour_cast_too_strong": "Ubwanga bwa kuwala ninshi bwalebeta sana. Sebeshani kuwala kwa musana nangu kuwala kwisa, kabili yesheni nakabili.",
        "err_unreadable": "Tatuswike ukubelenga iyi foto. Tafweni ifoto nakabili.",

        # ---- amafya ya service ------------------------------------------------
        "err_rate_limited": "Mwesha utuntungwa utwingi mu nshita iinono. Lindeni umuniti umo kabili yesheni nakabili.",
        "err_server": "Kuli icilufyanya ku mbali yesu. Tafweni nakabili.",

        # ---- amashiwi ya cishinka --------------------------------------------------------
        "verdict_safe": "Cilifye bwino",
        "verdict_risky": "Cilifye na cimo cingaleta ububi",
        "verdict_unsafe": "Tashala bwino",
        "verdict_retake": "Tafweni ifoto nakabili",
        "verdict_safe_detail": "Tatusangile amafya pali iyi strip. Uyu ni test wa kusambilila ifyo cintu caba, te result ya laboratory.",
        "verdict_risky_detail": "Imwe nangu ifyo results shimo shaba panse ya range isuma. Belengeni amashiwi ya malangizo ayali panshi.",
        "verdict_unsafe_detail": "Mutamwa aya menshi mpaka umubomfi wa fyalo nangu umubomfi wa afya amupeleni amalangililo.",
        "verdict_retake_detail": "Tatuswike ukubelenga results shonse bwino, eico tatwingalanda ukuti aya menshi yaba bwino. Tafweni ifoto nakabili.",

        # ---- amafunde pa pad imo imo ---------------------------------------------------
        "hint_no_match": "Pad imo tatuswike ukuyibelenga bwino.",
        "hint_ambiguous": "Result imo yali pafupi na line ya pakati pa levels shibili, eico twasebelele level iikalisha ubwafya panono.",
        "hint_blotchy": "Pad iloleshe nga te ya lingana (ukwalalika, mfwili nangu ukuitika bwino teko).",

        # ---- amashiwi ya cishinka ---------------------------------------------------------
        "prototype_notice": "Prototype: results shaba fye pa kulangisha ifyo system ingasebenza, kabili tatizilolesha bwino na bantu ba fyalo.",

        # ---- amalangililo (DRAFT: yafwile yapitulwa na umubomfi wa afya) -----------------
        "advice_nitrate_risky": "Nitrate yalipita pa bucende ubwasuminwa. Mutasebesa aya menshi pa kupela abana abapya amata nangu formula. Ukupisha aya menshi tekufumya nitrate.",
        "advice_nitrate_unsafe": "Nitrate ninshi yapita sana. Mutapeela abana abapya nangu abakashi abali ne mifuko aya menshi, kabili mutapisha aya menshi mukupesha ukuba ya safe, pantu ukupisha kungaleta nitrate ukuba iikalamba. Sebeshani ayambi menshi kabili ambileni umubomfi wa afya.",
        "advice_ph_risky": "pH yaba panse nangu pamulu ya range isuminwa (6.5 ukufika ku 8.5). Fwayeni amalangililo ku mubomfi wa afya nangu umubomfi wa menshi.",
        "advice_bacteria_unsafe": "Twasangile utubungwe (germs). Mutamwa aya menshi nga tamwaayapanga safe. Apisheni mpaka yabulungama, nangu mupange chlorine, kabili ambileni Community Health Worker wenu.",
        },  # TODO: native-speaker translation + health review
    "nya": {
                # ---- mavuto a chithunzi / upload (wogwiritsa ntchito akhoza kukonza potenganso chithunzi) -------------
        "err_no_image_data": "Palibe chithunzi chomwe chalandiridwa. Chonde tengani chithunzi cha test strip ndikuyesanso.",
        "err_unsupported_type": "Chonde kwezani chithunzi cha JPEG, PNG kapena WebP.",
        "err_image_too_large": "Chithunzichi ndi chachikulu kwambiri. Chonde tengani china pa quality kapena resolution yotsika.",
        "err_not_an_image": "Sitinathe kutsegula fayiloyi ngati chithunzi. Chonde tengani chithunzi chatsopano.",
        "err_image_too_small": "Chithunzichi ndi chaching'ono kwambiri. Yandikirani kuti strip idzaze guide frame.",
        "err_strip_not_found": "Sitinathe kupeza strip. Ikani stripyo mowongoka mkati mwa guide frame, pamalo osalala, ndikuyesanso.",
        "err_strip_too_small": "Strip ikuwoneka yaying'ono kwambiri pachithunzichi. Yandikirani kuti idzaze guide frame.",
        "err_invalid_segment_size": "Sitinathe kuwerenga strip. Chonde tengani chithunzichi kachiwiri strip yonse ili mkati mwa frame.",
        "err_too_dark": "Chithunzichi ndi chakuda kwambiri. Pitani pamalo owala kwambiri, kuchoka pamthunzi, ndikuyesanso.",
        "err_overexposed": "Chithunzichi ndi chowala kwambiri kapena chili ndi kuwala konyezimira. Chokani pa dzuwa lolunjika ndipo pewani kuwala komwe kumanyezimira.",
        "err_reference_uneven": "Pali mthunzi kapena kuwala konyezimira pa malo oyera. Gwirani foni molimba ndipo musalole mthunzi kugwera pa strip.",
        "err_colour_cast_too_strong": "Mtundu wa kuwala ndi wamphamvu kwambiri. Gwiritsani ntchito kuwala kwa masana kapena kuwala koyera, ndikuyesanso.",
        "err_unreadable": "Sitinathe kuwerenga chithunzichi. Chonde tengani chithunzichi kachiwiri.",

        # ---- mavuto a service ------------------------------------------------
        "err_rate_limited": "Mayeso achuluka kwambiri mu nthawi yochepa. Chonde dikirani mphindi imodzi ndikuyesanso.",
        "err_server": "China chake chalakwika kumbali yathu. Chonde yesaninso.",

        # ---- zotsatira --------------------------------------------------------
        "verdict_safe": "Ndi otetezeka",
        "verdict_risky": "Ndi oopsa",
        "verdict_unsafe": "Si otetezeka",
        "verdict_retake": "Chonde tengani chithunzichi kachiwiri",
        "verdict_safe_detail": "Palibe vuto lomwe lapezeka pa strip iyi. Ichi ndi chiyeso choyang'anira, osati zotsatira za laboratory.",
        "verdict_risky_detail": "Zotsatira chimodzi kapena zingapo zili kunja kwa mulingo woyenera. Onani malangizo omwe ali pansipa.",
        "verdict_unsafe_detail": "Musamwe madziwa mpaka wogwira ntchito zaumoyo atakupatsani malangizo.",
        "verdict_retake_detail": "Sitinathe kuwerenga zotsatira zonse bwino, choncho sitinganene kuti madziwa ndi otetezeka. Chonde tengani chithunzichi kachiwiri.",

        # ---- malangizo pa pad iliyonse ---------------------------------------------------
        "hint_no_match": "Pad imodzi sinathe kuwerengedwa bwino.",
        "hint_ambiguous": "Zotsatira zinali pafupi ndi mzere wolekanitsa milingo iwiri, choncho tagwiritsa ntchito mulingo wosamala kwambiri.",
        "hint_blotchy": "Pad inaoneka yosafanana (chifukwa cha kuwala konyezimira, mthunzi kapena kumizidwa mosafanana).",

        # ---- zidziwitso ---------------------------------------------------------
        "prototype_notice": "Prototype: zotsatirazi ndi zongowonetsera ndipo sizinatsimikizidwebe.",

        # ---- malangizo (DRAFT: akufunika kuwunikidwa ndi katswiri wa zaumoyo) -----------------
        "advice_nitrate_risky": "Nitrate ndi yochuluka kuposa mulingo woyenera. Musagwiritse ntchito madziwa kupatsa ana aang'ono chakudya kapena formula. Kuwiritsa madzi sikuchotsa nitrate.",
        "advice_nitrate_unsafe": "Nitrate ndi yochuluka kwambiri. Musapatse madziwa ana aang'ono kapena amayi apakati, ndipo musawiritse madziwa poganiza kuti adzakhala otetezeka, chifukwa kuwira kumatha kuwonjezera mphamvu ya nitrate. Gwiritsani ntchito madzi ena ndipo uzani wogwira ntchito zaumoyo.",
        "advice_ph_risky": "pH ili kunja kwa mulingo woyenera (6.5 mpaka 8.5). Funsani wogwira ntchito zaumoyo kapena woyang'anira madzi kuti akupatseni malangizo.",
        "advice_bacteria_unsafe": "Tizilombo toyambitsa matenda tapezeka. Musamwe madziwa osawathira mankhwala. Abweretseni pa kuwira kwambiri, kapena muwathire chlorine, ndipo uzani Community Health Worker wanu.",
        },  # TODO: native-speaker translation + health review
}


def normalise_language(code: str | None) -> str | None:
    """Map a user-supplied code to a supported language, or None."""
    if not code:
        return None
    code = code.strip().lower()
    code = LANGUAGE_ALIASES.get(code, code)
    return code if code in SUPPORTED_LANGUAGES else None


def t(key: str, lang: str = "en", default: str | None = None) -> str:
    """Translate `key`; fall back to English, then to `default`, then to the key."""
    return (MESSAGES.get(lang, {}).get(key)
            or MESSAGES["en"].get(key)
            or (default if default is not None else key))


def missing_translations(lang: str) -> list[str]:
    """Keys that still need translating for `lang` (handy for a release checklist)."""
    return sorted(set(MESSAGES["en"]) - set(MESSAGES.get(lang, {})))
