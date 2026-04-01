from __future__ import annotations

import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from datetime import date, datetime, timezone
from html import unescape
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "koto"
EXTRACTED_DIR = ROOT / "data" / "extracted" / "koto"
NORMALIZED_DIR = ROOT / "data" / "normalized" / "koto"
MANUAL_DIR = ROOT / "data" / "manual" / "koto"
SOURCE_REGISTRY_PATH = ROOT / "data" / "source-registry.json"

ENTRY_PAGE_PATH = RAW_DIR / "koto_entry_page.html"
ADDRESS_IMAGE_PATH = RAW_DIR / "koto_download_03.png"

SCHEDULE_OUTPUT_PATH = EXTRACTED_DIR / "koto_2026_schedule_patterns.json"
OCR_TEXT_PATH = EXTRACTED_DIR / "koto_address_ocr.txt"
OCR_TSV_PATH = EXTRACTED_DIR / "koto_address_ocr.tsv"
NORMALIZED_OUTPUT_PATH = NORMALIZED_DIR / "koto_district_dataset.json"
SELECTOR_INPUT_PATH = MANUAL_DIR / "district-boundary-selectors.json"

PARSER_VERSION = "koto_extract_v1"
SUBMITTED_BY = "scripts/extract_koto_data.py"
EFFECTIVE_FROM = "2026-04-01"
EFFECTIVE_TO = "2027-03-31"

DAY_MAP = {
    "月曜日": "monday",
    "火曜日": "tuesday",
    "水曜日": "wednesday",
    "木曜日": "thursday",
    "金曜日": "friday",
    "土曜日": "saturday",
}

SCHEDULE_PATTERN_RE = re.compile(
    r"^【(?P<district>\d+)地区】"
    r"資源(?P<resource>[^、]+)、"
    r"プラスチック(?P<plastic>[^、]+)、"
    r"燃やすごみ(?P<burnable>[^、]+)、"
    r"燃やさないごみ(?P<nonburnable>.+)$"
)


@dataclass(frozen=True)
class SourceRef:
    source_key: str
    source_kind: str
    label: str
    url: str
    format_value: str | None
    coverage_label: str | None = None
    encoding: str | None = None
    last_verified: str | None = None
    metadata: dict | None = None


class ImgTagParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.images: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() != "img":
            return

        values = {key: value for key, value in attrs if key and value}
        self.images.append(values)


def read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_koto_sources() -> dict[str, SourceRef]:
    registry = read_json(SOURCE_REGISTRY_PATH)
    ward = next(item for item in registry["wards"] if item["ward_slug"] == "koto")
    official_sources = ward["official_sources"]

    entry_page = official_sources["entry_page"]
    downloads = official_sources.get("downloads", [])

    address_image = next(item for item in downloads if item["url"].endswith("address.png"))
    front_pdf = next(item for item in downloads if item["url"].endswith("8omote.pdf"))

    return {
        "entry_page": SourceRef(
            source_key="koto:entry_page",
            source_kind="entry_page",
            label=entry_page["label"],
            url=entry_page["url"],
            format_value=entry_page.get("format"),
            last_verified=entry_page.get("last_verified"),
            metadata={"ward_slug": "koto", "raw_path": str(ENTRY_PAGE_PATH.relative_to(ROOT))},
        ),
        "front_pdf": SourceRef(
            source_key="koto:download:01",
            source_kind="download",
            label=front_pdf["label"],
            url=front_pdf["url"],
            format_value=front_pdf.get("format"),
            coverage_label=front_pdf.get("coverage"),
            metadata={"ward_slug": "koto", "fiscal_year": 2026},
        ),
        "address_image": SourceRef(
            source_key="koto:download:03",
            source_kind="download",
            label=address_image["label"],
            url=address_image["url"],
            format_value=address_image.get("format"),
            metadata={"ward_slug": "koto", "raw_path": str(ADDRESS_IMAGE_PATH.relative_to(ROOT))},
        ),
    }


