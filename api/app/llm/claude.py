"""Claude 구현체. 구조화 출력은 SDK의 messages.parse(output_format=Pydantic 모델)를 쓴다."""

from typing import Any

import anthropic

from app.llm.base import LLMError, T


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
        client: Any = None,
    ) -> None:
        if not api_key and client is None:
            raise LLMError("ANTHROPIC_API_KEY가 설정되지 않았습니다.")
        self.model = model
        self._effort = effort
        self._max_tokens = max_tokens
        self._client = client or anthropic.AsyncAnthropic(api_key=api_key, timeout=timeout, max_retries=2)

    async def structured(self, *, system: str, prompt: str, output_type: type[T]) -> T:
        try:
            response = await self._client.messages.parse(
                model=self.model,
                max_tokens=self._max_tokens,
                system=system,
                messages=[{"role": "user", "content": prompt}],
                output_format=output_type,
                output_config={"effort": self._effort},
            )
        except anthropic.AuthenticationError:
            raise LLMError("Claude 인증 실패 (ANTHROPIC_API_KEY 확인)") from None
        except anthropic.RateLimitError:
            raise LLMError("Claude 호출 한도 초과") from None
        except anthropic.APIStatusError as exc:
            raise LLMError(f"Claude API 오류 {exc.status_code}") from None
        except anthropic.APIConnectionError:
            raise LLMError("Claude 연결 실패") from None

        if response.stop_reason == "refusal":
            raise LLMError("Claude가 요청을 거절했습니다.")
        if response.stop_reason == "max_tokens":
            raise LLMError("출력이 max_tokens에서 잘렸습니다.")
        if response.parsed_output is None:
            raise LLMError("구조화 출력을 해석하지 못했습니다.")
        return response.parsed_output
