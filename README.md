# JARVIS AI Assistant

JARVIS is a personal AI assistant targeting Windows/PowerShell with conversational AI, voice I/O, persistent conversation history, consent-based face enrollment, and permission-controlled desktop utilities.

## Current implementation status

Implemented in this repository:
- Python package, environment-based settings, and safe logging defaults.
- SQLAlchemy/SQLite persistence for conversations and messages.
- Configurable OpenAI conversational provider (requires a valid API key and enabled model access).
- Terminal text chat and optional speech input/output.
- Optional OpenCV face detection and consent-gated enrollment image capture.
- Basic face-profile metadata registry.
- Central permission checks and a small Windows application allowlist.
- Initial automated tests.

Not yet implemented or not yet verified as production-ready:
- A reliable wake-word engine.
- Robust speaker identification.
- Production face recognition/identity matching and liveness checks.
- End-to-end authenticated owner identity.
- General-purpose safe computer control and model tool-calling.
- Camera-to-AI visual question answering.
- Web search, reminders scheduler, desktop UI, and mobile synchronization.
- CI execution and real device testing.

Do not treat face enrollment as face recognition authentication: the current vision module only detects one face and saves an enrollment crop after camera access is enabled.

## Windows / PowerShell setup

Python 3.11 or newer is required.

```powershell
git clone https://github.com/yenibaraanoopjoel-sys/JARVIS-AI-Bot.git
cd JARVIS-AI-Bot
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e ".[ai,test]"
Copy-Item .env.example .env
```

Edit `.env` locally and set `OPENAI_API_KEY` to your own valid API key. Do not commit that file. Confirm the configured model is available to your account.

Start text chat:

```powershell
jarvis chat
```

Check the installation:

```powershell
jarvis doctor
pytest
```

Optional voice packages:

```powershell
pip install -e ".[voice]"
jarvis chat --voice
```

Microphone and speech-recognition behavior depends on Windows audio devices and the configured speech provider. The current speech-recognition adapter uses Google's online recognition API; it is not offline recognition.

Optional vision dependencies:

```powershell
pip install -e ".[vision]"
```

The camera remains disabled by default. To enable local enrollment, explicitly set `JARVIS_CAMERA_ENABLED=true` in `.env`, ensure all captured faces are enrolled with informed consent, and run a supported application workflow that invokes the enrollment module. Camera support is not always-on monitoring.

## Safety

- Never commit `.env`, API keys, local databases, biometric images/embeddings, or recordings.
- Camera and microphone access must remain opt-in and visibly active.
- Facial or voice similarity is not sufficient alone for sensitive authorization.
- Terminal execution is deliberately not exposed by the current CLI.
- Desktop app launching is denied by default and limited to allowlisted applications.
- The current application is an early implementation with tests provided; run tests locally and evaluate all modules before relying on it for sensitive tasks.
