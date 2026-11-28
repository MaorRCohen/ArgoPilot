-- One photo per plot. Runs on SQLite and PostgreSQL: seed_registry.sh and setup_db.py apply it.
-- Idempotent. Grants for registry_app are not here: setup_db.py adds them on PostgreSQL only.
CREATE TABLE IF NOT EXISTS plot_photos (
  plot_id      TEXT PRIMARY KEY REFERENCES plots (id) ON DELETE CASCADE,
  key          TEXT NOT NULL,
  content_type TEXT NOT NULL
);
