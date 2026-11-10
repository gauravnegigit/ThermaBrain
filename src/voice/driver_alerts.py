"""
Driver voice alerts. A dispatcher reviews an incident and, with one click, generates a spoken
alert in the driver's language (Gnani Timbre TTS). Templates are deliberately short and use
the same wording every time so drivers learn to recognise them.

NOTE: the non-English templates should be reviewed by a native speaker before production use.
"""
from __future__ import annotations

from typing import Any

# {veh} vehicle id, {cargo} cargo type, {temp} reading, {lo}/{hi} safe band, {dir_word} direction
_TEMPLATES = {
    "en-IN": (
        "Attention driver of vehicle {veh}. Your {cargo} load is at {temp} degrees, which is {dir_word} "
        "the safe range of {lo} to {hi} degrees. Please restart the cooling unit now and call dispatch."
    ),
    "hi-IN": (
        "वाहन {veh} के ड्राइवर कृपया ध्यान दें। आपके {cargo} माल का तापमान {temp} डिग्री है, जो सुरक्षित सीमा "
        "{lo} से {hi} डिग्री से {dir_word} है। कृपया तुरंत कूलिंग यूनिट दोबारा चालू करें और डिस्पैच को फ़ोन करें।"
    ),
    "ta-IN": (
        "வாகனம் {veh} ஓட்டுநர் கவனிக்கவும். உங்கள் {cargo} சரக்கின் வெப்பநிலை {temp} டிகிரி, பாதுகாப்பான "
        "அளவு {lo} முதல் {hi} டிகிரி என்பதை விட {dir_word} உள்ளது. உடனே குளிரூட்டும் அலகை மீண்டும் இயக்கி டிஸ்பாட்சைத் தொடர்பு கொள்ளுங்கள்."
    ),
    "te-IN": (
        "వాహనం {veh} డ్రైవర్ దయచేసి గమనించండి. మీ {cargo} సరుకు ఉష్ణోగ్రత {temp} డిగ్రీలు, ఇది సురక్షిత పరిధి "
        "{lo} నుండి {hi} డిగ్రీల కంటే {dir_word} ఉంది. వెంటనే కూలింగ్ యూనిట్‌ను మళ్లీ ప్రారంభించి డిస్పాచ్‌కు కాల్ చేయండి."
    ),
    "kn-IN": (
        "ವಾಹನ {veh} ಚಾಲಕರೇ ಗಮನಿಸಿ. ನಿಮ್ಮ {cargo} ಸರಕಿನ ತಾಪಮಾನ {temp} ಡಿಗ್ರಿ, ಇದು ಸುರಕ್ಷಿತ ಮಿತಿ "
        "{lo} ರಿಂದ {hi} ಡಿಗ್ರಿಗಿಂತ {dir_word} ಇದೆ. ಈಗಲೇ ಕೂಲಿಂಗ್ ಯೂನಿಟ್ ಅನ್ನು ಮರುಪ್ರಾರಂಭಿಸಿ ಮತ್ತು ಡಿಸ್ಪ್ಯಾಚ್‌ಗೆ ಕರೆ ಮಾಡಿ."
    ),
}
_DIR = {
    "en-IN": {"above": "above", "below": "below"},
    "hi-IN": {"above": "ऊपर", "below": "नीचे"},
    "ta-IN": {"above": "அதிகமாக", "below": "குறைவாக"},
    "te-IN": {"above": "ఎక్కువగా", "below": "తక్కువగా"},
    "kn-IN": {"above": "ಹೆಚ್ಚು", "below": "ಕಡಿಮೆ"},
}
ALERT_LANGUAGES = list(_TEMPLATES)


def _num(x: float) -> str:
    return f"{x:g}" if float(x).is_integer() else f"{x:.1f}"


def build_driver_alert(incident: Any, language: str = "en-IN") -> str:
    """`incident` is a watchtower.Incident (or any object/dict with the same fields)."""
    get = (lambda k: incident[k]) if isinstance(incident, dict) else (lambda k: getattr(incident, k))
    lang = language if language in _TEMPLATES else "en-IN"
    return _TEMPLATES[lang].format(
        veh=get("vehicle_id"),
        cargo=get("cargo"),
        temp=_num(get("temperature_c")),
        lo=_num(get("safe_min_c")),
        hi=_num(get("safe_max_c")),
        dir_word=_DIR[lang][get("direction")],
    )