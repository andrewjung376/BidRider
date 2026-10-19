"""Claude 구현체.

- 구조화 출력: SDK의 messages.parse(output_format=Pydantic 모델)
- Agent: 도구 호출 루프를 직접 돈다 (최대 단계 수를 정해 비용·지연을 제한).
  강제 도구 호출(tool_choice any/tool)은 최신 모델에서 400이라 auto를 쓰고, 마지막 단계만 none으로 답변을 받는다.
"""

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import anthropic

from app.llm.base import AgentResult, LLMError, T, ToolCall, ToolExecutor, ToolSpec

FALLBACK_BETA = "server-side-fallback-2026-07-01"


@contextmanager
def _map_errors() -> Iterator[None]:
    try:
        yield
    except anthropic.AuthenticationError:
        raise LLMError("Claude 인증 실패 (ANTHROPIC_API_KEY 확인)") from None
    except anthropic.RateLimitError:
        raise LLMError("Claude 호출 한도 초과") from None
    except anthropic.APIStatusError as exc:
        raise LLMError(f"Claude API 오류 {exc.status_code}") from None
    except anthropic.APIConnectionError:
        raise LLMError("Claude 연결 실패") from None


class ClaudeProvider:
    provider = "claude"

    def __init__(
        self,
        api_key: str,
        model: str,
        *,
        effort: str = "low",
        max_tokens: int = 4000,
        timeout: float = 30.0,
        fallbacks: bool = False,
        client: Any = None,
    ) -> None:
        if not api_key and client is None:
            raise LLMError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        self.model = model
        self._effort = effort
        self._max_tokens = max_tokens
        # 안전 분류기가 요청을 거절(refusal)하면 서버가 다른 모델로 자동 재시도 (Agent 모델에서 사용)
        self._fallbacks = fallbacks
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=2)

    async def structured(self, *, system: str, prompt: str, output_type: type[T]) -> T:
        with _map_errors():
            response = await self._client.messages.parse(
                model=self.model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=output_type,
                output_config={"effort": self._effort},
            )
        if response.stop_reason == "refusal":
            raise LLMError("Claude가 요청을 거절했습니다.")
        if response.stop_reason == "max_tokens":
            raise LLMError("출력이 max_tokens에서 잘렸습니다.")
        if response.parsed_output is None:
            raise LLMError("구조화 출력을 해석하지 못했습니다.")
        return response.parsed_output

    async def run_agent(
        self,
        *,
        system: str,
        messages: list[dict[str, str]],
        tools: list[ToolSpec],
        execute: ToolExecutor,
        max_steps: int = 3,
    ) -> AgentResult:
        tool_defs = [{"name": t.name, "description": t.description, "input_schema": t.input_schema} for t in tools]
        convo: list[dict[str, Any]] = [{"role": m["role"], "content": m["content"]} for m in messages]
        calls: list[ToolCall] = []
        served_by = self.model

        for step in range(max_steps + 1):
            last = step == max_steps  # 마지막 단계는 도구 없이 답변만 받는다
            kwargs: dict[str, Any] = {
                "model": self.model,
                "max_tokens": self._max_tokens,
                "system": system,
                "messages": convo,
                "tools": tool_defs,
                "tool_choice": {"type": "none"} if last else {"type": "auto"},
                "output_config": {"effort": self._effort},
            }
            if self._fallbacks:
                kwargs.update(betas=[FALLBACK_BETA], fallbacks="default")
            with _map_errors():
                response = await self._client.beta.messages.create(**kwargs)
            served_by = getattr(response, "model", None) or served_by

            if response.stop_reason == "refusal":
                raise LLMError("Claude가 요청을 거절했습니다.")
            if response.stop_reason != "tool_use":
                text = "".join(b.text for b in response.content if b.type == "text").strip()
                if not text:
                    raise LLMError("빈 답변")
                return AgentResult(text=text, tool_calls=calls, model=served_by)

            # 모델의 응답(생각·도구 호출 블록 포함)을 그대로 이어 붙이고, 모든 도구 결과를 한 메시지로 돌려준다
            convo.append({"role": "assistant", "content": response.content})
            results = []
            for block in (b for b in response.content if b.type == "tool_use"):
                args = dict(block.input or {})
                try:
                    output, count = await execute(block.name, args)
                    results.append({"type": "tool_result", "tool_use_id": block.id, "content": output})
                except Exception as exc:  # 도구 오류는 모델에게 알려 다른 방법을 찾게 한다
                    count = None
                    results.append(
                        {"type": "tool_result", "tool_use_id": block.id, "content": f"오류: {exc}", "is_error": True}
                    )
                calls.append(ToolCall(name=block.name, args=args, result_count=count))
            convo.append({"role": "user", "content": results})

        raise LLMError("도구 호출 단계 수를 넘었습니다.")  # pragma: no cover (마지막 단계는 tool_choice none)
