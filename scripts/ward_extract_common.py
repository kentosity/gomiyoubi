from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_REGISTRY_PATH = ROOT / "data" / "source-registry.json"

DAY_MAP = {
    "月": "monday",
    "月曜": "monday",
    "月曜日": "monday",
    "火": "tuesday",
    "火曜": "tuesday",
    "火曜日": "tuesday",
    "水": "wednesday",
    "水曜": "wednesday",
    "水曜日": "wednesday",
    "木": "thursday",
    "木曜": "thursday",
    "木曜日": "thursday",
    "金": "friday",
    "金曜": "friday",
    "金曜日": "friday",
    "土": "saturday",
    "土曜": "saturday",
    "土曜日": "saturday",
    "日": "sunday",
    "日曜": "sunday",
    "日曜日": "sunday",
}

DAY_LABELS = {
    "monday": "月曜日",
    "tuesday": "火曜日",
    "wednesday": "水曜日",
    "thursday": "木曜日",
    "friday": "金曜日",
    "saturday": "土曜日",
    "sunday": "日曜日",
}

FULLWIDTH_TO_ASCII = str.maketrans("０１２３４５６７８９～−　", "0123456789~- ")
KANJI_DIGIT_MAP = str.maketrans(
    {
        "〇": "0",
        "零": "0",
        "一": "1",
        "二": "2",
        "三": "3",
        "四": "4",
        "五": "5",
        "六": "6",
        "七": "7",
        "八": "8",
        "九": "9",
    }
)
SAFE_TRAILING_NOTES = {"注", "注1", "注2", "注3"}
NUMERAL_TOKEN = r"[0-9〇零一二三四五六七八九十]+"


def now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def load_json(path: Path):
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


def read_source_registry() -> dict:
    return load_json(SOURCE_REGISTRY_PATH)


def get_ward_entry(ward_slug: str) -> dict:
    registry = read_source_registry()
    return next(item for item in registry["wards"] if item["ward_slug"] == ward_slug)


def fetch_bytes(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": "gomiyoubi-bot/1.0"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def fetch_to_path(url: str, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(fetch_bytes(url))
    return path


def fetch_text(url: str, path: Path, encodings: tuple[str, ...] = ("utf-8", "cp932", "shift_jis")) -> str:
    data = fetch_bytes(url)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    for encoding in encodings:
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="ignore")


def pdf_to_text(pdf_path: Path, text_path: Path, layout: bool = True) -> str:
    command = ["/opt/homebrew/bin/pdftotext"]
    if layout:
        command.append("-layout")
    command.extend([str(pdf_path), "-"])
    result = subprocess.run(command, check=True, capture_output=True, text=True)
    text_path.parent.mkdir(parents=True, exist_ok=True)
    text_path.write_text(result.stdout, encoding="utf-8")
    return result.stdout


def fetch_pdf_text(url: str, pdf_path: Path, text_path: Path, layout: bool = True) -> str:
    fetch_to_path(url, pdf_path)
    return pdf_to_text(pdf_path, text_path, layout=layout)


def load_csv_rows(path: Path, encoding: str = "cp932") -> list[dict[str, str]]:
    with path.open("r", encoding=encoding, newline="") as handle:
        return list(csv.DictReader(handle))


def compact_text(value: str) -> str:
    return re.sub(r"\s+", "", value.translate(FULLWIDTH_TO_ASCII)).strip()


def clean_label(value: str) -> str:
    value = value.replace("　", " ").strip()
    value = re.sub(r"\s+", " ", value)
    value = value.translate(str.maketrans({"〜": "～"}))
    return value


def clean_japanese_token(value: str) -> str:
    return compact_text(value).replace("〜", "～")


def strip_safe_annotation(label: str) -> tuple[str, str | None]:
    normalized = clean_label(label)
    match = re.search(r"（([^）]+)）\s*$", normalized)
    if not match:
        return normalized, None
    note = clean_japanese_token(match.group(1))
    stripped = normalized[: match.start()].strip()
    if note in SAFE_TRAILING_NOTES:
        return stripped, note
    return normalized, note


