"""LLM 제공자 인터페이스 (PRD 5.1).

서비스 코드는 이 인터페이스에만 의존하고, Claude·OpenAI 등 제공자별 차이는 구현체가 흡수한다.
"""

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """LLM 호출 실패 (인증, 한도, 네트워크, 거절, 출력 형식 오류)."""


@dataclass
class ToolSpec:
    """제공자와 무관한 도구 정의. input_schema는 JSON Schema."""

    name: str
    description: str
    input_schema: dict[str, Any]


@dataclass
class ToolCall:
    name: str
    args: dict[str, Any]
    result_count: int | None = None


@dataclass
class AgentResult:
    text: str
    tool_calls: list[ToolCall] = field(default_factory=list)
    model: str = ""


# 도구 실행기: (도구 이름, 입력) → (모델에게 돌려줄 결과 문자열, 결과 건수)
ToolExecutor = Callable[[str, dict[str, Any]], Awaitable[tuple[str, int | None]]]


class LLMProvider(Protocol):
    provider: str  # 예: "claude"
    model: str  # 예: "claude-haiku-5-5"

    async def structured(self, *, system: str, prompt: str, output_type: type[T]) -> T:
        """output_type 스키마에 맞는 구조화 출력을 반환한다. 실패하면 LLMError."""
        ...

    async def run_agent(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        tools: list[ToolSpec],
        execute: ToolExecutor,
        max_steps: int = 3,
    ) -> AgentResult:
        """도구 호출 루프를 돌려 최종 답변을 만든다. messages는 {"role", "content"} 텍스트 대화."""
        ...
