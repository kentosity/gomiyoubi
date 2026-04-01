from __future__ import annotations

import argparse
import csv
import datetime
import io
import json
import re
import urllib.parse
import urllib.request
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path

from bs4 import BeautifulSoup

from ward_extract_common import (
    DAY_LABELS,
    ROOT,
    build_area,
    build_claim,
    build_dataset,
    build_geometry_membership_payload,
    clean_japanese_token,
    clean_label,
    compact_text,
    encode_form,
    fetch_pdf_text,
    fetch_text,
    get_ward_entry,
    now_iso,
    parse_monthly_rule,
    parse_weekdays,
    read_source_registry,
    sha256_file,
    write_json,
    make_monthly_rule,
    make_weekly_rule,
)

SCRIPT_NAME = "scripts/extract_more_wards.py"
PARSER_VERSION = "ward_extract_v1"
EFFECTIVE_FROM = "2026-04-01"
EFFECTIVE_TO = "2027-03-31"

SUPPORTED_WARDS = (
    "adachi",
    "arakawa",
    "chiyoda",
    "edogawa",
    "itabashi",
    "meguro",
    "shinagawa",
    "minato",
    "nerima",
    "setagaya",
    "taito",
    "bunkyo",
    "shinjuku",
    "shibuya",
    "nakano",
    "suginami",
    "toshima",
)

CIRCLED_DIGITS = str.maketrans({"①": "1", "②": "2", "③": "3", "④": "4"})


@dataclass
class ParsedArea:
    label_ja: str
    weekly: dict[str, list[str]]
    monthly: dict[str, dict]
    evidence: dict
    note: str | None = None
    confidence: float = 1.0


def parse_args():
    parser = argparse.ArgumentParser(description="Extract additional ward schedule datasets.")
    parser.add_argument("--ward", choices=SUPPORTED_WARDS)
    return parser.parse_args()


def normalize_pdf_text(text: str) -> str:
    return text.translate(CIRCLED_DIGITS).translate(str.maketrans("１２３４", "1234")).replace("〜", "～")


def absolute_url(base_url: str, href: str) -> str:
    return urllib.parse.urljoin(base_url, href)


def area_to_claims(
    *,
    ward_slug: str,
    source_key: str,
    source_url: str,
    artifact_key: str,
    parsed_areas: list[ParsedArea],
) -> tuple[list[dict], list[dict]]:
    areas: list[dict] = []
    claims: list[dict] = []
    for index, parsed_area in enumerate(parsed_areas, start=1):
        area_key = f"{ward_slug}:area:{index:03d}"
        areas.append(
            build_area(
                area_key,
                parsed_area.label_ja,
                metadata={"extraction_scope": "ward_level_only"},
            )
        )

        for category, days in parsed_area.weekly.items():
            for day in days:
                claims.append(
                    build_claim(
                        ward_slug=ward_slug,
                        area_key=area_key,
                        category=category,
                        rule=make_weekly_rule(ward_slug, day),
                        source_key=source_key,
                        artifact_key=artifact_key,
                        source_url=source_url,
                        submitted_by=SCRIPT_NAME,
                        effective_from=EFFECTIVE_FROM,
                        effective_to=EFFECTIVE_TO,
                        evidence=parsed_area.evidence,
                        note=parsed_area.note,
                        confidence=parsed_area.confidence,
                    )
                )

        for category, monthly_rule in parsed_area.monthly.items():
            claims.append(
                build_claim(
                    ward_slug=ward_slug,
                    area_key=area_key,
                    category=category,
                    rule=make_monthly_rule(ward_slug, monthly_rule),
                    source_key=source_key,
                    artifact_key=artifact_key,
                    source_url=source_url,
                    submitted_by=SCRIPT_NAME,
                    effective_from=EFFECTIVE_FROM,
                    effective_to=EFFECTIVE_TO,
                    evidence=parsed_area.evidence,
                    note=parsed_area.note,
                    confidence=parsed_area.confidence,
                )
            )

    return areas, claims


def build_artifact(ward_slug: str, source_key: str, local_path: Path) -> dict:
    return {
        "artifact_key": f"{ward_slug}:artifact:parser_output:2026",
        "source_key": source_key,
        "artifact_kind": "parser_output",
        "local_path": str(local_path.relative_to(ROOT)),
        "content_type": "application/json",
        "sha256": sha256_file(local_path),
        "fetched_at": now_iso(),
        "parser_version": PARSER_VERSION,
        "metadata": {"ward_slug": ward_slug, "script": SCRIPT_NAME},
    }


def infer_primary_days(counter: Counter[str], *, top_n: int = 1, exclude: set[str] | None = None) -> list[str]:
    exclude = exclude or set()
    candidates = [
        (day, count)
        for day, count in counter.items()
        if day != "sunday" and day not in exclude and count > 0
    ]
    weekday_order = {day: index for index, day in enumerate(("monday", "tuesday", "wednesday", "thursday", "friday", "saturday"))}
    candidates.sort(key=lambda item: (-item[1], weekday_order.get(item[0], 99)))
    return [day for day, _count in candidates[:top_n]]


def attach_geometry_memberships(
    *,
    dataset: dict,
    areas: list[dict],
    source_key: str,
    source_label: str,
    source_urls: list[str],
) -> dict:
    memberships, area_match_tasks = build_geometry_membership_payload(
        ward_slug=dataset["ward_slug"],
        areas=areas,
        source_key=source_key,
        source_label=source_label,
        source_urls=source_urls,
        created_by=SCRIPT_NAME,
    )
    dataset["geometry_memberships"] = memberships
    dataset["review_tasks"] = [*(dataset.get("review_tasks") or []), *area_match_tasks]
    return dataset


def registry_source(ward_slug: str, kind: str, index: int | None = None) -> dict:
    ward_entry = get_ward_entry(ward_slug)
    official_sources = ward_entry.get("official_sources", {})
    if kind == "entry_page":
        return official_sources["entry_page"]
    if kind == "download":
        assert index is not None
        return official_sources["downloads"][index - 1]
    if kind == "related_page":
        assert index is not None
        return official_sources["related_pages"][index - 1]
    raise KeyError(kind)


def download_entry_html(ward_slug: str) -> tuple[Path, str]:
    raw_path = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_entry_page.html"
    source = registry_source(ward_slug, "entry_page")
    text = fetch_text(source["url"], raw_path)
    return raw_path, text


