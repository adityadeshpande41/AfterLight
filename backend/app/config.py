from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    app_name: str = "Afterlight Risk Intelligence"
    debug: bool = False

    # Postgres
    database_url: str = "postgresql+asyncpg://afterlight:afterlight@localhost:5433/afterlight"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # S3 / MinIO
    s3_endpoint: str = "http://localhost:9000"
    s3_access_key: str = "minioadmin"
    s3_secret_key: str = "minioadmin"
    s3_bucket: str = "afterlight-evidence"
    s3_region: str = "us-east-1"


settings = Settings()
