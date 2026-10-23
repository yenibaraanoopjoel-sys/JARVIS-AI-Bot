"""Consent-based local face identification using OpenCV's LBPH recognizer.

This is a basic face-matching feature, not liveness detection. It must never be used
as the sole factor for authorizing sensitive actions. Matching quality depends on
camera quality, lighting, enrollment samples, and the configured distance threshold.
"""
from __future__ import annotations

from collections import Counter, deque
from dataclasses import dataclass
from pathlib import Path
import re
import shutil
import time
from uuid import uuid4

from ..config import Settings


class VisionError(RuntimeError):
    """Raised when a camera or face-recognition operation cannot complete."""


@dataclass(frozen=True)
class FaceMatch:
    profile_id: str
    display_name: str
    distance: float
    threshold: float


def _validate_profile_id(profile_id: str) -> None:
    if not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", profile_id or ""):
        raise ValueError("profile_id may contain only letters, numbers, hyphens, and underscores.")


def _load_opencv():
    try:
        import cv2
        import numpy as np
    except ImportError as exc:
        raise VisionError("Install the vision dependencies with: pip install -e '.[vision]'") from exc
    if not hasattr(cv2, "face") or not hasattr(cv2.face, "LBPHFaceRecognizer_create"):
        raise VisionError(
            "The OpenCV contrib face recognizer is unavailable. Reinstall the vision extra "
            "so opencv-contrib-python is installed."
        )
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        raise VisionError("OpenCV could not load its frontal-face detector.")
    return cv2, np, detector


def _normalized_crop(cv2, gray, bounds) -> object:
    x, y, width, height = [int(value) for value in bounds]
    crop = gray[y:y + height, x:x + width]
    crop = cv2.resize(crop, (160, 160), interpolation=cv2.INTER_AREA)
    return cv2.equalizeHist(crop)