def _expand_chome_selector(selector: str) -> list[str] | None:
    normalized = selector.translate(FULLWIDTH_TO_ASCII).translate(KANJI_DIGIT_MAP).replace("〜", "～")
    normalized = normalized.replace("丁目から", "～").replace("から", "～")
    normalized = normalized.replace("丁目", "")
    normalized = normalized.replace("~", "～")
    normalized = normalized.strip("・")
    if not normalized:
        return None
    if "～" in normalized:
        start_text, end_text = normalized.split("～", 1)
        start_normalized = _normalize_chome_value(start_text)
        end_normalized = _normalize_chome_value(end_text)
        if start_normalized is None or end_normalized is None:
            return None
        start = int(start_normalized)
        end = int(end_normalized)
        if start > end:
            return None
        return [str(value) for value in range(start, end + 1)]
    if "・" in normalized:
        parts = []
        for part in normalized.split("・"):
            normalized_part = _normalize_chome_value(part)
            if normalized_part is None:
                return None
            parts.append(normalized_part)
        return parts
    normalized_value = _normalize_chome_value(normalized)
    return [normalized_value] if normalized_value is not None else None


def _normalize_chome_value(value: str) -> str | None:
    normalized = value.translate(FULLWIDTH_TO_ASCII).translate(KANJI_DIGIT_MAP).replace("〜", "～").replace("~", "～")
    if re.fullmatch(r"\d+", normalized):
        return str(int(normalized))

    if not re.fullmatch(r"[十\d]+", normalized):
        return None

    total = 0
    current = 0
    for char in normalized:
        if char == "十":
            current = 1 if current == 0 else current
            total += current * 10
            current = 0
        else:
            current = current * 10 + int(char)
    total += current
    return str(total) if total > 0 else None


def _parse_geometry_members(label: str, known_towns: list[str]) -> list[dict] | None:
    normalized, annotation = strip_safe_annotation(label)
    compacted = clean_japanese_token(normalized)
    compacted = compacted.replace("、", "・").replace(",", "・")
    compacted = compacted.replace("丁目から", "～").replace("丁目～", "～").replace("丁目~", "～")
    compacted = compacted.replace("から", "～").replace("~", "～")

    previous = None
    while previous != compacted:
        previous = compacted
        compacted = re.sub(
            rf"({NUMERAL_TOKEN})丁目・(?={NUMERAL_TOKEN})",
            r"\1・",
            compacted,
        )

    if any(token in compacted for token in ("除", "以外", "上記", "棟", "毎日", "地域資源")):
        return None
    if re.search(r"\d+番|\d+号", compacted):
        return None

    if compacted.endswith("全域"):
        town_ja = compacted[: -len("全域")]
        return [{"town_ja": town_ja}] if town_ja in known_towns else None

    if "丁目" not in compacted and not re.search(r"\d", compacted):
        return [{"town_ja": normalized}] if normalized in known_towns else None

    for town_ja in known_towns:
        if not compacted.startswith(town_ja) or not compacted.endswith("丁目"):
            continue
        selector = compacted[len(town_ja) : -len("丁目")]
        chomes = _expand_chome_selector(selector)
        if not chomes:
            continue
        normalized_chomes = []
        for chome in chomes:
            normalized_chome = _normalize_chome_value(str(chome))
            if normalized_chome is None:
                return None
            normalized_chomes.append(normalized_chome)
        return [{"town_ja": town_ja, "chomes": normalized_chomes}]

    members: list[dict] = []
    current_town: str | None = None
    for part in compacted.split("・"):
        token = part.strip()
        if not token:
            continue

        town_ja = next((town for town in known_towns if token.startswith(town)), None)
        selector_text: str | None = None
        if town_ja:
            suffix = token[len(town_ja) :]
            if suffix.endswith("丁目"):
                selector_text = suffix[: -len("丁目")]
            elif re.fullmatch(rf"{NUMERAL_TOKEN}(?:・{NUMERAL_TOKEN}|～{NUMERAL_TOKEN})*", suffix):
                selector_text = suffix
            else:
                selector_text = None
            current_town = town_ja
        elif current_town and token.endswith("丁目"):
            town_ja = current_town
            selector_text = token[: -len("丁目")]

        if town_ja and selector_text is not None:
            chomes = _expand_chome_selector(selector_text)
            if not chomes:
                return None

            normalized_chomes = []
            for chome in chomes:
                normalized_chome = _normalize_chome_value(str(chome))
                if normalized_chome is None:
                    return None
                normalized_chomes.append(normalized_chome)

            members.append({"town_ja": town_ja, "chomes": normalized_chomes})
            continue

        if annotation in SAFE_TRAILING_NOTES and not re.search(r"\d", token):
            continue
        return None

    return members or None