def extract_schedule_images(html_text: str) -> list[dict[str, str]]:
    parser = ImgTagParser()
    parser.feed(html_text)

    schedule_images: list[dict[str, str]] = []
    for image in parser.images:
        src = image.get("src", "")
        alt = unescape(image.get("alt", "").strip())
        match = re.search(r"/8-(\d+)\.png$", src)
        if not match or not alt:
            continue
        schedule_images.append(
            {
                "district_number": int(match.group(1)),
                "src": src,
                "alt": alt,
            }
        )

    return sorted(schedule_images, key=lambda item: item["district_number"])


def parse_day(day_text: str) -> str:
    day_key = DAY_MAP.get(day_text)
    if not day_key:
        raise ValueError(f"Unsupported weekday: {day_text}")
    return day_key


def parse_schedule_pattern(raw_alt: str, src: str, expected_district: int) -> dict:
    match = SCHEDULE_PATTERN_RE.match(raw_alt)
    if not match:
        raise ValueError(f"Unparseable schedule alt text: {raw_alt}")

    district_number = int(match.group("district"))
    if district_number != expected_district:
        raise ValueError(
            f"Mismatched district number for {src}: expected {expected_district}, got {district_number}"
        )

    burnable_days = [parse_day(item) for item in match.group("burnable").split("・")]

    return {
        "district_number": district_number,
        "source_image": src,
        "raw_alt": raw_alt,
        "weekly_schedule": {
            "resource": [parse_day(match.group("resource"))],
            "plastic": [parse_day(match.group("plastic"))],
            "burnable": burnable_days,
        },
        "nonweekly_schedule": {
            "nonburnable": {
                "rule_type": "freeform",
                "weekday": parse_day(match.group("nonburnable").replace("隔週", "")),
                "text_ja": match.group("nonburnable"),
                "pattern": "alternating_weeks",
            }
        },
    }


def extract_schedule_patterns() -> list[dict]:
    html_text = ENTRY_PAGE_PATH.read_text(encoding="utf-8")
    schedule_images = extract_schedule_images(html_text)
    if len(schedule_images) != 12:
        raise ValueError(f"Expected 12 schedule images for 2026, found {len(schedule_images)}")

    return [
        parse_schedule_pattern(item["alt"], item["src"], item["district_number"])
        for item in schedule_images
    ]


