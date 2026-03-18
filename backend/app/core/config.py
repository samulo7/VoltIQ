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
