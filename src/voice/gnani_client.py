from __future__ import annotations

import io
import os
import time
import uuid
import wave
from dataclasses import dataclass
from typing import Optional

import requests

STT_URL = "https://api.vachana.ai/stt/v3"
TTS_URL = "https://api.vachana.ai/api/v1/tts/inference"
STT_MAX_SECONDS = 30.0

# code -> human label (the 10 Indian languages Gnani documents for STT and TTS)
SUPPORTED_LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "हिन्दी (Hindi)",
    "ta-IN": "தமிழ் (Tamil)",
    "te-IN": "తెలుగు (Telugu)",
    "kn-IN": "ಕನ್ನಡ (Kannada)",
    "ml-IN": "മലയാളം (Malayalam)",
    "mr-IN": "मराठी (Marathi)",
    "bn-IN": "বাংলা (Bengali)",
    "gu-IN": "ગુજરાતી (Gujarati)",
    "pa-IN": "ਪੰਜਾਬੀ (Punjabi)",
}
AUTO_LANGUAGE = "indic-auto"  # Prisma v3.0 only: model identifies the language


class GnaniVoiceError(RuntimeError):
    """Raised for any failed Gnani call, with a message safe to show in the UI."""

    def __init__(self, message: str, status_code: Optional[int] = None):
        super().__init__(message)
        self.status_code = status_code


@dataclass
class Transcript:
    text: str
    language_code: str          # detected (v3.0) or the code that was requested
    latency_s: Optional[float]  # end-to-end latency reported by Gnani, if any
    request_id: Optional[str]


def wav_duration_seconds(audio: bytes) -> Optional[float]:
    """Duration of a WAV payload, or None if it is not parseable WAV."""
    try:
        with wave.open(io.BytesIO(audio), "rb") as w:
            return w.getnframes() / float(w.getframerate())
    except (wave.Error, EOFError):
        return None


def _error_message(resp: requests.Response) -> str:
    """Gnani uses three error shapes (see docs); normalise them to one string."""
    try:
        body = resp.json()
    except ValueError:
        return resp.text[:200] or f"HTTP {resp.status_code}"
    if isinstance(body, dict):
        if isinstance(body.get("detail"), dict):
            d = body["detail"]
            return f"{d.get('error_code', 'ERROR')}: {d.get('message', '')}".strip()
        if isinstance(body.get("error"), dict):
            return body["error"].get("message") or str(body["error"])
        if body.get("message"):
            return str(body["message"])
        if body.get("detail"):
            return str(body["detail"])
    return f"HTTP {resp.status_code}"


class GnaniVoiceClient:
    def __init__(
        self,
        api_key: Optional[str] = None,
        *,
        stt_model: Optional[str] = None,
        tts_model: Optional[str] = None,
        tts_voice: Optional[str] = None,
        timeout: float = 30.0,
        retries: int = 2,
        session: Optional[requests.Session] = None,
    ):
        self.api_key = api_key or os.getenv("GNANI_API_KEY", "")
        self.stt_model = stt_model or os.getenv("GNANI_STT_MODEL", "prisma-v3.0")
        self.tts_model = tts_model or os.getenv("GNANI_TTS_MODEL", "timbre-v3.0")
        # timbre-v3.0 voices each speak all 10 languages, so one default voice is safe.
        self.tts_voice = tts_voice or os.getenv("GNANI_TTS_VOICE", "Shivani")
        self.timeout = timeout
        self.retries = retries
        self.http = session or requests.Session()

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _headers(self) -> dict:
        if not self.api_key:
            raise GnaniVoiceError("GNANI_API_KEY is not set. Add it to your .env file.")
        return {"X-API-Key-ID": self.api_key}

    def _post(self, url: str, **kwargs) -> requests.Response:
        """POST with retry on network errors, 429 and 5xx (exponential backoff)."""
        last: Optional[Exception] = None
        for attempt in range(self.retries + 1):
            try:
                resp = self.http.post(url, timeout=self.timeout, **kwargs)
            except requests.RequestException as exc:
                last = exc
            else:
                if resp.status_code == 429 or resp.status_code >= 500:
                    last = GnaniVoiceError(_error_message(resp), resp.status_code)
                else:
                    return resp
            if attempt < self.retries:
                time.sleep(0.6 * (2 ** attempt))
        if isinstance(last, GnaniVoiceError):
            raise last
        raise GnaniVoiceError(f"Could not reach Gnani Vachana: {last}")

    # ------------------------------------------------------------------ STT
    def transcribe(
        self,
        audio: bytes,
        *,
        language_code: str = AUTO_LANGUAGE,
        filename: str = "speech.wav",
        keyterms: Optional[list[str]] = None,
    ) -> Transcript:
        """Speech -> text with Prisma v3.0. `keyterms` biases recognition toward domain words."""
        headers = self._headers()
        headers["X-API-Request-ID"] = str(uuid.uuid4())

        seconds = wav_duration_seconds(audio) if filename.lower().endswith(".wav") else None
        if seconds is not None and seconds > STT_MAX_SECONDS:
            raise GnaniVoiceError(
                f"Recording is {seconds:.0f}s; Gnani STT accepts at most {STT_MAX_SECONDS:.0f}s. Please keep it shorter."
            )

        data = {
            "model": self.stt_model,
            "language_code": language_code,
            "format": "transcribe",  # inverse text normalisation: "two degrees" -> "2 degrees"
        }
        if keyterms and self.stt_model == "prisma-v3.0":
            data["keyterms"] = ",".join(keyterms[:200])

        resp = self._post(
            STT_URL,
            headers=headers,
            data=data,
            files={"audio_file": (filename, audio, "audio/wav")},
        )
        if resp.status_code != 200:
            raise GnaniVoiceError(f"Speech recognition failed - {_error_message(resp)}", resp.status_code)
        body = resp.json()
        if not body.get("success", True):
            raise GnaniVoiceError(f"Speech recognition failed - {_error_message(resp)}", resp.status_code)
        return Transcript(
            text=(body.get("transcript") or "").strip(),
            language_code=body.get("detected_language_code") or language_code,
            latency_s=body.get("end_to_end_latency"),
            request_id=body.get("request_id"),
        )

    # ------------------------------------------------------------------ TTS
    def synthesize(
        self,
        text: str,
        *,
        language: str = "en-IN",
        voice: Optional[str] = None,
        speed: float = 1.0,
        sample_rate: int = 24000,
    ) -> bytes:
        """Text -> WAV bytes with Timbre."""
        text = (text or "").strip()
        if not text:
            raise GnaniVoiceError("Nothing to speak.")
        payload = {
            "text": text[:2000],
            "voice": voice or self.tts_voice,
            "model": self.tts_model,
            "language": language if language in SUPPORTED_LANGUAGES else "auto",
            "speed": max(0.85, min(1.15, float(speed))),
            "audio_config": {
                "sample_rate": sample_rate,
                "num_channels": 1,
                "sample_width": 2,
                "encoding": "linear_pcm",
                "container": "wav",
            },
        }
        headers = {**self._headers(), "Content-Type": "application/json"}
        resp = self._post(TTS_URL, headers=headers, json=payload)
        if resp.status_code != 200:
            raise GnaniVoiceError(f"Speech synthesis failed - {_error_message(resp)}", resp.status_code)
        if "json" in resp.headers.get("Content-Type", ""):
            raise GnaniVoiceError(f"Speech synthesis failed - {_error_message(resp)}", resp.status_code)
        return resp.content
