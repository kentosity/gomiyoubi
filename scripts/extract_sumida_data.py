from __future__ import annotations

import calendar
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw" / "sumida"
EXTRACTED_DIR = ROOT / "data" / "extracted" / "sumida"
NORMALIZED_DIR = ROOT / "data" / "normalized" / "sumida"
MANUAL_DIR = ROOT / "data" / "manual" / "sumida"

ENTRY_PAGE_PATH = RAW_DIR / "sumida_entry_page.html"
SUMMARY_PDF_PATH = RAW_DIR / "sumida_download_01.pdf"
WRITE_IN_PDF_PATH = RAW_DIR / "sumida_download_02.pdf"
ZONE_SAMPLE_PDF_PATH = RAW_DIR / "sumida_download_03.pdf"

SUMMARY_IMAGE_PATH = EXTRACTED_DIR / "summary-calendar-2026-page-1.png"
SUMMARY_OCR_PATH = EXTRACTED_DIR / "summary-ocr.txt"
ZONE_LABELS_PATH = EXTRACTED_DIR / "zone-labels.json"
SUMMARY_PATTERNS_PATH = EXTRACTED_DIR / "zone-patterns-2026.json"
MANIFEST_PATH = EXTRACTED_DIR / "extraction-manifest.json"
REVIEWED_PATTERN_INPUT_PATH = MANUAL_DIR / "summary-calendar-2026.reviewed.json"

NORMALIZED_DATASET_PATH = NORMALIZED_DIR / "zone-schedules-2026.json"

SCRIPT_VERSION = "2026-04-01"
SUBMITTED_BY = "system/extract_sumida_data"
EFFECTIVE_FROM = "2026-04-01"
EFFECTIVE_TO = "2027-03-31"

DAY_ORDER = (
    "sunday",
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
)

DAY_LABELS = {
    "sunday": "日曜日",
    "monday": "月曜日",
    "tuesday": "火曜日",
    "wednesday": "水曜日",
    "thursday": "木曜日",
    "friday": "金曜日",
    "saturday": "土曜日",
}

CALENDAR_WEEKDAY_INDEX = {
    "monday": 0,
    "tuesday": 1,
    "wednesday": 2,
    "thursday": 3,
    "friday": 4,
    "saturday": 5,
    "sunday": 6,
}

def sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def write_json(path: Path, payload: object):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def extract_zone_labels() -> list[str]:
    html = ENTRY_PAGE_PATH.read_text(encoding="utf-8")
    matches = re.findall(
        r'href="gomi-calendar\.files/(0804_\d{2}\.pdf)"[^>]*>([^<]+?)（2026年4月から2026年9月まで）',
        html,
    )
    labels = [label.strip() for _, label in matches]
    if len(labels) != 12:
        raise ValueError(f"Expected 12 Sumida zone labels, found {len(labels)}")
    return labels


def load_reviewed_pattern_rows() -> list[dict]:
    payload = load_json(REVIEWED_PATTERN_INPUT_PATH)
    rows = payload.get("rows", [])
    if len(rows) == 0:
        raise ValueError(f"No reviewed Sumida rows found in {REVIEWED_PATTERN_INPUT_PATH}")
    return rows


