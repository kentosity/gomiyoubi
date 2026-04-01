import csv
import io
import json
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import shapefile

CSV_URL = "https://www.city.chuo.lg.jp/documents/984/gomitoshigen.csv"
SHAPE_URL = (
    "https://www.e-stat.go.jp/gis/statmap-search/data"
    "?dlserveyId=A002005212020&code=13&coordSys=1&format=shape&downloadType=5&datum=2000"
)
GEOJSON_PATH = Path("public/data/chuo-zones.geojson")
UNRESOLVED_PATH = Path("public/data/chuo-unresolved.json")

WEEKDAY_MAP = {
    "月曜日": "monday",
    "火曜日": "tuesday",
    "水曜日": "wednesday",
    "木曜日": "thursday",
    "金曜日": "friday",
    "土曜日": "saturday",
}

CATEGORY_MAP = {
    "燃やすごみ": "burnable",
    "燃やさないごみ": "nonburnable",
    "プラマーク": "plastic",
    "資源": "resource",
    "粗大ごみ": "bulky",
}

KANJI_NUMERALS = {
    1: "一",
    2: "二",
    3: "三",
    4: "四",
    5: "五",
    6: "六",
    7: "七",
    8: "八",
    9: "九",
    10: "十",
}

KANJI_TO_ARABIC = {value: key for key, value in KANJI_NUMERALS.items()}


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gomiyoubi chuo zone builder"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def canonical_town_name(region: str, town: str) -> str:
    if region == "日本橋" and not town.startswith("日本橋") and not town.startswith("東日本橋"):
        return f"日本橋{town}"
    return town


def expand_chome_value(chome: str):
    if not chome or chome == "全域":
        return []

    range_match = __import__("re").match(r"^(\d+)～(\d+)丁目$", chome)
    if range_match:
        start = int(range_match.group(1))
        end = int(range_match.group(2))
        return list(range(start, end + 1))

    single_match = __import__("re").match(r"^(\d+)丁目$", chome)
    if single_match:
        return [int(single_match.group(1))]

    return None


def extract_weekdays(value: str):
    normalized = value.replace("\n", "・")
    if "月曜日～土曜日" in normalized:
        return list(WEEKDAY_MAP.values())
    return [key for ja, key in WEEKDAY_MAP.items() if ja in normalized]


def build_day_category_map(row):
    day_categories = {weekday: [] for weekday in WEEKDAY_MAP.values()}
    for source_column, category in CATEGORY_MAP.items():
        for weekday in extract_weekdays(row.get(source_column, "")):
            if category not in day_categories[weekday]:
                day_categories[weekday].append(category)
    return day_categories


def parse_geometry_name(s_name: str):
    match = __import__("re").match(r"^(.*?)([一二三四五六七八九十]+丁目)$", s_name)
    if match:
        area_name = match.group(1)
        chome_ja = match.group(2).replace("丁目", "")
        chome = f"{KANJI_TO_ARABIC[chome_ja]}丁目"
    else:
        area_name = s_name
        chome = "全域"

    if area_name.startswith("日本橋") and area_name != "日本橋" and not area_name.startswith("東日本橋"):
        area_name = area_name.removeprefix("日本橋")

    return area_name, chome


def zone_label(full_town_name: str, chome_number):
    if chome_number is None:
        return full_town_name
    return f"{full_town_name}{KANJI_NUMERALS.get(chome_number, str(chome_number))}丁目"


def shape_to_geometry(shape):
    if shape.shapeTypeName == "POLYGON":
        parts = list(shape.parts) + [len(shape.points)]
        polygons = []
        for start, end in zip(parts[:-1], parts[1:]):
            ring = shape.points[start:end]
            polygons.append([[lng, lat] for lng, lat in ring])
        return {"type": "Polygon", "coordinates": polygons}

    if shape.shapeTypeName == "POLYGONZ":
        parts = list(shape.parts) + [len(shape.points)]
        polygons = []
        for start, end in zip(parts[:-1], parts[1:]):
            ring = shape.points[start:end]
            polygons.append([[lng, lat] for lng, lat, *_ in ring])
        return {"type": "Polygon", "coordinates": polygons}

    raise ValueError(f"Unsupported shape type: {shape.shapeTypeName}")


