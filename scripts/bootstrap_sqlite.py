from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from tokyo_small_area_boundaries import build_boundary_index, load_ward_small_area_features

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "gomiyoubi.sqlite"
SCHEMA_PATH = ROOT / "data" / "schema.sql"
SOURCE_REGISTRY_PATH = ROOT / "data" / "source-registry.json"
WARD_BOUNDARIES_PATH = ROOT / "public" / "data" / "ward-boundaries.geojson"
CHUO_ZONES_PATH = ROOT / "public" / "data" / "chuo-zones.geojson"
CHUO_UNRESOLVED_PATH = ROOT / "public" / "data" / "chuo-unresolved.json"
WARD_OVERVIEWS_PATH = ROOT / "data" / "seed" / "ward-overviews.json"
NORMALIZED_DIR = ROOT / "data" / "normalized"

DAY_COLUMNS = (
    ("monday", "mondayCategories"),
    ("tuesday", "tuesdayCategories"),
    ("wednesday", "wednesdayCategories"),
    ("thursday", "thursdayCategories"),
    ("friday", "fridayCategories"),
    ("saturday", "saturdayCategories"),
)


def parse_args():
    parser = argparse.ArgumentParser(description="Bootstrap the canonical SQLite database.")
    parser.add_argument(
        "--db-path",
        default=str(DB_PATH),
        help="SQLite database path. Defaults to data/gomiyoubi.sqlite",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Replace the database file if it already exists.",
    )
    return parser.parse_args()


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def execute_schema(connection: sqlite3.Connection):
    connection.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))


def upsert_metadata(connection: sqlite3.Connection, key: str, value: str):
    connection.execute(
        """
        INSERT INTO app_metadata (key, value)
        VALUES (?, ?)
        ON CONFLICT(key) DO UPDATE SET value = excluded.value
        """,
        (key, value),
    )


