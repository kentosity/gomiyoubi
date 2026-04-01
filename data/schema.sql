PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS app_metadata (
  key TEXT PRIMARY KEY,
  value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS wards (
  id INTEGER PRIMARY KEY,
  slug TEXT NOT NULL UNIQUE,
  name_ja TEXT NOT NULL,
  name_en TEXT,
  status TEXT NOT NULL CHECK (status IN ('tracked', 'normalized', 'published', 'archived')),
  notes_json TEXT NOT NULL DEFAULT '[]',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY,
  source_key TEXT NOT NULL UNIQUE,
  ward_id INTEGER NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
  source_kind TEXT NOT NULL CHECK (
    source_kind IN ('entry_page', 'download', 'related_page', 'boundary', 'derived', 'user_submission')
  ),
  label TEXT NOT NULL,
  url TEXT NOT NULL,
  format TEXT,
  is_official INTEGER NOT NULL DEFAULT 1 CHECK (is_official IN (0, 1)),
  encoding TEXT,
  coverage_label TEXT,
  last_verified TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS source_artifacts (
  id INTEGER PRIMARY KEY,
  artifact_key TEXT NOT NULL UNIQUE,
  source_id INTEGER NOT NULL REFERENCES sources(id) ON DELETE CASCADE,
  artifact_kind TEXT NOT NULL CHECK (
    artifact_kind IN ('fetch', 'ocr', 'manual_transcription', 'parser_output', 'boundary')
  ),
  local_path TEXT,
  content_type TEXT,
  sha256 TEXT,
  fetched_at TEXT,
  parser_version TEXT,
  ocr_engine TEXT,
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS areas (
  id INTEGER PRIMARY KEY,
  area_key TEXT NOT NULL UNIQUE,
  ward_id INTEGER NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
  parent_area_id INTEGER REFERENCES areas(id) ON DELETE SET NULL,
  area_kind TEXT NOT NULL CHECK (
    area_kind IN ('ward', 'district', 'town', 'chome', 'block_range', 'custom_zone')
  ),
  label_ja TEXT NOT NULL,
  label_en TEXT,
  town_ja TEXT,
  chome TEXT,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'pending', 'unresolved', 'retired')),
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS ward_overviews (
  id INTEGER PRIMARY KEY,
  ward_id INTEGER NOT NULL UNIQUE REFERENCES wards(id) ON DELETE CASCADE,
  source_quality TEXT NOT NULL CHECK (source_quality IN ('high', 'medium', 'pending')),
  source_label TEXT NOT NULL,
  granularity TEXT NOT NULL,
  notes_json TEXT NOT NULL DEFAULT '[]',
  day_signals_json TEXT NOT NULL DEFAULT '{}',
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS area_geometries (
  id INTEGER PRIMARY KEY,
  geometry_key TEXT NOT NULL UNIQUE,
  area_id INTEGER NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
  geometry_source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
  boundary_key TEXT,
  boundary_name TEXT,
  part_index INTEGER NOT NULL DEFAULT 0,
  geometry_json TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'pending', 'retired')),
  metadata_json TEXT NOT NULL DEFAULT '{}',
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedule_rules (
  id INTEGER PRIMARY KEY,
  rule_key TEXT NOT NULL UNIQUE,
  rule_type TEXT NOT NULL CHECK (
    rule_type IN ('weekly', 'monthly_date', 'nth_weekday', 'date_list', 'freeform', 'exception')
  ),
  rule_json TEXT NOT NULL,
  description TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS schedule_claims (
  id INTEGER PRIMARY KEY,
  claim_key TEXT NOT NULL UNIQUE,
  ward_id INTEGER NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
  area_id INTEGER REFERENCES areas(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  rule_id INTEGER NOT NULL REFERENCES schedule_rules(id) ON DELETE RESTRICT,
  source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
  artifact_id INTEGER REFERENCES source_artifacts(id) ON DELETE SET NULL,
  source_type TEXT NOT NULL CHECK (
    source_type IN ('official', 'ocr', 'manual', 'user_label', 'derived')
  ),
  effective_from TEXT,
  effective_to TEXT,
  confidence REAL,
  status TEXT NOT NULL DEFAULT 'active' CHECK (
    status IN ('active', 'pending_review', 'rejected', 'superseded')
  ),
  submitted_by TEXT NOT NULL,
  supersedes_claim_id INTEGER REFERENCES schedule_claims(id) ON DELETE SET NULL,
  evidence_json TEXT NOT NULL DEFAULT '{}',
  note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS claim_votes (
  id INTEGER PRIMARY KEY,
  claim_id INTEGER NOT NULL REFERENCES schedule_claims(id) ON DELETE CASCADE,
  voter_id TEXT NOT NULL,
  vote INTEGER NOT NULL CHECK (vote IN (-1, 1)),
  note TEXT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (claim_id, voter_id)
);

CREATE TABLE IF NOT EXISTS consensus_records (
  id INTEGER PRIMARY KEY,
  ward_id INTEGER NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
  area_id INTEGER NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
  category TEXT NOT NULL,
  rule_id INTEGER NOT NULL REFERENCES schedule_rules(id) ON DELETE RESTRICT,
  resolved_claim_id INTEGER NOT NULL REFERENCES schedule_claims(id) ON DELETE CASCADE,
  resolution_method TEXT NOT NULL CHECK (
    resolution_method IN ('official_priority', 'quorum', 'manual')
  ),
  confidence REAL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE (area_id, category, rule_id)
);

CREATE TABLE IF NOT EXISTS review_tasks (
  id INTEGER PRIMARY KEY,
  task_key TEXT NOT NULL UNIQUE,
  ward_id INTEGER NOT NULL REFERENCES wards(id) ON DELETE CASCADE,
  area_id INTEGER REFERENCES areas(id) ON DELETE SET NULL,
  source_id INTEGER REFERENCES sources(id) ON DELETE SET NULL,
  task_type TEXT NOT NULL CHECK (
    task_type IN ('area_match', 'schedule_review', 'source_refresh', 'manual_transcription')
  ),
  status TEXT NOT NULL DEFAULT 'open' CHECK (
    status IN ('open', 'in_review', 'resolved', 'rejected')
  ),
  title TEXT NOT NULL,
  payload_json TEXT NOT NULL DEFAULT '{}',
  created_by TEXT NOT NULL,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_sources_ward_id ON sources (ward_id);
CREATE INDEX IF NOT EXISTS idx_source_artifacts_source_id ON source_artifacts (source_id);
CREATE INDEX IF NOT EXISTS idx_areas_ward_id ON areas (ward_id);
CREATE INDEX IF NOT EXISTS idx_areas_parent_area_id ON areas (parent_area_id);
CREATE INDEX IF NOT EXISTS idx_ward_overviews_ward_id ON ward_overviews (ward_id);
CREATE INDEX IF NOT EXISTS idx_area_geometries_area_id ON area_geometries (area_id);
CREATE INDEX IF NOT EXISTS idx_schedule_claims_area_id ON schedule_claims (area_id);
CREATE INDEX IF NOT EXISTS idx_schedule_claims_source_id ON schedule_claims (source_id);
CREATE INDEX IF NOT EXISTS idx_claim_votes_claim_id ON claim_votes (claim_id);
CREATE INDEX IF NOT EXISTS idx_consensus_records_area_id ON consensus_records (area_id);
CREATE INDEX IF NOT EXISTS idx_review_tasks_status ON review_tasks (status);
