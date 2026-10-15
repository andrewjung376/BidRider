"""환경 변수 기반 설정. 값은 .env(로컬) 또는 Vercel 환경 변수에서 읽는다."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=(".env", "../.env"), extra="ignore")

    # 공공데이터포털 (조달청_나라장터 입찰공고정보서비스)
    data_go_kr_service_key: str = ""
    koneps_base_url: str = "https://apis.data.go.kr/1230000/ad/BidPublicInfoService"

    # LLM (PRD 5.1)
    llm_provider: Literal["claude", "openai"] = "claude"
    llm_model_fast: str = "claude-haiku-5-5"
    llm_model_agent: str = "claude-sonnet-5-5"
    anthropic_api_key: str = ""
    openai_api_key: str = ""

    # Supabase
    supabase_url: str = ""
    supabase_service_role_key: str = ""
    supabase_anon_key: str = ""  # 로그인 토큰 검증 호출용

    # Vercel Cron 보호 (NFR-03)
    cron_secret: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
