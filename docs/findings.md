# Findings

Last updated: `2026-04-01`

## Data

- `Chuo` is the strongest source so far. The ward publishes machine-readable waste data in `gomitoshigen.csv`, which can be joined to `e-Stat` town/chome boundaries for real sub-ward masks.
- `Chuo` is not fully resolved yet. There are `11` official rows that split at block/address level, so they are tracked as unresolved instead of being forced into fake polygons.
- `Koto` is partially structured. The weekly collection logic is usable, but the ward still relies on district mapping that is effectively trapped in an official image, and non-burnable collection is date-specific rather than weekday-based.
- `Sumida` is still at source-tracking stage. The official PDFs are recorded, but weekday/category normalization has not been completed yet.

## Product

- Ward-level rendering is still useful as a fallback, but detailed weekly schedules make sense only when the source is actually sub-ward.
- Hover alone is too unstable for inspection. The map needs click-to-focus so a user can keep one area selected while moving the pointer elsewhere.
- For the left detail card, the most useful fields are:
  - place name
  - source quality
  - weekly collection schedule for detailed areas only
  - data source
- For ward-only areas, showing too much implied precision is misleading. It is better to show source and quality than a fake detailed schedule.

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

## Next Likely Work

- Build `Koto` sub-ward mapping from the official district/address source.
- Normalize `Sumida` PDFs into structured weekday/category data.
- Resolve the remaining `Chuo` address-split rows without inventing geometry.
- Reduce the client bundle size if frontend performance becomes a problem.
