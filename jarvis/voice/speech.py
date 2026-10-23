"""Optional speech input/output adapters with explicit setup errors."""
import logging
from ..config import Settings

log = logging.getLogger(__name__)


class VoiceError(RuntimeError):
    pass


class VoiceEngine:
    def __init__(self, settings: Settings):
        self.settings = settings

    def listen_once(self, timeout: int = 8, phrase_time_limit: int = 20) -> str:
        try:
            import speech_recognition as sr
        except ImportError as exc:
            raise VoiceError("Speech recognition dependencies missing. Install with: pip install -e '.[voice]'") from exc
        recognizer = sr.Recognizer()
        try:
            with sr.Microphone() as source:
                log.info("Listening for a single user utterance")
                recognizer.adjust_for_ambient_noise(source, duration=0.5)
                audio = recognizer.listen(source, timeout=timeout, phrase_time_limit=phrase_time_limit)
        except sr.WaitTimeoutError as exc:
            raise VoiceError("No speech was detected before the listening timeout.") from exc
        except OSError as exc:
            raise VoiceError("Could not open the microphone. Check device selection and microphone permissions.") from exc
        try:
            return recognizer.recognize_google(audio, language=self.settings.stt_language).strip()
        except sr.UnknownValueError as exc:
            raise VoiceError("Speech was captured but could not be understood.") from exc
        except sr.RequestError as exc:
            raise VoiceError("The speech recognition service is unavailable. Check internet access, or configure an offline STT provider.") from exc

    def speak(self, text: str) -> None:
        if not self.settings.tts_enabled:
            return
        try:
            import pyttsx3
        except ImportError as exc:
            raise VoiceError("Text-to-speech dependencies missing. Install with: pip install -e '.[voice]'") from exc
        try:
            engine = pyttsx3.init()
            engine.say(text)
            engine.runAndWait()
            engine.stop()
        except Exception as exc:
            raise VoiceError(f"Text-to-speech playback failed ({type(exc).__name__}).") from exc
