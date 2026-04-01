# gomiyoubi

Prototype map for Tokyo ward household waste schedules, starting with source tracking for `Sumida`, `Koto`, and `Chuo`.

What is in the repo right now:
- a source registry for the official ward schedule pages
- a `MapLibre + React + Vite` display prototype
- a small boundary fetch script that pulls the three ward polygons into local GeoJSON
- project notes and findings in `docs/findings.md`

Current prototype limits:
- the map is still ward-level, not exact block-level collection-zone masking
- `Chuo` is backed by the official CSV and has the strongest day signal
- `Koto` is backed by district templates, but non-burnable is still date-specific and omitted from the prototype view
- `Sumida` is tracked on the map but still waiting on schedule normalization

Run it:

```bash
/opt/homebrew/bin/mise x -- pnpm install
/opt/homebrew/bin/mise x -- pnpm fetch:boundaries
/opt/homebrew/bin/mise x -- pnpm dev
```

Build it:

```bash
/opt/homebrew/bin/mise x -- pnpm build
```

Primary data files:
- `data/source-registry.json`
- `public/data/ward-boundaries.geojson`

Useful notes:
- `docs/findings.md`

Last refreshed:
- `2026-04-01`
