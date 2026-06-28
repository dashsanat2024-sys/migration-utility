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
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:3000,http://localhost,"
        "https://migration-utility.vercel.app,https://migration-utility-ktutcltba-dashsanat2024-9148s-projects.vercel.app"
    )

    kraken_api_url: str = "https://api.kraken.tech/migration/v1"
    kraken_mock_mode: bool = True
    sap_api_url: str = "https://sap.example.local/idoc"
    sap_mock_mode: bool = True

    # Auth (P1)
    auth_enabled: bool = False
    auth_secret: str = "change-me-in-production"
    auth_token_hours: int = 12
    auth_seed_email: str = "admin@arthavi.local"
    auth_seed_password: str = "admin123"
    auth_seed_name: str = "Migration Admin"

    # Runner / deployment (P0)
    runner_mode: str = "api"  # api | worker
    async_runs_enabled: bool = True
    run_chunk_size: int = 500
    worker_poll_seconds: float = 2.0

    # Corporate network (P0)
    http_proxy: str = ""
    https_proxy: str = ""
    client_cert_path: str = ""
    client_key_path: str = ""
    ca_bundle_path: str = ""
    http_timeout_seconds: float = 60.0

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
