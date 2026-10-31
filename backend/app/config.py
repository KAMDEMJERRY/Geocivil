from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "sqlite:///./geocivil.db"
    secret_key: str = "dev-only-change-me"
    access_token_minutes: int = 60 * 24
    admin_email: str | None = None
    cors_origins: str = "http://localhost:5173"
    environment: str = "development"

    @property
    def sqlalchemy_url(self) -> str:
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+psycopg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+psycopg://", 1)
        return url

    @property
    def cors_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @model_validator(mode="after")
    def _check_prod_secret(self):
        if self.environment == "production" and (
            self.secret_key.startswith("dev-only") or len(self.secret_key) < 32
        ):
            raise ValueError("SECRET_KEY robuste (32+ caractères) requise en production")
        return self


settings = Settings()