def insert_ward(connection: sqlite3.Connection, ward: dict) -> int:
    cursor = connection.execute(
        """
        INSERT INTO wards (slug, name_ja, name_en, status, notes_json)
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            ward["ward_slug"],
            ward["ward_name_ja"],
            ward["ward_name_en"],
            ward["status"],
            json.dumps(ward.get("notes", []), ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def insert_source(
    connection: sqlite3.Connection,
    *,
    ward_id: int,
    source_key: str,
    source_kind: str,
    label: str,
    url: str,
    format_value: str | None,
    metadata: dict | None = None,
    coverage_label: str | None = None,
    encoding: str | None = None,
    last_verified: str | None = None,
    is_official: int = 1,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO sources (
          source_key,
          ward_id,
          source_kind,
          label,
          url,
          format,
          is_official,
          encoding,
          coverage_label,
          last_verified,
          metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            source_key,
            ward_id,
            source_kind,
            label,
            url,
            format_value,
            is_official,
            encoding,
            coverage_label,
            last_verified,
            json.dumps(metadata or {}, ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def get_source_id(connection: sqlite3.Connection, source_key: str) -> int | None:
    row = connection.execute("SELECT id FROM sources WHERE source_key = ?", (source_key,)).fetchone()
    return int(row["id"]) if row else None


def get_ward_id(connection: sqlite3.Connection, slug: str) -> int:
    row = connection.execute("SELECT id FROM wards WHERE slug = ?", (slug,)).fetchone()
    if row is None:
        raise ValueError(f"Missing ward for slug={slug}")
    return int(row["id"])


def insert_area(
    connection: sqlite3.Connection,
    *,
    area_key: str,
    ward_id: int,
    parent_area_id: int | None,
    area_kind: str,
    label_ja: str,
    label_en: str | None = None,
    town_ja: str | None = None,
    chome: str | None = None,
    status: str = "active",
    metadata: dict | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO areas (
          area_key,
          ward_id,
          parent_area_id,
          area_kind,
          label_ja,
          label_en,
          town_ja,
          chome,
          status,
          metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            area_key,
            ward_id,
            parent_area_id,
            area_kind,
            label_ja,
            label_en,
            town_ja,
            chome,
            status,
            json.dumps(metadata or {}, ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def insert_ward_overview(
    connection: sqlite3.Connection,
    *,
    ward_id: int,
    source_quality: str,
    source_label: str,
    granularity: str,
    notes: list,
    day_signals: dict,
):
    connection.execute(
        """
        INSERT INTO ward_overviews (
          ward_id,
          source_quality,
          source_label,
          granularity,
          notes_json,
          day_signals_json
        )
        VALUES (?, ?, ?, ?, ?, ?)
        ON CONFLICT(ward_id) DO UPDATE SET
          source_quality = excluded.source_quality,
          source_label = excluded.source_label,
          granularity = excluded.granularity,
          notes_json = excluded.notes_json,
          day_signals_json = excluded.day_signals_json,
          updated_at = CURRENT_TIMESTAMP
        """,
        (
            ward_id,
            source_quality,
            source_label,
            granularity,
            json.dumps(notes, ensure_ascii=False),
            json.dumps(day_signals, ensure_ascii=False),
        ),
    )


def get_area_id(connection: sqlite3.Connection, area_key: str) -> int | None:
    row = connection.execute("SELECT id FROM areas WHERE area_key = ?", (area_key,)).fetchone()
    return int(row["id"]) if row else None


def insert_source_artifact(
    connection: sqlite3.Connection,
    *,
    artifact_key: str,
    source_id: int,
    artifact_kind: str,
    local_path: str | None,
    content_type: str | None,
    sha256: str | None = None,
    fetched_at: str | None = None,
    parser_version: str | None = None,
    ocr_engine: str | None = None,
    metadata: dict | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO source_artifacts (
          artifact_key,
          source_id,
          artifact_kind,
          local_path,
          content_type,
          sha256,
          fetched_at,
          parser_version,
          ocr_engine,
          metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            artifact_key,
            source_id,
            artifact_kind,
            local_path,
            content_type,
            sha256,
            fetched_at,
            parser_version,
            ocr_engine,
            json.dumps(metadata or {}, ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def get_artifact_id(connection: sqlite3.Connection, artifact_key: str) -> int | None:
    row = connection.execute(
        "SELECT id FROM source_artifacts WHERE artifact_key = ?",
        (artifact_key,),
    ).fetchone()
    return int(row["id"]) if row else None


def insert_area_geometry(
    connection: sqlite3.Connection,
    *,
    geometry_key: str,
    area_id: int,
    geometry_source_id: int | None,
    boundary_key: str | None,
    boundary_name: str | None,
    part_index: int,
    geometry: dict,
    metadata: dict | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO area_geometries (
          geometry_key,
          area_id,
          geometry_source_id,
          boundary_key,
          boundary_name,
          part_index,
          geometry_json,
          metadata_json
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            geometry_key,
            area_id,
            geometry_source_id,
            boundary_key,
            boundary_name,
            part_index,
            json.dumps(geometry, ensure_ascii=False),
            json.dumps(metadata or {}, ensure_ascii=False),
        ),
    )
    return int(cursor.lastrowid)


def get_rule_id(connection: sqlite3.Connection, day: str) -> int:
    rule_key = f"weekly:{day}"
    row = connection.execute("SELECT id FROM schedule_rules WHERE rule_key = ?", (rule_key,)).fetchone()
    if row is not None:
        return int(row["id"])

    cursor = connection.execute(
        """
        INSERT INTO schedule_rules (rule_key, rule_type, rule_json, description)
        VALUES (?, 'weekly', ?, ?)
        """,
        (
            rule_key,
            json.dumps({"day": day}, ensure_ascii=False),
            f"Weekly pickup on {day}",
        ),
    )
    return int(cursor.lastrowid)


def get_or_create_rule(
    connection: sqlite3.Connection,
    *,
    rule_key: str,
    rule_type: str,
    rule_json: dict,
    description: str | None = None,
) -> int:
    row = connection.execute("SELECT id FROM schedule_rules WHERE rule_key = ?", (rule_key,)).fetchone()
    if row is not None:
        return int(row["id"])

    cursor = connection.execute(
        """
        INSERT INTO schedule_rules (rule_key, rule_type, rule_json, description)
        VALUES (?, ?, ?, ?)
        """,
        (
            rule_key,
            rule_type,
            json.dumps(rule_json, ensure_ascii=False),
            description,
        ),
    )
    return int(cursor.lastrowid)


def insert_schedule_claim(
    connection: sqlite3.Connection,
    *,
    claim_key: str,
    ward_id: int,
    area_id: int,
    category: str,
    rule_id: int,
    source_id: int | None,
    source_type: str,
    submitted_by: str,
    confidence: float,
    evidence: dict | None = None,
    note: str | None = None,
) -> int:
    cursor = connection.execute(
        """
        INSERT INTO schedule_claims (
          claim_key,
          ward_id,
          area_id,
          category,
          rule_id,
          source_id,
          source_type,
          confidence,
          submitted_by,
          evidence_json,
          note
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            claim_key,
            ward_id,
            area_id,
            category,
            rule_id,
            source_id,
            source_type,
            confidence,
            submitted_by,
            json.dumps(evidence or {}, ensure_ascii=False),
            note,
        ),
    )
    return int(cursor.lastrowid)


