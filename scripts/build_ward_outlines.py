from __future__ import annotations

import io
import json
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import shapefile
from shapely.geometry import shape
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parent.parent
WARD_BOUNDARIES_OUTPUT_PATH = ROOT / "public" / "data" / "ward-boundaries.geojson"
OUTPUT_PATH = ROOT / "public" / "data" / "ward-outlines.geojson"
SHAPE_URL = (
    "https://www.e-stat.go.jp/gis/statmap-search/data"
    "?dlserveyId=A002005212020&code=13&coordSys=1&format=shape&downloadType=5&datum=2000"
)
SIMPLIFY_TOLERANCE = 0.00008

WARD_METADATA = {
    "101": {"slug": "chiyoda", "nameJa": "千代田区", "nameEn": "Chiyoda"},
    "102": {"slug": "chuo", "nameJa": "中央区", "nameEn": "Chuo"},
    "103": {"slug": "minato", "nameJa": "港区", "nameEn": "Minato"},
    "104": {"slug": "shinjuku", "nameJa": "新宿区", "nameEn": "Shinjuku"},
    "105": {"slug": "bunkyo", "nameJa": "文京区", "nameEn": "Bunkyo"},
    "106": {"slug": "taito", "nameJa": "台東区", "nameEn": "Taito"},
    "107": {"slug": "sumida", "nameJa": "墨田区", "nameEn": "Sumida"},
    "108": {"slug": "koto", "nameJa": "江東区", "nameEn": "Koto"},
    "109": {"slug": "shinagawa", "nameJa": "品川区", "nameEn": "Shinagawa"},
    "110": {"slug": "meguro", "nameJa": "目黒区", "nameEn": "Meguro"},
    "111": {"slug": "ota", "nameJa": "大田区", "nameEn": "Ota"},
    "112": {"slug": "setagaya", "nameJa": "世田谷区", "nameEn": "Setagaya"},
    "113": {"slug": "shibuya", "nameJa": "渋谷区", "nameEn": "Shibuya"},
    "114": {"slug": "nakano", "nameJa": "中野区", "nameEn": "Nakano"},
    "115": {"slug": "suginami", "nameJa": "杉並区", "nameEn": "Suginami"},
    "116": {"slug": "toshima", "nameJa": "豊島区", "nameEn": "Toshima"},
    "117": {"slug": "kita", "nameJa": "北区", "nameEn": "Kita"},
    "118": {"slug": "arakawa", "nameJa": "荒川区", "nameEn": "Arakawa"},
    "119": {"slug": "itabashi", "nameJa": "板橋区", "nameEn": "Itabashi"},
    "120": {"slug": "nerima", "nameJa": "練馬区", "nameEn": "Nerima"},
    "121": {"slug": "adachi", "nameJa": "足立区", "nameEn": "Adachi"},
    "122": {"slug": "katsushika", "nameJa": "葛飾区", "nameEn": "Katsushika"},
    "123": {"slug": "edogawa", "nameJa": "江戸川区", "nameEn": "Edogawa"},
}


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gomiyoubi ward outline builder"})
    with urllib.request.urlopen(request, timeout=120) as response:
        return response.read()


def shape_to_geometry(record_shape) -> dict:
    parts = list(record_shape.parts) + [len(record_shape.points)]
    polygons = []

    if record_shape.shapeTypeName == "POLYGON":
        for start, end in zip(parts[:-1], parts[1:]):
            ring = record_shape.points[start:end]
            polygons.append([[lng, lat] for lng, lat in ring])
    elif record_shape.shapeTypeName == "POLYGONZ":
        for start, end in zip(parts[:-1], parts[1:]):
            ring = record_shape.points[start:end]
            polygons.append([[lng, lat] for lng, lat, *_ in ring])
    else:
        raise ValueError(f"Unsupported shape type: {record_shape.shapeTypeName}")

    return {"type": "Polygon", "coordinates": polygons}


def build_features() -> tuple[list[dict], list[dict]]:
    zip_bytes = fetch_bytes(SHAPE_URL)

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            archive.extractall(temp_dir)

        reader = shapefile.Reader(str(Path(temp_dir) / "r2ka13.shp"), encoding="cp932")
        fields = [field[0] for field in reader.fields[1:]]
        geometries_by_city_code: dict[str, list] = {code: [] for code in WARD_METADATA}

        for shape_record in reader.iterShapeRecords():
            record = dict(zip(fields, shape_record.record))
            city_code = str(record.get("CITY") or "").strip()
            if city_code not in geometries_by_city_code:
                continue

            boundary_name = str(record.get("S_NAME") or "").strip()
            if not boundary_name:
                continue

            geometries_by_city_code[city_code].append(shape(shape_to_geometry(shape_record.shape)))

    fill_features: list[dict] = []
    outline_features: list[dict] = []
    for city_code, metadata in WARD_METADATA.items():
        ward_geometries = geometries_by_city_code[city_code]
        if not ward_geometries:
            raise ValueError(f"Missing e-Stat polygons for ward city code {city_code}")

        dissolved_geometry = unary_union(ward_geometries)
        fill_features.append(
            {
                "type": "Feature",
                "properties": {
                    "slug": metadata["slug"],
                    "nameJa": metadata["nameJa"],
                    "nameEn": metadata["nameEn"],
                    "source": "e-Stat 町丁・字等別境界データ",
                },
                "geometry": json.loads(
                    json.dumps(
                        dissolved_geometry.simplify(
                            SIMPLIFY_TOLERANCE,
                            preserve_topology=True,
                        ).__geo_interface__
                    )
                ),
            }
        )
        outline_features.append(
            {
                "type": "Feature",
                "properties": {
                    "slug": metadata["slug"],
                    "nameJa": metadata["nameJa"],
                    "nameEn": metadata["nameEn"],
                    "source": "e-Stat 町丁・字等別境界データ",
                },
                "geometry": json.loads(json.dumps(dissolved_geometry.__geo_interface__)),
            }
        )

    return (
        sorted(fill_features, key=lambda feature: feature["properties"]["slug"]),
        sorted(outline_features, key=lambda feature: feature["properties"]["slug"]),
    )


def main():
    fill_features, outline_features = build_features()
    fill_payload = {"type": "FeatureCollection", "features": fill_features}
    outline_payload = {"type": "FeatureCollection", "features": outline_features}
    WARD_BOUNDARIES_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    WARD_BOUNDARIES_OUTPUT_PATH.write_text(
        json.dumps(fill_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_PATH.write_text(
        json.dumps(outline_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {WARD_BOUNDARIES_OUTPUT_PATH}")
    print(f"Wrote {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
