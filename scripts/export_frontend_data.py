from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DB_PATH = ROOT / "data" / "gomiyoubi.sqlite"
OUTPUT_DIR = ROOT / "public" / "data"

WARD_BOUNDARIES_PATH = OUTPUT_DIR / "ward-boundaries.geojson"
WARD_OVERVIEWS_PATH = OUTPUT_DIR / "ward-overviews.json"
DETAILED_AREAS_PATH = OUTPUT_DIR / "detailed-areas.geojson"
CHUO_ZONES_PATH = OUTPUT_DIR / "chuo-zones.geojson"
CHUO_UNRESOLVED_PATH = OUTPUT_DIR / "chuo-unresolved.json"

DAY_ORDER = ("sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday")
CATEGORY_ORDER = ("burnable", "nonburnable", "plastic", "resource", "bulky")


def parse_args():
    parser = argparse.ArgumentParser(
        description="Export frontend-facing public/data artifacts from the canonical SQLite database."
    )
    parser.add_argument(
        "--db-path",
        default=str(DB_PATH),
        help="SQLite database path. Defaults to data/gomiyoubi.sqlite",
    )
    parser.add_argument(
        "--output-dir",
        default=str(OUTPUT_DIR),
        help="Output directory for public artifacts. Defaults to public/data",
    )
    return parser.parse_args()


