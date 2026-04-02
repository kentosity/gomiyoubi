# gomiyoubi

Prototype map for Tokyo ward household waste schedules, starting with source tracking for `Sumida`, `Koto`, and `Chuo`.

What is in the repo right now:

- a source registry for the official ward schedule pages
- a SQLite-backed canonical data model for sources, areas, claims, and consensus
- a SQLite-to-`public/data` export step for the frontend map artifacts
- a tile build step that packs ward and detailed-area geometry into `PMTiles`
- a `MapLibre + React + Vite` display prototype
- project notes and findings in `docs/findings.md`

Current prototype limits:

- the map is sub-ward for `Chuo`, `Koto`, and `Sumida`, but not yet exact collection-point masking
- `Chuo` is backed by the official CSV and has the strongest day signal
- `Koto` has normalized district-level claims and district geometry
- `Sumida` has normalized 12-zone weekday patterns and zone geometry
- the remaining `20` wards are still `pending` coverage placeholders

Run it:

```bash
/opt/homebrew/bin/mise x -- pnpm install
/opt/homebrew/bin/mise x -- pnpm db:build
/opt/homebrew/bin/mise x -- pnpm dev
```

Build it:

```bash
/opt/homebrew/bin/mise x -- pnpm build
```

Common commands:

```bash
/opt/homebrew/bin/mise x -- pnpm dev
/opt/homebrew/bin/mise x -- pnpm dev:host
/opt/homebrew/bin/mise x -- pnpm data:extract
/opt/homebrew/bin/mise x -- pnpm db:bootstrap
/opt/homebrew/bin/mise x -- pnpm db:export
/opt/homebrew/bin/mise x -- pnpm db:build
/opt/homebrew/bin/mise x -- pnpm build:tiles
/opt/homebrew/bin/mise x -- pnpm db:summary
/opt/homebrew/bin/mise x -- pnpm lint
/opt/homebrew/bin/mise x -- pnpm format
/opt/homebrew/bin/mise x -- pnpm test
/opt/homebrew/bin/mise x -- pnpm check
```

Development note:

- Do not run `lint`, `test`, `build`, or `check` after every tiny edit while iterating in the dev server.
- Use the dev server for fast UI and behavior work, then run the verification commands once a task or change set is in a good stopping state.
- `pnpm check` is the final verification pass when an agent is done with a chunk of work.

Primary data files:

- `data/source-registry.json`
- `data/schema.sql`
- `scripts/extract_koto_data.py`
- `scripts/extract_sumida_data.py`
- `scripts/export_frontend_data.py`
- `scripts/build_ward_outlines.py`
- `scripts/build_map_tiles.py`
- `public/data/ward-boundaries.geojson`
- `public/data/ward-outlines.geojson`
- `public/data/ward-overviews.json`
- `public/data/detailed-area-index.geojson`
- `public/data/gomiyoubi.pmtiles`

Published frontend artifacts:

- `public/data/ward-boundaries.geojson`
- `public/data/ward-outlines.geojson`
- `public/data/ward-overviews.json`
- `public/data/detailed-area-index.geojson`
- `public/data/gomiyoubi.pmtiles`
- refresh the JSON exports from SQLite with `pnpm db:export`
- rebuild the JSON exports and tiles with `pnpm db:build`
- rebuild just the tile artifacts with `pnpm build:tiles`

Useful notes:

- `docs/findings.md`
- `docs/data-model.md`
- `docs/deploy-homelab.md`

Homelab deploy:

```bash
./deploy/homelab-deploy.sh
./deploy/homelab-verify.sh
```

Last refreshed:

- `2026-04-01`
