from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    db_path: str = "./hospital.db"
    app_title: str = "Hospital Management API"
    app_version: str = "10.0.0"
    log_level: str = "INFO"
    secret_key: str = "change-me-in-production"
    token_expire_minutes: int = 60

    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
