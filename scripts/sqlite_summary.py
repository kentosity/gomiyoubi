from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "gomiyoubi.sqlite"


def parse_args():
    parser = argparse.ArgumentParser(description="Print a summary of the canonical SQLite database.")
    parser.add_argument(
        "--db-path",
        default=str(DB_PATH),
        help="SQLite database path. Defaults to data/gomiyoubi.sqlite",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    db_path = Path(args.db_path)
    if not db_path.exists():
        raise SystemExit(f"Missing database: {db_path}")

    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row

    try:
        summary = {}
        for table_name in (
            "wards",
            "sources",
            "ward_overviews",
            "areas",
            "area_geometries",
            "schedule_rules",
            "schedule_claims",
            "claim_votes",
            "consensus_records",
            "review_tasks",
        ):
            row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
            summary[table_name] = int(row["count"])

        summary["open_review_tasks"] = int(
            connection.execute(
                "SELECT COUNT(*) AS count FROM review_tasks WHERE status = 'open'"
            ).fetchone()["count"]
        )
        summary["user_claims"] = int(
            connection.execute(
                "SELECT COUNT(*) AS count FROM schedule_claims WHERE source_type = 'user_label'"
            ).fetchone()["count"]
        )

        print(json.dumps({"db_path": str(db_path), "summary": summary}, ensure_ascii=False, indent=2))
    finally:
        connection.close()


if __name__ == "__main__":
    main()
