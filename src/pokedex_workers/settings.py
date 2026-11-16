"""Runtime configuration loaded from the environment."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    redis_url: str = "redis://localhost:6379/0"
    database_url: str = "postgresql+psycopg://pokedex:pokedex@localhost:5432/pokedex_workers"

    s3_bucket: str = "pokedex"
    s3_endpoint_url: str | None = None
    s3_prefix: str = "pokemondb/"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_default_region: str = "us-east-1"

    scrape_min_interval_seconds: float = 1.0
    worker_queues: str = "pipelines characters character_moves moves dexes"


settings = Settings()
