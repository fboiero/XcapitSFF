from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./xcapitsff.db"
    redis_url: str = "redis://localhost:6379/0"
    anthropic_api_key: str = ""
    secret_key: str = "change-me-in-production"
    environment: str = "development"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://localhost:8000"

    # Argentor integration
    argentor_url: str = "http://localhost:3000"
    argentor_api_key: str = ""
    argentor_timeout: float = 30.0
    argentor_enabled: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


settings = Settings()
