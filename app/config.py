from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: SecretStr
    telegram_owner_id: int

    supabase_url: str
    supabase_key: SecretStr

    log_level: str = "INFO"
    environment: str = "development"


settings = Settings()