def connect(db_path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(db_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_json(value: str | None, default):
    if value is None or value == "":
        return default
    return json.loads(value)


def table_exists(connection: sqlite3.Connection, table_name: str) -> bool:
    row = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    ).fetchone()
    return row is not None


def build_ward_day_signals(connection: sqlite3.Connection) -> dict[str, dict[str, list[dict[str, int | str]]]]:
    rows = connection.execute(
        """
        SELECT
          w.slug AS ward_slug,
          sr.rule_json,
          cr.category,
          COUNT(DISTINCT a.id) AS area_count
        FROM consensus_records cr
        JOIN areas a ON a.id = cr.area_id
        JOIN wards w ON w.id = a.ward_id
        JOIN schedule_rules sr ON sr.id = cr.rule_id
        WHERE a.area_kind <> 'ward'
          AND sr.rule_type = 'weekly'
        GROUP BY w.slug, sr.rule_json, cr.category
        ORDER BY w.slug, cr.category
        """
    ).fetchall()

    signals_by_ward: dict[str, dict[str, list[dict[str, int | str]]]] = {}

    for row in rows:
        ward_slug = str(row["ward_slug"])
        day = str(parse_json(row["rule_json"], {}).get("day") or "")
        if day not in DAY_ORDER:
            continue

        ward_signals = signals_by_ward.setdefault(ward_slug, {})
        day_signals = ward_signals.setdefault(day, [])
        day_signals.append(
            {
                "category": str(row["category"]),
                "areas": int(row["area_count"]),
            }
        )

    for ward_signals in signals_by_ward.values():
        for day, signals in ward_signals.items():
            ward_signals[day] = sorted(
                signals,
                key=lambda signal: CATEGORY_ORDER.index(str(signal["category"]))
                if str(signal["category"]) in CATEGORY_ORDER
                else len(CATEGORY_ORDER),
            )

    return signals_by_ward


def numeric_chome_or_text(value: str | None):
    if value is None or value == "":
        return None
    if value.isdigit():
        return int(value)
    return value


def export_ward_boundaries(connection: sqlite3.Connection):
    rows = connection.execute(
        """
        SELECT
          a.area_key,
          a.label_ja,
          a.label_en,
          a.metadata_json AS area_metadata_json,
          ag.geometry_json,
          s.label AS source_label,
          s.metadata_json AS source_metadata_json
        FROM areas a
        JOIN area_geometries ag ON ag.area_id = a.id
        LEFT JOIN sources s ON s.id = ag.geometry_source_id
        WHERE a.area_kind = 'ward'
          AND a.status = 'active'
          AND ag.status = 'active'
        ORDER BY a.id, ag.part_index
        """
    ).fetchall()

    features = []

    for row in rows:
        area_metadata = parse_json(row["area_metadata_json"], {})
        source_metadata = parse_json(row["source_metadata_json"], {})
        slug = str(area_metadata.get("slug") or str(row["area_key"]).split(":", 1)[-1])
        source_label = source_metadata.get("source_label") or row["source_label"]

        features.append(
            {
                "type": "Feature",
                "properties": {
                    "slug": slug,
                    "nameJa": row["label_ja"],
                    "nameEn": row["label_en"] or slug.title(),
                    "source": source_label,
                },
                "geometry": parse_json(row["geometry_json"], {}),
            }
        )

    return {"type": "FeatureCollection", "features": features}


def export_ward_overviews(connection: sqlite3.Connection):
    derived_day_signals = build_ward_day_signals(connection)
    rows = connection.execute(
        """
        SELECT
          w.slug,
          w.name_ja,
          w.name_en,
          wo.source_quality,
          wo.source_label,
          (
            SELECT s.url
            FROM sources s
            WHERE s.ward_id = w.id
              AND s.is_official = 1
              AND s.url IS NOT NULL
              AND s.url <> ''
            ORDER BY CASE s.source_kind WHEN 'entry_page' THEN 0 ELSE 1 END, s.id
            LIMIT 1
          ) AS source_url,
          wo.granularity,
          wo.notes_json,
          wo.day_signals_json,
          EXISTS (
            SELECT 1
            FROM areas a
            JOIN area_geometries ag ON ag.area_id = a.id
            WHERE a.ward_id = w.id
              AND a.area_kind <> 'ward'
              AND a.status = 'active'
              AND ag.status = 'active'
          ) AS has_detailed_areas
        FROM wards w
        LEFT JOIN ward_overviews wo ON wo.ward_id = w.id
        ORDER BY w.slug
        """
    ).fetchall()

    return [
        {
            "wardSlug": row["slug"],
            "wardNameJa": row["name_ja"],
            "wardNameEn": row["name_en"] or row["slug"].title(),
            "sourceQuality": row["source_quality"] or "pending",
            "sourceLabel": row["source_label"] or "データソース未設定",
            "sourceUrl": row["source_url"],
            "granularity": row["granularity"] or "",
            "notes": parse_json(row["notes_json"], []),
            "daySignals": derived_day_signals.get(row["slug"]) or parse_json(row["day_signals_json"], {}),
            "hasDetailedAreas": bool(row["has_detailed_areas"]),
        }
        for row in rows
    ]


def build_categories_by_area(connection: sqlite3.Connection):
    categories_by_area: dict[int, dict[str, list[str]]] = {}
    source_url_by_area_id: dict[int, str] = {}

    rows = connection.execute(
        """
        SELECT
          a.id AS area_id,
          cr.category,
          sr.rule_json,
          sc.evidence_json,
          s.url AS source_url
        FROM consensus_records cr
        JOIN areas a ON a.id = cr.area_id
        JOIN schedule_rules sr ON sr.id = cr.rule_id
        JOIN schedule_claims sc ON sc.id = cr.resolved_claim_id
        LEFT JOIN sources s ON s.id = sc.source_id
        WHERE a.area_kind <> 'ward'
          AND sr.rule_type = 'weekly'
        ORDER BY a.id, cr.id
        """
    ).fetchall()

    for row in rows:
        area_id = int(row["area_id"])
        rule = parse_json(row["rule_json"], {})
        evidence = parse_json(row["evidence_json"], {})
        day = str(rule.get("day") or "")
        if day not in DAY_ORDER:
            continue

        area_categories = categories_by_area.setdefault(
            area_id, {weekday: [] for weekday in DAY_ORDER}
        )
        category = str(row["category"])
        if category not in area_categories[day]:
            area_categories[day].append(category)

        source_url = evidence.get("source_url") or row["source_url"]
        if source_url and area_id not in source_url_by_area_id:
            source_url_by_area_id[area_id] = str(source_url)

    return categories_by_area, source_url_by_area_id


def export_chuo_zones(connection: sqlite3.Connection):
    source_quality_by_ward_id: dict[int, str] = {}
    if table_exists(connection, "ward_overviews"):
        for row in connection.execute("SELECT ward_id, source_quality FROM ward_overviews"):
            source_quality_by_ward_id[int(row["ward_id"])] = str(row["source_quality"])

    area_properties_by_id: dict[int, dict] = {}
    area_categories_by_id: dict[int, dict[str, list[str]]] = {}
    source_url_by_area_id: dict[int, str] = {}

    rows = connection.execute(
        """
        SELECT
          a.id AS area_id,
          a.area_key,
          a.ward_id,
          a.label_ja,
          a.town_ja,
          a.chome,
          a.metadata_json AS area_metadata_json,
          w.slug AS ward_slug,
          w.name_ja AS ward_name_ja,
          cr.category,
          sr.rule_json,
          sc.evidence_json,
          s.url AS source_url
        FROM consensus_records cr
        JOIN areas a ON a.id = cr.area_id
        JOIN wards w ON w.id = a.ward_id
        JOIN schedule_rules sr ON sr.id = cr.rule_id
        JOIN schedule_claims sc ON sc.id = cr.resolved_claim_id
        LEFT JOIN sources s ON s.id = sc.source_id
        WHERE a.area_key LIKE 'chuo:zone:%'
          AND sr.rule_type = 'weekly'
        ORDER BY a.id, cr.id
        """
    ).fetchall()

    for row in rows:
        area_id = int(row["area_id"])
        area_metadata = parse_json(row["area_metadata_json"], {})
        rule = parse_json(row["rule_json"], {})
        evidence = parse_json(row["evidence_json"], {})
        day = str(rule.get("day") or "")
        if day not in DAY_ORDER:
            continue

        if area_id not in area_properties_by_id:
            area_properties_by_id[area_id] = {
                "zoneId": area_metadata.get("zone_id") or str(row["area_key"]).split("chuo:zone:", 1)[-1],
                "wardSlug": row["ward_slug"],
                "wardNameJa": row["ward_name_ja"],
                "regionJa": area_metadata.get("region_ja"),
                "townJa": row["town_ja"],
                "sourceTownJa": area_metadata.get("source_town_ja") or row["town_ja"],
                "chome": numeric_chome_or_text(row["chome"]),
                "labelJa": row["label_ja"],
                "precision": area_metadata.get("precision") or row["area_key"].rsplit(":", 1)[-1],
                "sourceQuality": source_quality_by_ward_id.get(int(row["ward_id"]), "pending"),
            }
            area_categories_by_id[area_id] = {weekday: [] for weekday in DAY_ORDER}

        category = str(row["category"])
        if category not in area_categories_by_id[area_id][day]:
            area_categories_by_id[area_id][day].append(category)

        source_url = evidence.get("source_url") or row["source_url"]
        if source_url and area_id not in source_url_by_area_id:
            source_url_by_area_id[area_id] = str(source_url)

    geometry_rows = connection.execute(
        """
        SELECT
          a.id AS area_id,
          a.area_key,
          a.ward_id,
          a.label_ja,
          a.town_ja,
          a.chome,
          a.metadata_json AS area_metadata_json,
          w.slug AS ward_slug,
          w.name_ja AS ward_name_ja,
          ag.boundary_key,
          ag.boundary_name,
          ag.geometry_json,
          ag.metadata_json AS geometry_metadata_json
        FROM areas a
        JOIN wards w ON w.id = a.ward_id
        JOIN area_geometries ag ON ag.area_id = a.id
        WHERE a.area_key LIKE 'chuo:zone:%'
          AND a.status = 'active'
          AND ag.status = 'active'
        ORDER BY a.id, ag.part_index
        """
    ).fetchall()

    features = []

    for row in geometry_rows:
        area_id = int(row["area_id"])
        area_metadata = parse_json(row["area_metadata_json"], {})
        geometry_metadata = parse_json(row["geometry_metadata_json"], {})

        base_properties = area_properties_by_id.get(area_id)
        if base_properties is None:
            base_properties = {
                "zoneId": area_metadata.get("zone_id") or str(row["area_key"]).split("chuo:zone:", 1)[-1],
                "wardSlug": row["ward_slug"],
                "wardNameJa": row["ward_name_ja"],
                "regionJa": area_metadata.get("region_ja"),
                "townJa": row["town_ja"],
                "sourceTownJa": area_metadata.get("source_town_ja") or row["town_ja"],
                "chome": numeric_chome_or_text(row["chome"]),
                "labelJa": row["label_ja"],
                "precision": area_metadata.get("precision") or row["area_key"].rsplit(":", 1)[-1],
                "sourceQuality": source_quality_by_ward_id.get(int(row["ward_id"]), "pending"),
            }
            area_categories_by_id[area_id] = {weekday: [] for weekday in DAY_ORDER}

        properties = dict(base_properties)
        properties["sourceUrl"] = source_url_by_area_id.get(area_id)
        properties["boundarySourceUrl"] = geometry_metadata.get("source_url")
        properties["boundaryKeyCode"] = row["boundary_key"]
        properties["boundaryName"] = row["boundary_name"]

        categories_by_day = area_categories_by_id.get(area_id, {})
        for day in DAY_ORDER:
            ordered_categories = sorted(
                categories_by_day.get(day, []),
                key=lambda value: CATEGORY_ORDER.index(value)
                if value in CATEGORY_ORDER
                else len(CATEGORY_ORDER),
            )
            properties[f"{day}Categories"] = ",".join(ordered_categories)

        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": parse_json(row["geometry_json"], {}),
            }
        )

    return {"type": "FeatureCollection", "features": features}


