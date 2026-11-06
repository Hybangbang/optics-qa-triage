"""Environment-backed configuration.

No dependency on python-dotenv: a small parser keeps the runtime footprint
small and makes the public repository easy to audit.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _parse_bool(value: str | None, default: bool = False) -> bool:
    if value is None or value == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "y", "on"}


def _read_dotenv(path: Path) -> None:
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def load_dotenv() -> None:
    candidates = [Path.cwd() / ".env", PROJECT_ROOT / ".env"]
    seen: set[Path] = set()
    for candidate in candidates:
        resolved = candidate.resolve()
        if resolved in seen:
            continue
        seen.add(resolved)
        _read_dotenv(resolved)


@dataclass(frozen=True)
class Settings:
    db_path: Path
    outbox_dir: Path
    retention_hours: int
    subreddit: str
    reddit_client_id: str
    reddit_client_secret: str
    reddit_user_agent: str
    reddit_api_approved: bool
    llm_base_url: str
    llm_api_key: str
    llm_model: str
    llm_store: bool
    llm_timeout_seconds: int
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    email_to: str

    @property
    def email_configured(self) -> bool:
        return bool(self.smtp_host and self.email_to)

    @property
    def llm_configured(self) -> bool:
        return bool(self.llm_api_key)


def load_settings() -> Settings:
    load_dotenv()

    retention = int(os.getenv("RETENTION_HOURS", "48"))
    if retention < 1 or retention > 48:
        raise ValueError("RETENTION_HOURS must be between 1 and 48")

    db_path = Path(os.getenv("OPTICS_QA_DB", str(PROJECT_ROOT / "var" / "optics_qa.sqlite3")))
    outbox_dir = Path(os.getenv("OPTICS_QA_OUTBOX", str(PROJECT_ROOT / "outbox")))

    settings = Settings(
        db_path=db_path,
        outbox_dir=outbox_dir,
        retention_hours=retention,
        subreddit=os.getenv("REDDIT_SUBREDDIT", "Optics").strip() or "Optics",
        reddit_client_id=os.getenv("REDDIT_CLIENT_ID", "").strip(),
        reddit_client_secret=os.getenv("REDDIT_CLIENT_SECRET", "").strip(),
        reddit_user_agent=os.getenv("REDDIT_USER_AGENT", "").strip(),
        reddit_api_approved=_parse_bool(os.getenv("REDDIT_API_APPROVED"), False),
        llm_base_url=os.getenv("LLM_BASE_URL", "https://api.openai.com/v1").rstrip("/"),
        llm_api_key=os.getenv("LLM_API_KEY", "").strip(),
        llm_model=os.getenv("LLM_MODEL", "gpt-4.1-mini").strip(),
        llm_store=_parse_bool(os.getenv("LLM_STORE"), False),
        llm_timeout_seconds=int(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
        smtp_host=os.getenv("SMTP_HOST", "").strip(),
        smtp_port=int(os.getenv("SMTP_PORT", "587")),
        smtp_user=os.getenv("SMTP_USER", "").strip(),
        smtp_password=os.getenv("SMTP_PASSWORD", ""),
        email_to=os.getenv("EMAIL_TO", "").strip(),
    )

    if settings.retention_hours > 48:
        raise ValueError("Reddit guidance recommends deleting content within 48 hours")

    settings.db_path.parent.mkdir(parents=True, exist_ok=True)
    settings.outbox_dir.mkdir(parents=True, exist_ok=True)
    return settings
