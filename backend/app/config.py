from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    database_url: str = "sqlite:///./data/librislog.db"
    google_books_api_key: str = ""
    cors_origins: List[str] = ["http://localhost", "http://localhost:5173", "http://localhost:4173"]
    log_level: str = "INFO"
    covers_dir: str = "./data/covers"
    api_key_encryption_key: str = "CHANGE_ME_TO_32PLUS_CHARS"
    auth_cookie_name: str = "librislog_session"
    auth_cookie_secure: bool = False
    auth_cookie_samesite: str = "lax"
    auth_cookie_domain: str = ""
    oidc_enabled: bool = False
    oidc_provider_id: str = "oidc"
    oidc_provider_name: str = "Single Sign-On"
    oidc_client_id: str = ""
    oidc_client_secret: str = ""
    oidc_well_known_url: str = ""
    oidc_scope: str = "openid email profile"
    dashboard_quote_enabled: bool = True
    dashboard_quote_url: str = (
        "https://motivational-spark-api.vercel.app/api/quotes/random"
    )


settings = Settings()
