# Data Model

Last updated: `2026-04-01`

## Why SQLite

The project was not using SQLite. The prototype started as a static frontend, so the easiest path was:

- track source links in `data/source-registry.json`
- generate display-ready GeoJSON into `public/data`
- keep ward summaries in frontend constants

That is acceptable for an early prototype, but it breaks down once the project needs:

- all 23 wards
- raw source caching
- OCR and manual transcription outputs
- structured normalization
- user-submitted labels
- quorum or moderator resolution

SQLite fits the next stage because it gives us:

- one local canonical store
- relational links between ward, source, area, claim, vote, and consensus rows
- a simple file-based workflow without introducing a full backend yet
- easy export into frontend GeoJSON or JSON artifacts

The frontend should treat `public/data/*.geojson` as published build artifacts, not the source of truth.

## Current Canonical Layout

The canonical pieces now live here:

- schema: `data/schema.sql`
- bootstrap script: `scripts/bootstrap_sqlite.py`
- frontend export script: `scripts/export_frontend_data.py`
- summary script: `scripts/sqlite_summary.py`
- local database: `data/gomiyoubi.sqlite` (generated, not committed)

Transitional seed data still lives here:

- `data/seed/ward-overviews.json`

Future raw and intermediate artifacts should live under:

- `data/raw/`
- `data/extracted/`
- `data/normalized/`

## Table Overview

### `wards`

Canonical ward registry.

- `slug`
- `name_ja`
- `name_en`
- `status`
- `notes_json`

### `sources`

One row per official page, file, boundary source, or future user-submitted source.

- `source_key`
- `ward_id`
- `source_kind`
- `label`
- `url`
- `format`
- `encoding`
- `coverage_label`
- `last_verified`

### `source_artifacts`

Fetched or derived files attached to a source.

- raw PDF/CSV/image downloads
- OCR output
- manual transcription output
- parser output

### `areas`

Logical service areas.

Examples:

- ward
- district
- town
- chome
- block range
- custom zone

This is intentionally separate from geometry so one logical area can have multiple polygon parts.

### `ward_overviews`

This is a transitional bridge for the current UI.

It stores ward-level fallback summaries such as:

- source quality
- source label
- granularity note
- ward-level day signals

This should eventually be derived from normalized claims, but keeping it explicit right now makes the migration away from frontend constants much easier.

### `area_geometries`

Geometry rows for an area.

This is important because the current Chuo GeoJSON already has repeated logical `zoneId` values with multiple geometry parts.

The important design decision now is:

- normalized datasets can carry `geometry_memberships`
- bootstrap resolves those memberships against shared `e-Stat` small-area polygons
- frontend consumes only published GeoJSON, not ward-specific geometry logic

That pattern is what made `Koto` and `Sumida` fit the same pipeline as `Chuo` without adding new frontend branching.

### `schedule_rules`

Reusable schedule rules.

Current example:

- `weekly` with payload like `{"day":"monday"}`

Future examples:

- monthly date rules
- nth weekday rules
- explicit date lists
- exceptions

### `schedule_claims`

One proposed schedule fact.

Examples:

- official CSV says this chome has `burnable` on Monday
- OCR says this district has `resource` on Thursday
- user label says this apartment block is an exception area

Important fields:

- `area_id`
- `category`
- `rule_id`
- `source_id`
- `source_type`
- `confidence`
- `status`
- `submitted_by`
- `evidence_json`

### `claim_votes`

User votes on a claim.

This is the minimum structure needed for quorum later.

### `consensus_records`

The currently accepted claim for a given area + category + rule combination.

Resolution methods currently modeled:

- `official_priority`
- `quorum`
- `manual`

### `review_tasks`

Open work that is not yet a resolved schedule claim.

Current use:

- unresolved Chuo rows that still need area matching

Future use:

- OCR review
- source refresh
- manual transcription

## What Gets Bootstrapped Right Now

`scripts/bootstrap_sqlite.py` currently imports:

- all wards and official source links from `data/source-registry.json`
- ward-level fallback summaries from `data/seed/ward-overviews.json`
- ward polygons from `public/data/ward-boundaries.geojson`
- normalized `Koto` district claims from `data/normalized/koto/koto_district_dataset.json`
- normalized `Sumida` zone claims from `data/normalized/sumida/zone-schedules-2026.json`
- geometry memberships from normalized ward datasets and resolves them through the shared `e-Stat` boundary loader
- Chuo logical areas and geometries from `public/data/chuo-zones.geojson`
- Chuo weekly official claims and initial consensus rows
- Chuo unresolved rows into `review_tasks`

This is intentionally incomplete:

- bootstrap still seeds some tables from checked-in `public/data` artifacts during the transition

## Next Migration Steps

1. Replace the remaining bootstrap dependency on checked-in derived artifacts with importer scripts that write claims directly.
2. Add a canonical area index for address-to-district joins beyond Chuo.
3. Add contribution flows that write `schedule_claims` and `claim_votes`.
4. Add quorum resolution logic on top of `claim_votes` and `consensus_records`.

## 23-Ward Coverage Strategy

The project now keeps all `23` special wards in `data/source-registry.json`, but only `Chuo`, `Koto`, and `Sumida` have normalized schedule data today.

That split is deliberate:

- all `23` wards should exist in the canonical ward registry and on the published map
- unsupported wards should still render as `pending`
- source discovery and normalization can happen ward by ward without changing frontend logic

This is a better fit for incremental coverage than hiding unsupported wards entirely.

## Frontend Performance Notes

The current frontend architecture is intentionally split between:

- static source data
- dynamic feature state

Published GeoJSON should be treated as mostly static. Interactive filter changes should avoid rebuilding and re-uploading entire GeoJSON sources when possible.

The current direction is:

- keep ward/detailed geometry in published `public/data`
- use `MapLibre feature-state` for day/category paint updates
- keep outside-mask geometry simple
- simplify fetched ward boundaries at generation time

That approach proved materially faster than pushing full source replacements on every filter change.

## Frontend Export

The browser does not read SQLite directly.

Instead we export frontend-ready artifacts from the canonical database:

- `public/data/ward-boundaries.geojson`
- `public/data/ward-overviews.json`
- `public/data/detailed-areas.geojson`

The runtime app currently fetches these published artifacts and no longer depends on hardcoded ward metadata in `src/data`.

Run:

```bash
pnpm db:export
pnpm db:build
```
