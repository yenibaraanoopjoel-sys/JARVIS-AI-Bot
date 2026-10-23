from jarvis.models import Message, MessageRole


def test_message_defaults_and_role():
    message = Message(conversation_id="c1", role=MessageRole.USER, content="Hello")
    assert message.id
    assert message.role == MessageRole.USER
    assert message.content == "Hello"
    assert message.created_at.tzinfo is not None
