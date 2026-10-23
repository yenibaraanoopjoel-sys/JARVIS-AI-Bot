from jarvis.config import Settings
from jarvis.models import MessageRole
from jarvis.storage import ConversationStore
from jarvis.brain.conversation import ConversationEngine


class FakeProvider:
    def generate(self, messages):
        assert any(message["role"] == "user" for message in messages)
        return "Test response"


def test_conversation_saves_user_and_assistant_messages(tmp_path):
    settings = Settings(_env_file=None, database_url=f"sqlite:///{tmp_path / 'test.db'}")
    store = ConversationStore(settings)
    engine = ConversationEngine(settings, store, provider=FakeProvider())
    result = engine.ask("c1", "Hello")
    assert result == "Test response"
    messages = store.get_messages("c1")
    assert [message.role for message in messages] == [MessageRole.USER, MessageRole.ASSISTANT]
    store.close()
