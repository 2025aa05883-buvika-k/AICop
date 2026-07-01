import sqlite3
from pathlib import Path
from typing import Any

from backend.config import settings


class AICopDatabase:
    def __init__(self, database_path: str | None = None) -> None:
        self.database_path = Path(database_path or settings.database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _initialize(self) -> None:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS investigations (
                    case_id TEXT PRIMARY KEY,
                    timestamp TEXT NOT NULL,
                    prompt TEXT NOT NULL,
                    response TEXT NOT NULL,
                    security_score REAL,
                    reliability_score REAL,
                    overall_score REAL,
                    overall_risk TEXT,
                    recommendations TEXT,
                    report TEXT
                )
                """
            )
            cursor.execute("PRAGMA table_info(investigations)")
            columns = {row[1] for row in cursor.fetchall()}
            if "report" not in columns:
                cursor.execute("ALTER TABLE investigations ADD COLUMN report TEXT")
            connection.commit()

    def save_case(self, payload: dict[str, Any]) -> None:
        with sqlite3.connect(self.database_path) as connection:
            cursor = connection.cursor()
            cursor.execute(
                """
                INSERT OR REPLACE INTO investigations (
                    case_id, timestamp, prompt, response, security_score, reliability_score,
                    overall_score, overall_risk, recommendations, report
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload["case_id"],
                    payload["timestamp"],
                    payload["prompt"],
                    payload["response"],
                    payload.get("security_score"),
                    payload.get("reliability_score"),
                    payload.get("overall_score"),
                    payload.get("overall_risk"),
                    "\n".join(payload.get("recommendations", [])),
                    payload.get("report", ""),
                ),
            )
            connection.commit()

    def list_cases(self) -> list[dict[str, Any]]:
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            cursor.execute(
                "SELECT case_id, timestamp, prompt, response, security_score, reliability_score, overall_score, overall_risk, recommendations, report FROM investigations ORDER BY timestamp DESC"
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_case(self, case_id: str) -> dict[str, Any] | None:
        with sqlite3.connect(self.database_path) as connection:
            connection.row_factory = sqlite3.Row
            cursor = connection.cursor()
            cursor.execute(
                "SELECT case_id, timestamp, prompt, response, security_score, reliability_score, overall_score, overall_risk, recommendations, report FROM investigations WHERE case_id = ?",
                (case_id,),
            )
            row = cursor.fetchone()
            return dict(row) if row else None
