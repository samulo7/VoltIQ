from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from urllib.parse import quote_plus

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    db_host: str = os.getenv("VOLTIQ_DB_HOST", "127.0.0.1")
    db_port: int = int(os.getenv("VOLTIQ_DB_PORT", "5432"))
    db_name: str = os.getenv("VOLTIQ_DB_NAME", "voltiq")
    db_user: str = os.getenv("VOLTIQ_DB_USER", "voltiq")
    db_password: str = os.getenv("VOLTIQ_DB_PASSWORD", "voltiq_dev_password")
    dify_base_url: str = os.getenv("VOLTIQ_DIFY_BASE_URL", os.getenv("DIFY_BASE_URL", "http://localhost/v1"))
    dify_api_key: str = os.getenv("VOLTIQ_DIFY_API_KEY", os.getenv("DIFY_API_KEY", "replace_me"))
    dify_request_timeout_seconds: float = float(os.getenv("VOLTIQ_DIFY_REQUEST_TIMEOUT_SECONDS", "30"))
    dify_response_mode: str = os.getenv("VOLTIQ_DIFY_RESPONSE_MODE", "blocking")
    dify_request_max_retries: int = int(os.getenv("VOLTIQ_DIFY_REQUEST_MAX_RETRIES", "2"))
    dify_request_retry_backoff_seconds: float = float(
        os.getenv("VOLTIQ_DIFY_REQUEST_RETRY_BACKOFF_SECONDS", "1")
    )

    @property
    def sqlalchemy_database_uri(self) -> str:
        user = quote_plus(self.db_user)
        password = quote_plus(self.db_password)
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
