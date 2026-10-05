from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional


class ReviewStore:
    """Small SQLite repository for reviews, dispositions, and audit events."""

    def __init__(self, database_path: str | Path):
        self.database_path = Path(database_path)
        self.database_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    def _connect(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys = ON")
        return connection

    def _initialize(self) -> None:
        with self._connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    review_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    file_name TEXT NOT NULL,
                    code_hash TEXT NOT NULL,
                    warnings_hash TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'Pending review',
                    reviewer TEXT,
                    reviewer_notes TEXT,
                    updated_at TEXT NOT NULL,
                    response_json TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS review_events (
                    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    review_id TEXT NOT NULL,
                    event_type TEXT NOT NULL,
                    actor TEXT,
                    detail TEXT,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (review_id) REFERENCES reviews(review_id)
                );
                """
            )

    def save_review(
        self,
        *,
        review_id: str,
        created_at: str,
        file_name: str,
        code_hash: str,
        warnings_hash: str,
        response: Dict[str, Any],
    ) -> None:
        with self._connect() as connection:
            connection.execute(
                """
                INSERT INTO reviews (
                    review_id, created_at, file_name, code_hash, warnings_hash,
                    status, updated_at, response_json
                ) VALUES (?, ?, ?, ?, ?, 'Pending review', ?, ?)
                """,
                (
                    review_id,
                    created_at,
                    file_name,
                    code_hash,
                    warnings_hash,
                    created_at,
                    json.dumps(response, ensure_ascii=True),
                ),
            )
            connection.execute(
                """
                INSERT INTO review_events (review_id, event_type, actor, detail, created_at)
                VALUES (?, 'submitted', 'system', 'Review generated and queued for human approval.', ?)
                """,
                (review_id, created_at),
            )

    def list_reviews(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT review_id, created_at, file_name, status, reviewer, updated_at,
                       json_extract(response_json, '$.confidence') AS confidence,
                       json_array_length(json_extract(response_json, '$.findings')) AS finding_count
                FROM reviews ORDER BY created_at DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def get_review(self, review_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as connection:
            row = connection.execute(
                "SELECT * FROM reviews WHERE review_id = ?", (review_id,)
            ).fetchone()
            if row is None:
                return None
            events = connection.execute(
                """
                SELECT event_type, actor, detail, created_at
                FROM review_events WHERE review_id = ? ORDER BY event_id
                """,
                (review_id,),
            ).fetchall()
        result = dict(row)
        result["response"] = json.loads(result.pop("response_json"))
        result["events"] = [dict(event) for event in events]
        return result

    def update_disposition(
        self,
        *,
        review_id: str,
        status: str,
        reviewer: str,
        notes: str,
        updated_at: str,
    ) -> bool:
        with self._connect() as connection:
            cursor = connection.execute(
                """
                UPDATE reviews
                SET status = ?, reviewer = ?, reviewer_notes = ?, updated_at = ?
                WHERE review_id = ?
                """,
                (status, reviewer, notes, updated_at, review_id),
            )
            if cursor.rowcount == 0:
                return False
            connection.execute(
                """
                INSERT INTO review_events (review_id, event_type, actor, detail, created_at)
                VALUES (?, 'disposition', ?, ?, ?)
                """,
                (review_id, reviewer, f"{status}: {notes}".strip(), updated_at),
            )
        return True

    def metrics(self) -> Dict[str, Any]:
        with self._connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM reviews").fetchone()[0]
            rows = connection.execute(
                "SELECT status, COUNT(*) AS count FROM reviews GROUP BY status"
            ).fetchall()
            finding_total = connection.execute(
                "SELECT COALESCE(SUM(json_array_length(json_extract(response_json, '$.findings'))), 0) FROM reviews"
            ).fetchone()[0]
            average_resolution_hours = connection.execute(
                """
                SELECT AVG((julianday(updated_at) - julianday(created_at)) * 24.0)
                FROM reviews WHERE status != 'Pending review'
                """
            ).fetchone()[0]
        by_status = {str(row["status"]): int(row["count"]) for row in rows}
        completed = sum(
            by_status.get(status, 0)
            for status in ("Accepted", "Rejected", "Needs changes")
        )
        return {
            "total_reviews": int(total),
            "pending_reviews": by_status.get("Pending review", 0),
            "completed_reviews": completed,
            "by_status": by_status,
            "finding_total": int(finding_total or 0),
            "actionable_review_rate": round(completed / total, 4) if total else 0.0,
            "average_disposition_hours": round(float(average_resolution_hours), 3)
            if average_resolution_hours is not None
            else None,
        }

    def approved_findings(self, limit: int = 25) -> List[Dict[str, Any]]:
        """Return bounded findings from reviews explicitly accepted by a human."""
        with self._connect() as connection:
            rows = connection.execute(
                """
                SELECT review_id, reviewer, updated_at, response_json
                FROM reviews WHERE status = 'Accepted'
                ORDER BY updated_at DESC LIMIT ?
                """,
                (max(1, min(limit, 100)),),
            ).fetchall()
        approved: List[Dict[str, Any]] = []
        for row in rows:
            response = json.loads(row["response_json"])
            for finding in (response.get("findings") or [])[:20]:
                approved.append(
                    {
                        "review_id": row["review_id"],
                        "reviewer": row["reviewer"],
                        "approved_at": row["updated_at"],
                        "title": finding.get("title"),
                        "category": finding.get("category"),
                        "recommendation": finding.get("recommendation"),
                        "cwe": finding.get("cwe"),
                    }
                )
                if len(approved) >= limit:
                    return approved
        return approved
