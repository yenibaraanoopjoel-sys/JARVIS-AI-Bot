"""AI provider abstraction; does not fabricate answers when the provider is unavailable."""
from typing import Protocol, Sequence
from . import __name__ as _package_name
from ..models import Message
from ..config import Settings


class AIProvider(Protocol):
    def generate(self, messages: Sequence[dict[str, str]]) -> str: ...


class ProviderError(RuntimeError):
    pass


class OpenAIProvider:
    def __init__(self, settings: Settings):
        if not settings.openai_api_key:
            raise ProviderError("OPENAI_API_KEY is not configured. Set it in .env to enable AI responses.")
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError("Install the AI extra with: pip install -e '.[ai]'") from exc
        self.client = OpenAI(api_key=settings.openai_api_key, timeout=60.0, max_retries=2)
        self.model = settings.openai_model

    def generate(self, messages: Sequence[dict[str, str]]) -> str:
        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=list(messages),
                temperature=0.7,
            )
            content = response.choices[0].message.content
            if not content or not content.strip():
                raise ProviderError("The AI provider returned an empty response.")
            return content.strip()
        except ProviderError:
            raise
        except Exception as exc:
            raise ProviderError(f"AI provider request failed ({type(exc).__name__}). Check connectivity, model configuration, and API access.") from exc
