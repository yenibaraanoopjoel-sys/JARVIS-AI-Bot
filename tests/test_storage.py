from jarvis.config import Settings
from jarvis.models import Message, MessageRole
from jarvis.storage import ConversationStore


def test_messages_persist_in_sqlite(tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'test.db'}")
    store = ConversationStore(settings)
    store.ensure_conversation("conversation-1")
    message = Message(conversation_id="conversation-1", role=MessageRole.USER, content="Hello JARVIS")
    store.save_message(message)
    loaded = store.get_messages("conversation-1")
    assert len(loaded) == 1
    assert loaded[0].content == "Hello JARVIS"
    store.close()
