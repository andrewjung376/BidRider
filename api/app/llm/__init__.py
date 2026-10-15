from app.llm.base import LLMError, LLMProvider
from app.llm.claude import ClaudeProvider


def create_provider(provider: str, *, api_key: str, model: str) -> LLMProvider:
    """LLM_PROVIDER 값으로 제공자를 고른다 (PRD 5.1). OpenAI는 아직 구현하지 않았다."""
    if provider == "claude":
        return ClaudeProvider(api_key, model)
    raise LLMError(f"LLM 제공자 '{provider}'는 아직 구현되지 않았습니다.")


__all__ = ["ClaudeProvider", "LLMError", "LLMProvider", "create_provider"]
