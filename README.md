# JARVIS AI Assistant

JARVIS is a Python-based personal assistant targeting Windows and PowerShell. This repository contains a real AI conversation provider, persisted chat history, optional speech input/output, consent-based local face identification, a local owner PIN, and permission-controlled application launching.

## Current working capabilities

- AI-backed chat through the configured OpenAI API (requires a valid API key and model access).
- Persistent conversations and messages in SQLite.
- Terminal text chat and single-utterance voice turns.
- Text-to-speech through the system voice engine when enabled.
- Deterministic local commands for current time/date and a small allowlist of Windows applications.
- Owner PIN protected application launching, with app launching disabled by default.
- Multi-sample face enrollment and local face identification using OpenCV-contrib LBPH.
- Consent metadata and face-profile revocation that removes local enrollment samples.
- Central permission checks, safe logging defaults, and automated unit tests.

## Not implemented / not claimed to work yet

- A reliable wake-word engine or background always-listening service.
- Robust speaker identification or voice biometrics.
- Face liveness detection or spoof resistance. A face match is **not** authentication.
- General-purpose model tool calling, unrestricted terminal execution, or broad computer control.
- Web search integration, reminder scheduler, desktop UI, mobile sync, or camera-to-AI visual question answering.
- End-to-end device testing on every Windows camera/microphone configuration.

JARVIS must not be trusted with sensitive operations solely because a face was matched. App launch remains protected by the local owner PIN and configuration allowlist.

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

Edit `.env` locally and set `OPENAI_API_KEY` to your own API key. Confirm that `OPENAI_MODEL` is available to your account. Never commit `.env`.

Start text chat:

```powershell
jarvis chat
```

Run diagnostics and tests:

```powershell
jarvis doctor
pytest
ruff check .
```

## Voice commands

Install the optional voice dependencies:

```powershell
pip install -e ".[voice]"
jarvis chat --voice
```

JARVIS listens for one utterance at a time, sends transcribed text to its conversation engine, then speaks the response. The current speech-recognition adapter uses Google's online recognition API; it is **not offline speech recognition**. Speech output uses `pyttsx3` and the installed system voice.

Commands currently handled by deterministic local code include:

- "JARVIS, what time is it?"
- "JARVIS, what's today's date?"
- "JARVIS, open Notepad"
- "JARVIS, open Calculator"
- "JARVIS, open Explorer"
- "JARVIS, open PowerShell"
- "JARVIS, who is in front of me?" (opens the camera only when camera access is enabled)

App launching is disabled by default. To enable the small allowlist, set this in your local `.env`:

```dotenv
JARVIS_ALLOW_APP_LAUNCH=true
```

Configure a local owner PIN:

```powershell
jarvis auth setup
jarvis auth status
```

The PIN is stored as a salted PBKDF2 hash in `data/owner_auth.json`; the plaintext PIN is not saved. When an allowlisted application is requested, JARVIS asks for the PIN if the session is not already authenticated. Use `/logout` to lock the local action session again.

## Face identification

Install the vision extra; this uses OpenCV-contrib because the LBPH face recognizer is not included in the standard OpenCV wheel:

```powershell
pip install -e ".[vision]"
```

Enable the camera explicitly in `.env`:

```dotenv
JARVIS_CAMERA_ENABLED=true
JARVIS_FACE_MATCH_THRESHOLD=70.0
JARVIS_FACE_ENROLLMENT_SAMPLES=8
```

Enroll a person only after they have been informed and have explicitly consented:

```powershell
jarvis face enroll --profile-id anoop --name "Anoop"
```

The camera window opens after consent confirmation. Press **C** to capture each sample while changing head angle and expression slightly; press **Q** to cancel. At least five samples are required. Sample images are stored locally under the ignored `data/user_profiles/` directory.

Identify an enrolled person:

```powershell
jarvis face identify --seconds 15
jarvis face list
jarvis face revoke --profile-id anoop
```

Revoking asks for confirmation, deactivates the profile, and deletes its local samples. If recognition quality is poor, adjust the distance threshold cautiously and re-enroll with varied lighting and angles. The reported LBPH distance is **not a calibrated probability**; lower distances indicate closer matches. No liveness check is implemented, so photos or screens may be mistaken for a face match. Do not use face matching alone to authorize private data access or sensitive actions.

## Safety and privacy

- Camera use is disabled by default and requires explicit local configuration.
- Biometric enrollment requires a consent confirmation.
- Face samples, the local owner PIN hash, databases, recordings, and `.env` are excluded from source control.
- A face match is an identification result, not authentication.
- Terminal execution is not exposed by the current CLI.
- Application launching is limited to Notepad, Calculator, Explorer, and PowerShell and is denied unless enabled in configuration and owner-authenticated.
- JARVIS should report failures honestly and must not claim an action succeeded without a real tool result.