def tesseract_version() -> str:
    result = subprocess.run(
        ["/opt/homebrew/bin/tesseract", "--version"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout.splitlines()[0].strip()


def run_address_ocr() -> dict:
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    output_base = EXTRACTED_DIR / "koto_address_ocr"

    subprocess.run(
        [
            "/opt/homebrew/bin/tesseract",
            str(ADDRESS_IMAGE_PATH),
            str(output_base),
            "-l",
            "jpn",
            "--psm",
            "4",
            "txt",
            "tsv",
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    text = OCR_TEXT_PATH.read_text(encoding="utf-8")
    return {
        "text_path": str(OCR_TEXT_PATH.relative_to(ROOT)),
        "tsv_path": str(OCR_TSV_PATH.relative_to(ROOT)),
        "text_sha256": sha256_file(OCR_TEXT_PATH),
        "tsv_sha256": sha256_file(OCR_TSV_PATH),
        "line_count": len(text.splitlines()),
        "character_count": len(text),
        "ocr_engine": f"{tesseract_version()} lang=jpn psm=4",
    }


def build_schedule_rules(schedule_patterns: list[dict]) -> list[dict]:
    rule_index: dict[str, dict] = {}

    for pattern in schedule_patterns:
        for category, days in pattern["weekly_schedule"].items():
            for day in days:
                rule_key = f"koto:rule:weekly:{day}"
                rule_index.setdefault(
                    rule_key,
                    {
                        "rule_key": rule_key,
                        "rule_type": "weekly",
                        "rule_json": {"day": day},
                        "description": f"{day} weekly collection",
                    },
                )

        nonburnable = pattern["nonweekly_schedule"]["nonburnable"]
        weekday = nonburnable["weekday"]
        rule_key = f"koto:rule:freeform:alternating_weeks:{weekday}"
        rule_index.setdefault(
            rule_key,
            {
                "rule_key": rule_key,
                "rule_type": "freeform",
                "rule_json": {
                    "text_ja": nonburnable["text_ja"],
                    "weekday": weekday,
                    "pattern": nonburnable["pattern"],
                },
                "description": nonburnable["text_ja"],
            },
        )

    return [rule_index[key] for key in sorted(rule_index)]


def build_source_records(source_refs: dict[str, SourceRef]) -> list[dict]:
    return [
        {
            "source_key": source.source_key,
            "ward_slug": "koto",
            "source_kind": source.source_kind,
            "label": source.label,
            "url": source.url,
            "format": source.format_value,
            "is_official": 1,
            "encoding": source.encoding,
            "coverage_label": source.coverage_label,
            "last_verified": source.last_verified,
            "metadata": source.metadata or {},
        }
        for source in source_refs.values()
    ]


def build_artifact_records(
    *,
    source_refs: dict[str, SourceRef],
    ocr_metadata: dict,
) -> list[dict]:
    today = date.today().isoformat()

    return [
        {
            "artifact_key": "koto:artifact:entry_page:fetch",
            "source_key": source_refs["entry_page"].source_key,
            "artifact_kind": "fetch",
            "local_path": str(ENTRY_PAGE_PATH.relative_to(ROOT)),
            "content_type": "text/html",
            "sha256": sha256_file(ENTRY_PAGE_PATH),
            "fetched_at": today,
            "parser_version": None,
            "ocr_engine": None,
            "metadata": {"fiscal_year": 2026},
        },
        {
            "artifact_key": "koto:artifact:address_image:fetch",
            "source_key": source_refs["address_image"].source_key,
            "artifact_kind": "fetch",
            "local_path": str(ADDRESS_IMAGE_PATH.relative_to(ROOT)),
            "content_type": "image/png",
            "sha256": sha256_file(ADDRESS_IMAGE_PATH),
            "fetched_at": today,
            "parser_version": None,
            "ocr_engine": None,
            "metadata": {"purpose": "district address lookup image"},
        },
        {
            "artifact_key": "koto:artifact:entry_page:parser_output:2026",
            "source_key": source_refs["entry_page"].source_key,
            "artifact_kind": "parser_output",
            "local_path": str(SCHEDULE_OUTPUT_PATH.relative_to(ROOT)),
            "content_type": "application/json",
            "sha256": sha256_file(SCHEDULE_OUTPUT_PATH),
            "fetched_at": today,
            "parser_version": PARSER_VERSION,
            "ocr_engine": None,
            "metadata": {"fiscal_year": 2026},
        },
        {
            "artifact_key": "koto:artifact:address_image:ocr",
            "source_key": source_refs["address_image"].source_key,
            "artifact_kind": "ocr",
            "local_path": ocr_metadata["text_path"],
            "content_type": "text/plain",
            "sha256": ocr_metadata["text_sha256"],
            "fetched_at": today,
            "parser_version": PARSER_VERSION,
            "ocr_engine": ocr_metadata["ocr_engine"],
            "metadata": {
                "tsv_path": ocr_metadata["tsv_path"],
                "tsv_sha256": ocr_metadata["tsv_sha256"],
                "line_count": ocr_metadata["line_count"],
                "character_count": ocr_metadata["character_count"],
            },
        },
        {
            "artifact_key": "koto:artifact:district-selectors:manual",
            "source_key": source_refs["address_image"].source_key,
            "artifact_kind": "manual_transcription",
            "local_path": str(SELECTOR_INPUT_PATH.relative_to(ROOT)),
            "content_type": "application/json",
            "sha256": sha256_file(SELECTOR_INPUT_PATH),
            "fetched_at": today,
            "parser_version": PARSER_VERSION,
            "ocr_engine": None,
            "metadata": {
                "review_basis": "Official district membership normalized for boundary joins.",
            },
        },
    ]


def load_boundary_selector_dataset() -> dict:
    return read_json(SELECTOR_INPUT_PATH)


def build_area_records(schedule_patterns: list[dict], selector_dataset: dict) -> list[dict]:
    district_numbers_with_geometry = {
        int(item["district_number"]) for item in selector_dataset.get("districts", [])
    }
    areas = []
    district_numbers = sorted({int(pattern["district_number"]) for pattern in schedule_patterns})
    for district_number in district_numbers:
        areas.append(
            {
                "area_key": f"koto:district:{district_number:02d}",
                "ward_slug": "koto",
                "parent_area_key": "ward:koto",
                "area_kind": "district",
                "label_ja": f"{district_number}地区",
                "label_en": f"Koto District {district_number}",
                "town_ja": None,
                "chome": None,
                "status": "active",
                "metadata": {
                    "district_number": district_number,
                    "schedule_year": 2026,
                    "address_mapping_status": (
                        "ready" if district_number in district_numbers_with_geometry else "pending_manual_transcription"
                    ),
                },
            }
        )
    return areas


def build_geometry_memberships(selector_dataset: dict) -> list[dict]:
    sources = selector_dataset.get("sources", [])
    source_urls = [str(item["url"]) for item in sources if item.get("url")]

    return [
        {
            "area_key": f"koto:district:{int(district['district_number']):02d}",
            "selector_source_label": "江東区 地区別地区番号対応",
            "selector_source_urls": source_urls,
            "members": district["members"],
        }
        for district in selector_dataset.get("districts", [])
    ]


def build_schedule_claims(
    schedule_patterns: list[dict],
    *,
    source_refs: dict[str, SourceRef],
) -> list[dict]:
    claims = []
    parser_artifact_key = "koto:artifact:entry_page:parser_output:2026"

    for pattern in schedule_patterns:
        district_number = pattern["district_number"]
        area_key = f"koto:district:{district_number:02d}"

        for category, days in pattern["weekly_schedule"].items():
            for day in days:
                claims.append(
                    {
                        "claim_key": f"koto:claim:district:{district_number:02d}:{category}:{day}",
                        "ward_slug": "koto",
                        "area_key": area_key,
                        "category": category,
                        "rule_key": f"koto:rule:weekly:{day}",
                        "source_key": source_refs["entry_page"].source_key,
                        "artifact_key": parser_artifact_key,
                        "source_type": "official",
                        "effective_from": EFFECTIVE_FROM,
                        "effective_to": EFFECTIVE_TO,
                        "confidence": 1.0,
                        "status": "active",
                        "submitted_by": SUBMITTED_BY,
                        "supersedes_claim_key": None,
                        "rule": {
                            "rule_key": f"koto:rule:weekly:{day}",
                            "rule_type": "weekly",
                            "rule_json": {"day": day},
                            "description": f"{day} weekly collection",
                        },
                        "evidence": {
                            "source_url": source_refs["entry_page"].url,
                            "source_image": pattern["source_image"],
                            "raw_alt": pattern["raw_alt"],
                            "district_number": district_number,
                            "fiscal_year": 2026,
                        },
                        "note": None,
                        "resolution_method": "official_priority",
                    }
                )

        nonburnable = pattern["nonweekly_schedule"]["nonburnable"]
        weekday = nonburnable["weekday"]
        claims.append(
            {
                "claim_key": f"koto:claim:district:{district_number:02d}:nonburnable:alternating:{weekday}",
                "ward_slug": "koto",
                "area_key": area_key,
                "category": "nonburnable",
                "rule_key": f"koto:rule:freeform:alternating_weeks:{weekday}",
                "source_key": source_refs["entry_page"].source_key,
                "artifact_key": parser_artifact_key,
                "source_type": "official",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": EFFECTIVE_TO,
                "confidence": 0.95,
                "status": "active",
                "submitted_by": SUBMITTED_BY,
                "supersedes_claim_key": None,
                "rule": {
                    "rule_key": f"koto:rule:freeform:alternating_weeks:{weekday}",
                    "rule_type": "freeform",
                    "rule_json": {
                        "text_ja": nonburnable["text_ja"],
                        "weekday": weekday,
                        "pattern": nonburnable["pattern"],
                    },
                    "description": nonburnable["text_ja"],
                },
                "evidence": {
                    "source_url": source_refs["entry_page"].url,
                    "source_image": pattern["source_image"],
                    "raw_alt": pattern["raw_alt"],
                    "district_number": district_number,
                    "fiscal_year": 2026,
                    "rule_text_ja": nonburnable["text_ja"],
                },
                "note": "隔週のどちら側かは月間カレンダー確認が必要です。",
                "resolution_method": "official_priority",
            }
        )

    return claims


def build_review_tasks(source_refs: dict[str, SourceRef], selector_dataset: dict) -> list[dict]:
    tasks = []
    for item in selector_dataset.get("unmatched_members", []):
        district_number = int(item["district_number"])
        tasks.append(
            {
                "task_key": f"koto:task:boundary-gap:{district_number:02d}:{item['town_ja']}",
                "ward_slug": "koto",
                "area_key": f"koto:district:{district_number:02d}",
                "source_key": source_refs["address_image"].source_key,
                "task_type": "source_refresh",
                "status": "open",
                "title": f"{item['town_ja']} の境界データ確認",
                "payload": {
                    "raw_image_path": str(ADDRESS_IMAGE_PATH.relative_to(ROOT)),
                    "selector_file_path": str(SELECTOR_INPUT_PATH.relative_to(ROOT)),
                    "member": item,
                },
                "created_by": SUBMITTED_BY,
            }
        )
    return tasks


def build_normalized_dataset(
    schedule_patterns: list[dict],
    *,
    source_refs: dict[str, SourceRef],
    ocr_metadata: dict,
    selector_dataset: dict,
) -> dict:
    artifacts = build_artifact_records(source_refs=source_refs, ocr_metadata=ocr_metadata)
    claims = build_schedule_claims(schedule_patterns, source_refs=source_refs)
    return {
        "ward_slug": "koto",
        "generated_at": now_iso(),
        "parser_version": PARSER_VERSION,
        "overview": {
            "source_quality": "medium",
            "source_label": "江東区 地区別資源回収・ごみ収集日一覧（2026年度）",
            "granularity": f"{len(schedule_patterns)}地区の収集パターンと地区境界を反映済みです。",
            "notes": [
                "12地区の weekly pattern を公式 entry page の画像 alt text から抽出しました。",
                "地区境界は公式 district image と公式区報テキスト版をもとに町丁目 selector へ正規化しています。",
                "燃やさないごみは隔週パターンなので freeform rule として保持しています。",
                "集合住宅や一部地域の例外は別 claim として扱う前提です。",
            ],
        },
        "sources": build_source_records(source_refs),
        "source_artifacts": artifacts,
        "artifacts": artifacts,
        "areas": build_area_records(schedule_patterns, selector_dataset),
        "geometry_memberships": build_geometry_memberships(selector_dataset),
        "schedule_rules": build_schedule_rules(schedule_patterns),
        "schedule_claims": claims,
        "claims": claims,
        "review_tasks": build_review_tasks(source_refs, selector_dataset),
    }


def main() -> None:
    source_refs = load_koto_sources()
    schedule_patterns = extract_schedule_patterns()
    selector_dataset = load_boundary_selector_dataset()

    write_json(
        SCHEDULE_OUTPUT_PATH,
        {
            "ward_slug": "koto",
            "fiscal_year": 2026,
            "generated_at": now_iso(),
            "parser_version": PARSER_VERSION,
            "source_path": str(ENTRY_PAGE_PATH.relative_to(ROOT)),
            "district_patterns": schedule_patterns,
        },
    )

    ocr_metadata = run_address_ocr()

    normalized_dataset = build_normalized_dataset(
        schedule_patterns,
        source_refs=source_refs,
        ocr_metadata=ocr_metadata,
        selector_dataset=selector_dataset,
    )
    write_json(NORMALIZED_OUTPUT_PATH, normalized_dataset)

    print(
        json.dumps(
            {
                "schedule_output": str(SCHEDULE_OUTPUT_PATH.relative_to(ROOT)),
                "ocr_text_output": str(OCR_TEXT_PATH.relative_to(ROOT)),
                "ocr_tsv_output": str(OCR_TSV_PATH.relative_to(ROOT)),
                "normalized_output": str(NORMALIZED_OUTPUT_PATH.relative_to(ROOT)),
                "district_count": len(schedule_patterns),
                "claim_count": len(normalized_dataset["schedule_claims"]),
                "rule_count": len(normalized_dataset["schedule_rules"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