def build_geometry_membership_payload(
    *,
    ward_slug: str,
    areas: list[dict],
    source_key: str,
    source_label: str,
    source_urls: list[str],
    created_by: str,
) -> tuple[list[dict], list[dict]]:
    from tokyo_small_area_boundaries import load_ward_small_area_features

    memberships: list[dict] = []
    review_tasks: list[dict] = []
    boundary_features = load_ward_small_area_features(ward_slug)
    known_towns = sorted({str(feature["town_ja"]) for feature in boundary_features}, key=len, reverse=True)
    known_chomes_by_town: dict[str, set[str]] = {}
    for feature in boundary_features:
        town_ja = str(feature["town_ja"])
        chome = feature.get("chome")
        if chome is None:
            continue
        known_chomes_by_town.setdefault(town_ja, set()).add(str(chome))

    for area in areas:
        area_key = str(area["area_key"])
        label = str(area["label_ja"])
        normalized, annotation = strip_safe_annotation(label)
        compacted = clean_japanese_token(normalized)
        members = _parse_geometry_members(label, known_towns)
        if members:
            if any(
                "chomes" in member
                and any(str(chome) not in known_chomes_by_town.get(str(member["town_ja"]), set()) for chome in member["chomes"])
                for member in members
            ):
                review_tasks.append(
                    {
                        "task_key": f"{area_key}:area_match",
                        "task_type": "area_match",
                        "area_key": area_key,
                        "source_key": source_key,
                        "title": f"Geometry match requires review: {label}",
                        "payload": {
                            "label_ja": label,
                            "normalized_label_ja": normalized,
                            "annotation": annotation,
                            "reason": "Parsed chome selector does not exist in ward boundary data.",
                        },
                        "created_by": created_by,
                    }
                )
                continue

            merged_members: dict[str, set[str] | None] = {}
            for member in members:
                town_ja = str(member["town_ja"])
                chomes = member.get("chomes")
                if not chomes:
                    merged_members[town_ja] = None
                    continue
                if town_ja not in merged_members or merged_members[town_ja] is None:
                    merged_members[town_ja] = set(str(chome) for chome in chomes)
                else:
                    merged_members[town_ja].update(str(chome) for chome in chomes)

            memberships.append(
                {
                    "area_key": area_key,
                    "selector_source_label": source_label,
                    "selector_source_urls": source_urls,
                    "members": [
                        {"town_ja": town_ja}
                        if chomes is None
                        else {"town_ja": town_ja, "chomes": sorted(chomes, key=int)}
                        for town_ja, chomes in merged_members.items()
                    ],
                }
            )
            continue

        review_tasks.append(
            {
                "task_key": f"{area_key}:area_match",
                "task_type": "area_match",
                "area_key": area_key,
                "source_key": source_key,
                "title": f"Geometry match requires review: {label}",
                "payload": {
                    "label_ja": label,
                    "normalized_label_ja": normalized,
                    "annotation": annotation,
                    "reason": "Could not safely map label to town/chome selectors.",
                },
                "created_by": created_by,
            }
        )

    return memberships, review_tasks


def parse_weekdays(text: str) -> list[str]:
    normalized = compact_text(text)
    if not normalized:
        return []

    ordered_days = ["sunday", "monday", "tuesday", "wednesday", "thursday", "friday", "saturday"]
    separator_normalized = re.sub(r"[、,／/･]", "・", normalized.replace("毎週", ""))
    matches = re.findall(r"(?:^|・)([月火水木金土日])(?:曜日|曜)?(?=・|$)", separator_normalized)
    seen: set[str] = set()
    days: list[str] = []
    for match in matches:
        key = DAY_MAP.get(match)
        if key and key not in seen:
            seen.add(key)
            days.append(key)
    return [day for day in ordered_days if day in days]