def load_chuo_geometry_features():
    zip_bytes = fetch_bytes(SHAPE_URL)

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            archive.extractall(temp_dir)

        reader = shapefile.Reader(str(Path(temp_dir) / "r2ka13.shp"), encoding="cp932")
        fields = [field[0] for field in reader.fields[1:]]
        features = []

        for shape_record in reader.iterShapeRecords():
            record = dict(zip(fields, shape_record.record))
            if int(record["CITY"]) != 102:
                continue

            town, chome = parse_geometry_name(record["S_NAME"])
            record["zoneTownJa"] = town
            record["zoneChome"] = chome

            features.append(
                {
                    "type": "Feature",
                    "properties": record,
                    "geometry": shape_to_geometry(shape_record.shape),
                }
            )

    return features


def load_chuo_csv_rows():
    raw = fetch_bytes(CSV_URL).decode("cp932")
    return list(csv.DictReader(io.StringIO(raw)))


def main():
    rows = load_chuo_csv_rows()
    geometry_features = load_chuo_geometry_features()
    built_features = []
    unresolved = []

    features_by_town = {}
    features_by_town_chome = {}

    for feature in geometry_features:
        town = feature["properties"]["zoneTownJa"]
        chome = feature["properties"]["zoneChome"]
        features_by_town.setdefault(town, []).append(feature)
        features_by_town_chome[f"{town}|{chome}"] = feature

    for row in rows:
        full_town_for_label = canonical_town_name(row["地域"], row["町名"])
        geometry_town = row["町名"]
        day_categories = build_day_category_map(row)
        chome_numbers = expand_chome_value(row["丁目"])

        if chome_numbers is None:
            unresolved.append(
                {
                    **row,
                    "normalizedTown": full_town_for_label,
                    "reason": "ban_split_or_unsupported_range",
                }
            )
            continue

        if chome_numbers:
            targets = [
                {
                    "feature": features_by_town_chome.get(f"{geometry_town}|{chome_number}丁目"),
                    "chomeNumber": chome_number,
                }
                for chome_number in chome_numbers
            ]
        else:
            targets = [
                {
                    "feature": feature,
                    "chomeNumber": None if feature["properties"]["zoneChome"] == "全域" else int(feature["properties"]["zoneChome"].replace("丁目", "")),
                }
                for feature in features_by_town.get(geometry_town, [])
            ]

        if not targets:
            unresolved.append(
                {
                    **row,
                    "normalizedTown": full_town_for_label,
                    "reason": "geometry_not_found_for_town",
                }
            )
            continue

        for target in targets:
            if not target["feature"]:
                unresolved.append(
                    {
                        **row,
                        "normalizedTown": full_town_for_label,
                        "chomeNumber": target["chomeNumber"],
                        "reason": "geometry_not_found_for_chome",
                    }
                )
                continue

            feature = target["feature"]
            zone_town = feature["properties"]["zoneTownJa"]

            built_features.append(
                {
                    "type": "Feature",
                    "properties": {
                        "zoneId": f"{zone_town}:{target['chomeNumber'] or 'all'}",
                        "wardSlug": "chuo",
                        "wardNameJa": "中央区",
                        "regionJa": row["地域"],
                        "townJa": zone_town,
                        "sourceTownJa": row["町名"],
                        "chome": target["chomeNumber"],
                        "labelJa": zone_label(full_town_for_label, target["chomeNumber"]),
                        "precision": "town" if target["chomeNumber"] is None else "chome",
                        "sourceQuality": "high",
                        "sourceUrl": CSV_URL,
                        "boundarySourceUrl": SHAPE_URL,
                        "boundaryKeyCode": str(feature["properties"]["KEY_CODE"]),
                        "boundaryName": feature["properties"]["S_NAME"],
                        "mondayCategories": ",".join(day_categories["monday"]),
                        "tuesdayCategories": ",".join(day_categories["tuesday"]),
                        "wednesdayCategories": ",".join(day_categories["wednesday"]),
                        "thursdayCategories": ",".join(day_categories["thursday"]),
                        "fridayCategories": ",".join(day_categories["friday"]),
                        "saturdayCategories": ",".join(day_categories["saturday"]),
                    },
                    "geometry": feature["geometry"],
                }
            )

    GEOJSON_PATH.parent.mkdir(parents=True, exist_ok=True)
    GEOJSON_PATH.write_text(
        json.dumps({"type": "FeatureCollection", "features": built_features}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    UNRESOLVED_PATH.write_text(json.dumps(unresolved, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print(
        json.dumps(
            {
                "builtFeatures": len(built_features),
                "unresolved": len(unresolved),
                "geometryFeatures": len(geometry_features),
                "geojsonPath": str(GEOJSON_PATH),
                "unresolvedPath": str(UNRESOLVED_PATH),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
