"""Metadata registry for enrolled face profiles.

Raw biometric images are not database defaults. Enrollment images are stored locally
under the ignored data/user_profiles directory and must only be created with consent.
This registry is a minimal SQLite-compatible metadata table; face matching is not
implemented by this registry and must not be treated as authentication.
"""
from sqlalchemy import String, Boolean, DateTime, select
from sqlalchemy.orm import Mapped, mapped_column
from ..storage import Base
from ..models import utc_now


class FaceProfileRow(Base):
    __tablename__ = "face_profiles"
    profile_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120))
    consent_recorded: Mapped[bool] = mapped_column(Boolean, default=False)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True), default=utc_now)


class FaceProfileStore:
    def __init__(self, store):
        self.store = store
        Base.metadata.create_all(store.engine)

    def enroll_metadata(self, profile_id: str, display_name: str, *, consent: bool) -> None:
        if not consent:
            raise PermissionError("Explicit consent is required before enrolling biometric data.")
        if not profile_id.strip() or not display_name.strip():
            raise ValueError("profile_id and display_name are required")
        with self.store.sessions.begin() as session:
            if session.get(FaceProfileRow, profile_id):
                raise ValueError("This profile ID already exists")
            session.add(FaceProfileRow(profile_id=profile_id, display_name=display_name, consent_recorded=True, active=True))

    def revoke(self, profile_id: str) -> bool:
        with self.store.sessions.begin() as session:
            row = session.get(FaceProfileRow, profile_id)
            if not row:
                return False
            row.active = False
            return True

    def list_active(self) -> list[dict[str, str]]:
        with self.store.sessions() as session:
            rows = session.scalars(select(FaceProfileRow).where(FaceProfileRow.active.is_(True))).all()
            return [{"profile_id": r.profile_id, "display_name": r.display_name} for r in rows]
