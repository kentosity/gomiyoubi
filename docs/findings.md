# Findings

Last updated: `2026-04-01`

## Data

- `Chuo` is the strongest source so far. The ward publishes machine-readable waste data in `gomitoshigen.csv`, which can be joined to `e-Stat` town/chome boundaries for real sub-ward masks.
- `Chuo` is not fully resolved yet. There are `11` official rows that split at block/address level, so they are tracked as unresolved instead of being forced into fake polygons.
- `Koto` now has normalized district-level claims and geometry memberships. The weekly schedule was extracted from official HTML image `alt` text, and district-to-town/chome selectors are stored as editable manual data in `data/manual/koto/district-boundary-selectors.json`.
- `Koto` does not need to stay OCR-only. The district image is still the official mapping source, but an official Koto ward text page also lists district membership by town and chome, which makes the mapping more reviewable and less fragile than image OCR alone.
- `Sumida` now has normalized 12-zone weekday patterns and geometry memberships. The zone order comes from the official entry page, the weekly pattern set comes from the official 2026 summary calendar, and the zone labels themselves are already sufficient to derive town/chome selectors.
- `Chuo` does contain official `燃やすごみ = 月曜日～土曜日` rows in some commercial areas. That behavior is faithful to the source CSV, not a current importer bug.
- The project can now render real detailed areas for all three currently supported wards:
  - `Chuo`: `95` detailed features
  - `Koto`: `155` detailed features
  - `Sumida`: `104` detailed features
- The project now carries `23` ward boundary polygons in the published map artifacts, even though only `3` wards currently have normalized schedule data.
- `Koto` still has one known boundary gap: `海の森` is not present in the `2020` e-Stat small-area dataset used by the importer, so it remains a tracked review task instead of a fake polygon.

## Product

- Ward-level rendering is still useful as a fallback, but detailed weekly schedules make sense only when the source is actually sub-ward.
- Hover alone is too unstable for inspection. The map needs click-to-focus so a user can keep one area selected while moving the pointer elsewhere.
- For the left detail card, the most useful fields are:
  - place name
  - source quality
  - weekly collection schedule for detailed areas only
  - data source
- For ward-only areas, showing too much implied precision is misleading. It is better to show source and quality than a fake detailed schedule.
- Once all `23` ward boundaries are visible, unsupported wards should render as intentionally muted `pending` overlays rather than simply disappearing. That makes project coverage obvious at a glance.

## Frontend

- `App` was carrying too many responsibilities at once: filter state, hover/focus state, GeoJSON loading, MapLibre lifecycle, source updates, highlighting, and panel data shaping.
- The project is easier to maintain when those concerns are separated:
  - `useTrashFilters` for filter state
  - `useMapSelection` for hover/focus state
  - `useMapData` for GeoJSON loading
  - `useTrashMap` for initial MapLibre bootstrapping and event wiring
  - `useMapSourceData` for GeoJSON source refreshes
  - `useMapHighlighting` for outline/highlight paint updates
- Components are easier to reuse when they receive precomputed view models instead of importing domain metadata directly. `ControlPanel` and `HoverCard` now follow that pattern.
- Map styling and map data transforms should stay separate. Style constants and layer/source ids now belong to `mapStyle`, while schedule/category logic belongs to `scheduleData` and `uiModels`.
- The biggest rendering slowdown was not React itself. The main regressions came from:
  - high-resolution `23`-ward boundary GeoJSON
  - an expensive outside-mask polygon
  - repeated whole-source `setData()` updates for day/category changes
- Deterministic fixes were more effective than styling tweaks:
  - simplify ward boundaries at fetch time
  - replace the outside mask with `4` simple rectangles instead of a complex hole polygon
  - stop rebuilding GeoJSON sources on filter changes
  - use `feature-state` for fill color and category counts
  - suppress redundant hover state updates and limit pointer work to `1` animation frame
- After simplifying ward boundaries, `public/data/ward-boundaries.geojson` dropped from about `1.8 MB` / `22k` coordinates to about `163 KB` / `1.9k` coordinates. That was a major performance win.
- In this app, `feature-state` is the right model for interactive coloring. Static geometry should stay static; only the paint-relevant state should change when filters change.

## Next Likely Work

- Resolve the remaining `Chuo` address-split rows without inventing geometry.
- Add real source discovery for the remaining `20` wards that are currently boundary-only placeholders.
- Decide whether the next frontend bottleneck is small enough to leave as-is or whether to move more hover/highlight logic into `feature-state`.
- Reduce the client bundle size if frontend performance becomes a problem.
