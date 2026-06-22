from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "postgresql://migration:migration@localhost:5432/migration_utility"
    landing_zone_path: str = "./data/landing"
    export_path: str = "./data/exports"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_reload: bool = True
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost"

    kraken_api_url: str = "https://api.kraken.tech/migration/v1"
    kraken_mock_mode: bool = True
    sap_api_url: str = "https://sap.example.local/idoc"
    sap_mock_mode: bool = True

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