def render_summary_page():
    with tempfile.TemporaryDirectory() as temp_dir:
        prefix = Path(temp_dir) / "sumida-summary"
        subprocess.run(
            [
                "pdftoppm",
                "-png",
                "-r",
                "300",
                str(SUMMARY_PDF_PATH),
                str(prefix),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        rendered_path = prefix.with_name(f"{prefix.name}-1.png")
        if not rendered_path.exists():
            raise FileNotFoundError(f"Expected rendered page: {rendered_path}")
        shutil.copy2(rendered_path, SUMMARY_IMAGE_PATH)


def run_summary_ocr():
    result = subprocess.run(
        [
            "tesseract",
            str(SUMMARY_IMAGE_PATH),
            "stdout",
            "-l",
            "jpn",
            "--psm",
            "6",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    SUMMARY_OCR_PATH.write_text(result.stdout, encoding="utf-8")


def nth_weekday_dates(start_year: int, start_month: int, months: int, day: str, ordinals: tuple[int, ...]):
    output: dict[str, list[str]] = {}
    weekday_index = CALENDAR_WEEKDAY_INDEX[day]
    year = start_year
    month = start_month

    for _ in range(months):
        dates = []
        matrix = calendar.monthcalendar(year, month)
        occurrences = [week[weekday_index] for week in matrix if week[weekday_index] != 0]
        for ordinal in ordinals:
            day_number = occurrences[ordinal - 1]
            dates.append(f"{year:04d}-{month:02d}-{day_number:02d}")

        output[f"{year:04d}-{month:02d}"] = dates

        month += 1
        if month == 13:
            month = 1
            year += 1

    return output


def build_pattern_rows(labels: list[str], reviewed_rows: list[dict]) -> list[dict]:
    if len(labels) != len(reviewed_rows):
        raise ValueError(
            f"Expected {len(reviewed_rows)} labels, received {len(labels)}"
        )

    rows = []
    for index, (label, pattern) in enumerate(zip(labels, reviewed_rows), start=1):
        ordinals = tuple(pattern["nonburnable_ordinals"])
        nonburnable_day = str(pattern["nonburnable_day"])
        pattern_id = (
            f"resource-{pattern['resource_day']}_plastic-{pattern['plastic_day']}"
            f"_burnable-{'-'.join(pattern['burnable_days'])}"
            f"_nonburnable-{ordinals[0]}-{ordinals[1]}-{nonburnable_day}"
        )
        rows.append(
            {
                "zone_index": index,
                "zone_code": f"{index:02d}",
                "label_ja": label,
                "resource_day": pattern["resource_day"],
                "plastic_day": pattern["plastic_day"],
                "burnable_days": list(pattern["burnable_days"]),
                "nonburnable": {
                    "day": nonburnable_day,
                    "ordinals": list(ordinals),
                    "label_ja": f"{ordinals[0]}回目・{ordinals[1]}回目 {DAY_LABELS[nonburnable_day]}",
                    "dates_by_month": nth_weekday_dates(2026, 4, 12, nonburnable_day, ordinals),
                },
                "source_evidence": {
                    "entry_page_path": str(ENTRY_PAGE_PATH.relative_to(ROOT)),
                    "summary_pdf_path": str(SUMMARY_PDF_PATH.relative_to(ROOT)),
                    "summary_row_index": index,
                    "pattern_id": pattern_id,
                },
            }
        )
    return rows


def build_artifacts() -> list[dict]:
    return [
        {
            "artifact_key": "sumida:artifact:entry-page:zone-labels",
            "source_key": "sumida:entry_page",
            "artifact_kind": "parser_output",
            "local_path": str(ZONE_LABELS_PATH.relative_to(ROOT)),
            "content_type": "application/json",
            "parser_version": SCRIPT_VERSION,
            "metadata": {
                "raw_path": str(ENTRY_PAGE_PATH.relative_to(ROOT)),
                "method": "regex_html_parse",
            },
        },
        {
            "artifact_key": "sumida:artifact:summary-calendar:ocr-jpn",
            "source_key": "sumida:download:01",
            "artifact_kind": "ocr",
            "local_path": str(SUMMARY_OCR_PATH.relative_to(ROOT)),
            "content_type": "text/plain",
            "parser_version": SCRIPT_VERSION,
            "ocr_engine": "tesseract jpn --psm 6",
            "metadata": {
                "raw_pdf_path": str(SUMMARY_PDF_PATH.relative_to(ROOT)),
                "rendered_page_path": str(SUMMARY_IMAGE_PATH.relative_to(ROOT)),
            },
        },
        {
            "artifact_key": "sumida:artifact:summary-calendar:patterns",
            "source_key": "sumida:download:01",
            "artifact_kind": "manual_transcription",
            "local_path": str(REVIEWED_PATTERN_INPUT_PATH.relative_to(ROOT)),
            "content_type": "application/json",
            "parser_version": SCRIPT_VERSION,
            "metadata": {
                "raw_pdf_path": str(SUMMARY_PDF_PATH.relative_to(ROOT)),
                "rendered_page_path": str(SUMMARY_IMAGE_PATH.relative_to(ROOT)),
                "extracted_output_path": str(SUMMARY_PATTERNS_PATH.relative_to(ROOT)),
                "method": "manual_review_of_official_summary_table",
            },
        },
    ]


def build_areas(pattern_rows: list[dict]) -> list[dict]:
    return [
        {
            "area_key": f"sumida:zone:{row['zone_code']}",
            "parent_area_key": "ward:sumida",
            "area_kind": "district",
            "label_ja": row["label_ja"],
            "status": "active",
            "metadata": {
                "zone_index": row["zone_index"],
                "zone_code": row["zone_code"],
                "source_label_ja": row["label_ja"],
                "source_kind": "summary_calendar_zone",
            },
        }
        for row in pattern_rows
    ]


def weekly_rule(day: str) -> dict:
    return {
        "rule_key": f"weekly:{day}",
        "rule_type": "weekly",
        "rule_json": {"day": day},
        "description": f"Weekly pickup on {day}",
    }


def nonburnable_rule(day: str, ordinals: tuple[int, ...], dates_by_month: dict[str, list[str]]) -> dict:
    ordinal_key = "-".join(str(ordinal) for ordinal in ordinals)
    return {
        "rule_key": f"sumida:freeform:nonburnable:{ordinal_key}:{day}",
        "rule_type": "freeform",
        "rule_json": {
            "pattern_kind": "alternating_monthly_weekday",
            "day": day,
            "ordinals": list(ordinals),
            "dates_by_month": dates_by_month,
            "display_label_ja": f"{ordinals[0]}回目・{ordinals[1]}回目 {DAY_LABELS[day]}",
        },
        "description": f"Nonburnable pickup on the {ordinal_key} occurrences of {day} each month",
    }


def build_claims(pattern_rows: list[dict]) -> list[dict]:
    claims = []

    for row in pattern_rows:
        area_key = f"sumida:zone:{row['zone_code']}"
        evidence_base = {
            "zone_index": row["zone_index"],
            "zone_label_ja": row["label_ja"],
            "summary_pdf_path": str(SUMMARY_PDF_PATH.relative_to(ROOT)),
            "entry_page_path": str(ENTRY_PAGE_PATH.relative_to(ROOT)),
            "summary_row_index": row["zone_index"],
        }

        claims.append(
            {
                "claim_key": f"{area_key}:weekly:{row['resource_day']}:resource:official",
                "area_key": area_key,
                "category": "resource",
                "rule": weekly_rule(str(row["resource_day"])),
                "source_key": "sumida:download:01",
                "artifact_key": "sumida:artifact:summary-calendar:patterns",
                "source_type": "official",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": EFFECTIVE_TO,
                "confidence": 0.98,
                "submitted_by": SUBMITTED_BY,
                "resolution_method": "official_priority",
                "evidence": {
                    **evidence_base,
                    "column": "resource_day",
                    "display_label_ja": DAY_LABELS[str(row["resource_day"])],
                },
                "note": "Extracted from the official 2026 Sumida summary calendar table.",
            }
        )
        claims.append(
            {
                "claim_key": f"{area_key}:weekly:{row['plastic_day']}:plastic:official",
                "area_key": area_key,
                "category": "plastic",
                "rule": weekly_rule(str(row["plastic_day"])),
                "source_key": "sumida:download:01",
                "artifact_key": "sumida:artifact:summary-calendar:patterns",
                "source_type": "official",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": EFFECTIVE_TO,
                "confidence": 0.98,
                "submitted_by": SUBMITTED_BY,
                "resolution_method": "official_priority",
                "evidence": {
                    **evidence_base,
                    "column": "plastic_day",
                    "display_label_ja": DAY_LABELS[str(row["plastic_day"])],
                },
                "note": "Extracted from the official 2026 Sumida summary calendar table.",
            }
        )
        for burnable_day in row["burnable_days"]:
            claims.append(
                {
                    "claim_key": f"{area_key}:weekly:{burnable_day}:burnable:official",
                    "area_key": area_key,
                    "category": "burnable",
                    "rule": weekly_rule(str(burnable_day)),
                    "source_key": "sumida:download:01",
                    "artifact_key": "sumida:artifact:summary-calendar:patterns",
                    "source_type": "official",
                    "effective_from": EFFECTIVE_FROM,
                    "effective_to": EFFECTIVE_TO,
                    "confidence": 0.98,
                    "submitted_by": SUBMITTED_BY,
                    "resolution_method": "official_priority",
                    "evidence": {
                        **evidence_base,
                        "column": "burnable_days",
                        "display_label_ja": DAY_LABELS[str(burnable_day)],
                    },
                    "note": "Extracted from the official 2026 Sumida summary calendar table.",
                }
            )

        ordinals = tuple(row["nonburnable"]["ordinals"])
        nonburnable_day = str(row["nonburnable"]["day"])
        claims.append(
            {
                "claim_key": (
                    f"{area_key}:freeform:{ordinals[0]}-{ordinals[1]}:{nonburnable_day}:nonburnable:official"
                ),
                "area_key": area_key,
                "category": "nonburnable",
                "rule": nonburnable_rule(
                    nonburnable_day,
                    ordinals,
                    dict(row["nonburnable"]["dates_by_month"]),
                ),
                "source_key": "sumida:download:01",
                "artifact_key": "sumida:artifact:summary-calendar:patterns",
                "source_type": "official",
                "effective_from": EFFECTIVE_FROM,
                "effective_to": EFFECTIVE_TO,
                "confidence": 0.96,
                "submitted_by": SUBMITTED_BY,
                "resolution_method": "official_priority",
                "evidence": {
                    **evidence_base,
                    "column": "nonburnable",
                    "display_label_ja": row["nonburnable"]["label_ja"],
                    "dates_by_month": row["nonburnable"]["dates_by_month"],
                },
                "note": "Official Sumida summary calendar shows nonburnable pickup as alternating monthly weekday occurrences.",
            }
        )

    return claims


def build_manifest(labels: list[str], pattern_rows: list[dict]) -> dict:
    raw_files = []
    for path in (ENTRY_PAGE_PATH, SUMMARY_PDF_PATH, WRITE_IN_PDF_PATH, ZONE_SAMPLE_PDF_PATH):
        raw_files.append(
            {
                "path": str(path.relative_to(ROOT)),
                "sha256": sha256_for_file(path),
            }
        )

    return {
        "ward_slug": "sumida",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "script_version": SCRIPT_VERSION,
        "raw_files": raw_files,
        "outputs": [
            str(ZONE_LABELS_PATH.relative_to(ROOT)),
            str(SUMMARY_IMAGE_PATH.relative_to(ROOT)),
            str(SUMMARY_OCR_PATH.relative_to(ROOT)),
            str(REVIEWED_PATTERN_INPUT_PATH.relative_to(ROOT)),
            str(SUMMARY_PATTERNS_PATH.relative_to(ROOT)),
            str(NORMALIZED_DATASET_PATH.relative_to(ROOT)),
        ],
        "zone_count": len(labels),
        "claim_count": len(pattern_rows) * 5,
        "notes": [
            "Zone labels come from the official Sumida entry page links for 0804_01.pdf through 0804_12.pdf.",
            "Weekly and alternating nonburnable patterns are loaded from a reviewed transcription file, not embedded in this script.",
            "The OCR text is preserved as an audit artifact, but the normalized pattern rows are based on manual verification against the rendered page image.",
        ],
    }


def parse_zone_members(label_ja: str) -> list[dict]:
    members = []
    for chunk in [item.strip() for item in label_ja.split("、") if item.strip()]:
        match = re.match(r"^(?P<town>.+?)(?P<chomes>\d+(?:・\d+)*)丁目$", chunk)
        if match:
            members.append(
                {
                    "town_ja": match.group("town"),
                    "chomes": match.group("chomes").split("・"),
                }
            )
            continue

        members.append({"town_ja": chunk})

    return members


def build_geometry_memberships(pattern_rows: list[dict]) -> list[dict]:
    return [
        {
            "area_key": f"sumida:zone:{row['zone_code']}",
            "selector_source_label": "墨田区 ごみの分別・収集日ページ",
            "selector_source_urls": [
                "https://www.city.sumida.lg.jp/kurashi/gomi_recycle/kateikei/gomi-calendar.html"
            ],
            "members": parse_zone_members(str(row["label_ja"])),
        }
        for row in pattern_rows
    ]


def main():
    EXTRACTED_DIR.mkdir(parents=True, exist_ok=True)
    NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)

    labels = extract_zone_labels()
    write_json(
        ZONE_LABELS_PATH,
        {
            "ward_slug": "sumida",
            "source_path": str(ENTRY_PAGE_PATH.relative_to(ROOT)),
            "labels": [
                {
                    "zone_index": index,
                    "zone_code": f"{index:02d}",
                    "label_ja": label,
                }
                for index, label in enumerate(labels, start=1)
            ],
        },
    )

    render_summary_page()
    run_summary_ocr()

    reviewed_rows = load_reviewed_pattern_rows()
    pattern_rows = build_pattern_rows(labels, reviewed_rows)
    write_json(
        SUMMARY_PATTERNS_PATH,
        {
            "ward_slug": "sumida",
            "source_path": str(SUMMARY_PDF_PATH.relative_to(ROOT)),
            "rows": pattern_rows,
        },
    )

    write_json(
        NORMALIZED_DATASET_PATH,
        {
            "ward_slug": "sumida",
            "overview": {
                "source_quality": "medium",
                "source_label": "墨田区 資源とごみの収集カレンダー",
                "granularity": f"{len(pattern_rows)}地区の収集パターンと地区境界を反映済みです。",
                "notes": [
                    "地区ラベルは公式 entry page の PDF リンク文言から抽出しています。",
                    "収集曜日は公式 2026 年度 summary calendar をレビュー済み転記から正規化しています。",
                    "燃やさないごみは月内の第1・第3回または第2・第4回の freeform rule として保持しています。",
                ],
                "day_signals": {},
            },
            "artifacts": build_artifacts(),
            "areas": build_areas(pattern_rows),
            "geometry_memberships": build_geometry_memberships(pattern_rows),
            "claims": build_claims(pattern_rows),
            "review_tasks": [],
        },
    )
    write_json(MANIFEST_PATH, build_manifest(labels, pattern_rows))

    print(
        json.dumps(
            {
                "zone_labels_path": str(ZONE_LABELS_PATH.relative_to(ROOT)),
                "summary_patterns_path": str(SUMMARY_PATTERNS_PATH.relative_to(ROOT)),
                "normalized_dataset_path": str(NORMALIZED_DATASET_PATH.relative_to(ROOT)),
                "zone_count": len(labels),
                "claim_count": len(pattern_rows) * 5,
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