def insert_consensus_record(
    connection: sqlite3.Connection,
    *,
    ward_id: int,
    area_id: int,
    category: str,
    rule_id: int,
    resolved_claim_id: int,
    resolution_method: str,
    confidence: float,
):
    connection.execute(
        """
        INSERT INTO consensus_records (
          ward_id,
          area_id,
          category,
          rule_id,
          resolved_claim_id,
          resolution_method,
          confidence
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            ward_id,
            area_id,
            category,
            rule_id,
            resolved_claim_id,
            resolution_method,
            confidence,
        ),
    )


def insert_review_task(
    connection: sqlite3.Connection,
    *,
    task_key: str,
    ward_id: int,
    source_id: int | None,
    task_type: str,
    title: str,
    payload: dict,
    created_by: str,
):
    connection.execute(
        """
        INSERT INTO review_tasks (
          task_key,
          ward_id,
          source_id,
          task_type,
          title,
          payload_json,
          created_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            task_key,
            ward_id,
            source_id,
            task_type,
            title,
            json.dumps(payload, ensure_ascii=False),
            created_by,
        ),
        )


def ensure_estat_boundary_source(connection: sqlite3.Connection, ward_id: int, ward_slug: str, ward_name_ja: str) -> int:
    source_key = f"{ward_slug}:boundary:e-stat"
    existing_id = get_source_id(connection, source_key)
    if existing_id is not None:
        return existing_id

    return insert_source(
        connection,
        ward_id=ward_id,
        source_key=source_key,
        source_kind="boundary",
        label=f"{ward_name_ja} 町丁・字等別境界",
        url="https://www.e-stat.go.jp/gis/statmap-search/data",
        format_value="shape",
        metadata={"source_label": "e-Stat 町丁・字等別境界"},
        is_official=0,
    )


