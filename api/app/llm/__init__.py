from app.llm.base import AgentResult, LLMError, LLMProvider, ToolCall, ToolSpec
from app.llm.claude import ClaudeProvider


def create_provider(provider: str, *, api_key: str, model: str, agent: bool = False) -> LLMProvider:
    """LLM_PROVIDER 값으로 제공자를 고른다 (PRD 5.1). OpenAI는 아직 구현하지 않았다.

    agent=True: 도구 호출 Agent용 설정 (더 긴 출력, 거절 시 서버 측 대체 모델).
    """
    if provider == "claude":
        if agent:
            return ClaudeProvider(api_key, model, effort="low", max_tokens=8000, timeout=60.0, fallbacks=True)
        return ClaudeProvider(api_key, model)
    raise LLMError(f"LLM 제공자 '{provider}'는 아직 구현되지 않았습니다.")


__all__ = ["AgentResult", "ClaudeProvider", "LLMError", "LLMProvider", "ToolCall", "ToolSpec", "create_provider"]
