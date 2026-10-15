"""LLM 제공자 인터페이스 (PRD 5.1).

서비스 코드는 이 인터페이스에만 의존하고, Claude·OpenAI 등 제공자별 차이는 구현체가 흡수한다.
"""

from typing import Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """LLM 호출 실패 (인증, 한도, 네트워크, 거절, 출력 형식 오류)."""


class LLMProvider(Protocol):
    provider: str  # 예: "claude"
    model: str  # 예: "claude-haiku-5-5"

    async def structured(self, *, system: str, prompt: str, output_type: type[T]) -> T:
        """output_type 스키마에 맞는 구조화 출력을 반환한다. 실패하면 LLMError."""
        ...
