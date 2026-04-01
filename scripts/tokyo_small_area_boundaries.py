from __future__ import annotations

import io
import tempfile
import urllib.request
import zipfile
from pathlib import Path

import shapefile

ROOT = Path(__file__).resolve().parent.parent
SHAPE_URL = (
    "https://www.e-stat.go.jp/gis/statmap-search/data"
    "?dlserveyId=A002005212020&code=13&coordSys=1&format=shape&downloadType=5&datum=2000"
)

WARD_CITY_CODES = {
    "chuo": "102",
    "sumida": "107",
    "koto": "108",
}

KANJI_TO_ARABIC = {
    "一": 1,
    "二": 2,
    "三": 3,
    "四": 4,
    "五": 5,
    "六": 6,
    "七": 7,
    "八": 8,
    "九": 9,
    "十": 10,
}

_BOUNDARY_CACHE: dict[str, list[dict]] = {}


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gomiyoubi boundary loader"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def parse_small_area_name(s_name: str) -> tuple[str, str | None]:
    import re

    match = re.match(r"^(.*?)([一二三四五六七八九十]+)丁目$", s_name)
    if not match:
        return s_name, None
    return match.group(1), str(KANJI_TO_ARABIC[match.group(2)])


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


def load_ward_small_area_features(ward_slug: str) -> list[dict]:
    cached = _BOUNDARY_CACHE.get(ward_slug)
    if cached is not None:
        return cached

    city_code = WARD_CITY_CODES.get(ward_slug)
    if city_code is None:
        raise ValueError(f"Unsupported ward slug for boundary loading: {ward_slug}")

    zip_bytes = fetch_bytes(SHAPE_URL)

    with tempfile.TemporaryDirectory() as temp_dir:
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as archive:
            archive.extractall(temp_dir)

        reader = shapefile.Reader(str(Path(temp_dir) / "r2ka13.shp"), encoding="cp932")
        fields = [field[0] for field in reader.fields[1:]]
        features: list[dict] = []

        for shape_record in reader.iterShapeRecords():
            record = dict(zip(fields, shape_record.record))
            if str(record["CITY"]) != city_code:
                continue

            boundary_name = str(record.get("S_NAME") or "").strip()
            if not boundary_name:
                continue

            town_ja, chome = parse_small_area_name(boundary_name)
            features.append(
                {
                    "boundary_key": str(record["KEY_CODE"]),
                    "boundary_name": boundary_name,
                    "town_ja": town_ja,
                    "chome": chome,
                    "geometry": shape_to_geometry(shape_record.shape),
                }
            )

    _BOUNDARY_CACHE[ward_slug] = features
    return features


def build_boundary_index(features: list[dict]) -> tuple[dict[str, list[dict]], dict[tuple[str, str], dict]]:
    by_town: dict[str, list[dict]] = {}
    by_town_chome: dict[tuple[str, str], dict] = {}

    for feature in features:
        town_ja = str(feature["town_ja"])
        by_town.setdefault(town_ja, []).append(feature)
        chome = feature.get("chome")
        if chome is not None:
            by_town_chome[(town_ja, str(chome))] = feature

    return by_town, by_town_chome
