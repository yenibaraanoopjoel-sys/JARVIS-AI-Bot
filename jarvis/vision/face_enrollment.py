"""Consent-based face enrollment using OpenCV face detection.

This module detects and stores a face crop for a user-approved enrollment workflow.
It does not authenticate a person's identity by itself; production identity matching
requires an evaluated recognition model, liveness protections, and explicit consent.
"""
from pathlib import Path
from ..config import Settings


class VisionError(RuntimeError):
    pass


def capture_enrollment_image(profile_id: str, destination_dir: str, settings: Settings, camera_index: int = 0) -> Path:
    if not settings.camera_enabled:
        raise VisionError("Camera is disabled. Enable it in local configuration before enrollment.")
    if not profile_id or any(ch not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for ch in profile_id):
        raise ValueError("profile_id may contain only letters, numbers, hyphen, and underscore")
    try:
        import cv2
    except ImportError as exc:
        raise VisionError("Install the vision extra with: pip install -e '.[vision]'") from exc
    cascade_path = Path(cv2.data.haarcascades) / "haarcascade_frontalface_default.xml"
    detector = cv2.CascadeClassifier(str(cascade_path))
    if detector.empty():
        raise VisionError("OpenCV face detector could not be loaded.")
    capture = cv2.VideoCapture(camera_index)
    if not capture.isOpened():
        capture.release()
        raise VisionError("Could not open camera. Check permissions and device availability.")
    try:
        ok, frame = capture.read()
        if not ok:
            raise VisionError("Camera did not return an image.")
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = detector.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(80, 80))
        if len(faces) != 1:
            raise VisionError(f"Enrollment requires exactly one clearly detected face; detected {len(faces)}.")
        x, y, w, h = faces[0]
        crop = frame[y:y+h, x:x+w]
        target_dir = Path(destination_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        target = target_dir / f"{profile_id}.jpg"
        if not cv2.imwrite(str(target), crop):
            raise VisionError("Could not save enrollment image.")
        return target
    finally:
        capture.release()
