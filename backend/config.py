from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
DATABASE_PATH = BASE_DIR / "database" / "aicop.db"
REPORTS_DIR = BASE_DIR / "reports" / "generated"
REPORTS_DIR.mkdir(parents=True, exist_ok=True)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=BASE_DIR / ".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "AICop"
    app_version: str = "1.0.0"
    debug: bool = False
    environment: str = "development"
    ollama_model: str = "gemma3:4b"
    ollama_base_url: str = "http://localhost:11434"
    database_path: str = str(DATABASE_PATH)
    reports_path: str = str(REPORTS_DIR)


settings = Settings()