def export_detailed_areas(connection: sqlite3.Connection):
    source_quality_by_ward_id: dict[int, str] = {}
    source_label_by_ward_id: dict[int, str] = {}
    if table_exists(connection, "ward_overviews"):
        for row in connection.execute("SELECT ward_id, source_quality, source_label FROM ward_overviews"):
            source_quality_by_ward_id[int(row["ward_id"])] = str(row["source_quality"])
            source_label_by_ward_id[int(row["ward_id"])] = str(row["source_label"])

    categories_by_area, source_url_by_area_id = build_categories_by_area(connection)

    rows = connection.execute(
        """
        SELECT
          a.id AS area_id,
          a.area_key,
          a.ward_id,
          a.area_kind,
          a.label_ja,
          a.label_en,
          a.town_ja,
          a.chome,
          a.metadata_json AS area_metadata_json,
          w.slug AS ward_slug,
          w.name_ja AS ward_name_ja,
          ag.boundary_key,
          ag.boundary_name,
          ag.geometry_json,
          ag.metadata_json AS geometry_metadata_json
        FROM areas a
        JOIN wards w ON w.id = a.ward_id
        JOIN area_geometries ag ON ag.area_id = a.id
        WHERE a.area_kind <> 'ward'
          AND a.status = 'active'
          AND ag.status = 'active'
        ORDER BY w.slug, a.id, ag.part_index
        """
    ).fetchall()

    features = []

    for row in rows:
        area_id = int(row["area_id"])
        area_metadata = parse_json(row["area_metadata_json"], {})
        geometry_metadata = parse_json(row["geometry_metadata_json"], {})

        properties = {
            "areaId": row["area_key"],
            "zoneId": area_metadata.get("zone_id"),
            "wardSlug": row["ward_slug"],
            "wardNameJa": row["ward_name_ja"],
            "labelJa": row["label_ja"],
            "labelEn": row["label_en"],
            "areaType": row["area_kind"],
            "regionJa": area_metadata.get("region_ja"),
            "townJa": row["town_ja"],
            "sourceTownJa": area_metadata.get("source_town_ja") or row["town_ja"],
            "chome": numeric_chome_or_text(row["chome"]),
            "precision": area_metadata.get("precision"),
            "sourceQuality": source_quality_by_ward_id.get(int(row["ward_id"]), "pending"),
            "sourceLabel": source_label_by_ward_id.get(int(row["ward_id"]), "データソース未設定"),
            "sourceUrl": source_url_by_area_id.get(area_id),
            "boundarySourceUrl": geometry_metadata.get("source_url"),
            "boundaryKeyCode": row["boundary_key"],
            "boundaryName": row["boundary_name"],
        }

        categories_by_day = categories_by_area.get(area_id, {})
        for day in DAY_ORDER:
            ordered_categories = sorted(
                categories_by_day.get(day, []),
                key=lambda value: CATEGORY_ORDER.index(value)
                if value in CATEGORY_ORDER
                else len(CATEGORY_ORDER),
            )
            properties[f"{day}Categories"] = ",".join(ordered_categories)

        features.append(
            {
                "type": "Feature",
                "properties": properties,
                "geometry": parse_json(row["geometry_json"], {}),
            }
        )

    return {"type": "FeatureCollection", "features": features}