class FaceRecognitionService:
    """Capture consented face samples and match against active local profiles."""

    def __init__(self, settings: Settings, profile_store, samples_root: Path | None = None) -> None:
        self.settings = settings
        self.profile_store = profile_store
        self.samples_root = samples_root or (settings.data_dir / "user_profiles")

    def enroll_from_camera(
        self,
        profile_id: str,
        display_name: str,
        *,
        consent: bool,
        camera_index: int = 0,
        target_samples: int | None = None,
    ) -> Path:
        """Collect multiple samples after informed consent and register the profile."""
        if not self.settings.camera_enabled:
            raise VisionError("Camera access is disabled. Set JARVIS_CAMERA_ENABLED=true in .env first.")
        if not consent:
            raise PermissionError("The person being enrolled must explicitly consent.")
        _validate_profile_id(profile_id)
        if not display_name or not display_name.strip():
            raise ValueError("display_name is required.")
        if self.profile_store.get_profile(profile_id) is not None:
            raise ValueError("That profile ID already exists. Revoke it before using a different ID.")
        required_samples = target_samples or self.settings.face_enrollment_samples
        required_samples = max(5, min(int(required_samples), 30))

        cv2, _, detector = _load_opencv()
        self.samples_root.mkdir(parents=True, exist_ok=True)
        temporary_dir = self.samples_root / f".pending-{profile_id}-{uuid4().hex[:8]}"
        temporary_dir.mkdir(parents=False, exist_ok=False)
        capture = cv2.VideoCapture(camera_index)
        if not capture.isOpened():
            capture.release()
            shutil.rmtree(temporary_dir, ignore_errors=True)
            raise VisionError("Could not open the camera. Check Windows camera permissions and device selection.")

        saved = 0
        try:
            while saved < required_samples:
                ok, frame = capture.read()
                if not ok:
                    raise VisionError("The camera stopped returning frames during enrollment.")
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = detector.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
                )
                preview = frame.copy()
                for x, y, width, height in faces:
                    cv2.rectangle(preview, (x, y), (x + width, y + height), (60, 220, 120), 2)
                status = (
                    f"JARVIS enrollment: {saved}/{required_samples} captured | C: capture | Q: cancel"
                )
                cv2.putText(preview, status, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (255, 255, 255), 2)
                cv2.imshow("JARVIS - Face Enrollment (consent required)", preview)
                key = cv2.waitKey(1) & 0xFF
                if key == ord("q"):
                    break
                if key in {ord("c"), ord(" ")}:
                    if len(faces) != 1:
                        continue
                    face = _normalized_crop(cv2, gray, faces[0])
                    sample_path = temporary_dir / f"sample_{saved + 1:03d}.png"
                    if not cv2.imwrite(str(sample_path), face):
                        raise VisionError("A captured face sample could not be saved.")
                    saved += 1
        except Exception:
            shutil.rmtree(temporary_dir, ignore_errors=True)
            raise
        finally:
            capture.release()
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass

        if saved < required_samples:
            shutil.rmtree(temporary_dir, ignore_errors=True)
            raise VisionError(
                f"Enrollment cancelled: {saved} of {required_samples} required samples were captured."
            )

        target_dir = self.samples_root / profile_id
        if target_dir.exists():
            shutil.rmtree(temporary_dir, ignore_errors=True)
            raise VisionError("The local sample directory already exists; refusing to overwrite biometric data.")
        temporary_dir.rename(target_dir)
        try:
            self.profile_store.enroll_metadata(profile_id, display_name.strip(), consent=True)
        except Exception:
            shutil.rmtree(target_dir, ignore_errors=True)
            raise
        return target_dir

    def identify_from_camera(self, *, seconds: int = 15, camera_index: int = 0) -> FaceMatch | None:
        """Show the camera and return an enrolled identity only after repeated matching frames."""
        if not self.settings.camera_enabled:
            raise VisionError("Camera access is disabled. Set JARVIS_CAMERA_ENABLED=true in .env first.")
        seconds = max(1, min(int(seconds), 120))
        cv2, np, detector = _load_opencv()
        profiles = sorted(self.profile_store.list_active(), key=lambda profile: profile["profile_id"])
        if not profiles:
            raise VisionError("No active face profiles are enrolled. Run 'jarvis face enroll' first.")

        labels: list[int] = []
        images: list[object] = []
        label_to_profile: dict[int, dict[str, str]] = {}
        for label, profile in enumerate(profiles):
            label_to_profile[label] = profile
            profile_dir = self.samples_root / profile["profile_id"]
            sample_paths = sorted(profile_dir.glob("*.png")) + sorted(profile_dir.glob("*.jpg"))
            for sample_path in sample_paths:
                image = cv2.imread(str(sample_path), cv2.IMREAD_GRAYSCALE)
                if image is None:
                    continue
                image = cv2.resize(image, (160, 160), interpolation=cv2.INTER_AREA)
                images.append(cv2.equalizeHist(image))
                labels.append(label)
        if not images:
            raise VisionError("No usable enrollment samples were found for active profiles.")

        recognizer = cv2.face.LBPHFaceRecognizer_create()
        recognizer.train(images, np.asarray(labels, dtype=np.int32))

        capture = cv2.VideoCapture(camera_index)
        if not capture.isOpened():
            capture.release()
            raise VisionError("Could not open the camera. Check Windows camera permissions and device selection.")

        recent_labels: deque[int] = deque(maxlen=5)
        match: FaceMatch | None = None
        started = time.monotonic()
        try:
            while time.monotonic() - started < seconds:
                ok, frame = capture.read()
                if not ok:
                    raise VisionError("The camera stopped returning frames during identification.")
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = detector.detectMultiScale(
                    gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80)
                )
                status = "No face detected"
                if len(faces) == 1:
                    face = _normalized_crop(cv2, gray, faces[0])
                    label, distance = recognizer.predict(face)
                    if float(distance) <= float(self.settings.face_match_threshold):
                        recent_labels.append(int(label))
                        winner, votes = Counter(recent_labels).most_common(1)[0]
                        if votes >= 3 and winner in label_to_profile:
                            profile = label_to_profile[winner]
                            match = FaceMatch(
                                profile_id=profile["profile_id"],
                                display_name=profile["display_name"],
                                distance=float(distance),
                                threshold=float(self.settings.face_match_threshold),
                            )
                            status = f"Matched: {match.display_name} (distance {distance:.1f})"
                        else:
                            status = "Verifying consistent match..."
                    else:
                        recent_labels.clear()
                        status = "Unknown face"
                else:
                    recent_labels.clear()
                    if len(faces) > 1:
                        status = "Multiple faces detected"

                cv2.putText(frame, "JARVIS face identification - Q to close", (12, 26),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.58, (255, 255, 255), 2)
                cv2.putText(frame, status, (12, 54), cv2.FONT_HERSHEY_SIMPLEX, 0.62,
                            (60, 220, 120) if match else (40, 180, 240), 2)
                for x, y, width, height in faces:
                    cv2.rectangle(frame, (x, y), (x + width, y + height), (60, 220, 120), 2)
                cv2.imshow("JARVIS - Face Identification", frame)
                if cv2.waitKey(1) & 0xFF == ord("q"):
                    break
                if match is not None:
                    return match
        except Exception as exc:
            if isinstance(exc, VisionError):
                raise
            raise VisionError(f"Face identification failed ({type(exc).__name__}).") from exc
        finally:
            capture.release()
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass
        return match

    def delete_local_samples(self, profile_id: str) -> bool:
        """Delete sample files only from this application's profile-data directory."""
        _validate_profile_id(profile_id)
        target = (self.samples_root / profile_id).resolve()
        root = self.samples_root.resolve()
        try:
            target.relative_to(root)
        except ValueError as exc:
            raise ValueError("Refusing to delete data outside the JARVIS profile directory.") from exc
        if not target.exists():
            return False
        shutil.rmtree(target)
        return True
