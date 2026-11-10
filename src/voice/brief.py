"""Helpers that turn a written incident report into something worth speaking."""
from __future__ import annotations

import re

_VOICE_RE = re.compile(r"^\s*VOICE_BRIEF\s*:\s*(.+)\Z", re.IGNORECASE | re.MULTILINE | re.DOTALL)


def split_voice_brief(report: str) -> tuple[str, str]:
    """
    The system prompt asks the model to finish with a single `VOICE_BRIEF: ...` line,
    written in the user's language with numbers spelled out. Returns (visible_report, brief).
    The brief is "" when the model omitted it.
    """
    if not report:
        return "", ""
    m = _VOICE_RE.search(report)
    if not m:
        return report.strip(), ""
    return report[: m.start()].rstrip(), clean_for_speech(m.group(1))


def clean_for_speech(text: str) -> str:
    """Strip markdown/tables/emoji so TTS doesn't read symbols aloud."""
    text = re.sub(r"```.*?```", " ", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]*)`", r"\1", text)
    text = re.sub(r"\*\*?|__?|#+\s*|^\s*[-*]\s+", "", text, flags=re.MULTILINE)
    text = re.sub(r"\|", " ", text)
    text = re.sub(r"[^\w\s.,;:!?'%°/\-()ऀ-ൿ]", " ", text)  # keep Indic scripts
    return re.sub(r"\s+", " ", text).strip()


def fallback_brief(report: str, max_chars: int = 400) -> str:
    """If the model gave no VOICE_BRIEF, speak the Executive Summary section instead."""
    m = re.search(r"Executive Summary(.*?)(?:###|\Z)", report or "", flags=re.DOTALL | re.IGNORECASE)
    body = clean_for_speech(m.group(1)) if m else clean_for_speech(report or "")
    return body[:max_chars].rsplit(" ", 1)[0] if len(body) > max_chars else body
