from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """All runtime config. Override via .env or environment variables."""

    # Which adapter to use: sample | newsapi | gnews | newsdata
    news_provider: str = "sample"
    # API key for the chosen provider (leave blank for 'sample')
    news_api_key: str = ""
    # What "national" means for this deployment (ISO-3166 alpha-2)
    news_country: str = "us"
    news_language: str = "en"
    # Cache lifetime for provider responses, in seconds
    cache_ttl: int = 600
    # How many hours of news to retain in SQLite for outage fallback
    retention_hours: int = 6
    # SQLite file for the rolling news cache (used only when DATABASE_URL is empty)
    db_path: str = "newsfold.db"
    # Postgres/Supabase connection string. When set, used instead of SQLite.
    database_url: str = ""
    # Comma-separated list of allowed front-end origins
    cors_origins: str = "http://localhost:5173,http://localhost:3000"

    # --- Newsletter digest / email ---
    api_base_url: str = "http://localhost:8000"     # backend's public URL (unsubscribe links)
    app_base_url: str = "http://localhost:5173"     # frontend URL (for email "open app")
    digest_token: str = ""                          # shared secret to trigger a send
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    from_email: str = ""
    from_name: str = "Newsfold"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


settings = Settings()