def bootstrap_geometry_memberships(
    connection: sqlite3.Connection,
    *,
    ward_id: int,
    ward_slug: str,
    ward_name_ja: str,
    area_ids_by_key: dict[str, int],
    memberships: list[dict],
):
    if not memberships:
        return

    boundary_features = load_ward_small_area_features(ward_slug)
    features_by_town, features_by_town_chome = build_boundary_index(boundary_features)
    boundary_source_id = ensure_estat_boundary_source(connection, ward_id, ward_slug, ward_name_ja)

    for membership in memberships:
        area_key = membership["area_key"]
        area_id = area_ids_by_key.get(area_key) or get_area_id(connection, area_key)
        if area_id is None:
            raise ValueError(f"Missing area for geometry membership: {area_key}")

        matched_features: list[dict] = []
        seen_boundary_keys: set[str] = set()

        for member in membership.get("members", []):
            town_ja = str(member["town_ja"])
            chomes = member.get("chomes") or []

            if chomes:
                for chome in chomes:
                    feature = features_by_town_chome.get((town_ja, str(chome)))
                    if feature is None:
                        raise ValueError(f"Missing boundary match for {ward_slug} {town_ja}{chome}丁目")
                    boundary_key = str(feature["boundary_key"])
                    if boundary_key not in seen_boundary_keys:
                        seen_boundary_keys.add(boundary_key)
                        matched_features.append(feature)
                continue

            town_features = features_by_town.get(town_ja)
            if not town_features:
                raise ValueError(f"Missing boundary match for {ward_slug} {town_ja}")
            for feature in town_features:
                boundary_key = str(feature["boundary_key"])
                if boundary_key not in seen_boundary_keys:
                    seen_boundary_keys.add(boundary_key)
                    matched_features.append(feature)

        for part_index, feature in enumerate(matched_features):
            insert_area_geometry(
                connection,
                geometry_key=f"{area_key}:geometry:{part_index}",
                area_id=area_id,
                geometry_source_id=boundary_source_id,
                boundary_key=str(feature["boundary_key"]),
                boundary_name=str(feature["boundary_name"]),
                part_index=part_index,
                geometry=feature["geometry"],
                metadata={
                    "source_url": membership.get("selector_source_urls", [None])[0],
                    "selector_source_label": membership.get("selector_source_label"),
                },
            )


