# gomiyoubi

Prototype map for Tokyo ward household waste schedules, starting with source tracking for `Sumida`, `Koto`, and `Chuo`.

What is in the repo right now:

- a source registry for the official ward schedule pages
- a SQLite-backed canonical data model for sources, areas, claims, and consensus
- a SQLite-to-`public/data` export step for the frontend map artifacts
- a `MapLibre + React + Vite` display prototype
- project notes and findings in `docs/findings.md`

Current prototype limits:

- the map is still ward-level, not exact block-level collection-zone masking
- `Chuo` is backed by the official CSV and has the strongest day signal
- `Koto` is backed by district templates, but non-burnable is still date-specific and omitted from the prototype view
- `Sumida` is tracked on the map but still waiting on schedule normalization

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
/opt/homebrew/bin/mise x -- pnpm db:bootstrap
/opt/homebrew/bin/mise x -- pnpm db:export
/opt/homebrew/bin/mise x -- pnpm db:build
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
- `scripts/export_frontend_data.py`
- `public/data/ward-boundaries.geojson`
- `public/data/ward-overviews.json`
- `public/data/detailed-areas.geojson`

Published frontend artifacts:

- `public/data/ward-boundaries.geojson`
- `public/data/ward-overviews.json`
- `public/data/detailed-areas.geojson`
- refresh them from SQLite with `pnpm db:export`
- rebuild the SQLite database and refresh those artifacts with `pnpm db:build`

Useful notes:

- `docs/findings.md`
- `docs/data-model.md`

Last refreshed:

- `2026-04-01`
