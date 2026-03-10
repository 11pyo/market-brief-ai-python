from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Keys
    finnhub_api_key: str = ""
    openai_api_key: str = ""
    gemini_api_key: str = ""
    anthropic_api_key: str = ""

    # Upstash Redis (영구 통계 저장)
    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    # LLM 설정
    llm_provider: str = "openai"           # openai | gemini | anthropic
    llm_model: str = "gpt-4o"
    llm_fallback_model: str = "gemini-2.0-flash"

    # 서버
    port: int = 3000
    tz: str = "Asia/Seoul"

    # 스케줄
    briefing_cron: str = "0 7 * * *"
    max_briefings: int = 30


settings = Settings()