def parse_monthly_rule(text: str) -> dict | None:
    normalized = compact_text(text)
    if not normalized:
        return None

    weekday = None
    for token, key in DAY_MAP.items():
        if token in normalized:
            weekday = key
            break
    if weekday is None:
        return None

    ordinal_matches = re.findall(r"[第]?([1234])", normalized)
    ordinals = [int(value) for value in ordinal_matches[:4]]
    if not ordinals:
        return None

    seen: set[int] = set()
    ordered_ordinals: list[int] = []
    for ordinal in ordinals:
        if ordinal not in seen:
            seen.add(ordinal)
            ordered_ordinals.append(ordinal)

    return {
        "rule_type": "nth_weekday",
        "day": weekday,
        "ordinals": ordered_ordinals,
        "text_ja": clean_label(text),
    }


def make_weekly_rule(ward_slug: str, day: str) -> dict:
    return {
        "rule_key": f"{ward_slug}:rule:weekly:{day}",
        "rule_type": "weekly",
        "rule_json": {"day": day},
        "description": f"{DAY_LABELS[day]} weekly collection",
    }


def make_monthly_rule(ward_slug: str, monthly_rule: dict) -> dict:
    ordinals = "-".join(str(item) for item in monthly_rule["ordinals"])
    day = monthly_rule["day"]
    return {
        "rule_key": f"{ward_slug}:rule:nth_weekday:{day}:{ordinals}",
        "rule_type": "nth_weekday",
        "rule_json": {
            "day": day,
            "ordinals": monthly_rule["ordinals"],
            "text_ja": monthly_rule["text_ja"],
        },
        "description": monthly_rule["text_ja"],
    }


def build_claim(
    *,
    ward_slug: str,
    area_key: str,
    category: str,
    rule: dict,
    source_key: str,
    artifact_key: str,
    source_url: str,
    submitted_by: str,
    effective_from: str,
    effective_to: str,
    evidence: dict,
    note: str | None = None,
    confidence: float = 1.0,
) -> dict:
    rule_suffix = rule["rule_key"].split(":")[-1]
    return {
        "claim_key": f"{area_key}:{category}:{rule_suffix}:official",
        "area_key": area_key,
        "category": category,
        "rule": rule,
        "source_key": source_key,
        "artifact_key": artifact_key,
        "source_type": "official",
        "effective_from": effective_from,
        "effective_to": effective_to,
        "confidence": confidence,
        "submitted_by": submitted_by,
        "resolution_method": "official_priority",
        "evidence": {"source_url": source_url, **evidence},
        "note": note,
    }


def build_area(area_key: str, label_ja: str, *, metadata: dict | None = None) -> dict:
    return {
        "area_key": area_key,
        "parent_area_key": f"ward:{area_key.split(':', 1)[0]}",
        "area_kind": "district",
        "label_ja": label_ja,
        "status": "active",
        "metadata": metadata or {},
    }


def build_dataset(
    *,
    ward_slug: str,
    source_quality: str,
    source_label: str,
    granularity: str,
    notes: list[str],
    areas: list[dict],
    claims: list[dict],
    artifacts: list[dict],
    geometry_memberships: list[dict] | None = None,
    review_tasks: list[dict] | None = None,
) -> dict:
    return {
        "ward_slug": ward_slug,
        "generated_at": now_iso(),
        "overview": {
            "source_quality": source_quality,
            "source_label": source_label,
            "granularity": granularity,
            "notes": notes,
            "day_signals": {},
        },
        "artifacts": artifacts,
        "areas": areas,
        "claims": claims,
        "geometry_memberships": geometry_memberships or [],
        "review_tasks": review_tasks or [],
    }


def encode_form(data: dict[str, str]) -> bytes:
    return urllib.parse.urlencode(data).encode("utf-8")