def parse_adachi() -> tuple[dict, Path]:
    ward_slug = "adachi"
    source = registry_source(ward_slug, "download", 1)
    raw_pdf = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_download_01.pdf"
    extracted_txt = ROOT / "data" / "extracted" / ward_slug / "wakedashi2026.txt"
    lines = normalize_pdf_text(fetch_pdf_text(source["url"], raw_pdf, extracted_txt)).splitlines()

    parsed_areas: list[ParsedArea] = []
    for index, line in enumerate(lines):
        stripped = line.rstrip()
        if not stripped:
            continue
        if any(
            token in stripped
            for token in (
                "町丁名",
                "Plastic",
                "Address",
                "基本ルール",
                "一       覧",
                "プ ラ ス",
                "燃 や す",
                "燃やさない",
                "資       源",
                "粗大ごみ",
                "臨時ごみ",
                "動物死体",
                "収       集",
                "家 庭 系",
                "リサイクル",
                "※ 月=Mon",
            )
        ):
            continue
        if re.fullmatch(r"\s*\d+\s*", stripped):
            continue

        cols = re.split(r"\s{2,}", stripped.strip())
        if len(cols) < 6 or len(cols) > 7:
            continue

        first = re.sub(r"^[ぁ-ん]\s+", "", cols[0]).strip()
        if not first:
            continue

        if len(cols) == 7:
            _, selector, plastic, burnable, nonburnable, resource = cols[1:]
        else:
            if any(token in cols[2] for token in ("丁目", "全域", "〜", "～", "、", "・")):
                next_single = None
                for offset in range(index + 1, min(index + 4, len(lines))):
                    candidate = lines[offset].strip()
                    if not candidate:
                        continue
                    if re.fullmatch(r"[月火水木金土]", candidate):
                        next_single = candidate
                    break
                if next_single is None:
                    continue
                selector = cols[2]
                plastic = next_single
                burnable, nonburnable, resource = cols[3:]
            else:
                selector = ""
                plastic, burnable, nonburnable, resource = cols[2:]

        monthly_rule = parse_monthly_rule(nonburnable)
        label = clean_label(first if selector in {"", "全域"} else f"{first}{selector}")
        parsed_areas.append(
            ParsedArea(
                label_ja=label,
                weekly={
                    "plastic": parse_weekdays(plastic),
                    "burnable": parse_weekdays(burnable),
                    "resource": parse_weekdays(resource),
                },
                monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                evidence={"row_label": label},
                confidence=0.97,
            )
        )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:download:01",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="地域別収集曜日一覧 PDF を反映済みです。地図上は町丁目 selector で join しています。",
        notes=[
            "足立区の 2026 年版『資源とごみの分け方・出し方』PDF から地域別収集曜日一覧を抽出しています。",
            "プラスチック・可燃ごみ・資源は weekly、不燃ごみは nth-weekday として保持しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:download:01",
        source_label=source["label"],
        source_urls=[registry_source(ward_slug, "entry_page")["url"], source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:download:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_edogawa() -> tuple[dict, Path]:
    ward_slug = "edogawa"
    source = registry_source(ward_slug, "entry_page")
    _, html = download_entry_html(ward_slug)
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        raise ValueError("Missing Edogawa schedule tables")

    parsed_areas: list[ParsedArea] = []
    current_town = ""
    for table in tables:
        for row in table.find_all("tr"):
            texts = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if len(texts) < 5 or texts[0] == "地域":
                continue

            if len(texts) == 6:
                current_town, selector, resource, burnable, nonburnable, office = texts
            elif len(texts) == 5:
                selector, resource, burnable, nonburnable, office = texts
            else:
                continue

            label = clean_label(current_town if selector == "全域" else f"{current_town}{selector}")
            monthly_rule = parse_monthly_rule(nonburnable)
            parsed_areas.append(
                ParsedArea(
                    label_ja=label,
                    weekly={
                        "resource": parse_weekdays(resource),
                        "burnable": parse_weekdays(burnable),
                    },
                    monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                    evidence={"row_label": label, "office": office},
                    confidence=0.99,
                )
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:entry_page",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="地域別 HTML table を反映済みです。地図上は join できる selector を優先して町丁目へ重ねています。",
        notes=[
            "江戸川区の公式『ごみ収集・資源回収地域別曜日表』HTML table を一次ソースとして使用しています。",
            "番地や道路境界を含む複雑な selector は review task に回り、町丁目 join できる範囲を詳細表示しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:entry_page",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:entry_page", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_arakawa() -> tuple[dict, Path]:
    ward_slug = "arakawa"
    source = registry_source(ward_slug, "entry_page")
    _, html = download_entry_html(ward_slug)
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if not tables:
        raise ValueError("Missing Arakawa schedule tables")

    parsed_areas: list[ParsedArea] = []
    review_tasks: list[dict] = []
    for row in tables[0].find_all("tr"):
        cells = row.find_all(["th", "td"])
        texts = [" ".join(cell.get_text(" ", strip=True).split()) for cell in cells]
        if len(texts) < 6 or texts[0] == "地域":
            continue

        calendar_link = row.find("a", href=True)
        label = clean_label(re.sub(r"（[^）]+）", "", texts[0]))
        monthly_rule = parse_monthly_rule(texts[2])
        parsed_areas.append(
            ParsedArea(
                label_ja=label,
                weekly={
                    "burnable": parse_weekdays(texts[1]),
                    "plastic": parse_weekdays(texts[3]),
                },
                monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                evidence={
                    "row_label": texts[0],
                    "calendar_url": absolute_url(source["url"], calendar_link["href"]) if calendar_link else source["url"],
                },
                note="大規模集合住宅は別表に例外あり" if "除く" in texts[0] else None,
                confidence=0.97,
            )
        )

    for table_index, table in enumerate(tables[1:], start=2):
        for row_index, row in enumerate(table.find_all("tr"), start=1):
            texts = [" ".join(cell.get_text(" ", strip=True).split()) for cell in row.find_all(["th", "td"])]
            if len(texts) < 4 or texts[0] == "物件名":
                continue
            review_tasks.append(
                {
                    "task_key": f"{ward_slug}:review:building:{table_index:02d}:{row_index:03d}",
                    "task_type": "schedule_review",
                    "source_key": f"{ward_slug}:entry_page",
                    "title": f"Arakawa building-specific schedule needs manual handling: {texts[0]}",
                    "payload": {"row": texts},
                    "created_by": SCRIPT_NAME,
                }
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:entry_page",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="地域行単位の収集ルールを反映済みです。建物個別例外は review task に分離しています。",
        notes=[
            "荒川区の公式収集日ページ 1 表目を町丁目ベースの正規 source として取り込みました。",
            f"大規模集合住宅などの建物個別例外 {len(review_tasks)} 件は review task に分離しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
        review_tasks=review_tasks,
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:entry_page",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:entry_page", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


ITABASHI_ROW_RE = re.compile(
    r"(?P<label>.+?)\s+"
    r"(?P<resource>[月火水木金土])\s+"
    r"(?P<burnable>[月火水木金土]・[月火水木金土](?:・[月火水木金土])?)\s+"
    r"毎月(?P<nonburnable>[1234]回目・[1234]回目の[月火水木金土])\s+"
    r"(?P<office>東清掃事務所|西清掃事務所)\s+"
    r"(?P<calendar>(?:東|西)\d+)"
)


def parse_itabashi() -> tuple[dict, Path]:
    ward_slug = "itabashi"
    source = registry_source(ward_slug, "entry_page")
    calendar_page = registry_source(ward_slug, "related_page", 1)
    related_page = registry_source(ward_slug, "related_page", 2)
    raw_path, html = download_entry_html(ward_slug)
    calendar_url = calendar_page["url"]
    calendar_html = fetch_text(
        calendar_url,
        ROOT / "data" / "raw" / ward_slug / "itabashi_region_calendars.html",
    )
    soup = BeautifulSoup(calendar_html, "html.parser")
    main_text = "\n".join(
        " ".join(node.get_text(" ", strip=True).split()) for node in soup.select("main *") if node.get_text(" ", strip=True)
    )
    start_token = "地域 資源 可燃ごみ 不燃ごみ 管轄の清掃事務所 地域別カレンダー番号 "
    end_token = "（注）この表の収集曜日と異なる地域があります。"
    start_index = main_text.find(start_token)
    if start_index < 0:
        raise ValueError("Missing Itabashi region listing start token")
    end_index = main_text.find(end_token, start_index)
    listing_text = main_text[start_index + len(start_token) : end_index if end_index > 0 else None]
    listing_text = re.sub(r"（PDF[^）]+）", "", listing_text)

    calendar_links: dict[str, str] = {}
    for anchor in soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(" ", strip=True).split())
        match = re.match(r"(?P<code>(?:東|西)\d+)\s+（PDF", text)
        if match:
            calendar_links[match.group("code")] = absolute_url(calendar_url, anchor["href"])

    parsed_areas: list[ParsedArea] = []
    for match in ITABASHI_ROW_RE.finditer(listing_text):
        label = clean_label(match.group("label").replace("~", "～"))
        monthly_rule = parse_monthly_rule(match.group("nonburnable"))
        parsed_areas.append(
            ParsedArea(
                label_ja=label,
                weekly={
                    "burnable": parse_weekdays(match.group("burnable")),
                    "resource": parse_weekdays(match.group("resource")),
                },
                monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                evidence={
                    "row_label": label,
                    "calendar_code": match.group("calendar"),
                    "calendar_url": calendar_links.get(match.group("calendar"), calendar_url),
                },
                note=f"{match.group('office')}管轄",
                confidence=0.97,
            )
        )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:entry_page",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="地域別一覧表の行単位で収集ルールを反映済みです。",
        notes=[
            "板橋区の地域別曜日表ページ本文から地域・曜日・カレンダー番号を抽出しています。",
            "資源回収欄は resource として保持し、可燃ごみと不燃ごみを別 category に分離しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:entry_page",
        source_label=source["label"],
        source_urls=[source["url"], related_page["url"], calendar_url],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:entry_page", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_nerima() -> tuple[dict, Path]:
    ward_slug = "nerima"
    source = registry_source(ward_slug, "entry_page")
    related_page = registry_source(ward_slug, "related_page", 1)
    raw_path, html = download_entry_html(ward_slug)
    listing_path = ROOT / "data" / "raw" / ward_slug / "nerima_listing.html"
    listing_html = fetch_text(related_page["url"], listing_path)
    listing_soup = BeautifulSoup(listing_html, "html.parser")

    area_page_urls: list[str] = []
    for anchor in listing_soup.find_all("a", href=True):
        text = " ".join(anchor.get_text(" ", strip=True).split())
        if "地域にお住まいのかた" in text:
            area_page_urls.append(absolute_url(related_page["url"], anchor["href"]))

    parsed_areas: list[ParsedArea] = []
    for page_index, page_url in enumerate(area_page_urls, start=1):
        area_html = fetch_text(
            page_url,
            ROOT / "data" / "raw" / ward_slug / f"nerima_region_{page_index:02d}.html",
        )
        area_soup = BeautifulSoup(area_html, "html.parser")
        table = area_soup.find("table")
        if table is None:
            continue

        for row in table.find_all("tr"):
            cells = row.find_all(["th", "td"])
            texts = [" ".join(cell.get_text(" ", strip=True).split()) for cell in cells]
            if len(texts) < 8 or texts[0] == "町 名":
                continue

            town, chome = texts[0], texts[1]
            label = clean_label(town if chome in {"全域", "全 域"} else f"{town}{chome}")
            calendar_link = row.find("a", href=True)
            monthly_rule = parse_monthly_rule(texts[3])

            resource_days = []
            for token in (texts[4], texts[5], texts[6]):
                for day in parse_weekdays(token):
                    if day not in resource_days:
                        resource_days.append(day)

            parsed_areas.append(
                ParsedArea(
                    label_ja=label,
                    weekly={
                        "burnable": parse_weekdays(texts[2]),
                        "plastic": parse_weekdays(texts[4]),
                        "resource": resource_days,
                    },
                    monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                    evidence={
                        "row_label": f"{town} {chome}",
                        "calendar_url": absolute_url(page_url, calendar_link["href"]) if calendar_link else page_url,
                        "source_page_url": page_url,
                    },
                    confidence=0.98,
                )
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:related_page:01",
        source_url=related_page["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=related_page["label"],
        granularity="地域別収集曜日一覧の行単位で収集ルールを反映済みです。",
        notes=[
            "練馬区の地域別収集曜日一覧の各 50 音ページ table を直接取り込んでいます。",
            "容器包装プラスチック・古紙列は plastic と resource の両方に反映し、びん・缶・ペットボトル列も resource に集約しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:related_page:01",
        source_label=related_page["label"],
        source_urls=[source["url"], related_page["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:related_page:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_suginami() -> tuple[dict, Path]:
    ward_slug = "suginami"
    entry_source = registry_source(ward_slug, "entry_page")
    related_source = registry_source(ward_slug, "related_page", 1)
    search_page = registry_source(ward_slug, "related_page", 2)
    download_source = registry_source(ward_slug, "download", 1)
    source_url = download_source["url"]
    raw_path = ROOT / "data" / "raw" / ward_slug / "garbage.csv"
    data = urllib.request.urlopen(
        urllib.request.Request(source_url, headers={"User-Agent": "gomiyoubi-bot/1.0"}),
        timeout=60,
    ).read()
    raw_path.parent.mkdir(parents=True, exist_ok=True)
    raw_path.write_bytes(data)
    rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))

    parsed_areas: list[ParsedArea] = []
    for row in rows:
        label = clean_label(str(row["町名"]))
        monthly_rule = parse_monthly_rule(str(row["不燃ごみ"]))

        resource_days: list[str] = []
        mixed_days = parse_weekdays(str(row["びん・かん・プラ"]))
        if mixed_days:
            resource_days.extend(day for day in mixed_days if day not in resource_days)

        for day in parse_weekdays(str(row["古紙・ペットボトル"])):
            if day not in resource_days:
                resource_days.append(day)

        parsed_areas.append(
            ParsedArea(
                label_ja=label,
                weekly={
                    "burnable": parse_weekdays(str(row["可燃ごみ"])),
                    "plastic": mixed_days,
                    "resource": resource_days,
                },
                monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                evidence={
                    "row_label": label,
                    "kana_group": row["五十音"],
                    "pdf_text": row["pdf_txt"],
                    "pdf_url": absolute_url(related_source["url"], str(row["pdf_url"])),
                },
                confidence=1.0,
            )
        )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:download:01",
        source_url=source_url,
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label="杉並区 garbage.csv",
        granularity="町名・丁目グループ CSV を反映済みです。地図上は町丁目 selector で join しています。",
        notes=[
            "杉並区の公式収集日ページから参照される garbage.csv を一次ソースとして使用しています。",
            "『びん・かん・プラ』列は plastic と resource の両方に反映し、『古紙・ペットボトル』は resource に集約しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:download:01",
        source_label="杉並区 garbage.csv",
        source_urls=[entry_source["url"], related_source["url"], search_page["url"], source_url],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:download:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def extract_chiyoda_calendar_rules(calendar_url: str, calendar_no: str) -> tuple[dict[str, list[str]], dict[str, dict], dict]:
    raw_pdf = ROOT / "data" / "raw" / "chiyoda" / f"calendar-{calendar_no}.pdf"
    extracted_txt = ROOT / "data" / "extracted" / "chiyoda" / f"calendar-{calendar_no}.txt"
    lines = fetch_pdf_text(calendar_url, raw_pdf, extracted_txt).splitlines()

    def extract_number_positions(line: str) -> list[tuple[int, int]]:
        return [(match.start(), int(match.group(1))) for match in re.finditer(r"(?<!\d)(\d{1,2})(?!\d)", line)]

    def assign_inline(date_line: str, positions: list[tuple[int, int]]) -> list[tuple[int, str]]:
        events: list[tuple[int, str]] = []
        for match in re.finditer(r"可燃|プラ|資源|不燃|蛍光管等", date_line):
            previous = [(pos, day) for pos, day in positions if pos < match.start() + 1]
            if previous:
                events.append((previous[-1][1], match.group(0)))
        return events

    def assign_below(label_line: str, positions: list[tuple[int, int]]) -> list[tuple[int, str]]:
        if not positions:
            return []
        events: list[tuple[int, str]] = []
        for match in re.finditer(r"可燃|プラ|資源|不燃|蛍光管等", label_line):
            nearest = min(positions, key=lambda item: abs(item[0] - match.start()))
            events.append((nearest[1], match.group(0)))
        return events

    weekday_counts: dict[str, Counter[str]] = defaultdict(Counter)
    nonburnable_events: list[tuple[str, int]] = []

    index = 0
    while index < len(lines):
        month_match = re.search(r"(\d{1,2}) 月 [A-Za-z]+", lines[index])
        if not month_match or index + 2 >= len(lines):
            index += 1
            continue

        right_month_match = re.search(r"(\d{1,2}) 月 [A-Za-z]+", lines[index + 1])
        if not right_month_match:
            index += 1
            continue

        left_month = int(month_match.group(1))
        right_month = int(right_month_match.group(1))
        row_index = index + 3
        while row_index + 1 < len(lines):
            date_line = lines[row_index]
            label_line = lines[row_index + 1]
            if "★" in date_line or not date_line.strip():
                break

            left_positions = [(pos, day) for pos, day in extract_number_positions(date_line) if pos < 60]
            right_positions = [(pos - 60, day) for pos, day in extract_number_positions(date_line) if pos >= 60]

            for month, positions, inline_line, below_line in (
                (left_month, left_positions, date_line[:60], label_line[:60]),
                (right_month, right_positions, date_line[60:], label_line[60:]),
            ):
                year = 2026 if month >= 4 else 2027
                for day_number, label in [*assign_inline(inline_line, positions), *assign_below(below_line, positions)]:
                    weekday = datetime.date(year, month, day_number).strftime("%A").lower()
                    weekday_counts[label][weekday] += 1
                    if label == "不燃":
                        nonburnable_events.append((weekday, 1 + (day_number - 1) // 7))

            row_index += 2

        index = row_index

    plastic_days = infer_primary_days(weekday_counts["プラ"], top_n=1)
    resource_days = infer_primary_days(weekday_counts["資源"], top_n=1)
    burnable_days = infer_primary_days(
        weekday_counts["可燃"],
        top_n=2,
        exclude={*plastic_days, *resource_days},
    )
    nonburnable_days = infer_primary_days(weekday_counts["不燃"], top_n=1)

    weekly: dict[str, list[str]] = {}
    if burnable_days:
        weekly["burnable"] = sorted(burnable_days)
    if plastic_days:
        weekly["plastic"] = plastic_days
    if resource_days:
        weekly["resource"] = resource_days

    monthly: dict[str, dict] = {}
    if nonburnable_days:
        nonburnable_day = nonburnable_days[0]
        ordinals = sorted({ordinal for weekday, ordinal in nonburnable_events if weekday == nonburnable_day})
        if ordinals:
            monthly["nonburnable"] = {
                "rule_type": "nth_weekday",
                "day": nonburnable_day,
                "ordinals": ordinals,
                "text_ja": f"第{'・第'.join(str(item) for item in ordinals)}{DAY_LABELS[nonburnable_day]}",
            }

    evidence = {
        "calendar_no": calendar_no,
        "calendar_url": calendar_url,
        "weekday_counts": {label: dict(counter) for label, counter in weekday_counts.items()},
    }
    return weekly, monthly, evidence


def parse_chiyoda() -> tuple[dict, Path]:
    ward_slug = "chiyoda"
    source = registry_source(ward_slug, "entry_page")
    raw_html = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_entry_page.html"
    html = fetch_text(source["url"], raw_html)
    soup = BeautifulSoup(html, "html.parser")

    calendar_table = next(
        table
        for table in soup.select("table.datatable")
        if "住所・対象カレンダー一覧" in table.get_text(" ", strip=True)
    )

    calendar_rules: dict[str, tuple[dict[str, list[str]], dict[str, dict], dict]] = {}
    parsed_areas: list[ParsedArea] = []
    for row in calendar_table.select("tbody tr"):
        cells = row.find_all("td")
        if len(cells) != 2:
            continue
        label = clean_label(cells[0].get_text(" ", strip=True))
        link = cells[1].find("a", href=True)
        if not link:
            continue
        calendar_url = absolute_url(source["url"], link["href"])
        calendar_no_match = re.search(r"r8calender-(\d+)\.pdf", calendar_url)
        if not calendar_no_match:
            continue
        calendar_no = calendar_no_match.group(1)
        if calendar_no not in calendar_rules:
            calendar_rules[calendar_no] = extract_chiyoda_calendar_rules(calendar_url, calendar_no)

        weekly, monthly, evidence = calendar_rules[calendar_no]
        parsed_areas.append(
            ParsedArea(
                label_ja=label,
                weekly=weekly,
                monthly=monthly,
                evidence=evidence,
                confidence=0.92,
            )
        )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:entry_page",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="住所別カレンダー単位で official rules を正規化しています。番地・奇偶分割のある一部住所は review task に残ります。",
        notes=[
            "千代田区は公式 HTML の住所別カレンダー一覧と 12 種類の収集カレンダー PDF を一次ソースとして使用しています。",
            "calendar PDF の text layer から曜日パターンを推定し、可燃・プラ・資源・不燃を正規化しています。",
            "奇数番地・偶数番地・一部番地除外のような詳細 selectors は geometry join 時に review task へ落とします。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:entry_page",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:entry_page", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_bunkyo() -> tuple[dict, Path]:
    ward_slug = "bunkyo"
    _, html = download_entry_html(ward_slug)
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("Missing Bunkyo schedule table")

    parsed_areas: list[ParsedArea] = []
    current_town = ""
    for row in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if not cells or cells[0] == "地域":
            continue
        if cells[0] == "新聞、雑誌、雑がみ、 段ボール、びん、 缶、ペットボトル":
            continue

        if len(cells) == 6:
            current_town, chome, burnable, nonburnable, resource, plastic = cells
        elif len(cells) == 5:
            chome, burnable, nonburnable, resource, plastic = cells
        else:
            continue

        label = current_town if chome in {"-", "―", ""} else f"{current_town}{chome}"
        parsed_areas.append(
            ParsedArea(
                label_ja=clean_label(label),
                weekly={
                    "burnable": parse_weekdays(burnable),
                    "resource": parse_weekdays(resource),
                    "plastic": parse_weekdays(plastic),
                },
                monthly={"nonburnable": parse_monthly_rule(nonburnable) or {}}
                if parse_monthly_rule(nonburnable)
                else {},
                evidence={"row_label": label, "nonburnable_text_ja": clean_label(nonburnable)},
            )
        )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    source = registry_source(ward_slug, "entry_page")
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:entry_page",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="町丁目グループ単位の収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "文京区の公式 HTML table から地域別の収集曜日を抽出しています。",
            "可燃・不燃・資源・プラスチックを ward-level area claim として正規化しています。",
            "地図上の詳細マスクはまだ未実装です。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:entry_page",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:entry_page", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_taito() -> tuple[dict, Path]:
    ward_slug = "taito"
    source = registry_source(ward_slug, "download", 1)
    raw_path = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_download_01.csv"
    fetch_text(source["url"], raw_path, encodings=("cp932", "utf-8"))
    from ward_extract_common import load_csv_rows

    rows = load_csv_rows(raw_path, encoding="cp932")
    parsed_areas: list[ParsedArea] = []
    for row in rows:
        label = clean_label(row["町丁名"])
        monthly_rule = parse_monthly_rule(row["燃やさないごみ"])
        parsed_areas.append(
            ParsedArea(
                label_ja=label,
                weekly={
                    "burnable": parse_weekdays(row["燃やすごみ"]),
                    "resource": parse_weekdays(row["資源"]),
                },
                monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                evidence={"row_label": label, "csv_index": row["索引"]},
            )
        )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:download:01",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="町丁名単位の収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "台東区オープンデータ CSV を一次ソースとして使用しています。",
            "資源と燃やすごみは weekly rule、不燃系は nth-weekday rule として保持しています。",
            "プラスチック系の扱いは別ソース確認後に追加します。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:download:01",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:download:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_shibuya() -> tuple[dict, Path]:
    ward_slug = "shibuya"
    source = registry_source(ward_slug, "entry_page")
    _, html = download_entry_html(ward_slug)
    soup = BeautifulSoup(html, "html.parser")
    parsed_areas: list[ParsedArea] = []

    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True) for cell in table.find_all("th")[:6]]
        if "町名" not in headers or "可燃ごみ（週2回）" not in headers:
            continue
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if len(cells) != 6 or cells[1] == "町名":
                continue
            _, town, chome, burnable, nonburnable, resource = cells
            label = town if chome in {"―", "-", ""} else f"{town}{chome}"
            monthly_rule = parse_monthly_rule(nonburnable)
            parsed_areas.append(
                ParsedArea(
                    label_ja=clean_label(label),
                    weekly={
                        "burnable": parse_weekdays(burnable),
                        "resource": parse_weekdays(resource),
                    },
                    monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                    evidence={"row_label": label},
                )
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:entry_page",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="町名・丁目グループ単位の収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "渋谷区の公式 HTML table を一次ソースとして使用しています。",
            "資源欄は weekly rule、不燃欄は monthly nth-weekday rule として保持しています。",
            "繁華街地域の細かい例外は今後の review task で扱います。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:entry_page",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:entry_page", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_nakano() -> tuple[dict, Path]:
    ward_slug = "nakano"
    source = registry_source(ward_slug, "entry_page")
    _, html = download_entry_html(ward_slug)
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        raise ValueError("Missing Nakano table")

    parsed_areas: list[ParsedArea] = []
    for row in table.find_all("tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
        if not cells or cells[0] == "町名（50音順）":
            continue
        chunks = [cells[index : index + 6] for index in range(0, len(cells), 6)]
        for chunk in chunks:
            if len(chunk) != 6 or not chunk[0]:
                continue
            town, chome, plastic, resource, burnable, nonburnable = chunk
            label = f"{town}{chome}"
            monthly_rule = parse_monthly_rule(nonburnable)
            parsed_areas.append(
                ParsedArea(
                    label_ja=clean_label(label),
                    weekly={
                        "burnable": parse_weekdays(burnable),
                        "resource": parse_weekdays(resource),
                        "plastic": parse_weekdays(plastic),
                    },
                    monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                    evidence={"row_label": label},
                )
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:entry_page",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="町名・丁目単位の収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "中野区全域ページの HTML table を一次ソースとして使用しています。",
            "資源プラスチックとびん・缶・ペットボトルを別 category として保持しています。",
            "陶器・ガラス・金属ごみは monthly nth-weekday rule として保持しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:entry_page",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:entry_page", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_shinjuku() -> tuple[dict, Path]:
    ward_slug = "shinjuku"
    source = registry_source(ward_slug, "entry_page")
    _, html = download_entry_html(ward_slug)
    soup = BeautifulSoup(html, "html.parser")
    page_text = soup.get_text("\n", strip=True)
    parsed_areas: list[ParsedArea] = []
    review_tasks: list[dict] = []
    plastics_note = "新宿区の資源欄は古紙・プラスチック・びん・缶・ペットボトル等を含むため、plastic も同じ曜日へ展開しています。"

    for table in soup.find_all("table"):
        headers = [cell.get_text(" ", strip=True) for cell in table.find_all("th")[:6]]
        if "集積所の住所" not in headers:
            continue
        for row in table.find_all("tr"):
            cells = [cell.get_text(" ", strip=True) for cell in row.find_all(["th", "td"])]
            if len(cells) < 7 or cells[1] == "集積所の住所":
                continue
            _, address, resource, burnable, nonburnable, office, _ = cells[:7]
            if "*" in resource or "*" in burnable or "*" in nonburnable:
                review_tasks.append(
                    {
                        "task_key": f"{ward_slug}:review:{len(review_tasks)+1:03d}",
                        "task_type": "schedule_review",
                        "title": f"Special-case Shinjuku row requires review: {address}",
                        "source_key": f"{ward_slug}:entry_page",
                        "payload": {"address": address, "office": office},
                        "created_by": SCRIPT_NAME,
                    }
                )
                continue

            monthly_rule = parse_monthly_rule(nonburnable)
            parsed_areas.append(
                ParsedArea(
                    label_ja=clean_label(address),
                    weekly={
                        "burnable": parse_weekdays(burnable),
                        "resource": parse_weekdays(resource),
                        "plastic": parse_weekdays(resource),
                    },
                    monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                    evidence={"row_label": address, "office": office, "source_excerpt": plastics_note},
                    note=plastics_note,
                )
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:entry_page",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="住所行単位の収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "新宿区の公式 HTML table から住所行ベースの収集曜日を抽出しています。",
            plastics_note,
            f"特記事項付きの行は {len(review_tasks)} 件を review task に回しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
        review_tasks=review_tasks,
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:entry_page",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:entry_page", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_meguro() -> tuple[dict, Path]:
    ward_slug = "meguro"
    source = registry_source(ward_slug, "download", 1)
    raw_pdf = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_download_01.pdf"
    extracted_txt = ROOT / "data" / "extracted" / ward_slug / "weekday-table.txt"
    text = normalize_pdf_text(fetch_pdf_text(source["url"], raw_pdf, extracted_txt))

    parsed_areas: list[ParsedArea] = []
    for line in text.splitlines():
        raw = normalize_pdf_text(line).replace("　", " ").rstrip()
        if "曜日" not in raw or "第" not in raw:
            continue
        parts = [part.strip() for part in re.split(r"\s{2,}", raw.strip()) if part.strip()]
        if len(parts) == 5 and re.fullmatch(r"[ァ-ヶA-Z]", parts[0]):
            parts = parts[1:]
        if len(parts) != 4:
            continue
        label, resource, burnable, nonburnable = parts
        if not label or label.startswith("五十音") or label.startswith("燃やさないごみ"):
            continue
        label = re.sub(r"^[ァ-ヶA-Z]\s*", "", label).strip()
        monthly_rule = parse_monthly_rule(nonburnable)
        parsed_areas.append(
            ParsedArea(
                label_ja=clean_label(label),
                weekly={"burnable": parse_weekdays(burnable), "resource": parse_weekdays(resource)},
                monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                evidence={"row_label": clean_label(label), "pdf_path": str(raw_pdf.relative_to(ROOT))},
            )
        )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:download:01",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="medium",
        source_label=source["label"],
        granularity="地域グループ単位の収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "目黒区の地域別曜日一覧 PDF を text extraction して正規化しています。",
            "資源・燃やすごみは weekly rule、不燃は monthly nth-weekday rule として保持しています。",
            "詳細マスク化は次段階です。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:download:01",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:download:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_shinagawa_layout_half(
    half: str,
    current_town: str,
) -> tuple[str, ParsedArea | None, str | None]:
    normalized = clean_label(normalize_pdf_text(half))
    if not normalized:
        return current_town, None, None
    condensed = clean_japanese_token(normalized)
    if condensed in {"アイウエオ", "ア行", "カ行", "タ行", "ナ行", "ハ行", "マ行", "ヤ行"}:
        return current_town, None, None

    if "曜日一覧" in condensed or "月2回の収集曜日の例" in condensed:
        return current_town, None, None

    if re.fullmatch(r"[^\d第月火水木金土]+", condensed):
        return condensed, None, None

    match = re.match(
        r"^(?P<prefix>.+?)\s+(?P<resource>[月火水木金土])\s+(?P<burnable>[月火水木金土・]+)\s+第\s*(?P<ord1>[1234])・(?P<ord2>[1234])\s*(?P<monthly_day>[月火水木金土])$",
        normalized,
    )
    if not match:
        return current_town, None, normalized if any(ch.isdigit() or ch in "丁目番上記以外棟号" for ch in condensed) else None

    prefix = clean_japanese_token(match.group("prefix"))
    if current_town and (prefix.startswith("上記") or prefix[0].isdigit()):
        label = f"{current_town}{prefix}"
    else:
        town_match = re.match(r"^(?P<town>[^\d]+?)(?P<suffix>(?:\d|１|２|３|４|５|６|７|８|９|０).+)$", prefix)
        if town_match:
            current_town = clean_japanese_token(town_match.group("town"))
            label = f"{current_town}{clean_japanese_token(town_match.group('suffix'))}"
        else:
            label = prefix
            current_town = prefix

    monthly_rule = parse_monthly_rule(f"第{match.group('ord1')}・第{match.group('ord2')}{match.group('monthly_day')}曜日")
    parsed_area = ParsedArea(
        label_ja=label,
        weekly={
            "burnable": parse_weekdays(match.group("burnable")),
            "resource": parse_weekdays(match.group("resource")),
            "plastic": parse_weekdays(match.group("resource")),
        },
        monthly={"nonburnable": monthly_rule} if monthly_rule else {},
        evidence={"row_label": label},
        note="品川区の資源欄には資源プラスチックが含まれるため、plastic も同じ曜日へ展開しています。",
        confidence=0.98,
    )
    return current_town, parsed_area, None


SHINAGAWA_ROW_RE = re.compile(
    r"^(?P<label>.+?)\s+"
    r"(?P<resource>[月火水木金土])\s+"
    r"(?P<burnable>[月火水木金土・]+)\s+"
    r"第\s*(?P<ord1>[1234])・(?P<ord2>[1234])\s+"
    r"(?P<monthly_day>[月火水木金土])$"
)


def split_shinagawa_columns(line: str) -> tuple[str, str]:
    gap_matches = list(re.finditer(r" {6,}", line))
    crossing = [
        match
        for match in gap_matches
        if match.start() <= 62 and match.end() >= 54
    ]
    if crossing:
        gap = min(crossing, key=lambda match: abs(((match.start() + match.end()) / 2) - 58))
        return line[: gap.start()], line[gap.end() :]

    leading_spaces = len(line) - len(line.lstrip(" "))
    if leading_spaces >= 54:
        return "", line.lstrip()

    return line, ""


def clean_shinagawa_column_text(value: str) -> str:
    normalized = clean_label(normalize_pdf_text(value))
    normalized = re.sub(r"^[ア-ヤ]\s*", "", normalized)
    normalized = re.sub(r"^\s*行\s*", "", normalized)
    normalized = re.sub(r"^(?:ア行|カ行|タ行|ナ行|ハ行|マ行|ヤ行)\s*", "", normalized)
    normalized = normalized.strip()
    return normalized


def should_skip_shinagawa_segment(value: str) -> bool:
    compacted = clean_japanese_token(value)
    if not compacted:
        return True
    if compacted in {"地域", "資源", "ごみ", "地域資源", "ごみ金属ごみ"}:
        return True
    return any(
        marker in compacted
        for marker in (
            "収集曜日一覧",
            "品川区清掃事務所",
            "事業係",
            "燃やすごみ",
            "金属ごみ",
            "陶器・ガラス・金属ごみ",
            "月2回の収集曜日の例",
            "第1・3の収集日とは",
            "第2・4の収集日とは",
            "5回目の曜日の収集はありません",
            "オレンジの部分",
            "緑の部分",
        )
    )


def parse_shinagawa_column(
    segments: list[str],
) -> tuple[list[ParsedArea], list[dict]]:
    current_town = ""
    pending = ""
    parsed_areas: list[ParsedArea] = []
    review_tasks: list[dict] = []
    orphan_rows: list[tuple[re.Match[str], str]] = []

    def materialize_area(match: re.Match[str], prefix: str, town_override: str | None = None) -> ParsedArea:
        nonlocal current_town
        effective_town = town_override or current_town
        if effective_town and (prefix.startswith("上記") or prefix[0].isdigit()):
            label = f"{effective_town}{prefix}"
        else:
            town_match = re.match(
                r"^(?P<town>[^\d]+?)(?P<suffix>(?:\d|１|２|３|４|５|６|７|８|９|０).+)$",
                prefix,
            )
            if town_match:
                current_town = clean_japanese_token(town_match.group("town"))
                label = f"{current_town}{clean_japanese_token(town_match.group('suffix'))}"
            else:
                label = prefix
                current_town = prefix

        monthly_rule = parse_monthly_rule(
            f"第{match.group('ord1')}・第{match.group('ord2')}{match.group('monthly_day')}曜日"
        )
        return ParsedArea(
            label_ja=label,
            weekly={
                "burnable": parse_weekdays(match.group("burnable")),
                "resource": parse_weekdays(match.group("resource")),
                "plastic": parse_weekdays(match.group("resource")),
            },
            monthly={"nonburnable": monthly_rule} if monthly_rule else {},
            evidence={"row_label": label},
            note="品川区の資源欄には資源プラスチックが含まれるため、plastic も同じ曜日へ展開しています。",
            confidence=0.98,
        )

    for raw_segment in segments:
        segment = clean_shinagawa_column_text(raw_segment)
        if should_skip_shinagawa_segment(segment):
            continue

        compacted = clean_japanese_token(segment)
        if re.fullmatch(r"[^\d第月火水木金土]+", compacted):
            current_town = compacted
            if orphan_rows:
                for orphan_match, orphan_prefix in orphan_rows:
                    parsed_areas.append(materialize_area(orphan_match, orphan_prefix, town_override=current_town))
                orphan_rows = []
            pending = ""
            continue

        combined = segment if not pending else clean_label(f"{pending} {segment}")
        match = SHINAGAWA_ROW_RE.match(combined)
        if match:
            prefix = clean_japanese_token(match.group("label"))
            if not current_town and prefix and prefix[0].isdigit():
                orphan_rows.append((match, prefix))
            else:
                parsed_areas.append(materialize_area(match, prefix))
            pending = ""
            continue

        if re.search(r"[月火水木金土]|第", compacted):
            pending = combined
            continue

        if current_town and (compacted.startswith("上記") or compacted[0].isdigit()):
            pending = compacted
            continue

        if re.search(r"\d", compacted):
            review_tasks.append(
                {
                    "task_key": f"shinagawa:review:{len(review_tasks)+1:03d}",
                    "task_type": "schedule_review",
                    "title": f"Shinagawa row needs manual normalization: {segment}",
                    "source_key": "shinagawa:download:01",
                    "payload": {"raw_line": segment},
                    "created_by": SCRIPT_NAME,
                }
            )
            pending = ""
            continue

        current_town = compacted
        pending = ""

    if pending:
        review_tasks.append(
            {
                "task_key": f"shinagawa:review:{len(review_tasks)+1:03d}",
                "task_type": "schedule_review",
                "title": f"Shinagawa row needs manual normalization: {pending}",
                "source_key": "shinagawa:download:01",
                "payload": {"raw_line": pending},
                "created_by": SCRIPT_NAME,
            }
        )
    for orphan_match, orphan_prefix in orphan_rows:
        review_tasks.append(
            {
                "task_key": f"shinagawa:review:{len(review_tasks)+1:03d}",
                "task_type": "schedule_review",
                "title": f"Shinagawa row needs manual normalization: {orphan_prefix}",
                "source_key": "shinagawa:download:01",
                "payload": {"raw_line": orphan_prefix},
                "created_by": SCRIPT_NAME,
            }
        )

    return parsed_areas, review_tasks


def parse_shinagawa() -> tuple[dict, Path]:
    ward_slug = "shinagawa"
    source = registry_source(ward_slug, "download", 1)
    raw_pdf = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_download_01.pdf"
    extracted_txt = ROOT / "data" / "extracted" / ward_slug / "guidebook.txt"
    text = normalize_pdf_text(fetch_pdf_text(source["url"], raw_pdf, extracted_txt))
    pages = text.split("\f")
    lines = pages[1].splitlines()

    left_segments: list[str] = []
    right_segments: list[str] = []
    for line in lines:
        if not line.strip():
            continue
        left, right = split_shinagawa_columns(line.rstrip("\n"))
        if left.strip():
            left_segments.append(left)
        if right.strip():
            right_segments.append(right)

    left_areas, left_reviews = parse_shinagawa_column(left_segments)
    right_areas, right_reviews = parse_shinagawa_column(right_segments)
    parsed_areas = [*left_areas, *right_areas]
    review_tasks = []
    for task in [*left_reviews, *right_reviews]:
        review_tasks.append(
            {
                **task,
                "task_key": f"{ward_slug}:review:{len(review_tasks)+1:03d}",
                "source_key": f"{ward_slug}:download:01",
            }
        )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:download:01",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="medium",
        source_label=source["label"],
        granularity="地域行単位の収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "品川区のガイド PDF 収集曜日一覧を text extraction して ward-level area claim を作成しています。",
            "資源欄は資源プラスチックを含むため、plastic も同じ曜日へ展開しています。",
            f"複雑な番地分割など {len(review_tasks)} 件は review task に回しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
        review_tasks=review_tasks,
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:download:01",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:download:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def parse_toshima() -> tuple[dict, Path]:
    ward_slug = "toshima"
    source = registry_source(ward_slug, "related_page", 1)
    entry_source = registry_source(ward_slug, "entry_page")
    raw_html = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_entry_page.html"
    html = fetch_text(source["url"], raw_html)
    soup = BeautifulSoup(html, "html.parser")
    area1_options = []
    for option in soup.select("#cmbArea1 option"):
        value = option.get("value", "")
        label = option.get_text(strip=True)
        if value and value != "-":
            area1_options.append(label)

    parsed_areas: list[ParsedArea] = []
    for area1 in area1_options:
        request = urllib.request.Request(
            "https://manage.delight-system.com/threeR/web/selectArea",
            data=encode_form({"menu": "", "jichitaiId": "toshimaku", "area1": area1, "lang": "ja"}),
            method="POST",
            headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
        )
        area_rows = json.loads(urllib.request.urlopen(request, timeout=60).read())
        for area_row in area_rows:
            area_id = str(area_row["area_id"])
            area2 = str(area_row.get("area_name2") or "").strip()
            label = clean_label(f"{area1}{area2}")
            calendar_url = (
                "https://manage.delight-system.com/threeR/web/calendar"
                f"?menu=calendar&jichitaiId=toshimaku&areaId={area_id}&lang=ja"
            )
            calendar_html = urllib.request.urlopen(calendar_url, timeout=60).read().decode("utf-8", "ignore")
            calendar_soup = BeautifulSoup(calendar_html, "html.parser")
            labels_by_day: dict[int, list[str]] = {}
            for day_cell in calendar_soup.select("td .common"):
                day_text = day_cell.get_text(strip=True)
                if not day_text.isdigit():
                    continue
                day_number = int(day_text)
                card = day_cell.find_parent("td")
                trash_labels = [item.get_text(strip=True) for item in card.select(".trash_kind_name")]
                labels_by_day[day_number] = trash_labels

            weekly: dict[str, set[str]] = {"burnable": set(), "resource": set(), "plastic": set()}
            monthly: dict[str, dict] = {}
            for day_number, labels in labels_by_day.items():
                weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][
                    datetime.date(2026, 4, day_number).weekday()
                ]
                for label_text in labels:
                    if label_text == "燃やすごみ":
                        weekly["burnable"].add(weekday)
                    elif label_text == "資源（プラスチック）":
                        weekly["plastic"].add(weekday)
                    elif "資源（" in label_text:
                        weekly["resource"].add(weekday)
                    elif label_text == "金属・陶器・ガラスごみ":
                        ordinal = 1 + (day_number - 1) // 7
                        rule = monthly.setdefault(
                            "nonburnable",
                            {"rule_type": "nth_weekday", "day": weekday, "ordinals": [], "text_ja": ""},
                        )
                        if ordinal not in rule["ordinals"]:
                            rule["ordinals"].append(ordinal)
                        day_map = {
                            "monday": "月曜日",
                            "tuesday": "火曜日",
                            "wednesday": "水曜日",
                            "thursday": "木曜日",
                            "friday": "金曜日",
                            "saturday": "土曜日",
                            "sunday": "日曜日",
                        }
                        rule["text_ja"] = (
                            f"第{'・第'.join(str(item) for item in rule['ordinals'])}{day_map[weekday]}"
                        )

            parsed_areas.append(
                ParsedArea(
                    label_ja=label,
                    weekly={key: sorted(values) for key, values in weekly.items() if values},
                    monthly=monthly,
                    evidence={"area_id": area_id, "area1": area1, "area2": area2, "calendar_url": calendar_url},
                    note=area_row.get("note") or None,
                )
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:related_page:01",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="公式 app の地域選択単位で収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "豊島区は公式 WEB版さんあ〜るの地域 API と calendar HTML を一次ソースとして使用しています。",
            "資源は紙系とびん・かん・ペットボトルの両方を resource として扱い、プラスチックは別 category として保持しています。",
            "地図上の詳細マスクはまだ未実装です。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:related_page:01",
        source_label=source["label"],
        source_urls=[entry_source["url"], source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:related_page:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


def fetch_delight_area_rows(*, jichitai_id: str, area1: str, area2: str | None = None) -> list[dict]:
    payload = {"menu": "", "jichitaiId": jichitai_id, "area1": area1, "lang": "ja"}
    if area2:
        payload["area2"] = area2
    request = urllib.request.Request(
        "https://manage.delight-system.com/threeR/web/selectArea",
        data=encode_form(payload),
        method="POST",
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"},
    )
    return json.loads(urllib.request.urlopen(request, timeout=60).read())


def parse_delight_calendar_html(calendar_html: str) -> tuple[dict[str, list[str]], dict[str, dict]]:
    calendar_soup = BeautifulSoup(calendar_html, "html.parser")
    labels_by_day: dict[int, list[str]] = {}
    for day_cell in calendar_soup.select("td .common"):
        day_text = day_cell.get_text(strip=True)
        if not day_text.isdigit():
            continue
        day_number = int(day_text)
        card = day_cell.find_parent("td")
        labels_by_day[day_number] = [item.get_text(strip=True) for item in card.select(".trash_kind_name")]

    weekly: dict[str, set[str]] = {"burnable": set(), "resource": set(), "plastic": set()}
    monthly: dict[str, dict] = {}
    for day_number, labels in labels_by_day.items():
        weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"][
            datetime.date(2026, 4, day_number).weekday()
        ]
        for label_text in labels:
            if label_text in {"燃やすごみ", "可燃ごみ"}:
                weekly["burnable"].add(weekday)
            elif "プラスチック" in label_text:
                weekly["plastic"].add(weekday)
            elif label_text in {"資源", "ペットボトル"} or "資源" in label_text or "ペットボトル" in label_text:
                weekly["resource"].add(weekday)
            elif label_text in {"不燃ごみ", "金属・陶器・ガラスごみ"} or "不燃" in label_text:
                ordinal = 1 + (day_number - 1) // 7
                rule = monthly.setdefault(
                    "nonburnable",
                    {"rule_type": "nth_weekday", "day": weekday, "ordinals": [], "text_ja": ""},
                )
                if ordinal not in rule["ordinals"]:
                    rule["ordinals"].append(ordinal)
                rule["text_ja"] = f"第{'・第'.join(str(item) for item in rule['ordinals'])}{DAY_LABELS[weekday]}"

    return (
        {key: sorted(values) for key, values in weekly.items() if values},
        monthly,
    )


def parse_setagaya() -> tuple[dict, Path]:
    ward_slug = "setagaya"
    entry_source = registry_source(ward_slug, "entry_page")
    source = registry_source(ward_slug, "related_page", 1)
    raw_html = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_entry_page.html"
    html = fetch_text(source["url"], raw_html)
    soup = BeautifulSoup(html, "html.parser")

    area1_labels = []
    for option in soup.select("#cmbArea1 option"):
        value = option.get("value", "")
        label = option.get_text(strip=True)
        if value and value != "-":
            area1_labels.append(label)

    parsed_areas: list[ParsedArea] = []
    for area1_label in area1_labels:
        if area1_label == "町名（アイウエオ順）から選ぶ":
            area2_rows = fetch_delight_area_rows(jichitai_id="setagayaku", area1=area1_label)
            leaf_rows: list[dict] = []
            for area2_row in area2_rows:
                area2_label = str(area2_row.get("area_name2") or "").strip()
                if not area2_label:
                    continue
                leaf_rows.extend(fetch_delight_area_rows(jichitai_id="setagayaku", area1=area1_label, area2=area2_label))
        else:
            leaf_rows = fetch_delight_area_rows(jichitai_id="setagayaku", area1=area1_label)

        for area_row in leaf_rows:
            area_id = str(area_row["area_id"])
            label = next(
                (
                    clean_label(value)
                    for value in (
                        area_row.get("area_name4"),
                        area_row.get("area_name3"),
                        area_row.get("area_name2"),
                        area_row.get("area_name1"),
                    )
                    if value
                ),
                "",
            )
            if not label:
                continue

            calendar_url = (
                "https://manage.delight-system.com/threeR/web/calendar"
                f"?menu=calendar&jichitaiId=setagayaku&areaId={area_id}&lang=ja"
            )
            calendar_html = urllib.request.urlopen(calendar_url, timeout=60).read().decode("utf-8", "ignore")
            weekly, monthly = parse_delight_calendar_html(calendar_html)
            parsed_areas.append(
                ParsedArea(
                    label_ja=label,
                    weekly=weekly,
                    monthly=monthly,
                    evidence={
                        "area_id": area_id,
                        "area1": area1_label,
                        "area2": area_row.get("area_name2"),
                        "area3": area_row.get("area_name3"),
                        "calendar_url": calendar_url,
                    },
                    note=area_row.get("note") or None,
                    confidence=0.98,
                )
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:related_page:01",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="high",
        source_label=source["label"],
        granularity="世田谷区 official Web 版さんあ〜るの areaId 単位で収集ルールを反映しています。",
        notes=[
            "世田谷区は official Web 版さんあ〜るを一次ソースとして使用しています。",
            "町名（アイウエオ順）経路の areaId は丁目レベルで取得でき、例外的な集合住宅は個別 areaId として保持しています。",
            "ペットボトルは resource に含めて正規化しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:related_page:01",
        source_label=source["label"],
        source_urls=[entry_source["url"], source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:related_page:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


MINATO_SCHEDULE_RE = re.compile(
    r"(?P<plastic>[月火水木金土])\s+"
    r"(?P<resource>[月火水木金土])\s+"
    r"(?P<burnable>[月火水木金土・]+)\s+"
    r"(?P<nonburnable>第[1234]・[1234][月火水木金土])"
)

MINATO_GARBAGE_PREFIXES = (
    "不法投棄",
    "ごみを減らす",
    "ごみの行",
    "分け方一覧表",
    "資源・ごみの",
    "資源",
    "源",
    "は",
    "行",
)


def resolve_minato_label(segment: str, current_town: str) -> tuple[str, str | None, str | None]:
    normalized = clean_japanese_token(segment)
    normalized = re.sub(r"^(?:あ|か|さ|た|な|は|ま|ら|行)+", "", normalized)
    for prefix in MINATO_GARBAGE_PREFIXES:
        if normalized.startswith(prefix):
            normalized = normalized[len(prefix) :]
    normalized = normalized.strip("・")
    if not normalized or "右の表をご覧ください" in normalized:
        return current_town, None, None

    if current_town and (normalized[0].isdigit() or normalized.startswith("上記") or normalized.startswith("（")):
        return current_town, f"{current_town}{normalized}", None

    town_match = re.match(r"^(?P<town>[^\d]+?)(?P<suffix>(?:\d|１|２|３|４|５|６|７|８|９|０).+)$", normalized)
    if town_match:
        town = clean_japanese_token(town_match.group("town"))
        suffix = clean_japanese_token(town_match.group("suffix"))
        return town, f"{town}{suffix}", None

    if re.fullmatch(r"[^\d月火水木金土第※]+", normalized):
        return normalized, None, None

    return current_town, None, normalized


def parse_minato() -> tuple[dict, Path]:
    ward_slug = "minato"
    source = registry_source(ward_slug, "download", 1)
    raw_pdf = ROOT / "data" / "raw" / ward_slug / f"{ward_slug}_download_01.pdf"
    extracted_txt = ROOT / "data" / "extracted" / ward_slug / "guidebook.txt"
    text = normalize_pdf_text(fetch_pdf_text(source["url"], raw_pdf, extracted_txt))
    pages = text.split("\f")
    lines = "\n".join(pages[1:3]).splitlines()

    left_town = ""
    right_town = ""
    parsed_areas: list[ParsedArea] = []
    review_tasks: list[dict] = []
    for line in lines:
        if not line.strip() or "資源回収・" in line or "ごみ収集曜日" in line:
            continue
        normalized = clean_label(normalize_pdf_text(line))
        matches = list(MINATO_SCHEDULE_RE.finditer(normalized))
        if not matches:
            continue
        segments = []
        previous_end = 0
        for match in matches:
            segments.append(normalized[previous_end : match.start()])
            previous_end = match.end()
        for index, match in enumerate(matches):
            segment = segments[index]
            if index == 0:
                left_town, label, review = resolve_minato_label(segment, left_town)
            else:
                right_town, label, review = resolve_minato_label(segment, right_town)
            if review:
                review_tasks.append(
                    {
                        "task_key": f"{ward_slug}:review:{len(review_tasks)+1:03d}",
                        "task_type": "schedule_review",
                        "title": f"Minato row needs manual normalization: {review}",
                        "source_key": f"{ward_slug}:download:01",
                        "payload": {"raw_line": normalized},
                        "created_by": SCRIPT_NAME,
                    }
                )
            if not label:
                continue
            monthly_rule = parse_monthly_rule(match.group("nonburnable"))
            parsed_areas.append(
                ParsedArea(
                    label_ja=label,
                    weekly={
                        "burnable": parse_weekdays(match.group("burnable")),
                        "resource": parse_weekdays(match.group("resource")),
                        "plastic": parse_weekdays(match.group("plastic")),
                    },
                    monthly={"nonburnable": monthly_rule} if monthly_rule else {},
                    evidence={"row_label": label},
                    note="※ 印の地域は早朝回収区域です。",
                    confidence=0.97,
                )
            )

    normalized_path = ROOT / "data" / "normalized" / ward_slug / f"{ward_slug}_dataset.json"
    areas, claims = area_to_claims(
        ward_slug=ward_slug,
        source_key=f"{ward_slug}:download:01",
        source_url=source["url"],
        artifact_key=f"{ward_slug}:artifact:parser_output:2026",
        parsed_areas=parsed_areas,
    )
    dataset = build_dataset(
        ward_slug=ward_slug,
        source_quality="medium",
        source_label=source["label"],
        granularity="地域行単位の収集ルールを反映済みです。地図上は区表示です。",
        notes=[
            "港区の guidebook PDF 2ページ目の収集曜日一覧を text extraction して正規化しています。",
            "資源プラスチックと資源古紙・びん・かん・ペットボトルを別 category として保持しています。",
            f"複雑な番地分割など {len(review_tasks)} 件は review task に回しています。",
        ],
        areas=areas,
        claims=claims,
        artifacts=[],
        review_tasks=review_tasks,
    )
    dataset = attach_geometry_memberships(
        dataset=dataset,
        areas=areas,
        source_key=f"{ward_slug}:download:01",
        source_label=source["label"],
        source_urls=[source["url"]],
    )
    write_json(normalized_path, dataset)
    dataset["artifacts"] = [build_artifact(ward_slug, f"{ward_slug}:download:01", normalized_path)]
    write_json(normalized_path, dataset)
    return dataset, normalized_path


PARSERS = {
    "adachi": parse_adachi,
    "arakawa": parse_arakawa,
    "bunkyo": parse_bunkyo,
    "chiyoda": parse_chiyoda,
    "edogawa": parse_edogawa,
    "itabashi": parse_itabashi,
    "setagaya": parse_setagaya,
    "taito": parse_taito,
    "shibuya": parse_shibuya,
    "nakano": parse_nakano,
    "shinjuku": parse_shinjuku,
    "meguro": parse_meguro,
    "shinagawa": parse_shinagawa,
    "suginami": parse_suginami,
    "toshima": parse_toshima,
    "minato": parse_minato,
    "nerima": parse_nerima,
}


def main():
    args = parse_args()
    ward_slugs = [args.ward] if args.ward else list(PARSERS.keys())
    summary = []
    for ward_slug in ward_slugs:
        dataset, output_path = PARSERS[ward_slug]()
        summary.append(
            {
                "ward_slug": ward_slug,
                "output_path": str(output_path.relative_to(ROOT)),
                "areas": len(dataset["areas"]),
                "claims": len(dataset["claims"]),
                "review_tasks": len(dataset.get("review_tasks", [])),
            }
        )
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