def export_chuo_unresolved(connection: sqlite3.Connection):
    rows = connection.execute(
        """
        SELECT rt.payload_json
        FROM review_tasks rt
        JOIN wards w ON w.id = rt.ward_id
        WHERE w.slug = 'chuo'
          AND rt.task_type = 'area_match'
          AND rt.status IN ('open', 'in_review')
        ORDER BY rt.id
        """
    ).fetchall()

    return [parse_json(row["payload_json"], {}) for row in rows]


def main():
    args = parse_args()
    db_path = Path(args.db_path)
    output_dir = Path(args.output_dir)

    if not db_path.exists():
        raise SystemExit(f"Missing database: {db_path}")

    connection = connect(db_path)

    try:
        ward_boundaries = export_ward_boundaries(connection)
        ward_overviews = export_ward_overviews(connection)
        detailed_areas = export_detailed_areas(connection)
        chuo_zones = export_chuo_zones(connection)
        chuo_unresolved = export_chuo_unresolved(connection)
    finally:
        connection.close()

    write_json(output_dir / WARD_BOUNDARIES_PATH.name, ward_boundaries)
    write_json(output_dir / WARD_OVERVIEWS_PATH.name, ward_overviews)
    write_json(output_dir / DETAILED_AREAS_PATH.name, detailed_areas)
    write_json(output_dir / CHUO_ZONES_PATH.name, chuo_zones)
    write_json(output_dir / CHUO_UNRESOLVED_PATH.name, chuo_unresolved)

    print(
        json.dumps(
            {
                "db_path": str(db_path),
                "output_dir": str(output_dir),
                "exports": {
                    "ward_boundaries": len(ward_boundaries["features"]),
                    "ward_overviews": len(ward_overviews),
                    "detailed_areas": len(detailed_areas["features"]),
                    "chuo_zones": len(chuo_zones["features"]),
                    "chuo_unresolved": len(chuo_unresolved),
                },
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
