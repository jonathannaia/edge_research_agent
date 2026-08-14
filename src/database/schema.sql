-- Edge Research Agent — SQLite schema
-- Simple init-time DDL (no external migration framework needed for an MVP
-- this size). All tables use CREATE TABLE IF NOT EXISTS so init_db() is
-- idempotent and safe to call on every app start.

CREATE TABLE IF NOT EXISTS tickers (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                TEXT NOT NULL UNIQUE,
    company_name          TEXT NOT NULL,
    sector                TEXT NOT NULL DEFAULT '',
    subtheme              TEXT NOT NULL DEFAULT '',
    market_cap_category   TEXT NOT NULL DEFAULT '',
    jurisdiction          TEXT NOT NULL DEFAULT 'United States',
    is_mock               INTEGER NOT NULL DEFAULT 1,
    created_at            TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS watchlist_records (
    id                          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                      TEXT NOT NULL REFERENCES tickers(ticker),
    tier                        TEXT NOT NULL,
    thesis_short                TEXT NOT NULL DEFAULT '',
    why_on_watchlist            TEXT NOT NULL DEFAULT '',
    conviction_score            INTEGER NOT NULL DEFAULT 3,
    evidence_status             TEXT NOT NULL DEFAULT 'Insufficient evidence',
    next_catalyst               TEXT,
    next_catalyst_date          TEXT,
    key_confirmation_metric     TEXT,
    key_invalidation_metric     TEXT,
    latest_material_change      TEXT,
    risk_flags                  TEXT NOT NULL DEFAULT '',
    date_added                  TEXT NOT NULL DEFAULT (datetime('now')),
    date_last_reviewed          TEXT,
    is_active                   INTEGER NOT NULL DEFAULT 1,
    updated_at                  TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_watchlist_ticker_active ON watchlist_records(ticker);

CREATE TABLE IF NOT EXISTS theses (
    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                    TEXT NOT NULL REFERENCES tickers(ticker),
    theme                     TEXT NOT NULL DEFAULT '',
    subtheme                  TEXT NOT NULL DEFAULT '',
    why_on_watchlist          TEXT NOT NULL DEFAULT '',
    inflection_thesis         TEXT NOT NULL DEFAULT '',
    thesis_date_created        TEXT NOT NULL DEFAULT (datetime('now')),
    thesis_owner_notes        TEXT NOT NULL DEFAULT '',
    evidence_supporting       TEXT NOT NULL DEFAULT '[]',   -- JSON list of {source_id, note}
    evidence_contradicting    TEXT NOT NULL DEFAULT '[]',   -- JSON list of {source_id, note}
    confirmation_conditions   TEXT NOT NULL DEFAULT '',
    invalidation_conditions   TEXT NOT NULL DEFAULT '',
    key_risks                 TEXT NOT NULL DEFAULT '',
    next_catalyst             TEXT,
    next_catalyst_date        TEXT,
    last_review_date          TEXT,
    tier                      TEXT NOT NULL DEFAULT 'Watch Closely',
    score                     REAL NOT NULL DEFAULT 3.0,
    tags                      TEXT NOT NULL DEFAULT '',
    version                   INTEGER NOT NULL DEFAULT 1,
    is_current                INTEGER NOT NULL DEFAULT 1,
    created_at                TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_theses_ticker ON theses(ticker);

CREATE TABLE IF NOT EXISTS sources (
    id                   INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker               TEXT NOT NULL REFERENCES tickers(ticker),
    source_type          TEXT NOT NULL,
    title                TEXT NOT NULL,
    url_or_identifier    TEXT NOT NULL,
    source_date          TEXT NOT NULL,
    retrieval_date       TEXT NOT NULL,
    authority_rank       INTEGER NOT NULL,
    created_at           TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_sources_ticker ON sources(ticker);

CREATE TABLE IF NOT EXISTS source_excerpts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id       INTEGER NOT NULL REFERENCES sources(id),
    excerpt_text    TEXT NOT NULL,
    tag             TEXT NOT NULL DEFAULT 'neutral',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_excerpts_source ON source_excerpts(source_id);

CREATE TABLE IF NOT EXISTS research_briefs (
    id                       INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker                   TEXT NOT NULL REFERENCES tickers(ticker),
    question                 TEXT NOT NULL DEFAULT '',
    version                  INTEGER NOT NULL,
    bottom_line              TEXT NOT NULL,
    confidence_level         TEXT NOT NULL,
    confidence_explanation   TEXT NOT NULL DEFAULT '',
    sections_json            TEXT NOT NULL,
    what_changed_json        TEXT NOT NULL DEFAULT '{}',
    created_at               TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_briefs_ticker ON research_briefs(ticker);

CREATE TABLE IF NOT EXISTS research_snapshots (
    id                INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker            TEXT NOT NULL REFERENCES tickers(ticker),
    brief_id          INTEGER NOT NULL REFERENCES research_briefs(id),
    snapshot_json     TEXT NOT NULL,
    created_at        TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_snapshots_ticker ON research_snapshots(ticker);

CREATE TABLE IF NOT EXISTS scorecards (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker         TEXT NOT NULL REFERENCES tickers(ticker),
    brief_id       INTEGER REFERENCES research_briefs(id),
    total_score    REAL NOT NULL,
    is_capped      INTEGER NOT NULL DEFAULT 0,
    cap_reason     TEXT,
    created_at     TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_scorecards_ticker ON scorecards(ticker);

CREATE TABLE IF NOT EXISTS score_components (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    scorecard_id          INTEGER NOT NULL REFERENCES scorecards(id),
    component_key         TEXT NOT NULL,
    label                 TEXT NOT NULL,
    weight                REAL NOT NULL,
    raw_score             INTEGER NOT NULL,
    explanation           TEXT NOT NULL DEFAULT '',
    citation_source_ids   TEXT NOT NULL DEFAULT '[]'
);
CREATE INDEX IF NOT EXISTS idx_components_scorecard ON score_components(scorecard_id);

CREATE TABLE IF NOT EXISTS catalysts (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker           TEXT NOT NULL REFERENCES tickers(ticker),
    description      TEXT NOT NULL,
    catalyst_date    TEXT NOT NULL,
    status           TEXT NOT NULL DEFAULT 'upcoming',
    created_at       TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_catalysts_ticker ON catalysts(ticker);

CREATE TABLE IF NOT EXISTS alerts (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker          TEXT,
    rule_type       TEXT NOT NULL,
    message         TEXT NOT NULL,
    severity        TEXT NOT NULL DEFAULT 'info',
    status          TEXT NOT NULL DEFAULT 'open',
    snooze_until    TEXT,
    created_at      TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_alerts_status ON alerts(status);

CREATE TABLE IF NOT EXISTS notes (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticker        TEXT NOT NULL REFERENCES tickers(ticker),
    note_text     TEXT NOT NULL,
    tags          TEXT NOT NULL DEFAULT '',
    created_at    TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_notes_ticker ON notes(ticker);

CREATE TABLE IF NOT EXISTS app_settings (
    key           TEXT PRIMARY KEY,
    value         TEXT NOT NULL,
    updated_at    TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type      TEXT NOT NULL,
    ticker          TEXT,
    payload_json    TEXT NOT NULL DEFAULT '{}',
    created_at      TEXT NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_audit_ticker ON audit_logs(ticker);
CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs(event_type);
