"""Conversation orchestration with actual AI provider and persistent history."""
from uuid import uuid4
from ..config import Settings
from ..models import Message, MessageRole
from ..storage import ConversationStore
from ..personality.system_prompt import build_system_prompt
from .provider import OpenAIProvider, ProviderError, AIProvider


class ConversationEngine:
    def __init__(self, settings: Settings, store: ConversationStore, provider: AIProvider | None = None):
        self.settings = settings
        self.store = store
        self._provider = provider

    @property
    def provider(self) -> AIProvider:
        if self._provider is None:
            self._provider = OpenAIProvider(self.settings)
        return self._provider

    def new_conversation_id(self) -> str:
        conversation_id = str(uuid4())
        self.store.ensure_conversation(conversation_id)
        return conversation_id

    def ask(self, conversation_id: str, text: str, source: str = "text") -> str:
        prompt = text.strip()
        if not prompt:
            raise ValueError("Message cannot be empty.")
        self.store.ensure_conversation(conversation_id)
        user_message = Message(conversation_id=conversation_id, role=MessageRole.USER, content=prompt, source=source)
        self.store.save_message(user_message)
        history = self.store.get_messages(conversation_id, limit=80)
        provider_messages = [{"role": "system", "content": build_system_prompt(self.settings.owner_name)}]
        provider_messages.extend({"role": m.role.value, "content": m.content} for m in history if m.role in {MessageRole.USER, MessageRole.ASSISTANT})
        try:
            response = self.provider.generate(provider_messages)
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"Unexpected conversation failure ({type(exc).__name__}).") from exc
        self.store.save_message(Message(conversation_id=conversation_id, role=MessageRole.ASSISTANT, content=response, source="ai"))
        return response