def bootstrap_normalized_datasets(connection: sqlite3.Connection):
    if not NORMALIZED_DIR.exists():
        return

    for path in sorted(NORMALIZED_DIR.glob("*/*.json")):
        dataset = load_json(path)
        ward_slug = dataset.get("ward_slug")
        if not ward_slug:
            continue

        ward_id = get_ward_id(connection, ward_slug)
        ward_name_ja = connection.execute(
            "SELECT name_ja FROM wards WHERE id = ?",
            (ward_id,),
        ).fetchone()["name_ja"]

        overview = dataset.get("overview")
        if overview:
            insert_ward_overview(
                connection,
                ward_id=ward_id,
                source_quality=overview["source_quality"],
                source_label=overview["source_label"],
                granularity=overview["granularity"],
                notes=overview.get("notes", []),
                day_signals=overview.get("day_signals", {}),
            )

        artifact_ids_by_key: dict[str, int] = {}
        artifact_rows = dataset.get("artifacts") or dataset.get("source_artifacts") or []
        for artifact in artifact_rows:
            source_id = get_source_id(connection, artifact["source_key"])
            if source_id is None:
                raise ValueError(f"Missing source for artifact: {artifact['source_key']}")

            artifact_id = insert_source_artifact(
                connection,
                artifact_key=artifact["artifact_key"],
                source_id=source_id,
                artifact_kind=artifact["artifact_kind"],
                local_path=artifact.get("local_path"),
                content_type=artifact.get("content_type"),
                sha256=artifact.get("sha256"),
                fetched_at=artifact.get("fetched_at"),
                parser_version=artifact.get("parser_version"),
                ocr_engine=artifact.get("ocr_engine"),
                metadata=artifact.get("metadata"),
            )
            artifact_ids_by_key[artifact["artifact_key"]] = artifact_id

        area_ids_by_key = {}
        for area in dataset.get("areas", []):
            parent_area_key = area.get("parent_area_key")
            parent_area_id = get_area_id(connection, parent_area_key) if parent_area_key else None
            area_id = insert_area(
                connection,
                area_key=area["area_key"],
                ward_id=ward_id,
                parent_area_id=parent_area_id,
                area_kind=area["area_kind"],
                label_ja=area["label_ja"],
                label_en=area.get("label_en"),
                town_ja=area.get("town_ja"),
                chome=area.get("chome"),
                status=area.get("status", "active"),
                metadata=area.get("metadata"),
            )
            area_ids_by_key[area["area_key"]] = area_id

        bootstrap_geometry_memberships(
            connection,
            ward_id=ward_id,
            ward_slug=ward_slug,
            ward_name_ja=str(ward_name_ja),
            area_ids_by_key=area_ids_by_key,
            memberships=dataset.get("geometry_memberships", []),
        )

        for claim in dataset.get("claims", []):
            area_id = area_ids_by_key.get(claim["area_key"]) or get_area_id(connection, claim["area_key"])
            if area_id is None:
                raise ValueError(f"Missing area for claim: {claim['area_key']}")

            rule = claim["rule"]
            rule_id = get_or_create_rule(
                connection,
                rule_key=rule["rule_key"],
                rule_type=rule["rule_type"],
                rule_json=rule["rule_json"],
                description=rule.get("description"),
            )
            source_id = get_source_id(connection, claim["source_key"]) if claim.get("source_key") else None
            artifact_id = (
                artifact_ids_by_key.get(claim["artifact_key"]) or get_artifact_id(connection, claim["artifact_key"])
                if claim.get("artifact_key")
                else None
            )

            claim_id = connection.execute(
                """
                INSERT INTO schedule_claims (
                  claim_key,
                  ward_id,
                  area_id,
                  category,
                  rule_id,
                  source_id,
                  artifact_id,
                  source_type,
                  effective_from,
                  effective_to,
                  confidence,
                  submitted_by,
                  evidence_json,
                  note
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    claim["claim_key"],
                    ward_id,
                    area_id,
                    claim["category"],
                    rule_id,
                    source_id,
                    artifact_id,
                    claim["source_type"],
                    claim.get("effective_from"),
                    claim.get("effective_to"),
                    claim["confidence"],
                    claim["submitted_by"],
                    json.dumps(claim.get("evidence", {}), ensure_ascii=False),
                    claim.get("note"),
                ),
            ).lastrowid

            connection.execute(
                """
                INSERT INTO consensus_records (
                  ward_id,
                  area_id,
                  category,
                  rule_id,
                  resolved_claim_id,
                  resolution_method,
                  confidence
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    ward_id,
                    area_id,
                    claim["category"],
                    rule_id,
                    int(claim_id),
                    claim.get("resolution_method", "official_priority"),
                    claim["confidence"],
                ),
            )

        for task in dataset.get("review_tasks", []):
            source_id = get_source_id(connection, task["source_key"]) if task.get("source_key") else None
            area_id = area_ids_by_key.get(task["area_key"]) if task.get("area_key") else None
            connection.execute(
                """
                INSERT INTO review_tasks (
                  task_key,
                  ward_id,
                  area_id,
                  source_id,
                  task_type,
                  title,
                  payload_json,
                  created_by
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    task["task_key"],
                    ward_id,
                    area_id,
                    source_id,
                    task["task_type"],
                    task["title"],
                    json.dumps(task.get("payload", {}), ensure_ascii=False),
                    task["created_by"],
                ),
            )


def bootstrap_sources(connection: sqlite3.Connection):
    registry = load_json(SOURCE_REGISTRY_PATH)
    upsert_metadata(connection, "source_registry_updated_at", str(registry.get("updated_at", "")))
    upsert_metadata(connection, "source_registry_scope_json", json.dumps(registry.get("scope", [])))

    for ward in registry["wards"]:
        ward_id = insert_ward(connection, ward)
        official_sources = ward.get("official_sources", {})
        entry_page = official_sources.get("entry_page")

        if entry_page:
            insert_source(
                connection,
                ward_id=ward_id,
                source_key=f"{ward['ward_slug']}:entry_page",
                source_kind="entry_page",
                label=entry_page["label"],
                url=entry_page["url"],
                format_value=entry_page.get("format"),
                coverage_label=None,
                encoding=entry_page.get("encoding"),
                last_verified=entry_page.get("last_verified"),
            )

        for index, download in enumerate(official_sources.get("downloads", []), start=1):
            insert_source(
                connection,
                ward_id=ward_id,
                source_key=f"{ward['ward_slug']}:download:{index:02d}",
                source_kind="download",
                label=download["label"],
                url=download["url"],
                format_value=download.get("format"),
                coverage_label=download.get("coverage"),
                encoding=download.get("encoding"),
            )

        for index, related_page in enumerate(official_sources.get("related_pages", []), start=1):
            insert_source(
                connection,
                ward_id=ward_id,
                source_key=f"{ward['ward_slug']}:related_page:{index:02d}",
                source_kind="related_page",
                label=related_page["label"],
                url=related_page["url"],
                format_value=related_page.get("format"),
            )


def bootstrap_ward_overviews(connection: sqlite3.Connection):
    if not WARD_OVERVIEWS_PATH.exists():
        return

    overviews = load_json(WARD_OVERVIEWS_PATH)
    for overview in overviews:
        ward_id = get_ward_id(connection, overview["ward_slug"])
        insert_ward_overview(
            connection,
            ward_id=ward_id,
            source_quality=overview["source_quality"],
            source_label=overview["source_label"],
            granularity=overview["granularity"],
            notes=overview.get("notes", []),
            day_signals=overview.get("day_signals", {}),
        )


def bootstrap_ward_boundaries(connection: sqlite3.Connection):
    collection = load_json(WARD_BOUNDARIES_PATH)

    for feature in collection["features"]:
        properties = feature["properties"]
        slug = str(properties["slug"])
        ward_id = get_ward_id(connection, slug)

        boundary_source_id = insert_source(
            connection,
            ward_id=ward_id,
            source_key=f"{slug}:boundary:nominatim",
            source_kind="boundary",
            label=f"{properties['nameJa']} ward boundary",
            url="https://nominatim.openstreetmap.org/search",
            format_value="geojson",
            metadata={"source_label": properties.get("source")},
            is_official=0,
        )

        area_key = f"ward:{slug}"
        area_id = insert_area(
            connection,
            area_key=area_key,
            ward_id=ward_id,
            parent_area_id=None,
            area_kind="ward",
            label_ja=str(properties["nameJa"]),
            label_en=str(properties.get("nameEn") or ""),
            metadata={"slug": slug},
        )

        insert_area_geometry(
            connection,
            geometry_key=f"{area_key}:geometry:0",
            area_id=area_id,
            geometry_source_id=boundary_source_id,
            boundary_key=slug,
            boundary_name=str(properties["nameJa"]),
            part_index=0,
            geometry=feature["geometry"],
            metadata={"source_label": properties.get("source")},
        )


def bootstrap_chuo_zones(connection: sqlite3.Connection):
    collection = load_json(CHUO_ZONES_PATH)
    chuo_ward_id = get_ward_id(connection, "chuo")
    chuo_ward_area_id = get_area_id(connection, "ward:chuo")
    if chuo_ward_area_id is None:
        raise ValueError("Missing ward:chuo area")

    csv_source_id = get_source_id(connection, "chuo:download:01")
    if csv_source_id is None:
        raise ValueError("Missing chuo:download:01 source")

    boundary_source_id = insert_source(
        connection,
        ward_id=chuo_ward_id,
        source_key="chuo:boundary:e-stat",
        source_kind="boundary",
        label="中央区 町丁・字等別境界",
        url="https://www.e-stat.go.jp/gis/statmap-search/data",
        format_value="shape",
        metadata={"derived_from": "scripts/build_chuo_zones.py"},
        is_official=0,
    )

    geometry_part_counts: dict[str, int] = {}
    claims_seen: set[str] = set()

    for feature in collection["features"]:
        properties = feature["properties"]
        zone_id = str(properties["zoneId"])
        area_key = f"chuo:zone:{zone_id}"
        area_id = get_area_id(connection, area_key)

        if area_id is None:
            area_kind = "town" if properties.get("precision") == "town" else "chome"
            chome = None if properties.get("chome") is None else str(properties.get("chome"))
            area_id = insert_area(
                connection,
                area_key=area_key,
                ward_id=chuo_ward_id,
                parent_area_id=chuo_ward_area_id,
                area_kind=area_kind,
                label_ja=str(properties["labelJa"]),
                town_ja=str(properties.get("townJa") or ""),
                chome=chome,
                metadata={
                    "zone_id": zone_id,
                    "precision": properties.get("precision"),
                    "source_town_ja": properties.get("sourceTownJa"),
                    "region_ja": properties.get("regionJa"),
                },
            )

        part_index = geometry_part_counts.get(area_key, 0)
        geometry_part_counts[area_key] = part_index + 1

        insert_area_geometry(
            connection,
            geometry_key=f"{area_key}:geometry:{part_index}",
            area_id=area_id,
            geometry_source_id=boundary_source_id,
            boundary_key=str(properties.get("boundaryKeyCode") or ""),
            boundary_name=str(properties.get("boundaryName") or ""),
            part_index=part_index,
            geometry=feature["geometry"],
            metadata={"source_url": properties.get("boundarySourceUrl")},
        )

        for day, property_name in DAY_COLUMNS:
            raw_categories = str(properties.get(property_name) or "")
            categories = [value for value in raw_categories.split(",") if value]
            if not categories:
                continue

            rule_id = get_rule_id(connection, day)

            for category in categories:
                claim_key = f"{area_key}:weekly:{day}:{category}:official"
                if claim_key in claims_seen:
                    continue

                claim_id = insert_schedule_claim(
                    connection,
                    claim_key=claim_key,
                    ward_id=chuo_ward_id,
                    area_id=area_id,
                    category=category,
                    rule_id=rule_id,
                    source_id=csv_source_id,
                    source_type="official",
                    submitted_by="system/bootstrap",
                    confidence=1.0,
                    evidence={
                        "source_url": properties.get("sourceUrl"),
                        "boundary_name": properties.get("boundaryName"),
                    },
                    note="Bootstrapped from public/data/chuo-zones.geojson",
                )
                insert_consensus_record(
                    connection,
                    ward_id=chuo_ward_id,
                    area_id=area_id,
                    category=category,
                    rule_id=rule_id,
                    resolved_claim_id=claim_id,
                    resolution_method="official_priority",
                    confidence=1.0,
                )
                claims_seen.add(claim_key)


def bootstrap_chuo_review_tasks(connection: sqlite3.Connection):
    rows = load_json(CHUO_UNRESOLVED_PATH)
    chuo_ward_id = get_ward_id(connection, "chuo")
    csv_source_id = get_source_id(connection, "chuo:download:01")

    for index, row in enumerate(rows, start=1):
        title = f"中央区 未解決行 {row.get('町名', '')} {row.get('丁目', '')}".strip()
        insert_review_task(
            connection,
            task_key=f"chuo:review:unresolved:{index:03d}",
            ward_id=chuo_ward_id,
            source_id=csv_source_id,
            task_type="area_match",
            title=title,
            payload=row,
            created_by="system/bootstrap",
        )


def summarize(connection: sqlite3.Connection) -> dict:
    counts = {}
    for table_name in (
        "wards",
        "sources",
        "ward_overviews",
        "areas",
        "area_geometries",
        "schedule_rules",
        "schedule_claims",
        "consensus_records",
        "review_tasks",
    ):
        row = connection.execute(f"SELECT COUNT(*) AS count FROM {table_name}").fetchone()
        counts[table_name] = int(row["count"])
    return counts


def main():
    args = parse_args()
    db_path = Path(args.db_path)
    db_path.parent.mkdir(parents=True, exist_ok=True)

    if db_path.exists():
        if not args.force:
            raise SystemExit(f"{db_path} already exists. Re-run with --force to replace it.")
        db_path.unlink()

    connection = connect(db_path)

    try:
        execute_schema(connection)
        bootstrap_sources(connection)
        bootstrap_ward_overviews(connection)
        bootstrap_ward_boundaries(connection)
        bootstrap_normalized_datasets(connection)
        bootstrap_chuo_zones(connection)
        bootstrap_chuo_review_tasks(connection)
        upsert_metadata(connection, "bootstrap_script", "scripts/bootstrap_sqlite.py")
        connection.commit()
        print(
            json.dumps(
                {
                    "db_path": str(db_path),
                    "counts": summarize(connection),
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    finally:
        connection.close()


if __name__ == "__main__":
    main()
