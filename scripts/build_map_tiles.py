from __future__ import annotations

import json
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PUBLIC_DATA_DIR = ROOT / "public" / "data"

WARD_BOUNDARIES_PATH = PUBLIC_DATA_DIR / "ward-boundaries.geojson"
WARD_OUTLINES_PATH = PUBLIC_DATA_DIR / "ward-outlines.geojson"
DETAILED_AREAS_PATH = PUBLIC_DATA_DIR / "detailed-areas.geojson"
WARD_OVERVIEWS_PATH = PUBLIC_DATA_DIR / "ward-overviews.json"
DETAILED_AREA_INDEX_PATH = PUBLIC_DATA_DIR / "detailed-area-index.json"
TILESET_OUTPUT_PATH = PUBLIC_DATA_DIR / "gomiyoubi.pmtiles"

DAY_KEYS = (
    "sundayCategories",
    "mondayCategories",
    "tuesdayCategories",
    "wednesdayCategories",
    "thursdayCategories",
    "fridayCategories",
    "saturdayCategories",
)


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_compact_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def write_temp_geojson(path: Path, features: list[dict]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(feature, ensure_ascii=False) for feature in features) + "\n",
        encoding="utf-8",
    )


def build_tile_feature(payload: dict, properties: dict) -> dict:
    return {
        "type": "Feature",
        "properties": properties,
        "geometry": payload["geometry"],
    }


def main():
    ward_boundaries = load_json(WARD_BOUNDARIES_PATH)
    ward_outlines = load_json(WARD_OUTLINES_PATH)
    detailed_areas = load_json(DETAILED_AREAS_PATH)
    ward_overviews = load_json(WARD_OVERVIEWS_PATH)

    ward_tile_id_by_slug = {
        ward_overview["wardSlug"]: index + 1
        for index, ward_overview in enumerate(
            sorted(ward_overviews, key=lambda ward_overview: ward_overview["wardSlug"])
        )
    }

    area_id_to_tile_id: dict[str, int] = {}
    for feature in sorted(
        detailed_areas["features"],
        key=lambda feature: str(feature.get("properties", {}).get("areaId") or ""),
    ):
        area_id = str(feature.get("properties", {}).get("areaId") or "")
        if not area_id or area_id in area_id_to_tile_id:
            continue
        area_id_to_tile_id[area_id] = len(area_id_to_tile_id) + 1

    augmented_ward_overviews = []
    for ward_overview in ward_overviews:
        ward_slug = str(ward_overview["wardSlug"])
        augmented_ward_overviews.append(
            {
                **ward_overview,
                "tileFeatureId": ward_tile_id_by_slug[ward_slug],
            }
        )

    write_json(WARD_OVERVIEWS_PATH, augmented_ward_overviews)

    detailed_area_index_rows = []
    seen_area_ids: set[str] = set()
    for feature in detailed_areas["features"]:
        properties = dict(feature.get("properties") or {})
        area_id = str(properties.get("areaId") or "")
        if not area_id or area_id in seen_area_ids:
            continue
        seen_area_ids.add(area_id)
        detailed_area_index_rows.append(
            {
                "areaId": area_id,
                "boundaryName": properties.get("boundaryName"),
                "labelJa": properties.get("labelJa"),
                "mondayCategories": properties.get("mondayCategories"),
                "saturdayCategories": properties.get("saturdayCategories"),
                "sourceLabel": properties.get("sourceLabel"),
                "sourceUrl": properties.get("sourceUrl"),
                "sundayCategories": properties.get("sundayCategories"),
                "thursdayCategories": properties.get("thursdayCategories"),
                "tileFeatureId": area_id_to_tile_id[area_id],
                "tuesdayCategories": properties.get("tuesdayCategories"),
                "wardSlug": properties.get("wardSlug"),
                "wednesdayCategories": properties.get("wednesdayCategories"),
                "fridayCategories": properties.get("fridayCategories"),
            }
        )

    write_compact_json(DETAILED_AREA_INDEX_PATH, detailed_area_index_rows)

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir_path = Path(temp_dir)
        ward_tiles_path = temp_dir_path / "wards.geojson"
        ward_outline_tiles_path = temp_dir_path / "ward_outlines.geojson"
        detailed_area_tiles_path = temp_dir_path / "detailed_areas.geojson"

        ward_fill_features = []
        for feature in ward_boundaries["features"]:
            properties = dict(feature.get("properties") or {})
            ward_slug = str(properties.get("slug") or "")
            matching_overview = next(
                (
                    ward_overview
                    for ward_overview in augmented_ward_overviews
                    if ward_overview["wardSlug"] == ward_slug
                ),
                None,
            )
            ward_fill_features.append(
                build_tile_feature(
                    feature,
                    {
                        "slug": ward_slug,
                        "tileFeatureId": ward_tile_id_by_slug[ward_slug],
                        "sourceQuality": matching_overview["sourceQuality"] if matching_overview else "pending",
                        "hasDetailedAreas": bool(
                            matching_overview["hasDetailedAreas"] if matching_overview else False
                        ),
                    },
                )
            )

        ward_outline_features = []
        for feature in ward_outlines["features"]:
            properties = dict(feature.get("properties") or {})
            ward_slug = str(properties.get("slug") or "")
            ward_outline_features.append(
                build_tile_feature(
                    feature,
                    {
                        "slug": ward_slug,
                        "tileFeatureId": ward_tile_id_by_slug[ward_slug],
                    },
                )
            )

        detailed_area_tile_features = []
        for feature in detailed_areas["features"]:
            properties = dict(feature.get("properties") or {})
            area_id = str(properties.get("areaId") or "")
            if not area_id:
                continue

            detailed_area_tile_features.append(
                build_tile_feature(
                    feature,
                    {
                        "areaId": area_id,
                        "wardSlug": properties.get("wardSlug"),
                        "labelJa": properties.get("labelJa"),
                        "boundaryName": properties.get("boundaryName"),
                        "tileFeatureId": area_id_to_tile_id[area_id],
                    },
                )
            )

        write_temp_geojson(ward_tiles_path, ward_fill_features)
        write_temp_geojson(ward_outline_tiles_path, ward_outline_features)
        write_temp_geojson(detailed_area_tiles_path, detailed_area_tile_features)

        subprocess.run(
            [
                "tippecanoe",
                "--force",
                "--projection=EPSG:4326",
                "--minimum-zoom=8",
                "--maximum-zoom=15",
                "--detect-shared-borders",
                "--read-parallel",
                "--drop-densest-as-needed",
                "--use-attribute-for-id=tileFeatureId",
                "--output",
                str(TILESET_OUTPUT_PATH),
                "--named-layer",
                f"wards:{ward_tiles_path}",
                "--named-layer",
                f"ward_outlines:{ward_outline_tiles_path}",
                "--named-layer",
                f"detailed_areas:{detailed_area_tiles_path}",
            ],
            check=True,
        )

    print(f"Wrote {DETAILED_AREA_INDEX_PATH}")
    print(f"Wrote {TILESET_OUTPUT_PATH}")


if __name__ == "__main__":
    main()
