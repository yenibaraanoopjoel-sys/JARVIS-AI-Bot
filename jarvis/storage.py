"""Persistent SQLAlchemy storage for conversations and messages."""
from pathlib import Path

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text, select, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from .config import Settings
from .models import Conversation, Message, MessageRole, utc_now


class Base(DeclarativeBase):
    pass


class ConversationRow(Base):
    __tablename__ = "conversations"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    title: Mapped[str] = mapped_column(String(200), default="New conversation")
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[object] = mapped_column(DateTime(timezone=True))


class MessageRow(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    conversation_id: Mapped[str] = mapped_column(ForeignKey("conversations.id", ondelete="CASCADE"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    created_at: Mapped[object] = mapped_column(DateTime(timezone=True))
    source: Mapped[str] = mapped_column(String(30), default="text")
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, default=dict)


class ConversationStore:
    def __init__(self, settings: Settings):
        url = settings.database_url
        if url.startswith("sqlite:///"):
            raw_path = url.removeprefix("sqlite:///")
            if raw_path != ":memory:":
                Path(raw_path).parent.mkdir(parents=True, exist_ok=True)
        kwargs = {"check_same_thread": False} if url.startswith("sqlite") else {}
        self.engine = create_engine(url, future=True, connect_args=kwargs)
        if url.startswith("sqlite"):
            @event.listens_for(self.engine, "connect")
            def _enable_sqlite_foreign_keys(dbapi_connection, _connection_record):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.close()
        self.sessions = sessionmaker(self.engine, expire_on_commit=False)
        Base.metadata.create_all(self.engine)

    def ensure_conversation(self, conversation_id: str, title: str = "New conversation") -> None:
        with self.sessions.begin() as session:
            row = session.get(ConversationRow, conversation_id)
            if row is None:
                now = utc_now()
                session.add(ConversationRow(id=conversation_id, title=title, created_at=now, updated_at=now))

    def save_message(self, message: Message) -> None:
        self.ensure_conversation(message.conversation_id)
        with self.sessions.begin() as session:
            session.add(MessageRow(
                id=message.id,
                conversation_id=message.conversation_id,
                role=message.role.value,
                content=message.content,
                created_at=message.created_at,
                source=message.source,
                metadata_json=message.metadata,
            ))
            row = session.get(ConversationRow, message.conversation_id)
            if row:
                row.updated_at = utc_now()
                if row.title == "New conversation" and message.role == MessageRole.USER:
                    row.title = message.content[:60].strip() or row.title

    def get_messages(self, conversation_id: str, limit: int = 100) -> list[Message]:
        with self.sessions() as session:
            rows = session.scalars(
                select(MessageRow).where(MessageRow.conversation_id == conversation_id)
                .order_by(MessageRow.created_at.asc()).limit(max(1, min(limit, 1000)))
            ).all()
            return [
                Message(
                    id=r.id,
                    conversation_id=r.conversation_id,
                    role=MessageRole(r.role),
                    content=r.content,
                    created_at=r.created_at,
                    source=r.source,
                    metadata=r.metadata_json or {},
                )
                for r in rows
            ]

    def list_conversations(self, limit: int = 50) -> list[Conversation]:
        with self.sessions() as session:
            rows = session.scalars(
                select(ConversationRow).order_by(ConversationRow.updated_at.desc()).limit(max(1, min(limit, 200)))
            ).all()
            return [Conversation(id=r.id, title=r.title, created_at=r.created_at, updated_at=r.updated_at) for r in rows]

    def close(self) -> None:
        self.engine.dispose()
