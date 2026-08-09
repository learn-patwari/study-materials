CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT
);

CREATE TABLE IF NOT EXISTS tickets (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    jira_key     TEXT UNIQUE,
    title        TEXT,
    srs_content  TEXT,
    description  TEXT,
    status       TEXT DEFAULT 'draft',
    code_source  TEXT,
    source_type  TEXT,
    created_at   TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS chat_messages (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    role      TEXT,
    content   TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS tasks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id     INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    jira_task_key TEXT,
    title         TEXT,
    assignee      TEXT,
    status        TEXT DEFAULT 'todo',
    estimated_hrs REAL,
    task_type     TEXT DEFAULT 'dev',
    start_date    TEXT,
    end_date      TEXT
);

CREATE TABLE IF NOT EXISTS diagrams (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id           INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    mermaid_src         TEXT,
    drawio_xml          TEXT,
    confluence_page_url TEXT,
    generated_at        TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS documents (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id   INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    doc_type    TEXT,
    content     TEXT,
    approved_at TEXT,
    posted_at   TEXT
);

CREATE TABLE IF NOT EXISTS test_files (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    ticket_id    INTEGER REFERENCES tickets(id) ON DELETE CASCADE,
    filename     TEXT,
    content      TEXT,
    coverage_pct REAL
);

CREATE TABLE IF NOT EXISTS sprints (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    jira_sprint_id TEXT,
    name           TEXT,
    start_date     TEXT,
    end_date       TEXT,
    dev_days       INTEGER,
    test_days      INTEGER,
    fetched_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS voc_links (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    sprint_id      INTEGER REFERENCES sprints(id) ON DELETE CASCADE,
    voc_jira_key   TEXT,
    linked_task_id INTEGER REFERENCES tasks(id),
    notes          TEXT,
    logged_hrs     REAL,
    created_at     TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pull_requests (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    repo_slug     TEXT,
    pr_id         INTEGER,
    title         TEXT,
    author        TEXT,
    source_branch TEXT,
    target_branch TEXT,
    pr_url        TEXT,
    diff_text     TEXT,
    status        TEXT DEFAULT 'new',
    notified_at   TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS pr_review_comments (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    pr_id     INTEGER REFERENCES pull_requests(id) ON DELETE CASCADE,
    file_path TEXT,
    line_num  INTEGER,
    comment   TEXT,
    approved  INTEGER DEFAULT 0,
    posted_at TEXT
);

CREATE TABLE IF NOT EXISTS bug_analyses (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    jira_key         TEXT UNIQUE,
    title            TEXT,
    description      TEXT,
    codebase_path    TEXT,
    root_cause       TEXT,
    fix_plan_json    TEXT,
    test_impact_json TEXT,
    status           TEXT DEFAULT 'analysed',
    backup_path      TEXT,
    created_at       TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS bug_counts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_key TEXT,
    period_days INTEGER,
    total       INTEGER,
    open        INTEGER,
    in_progress INTEGER,
    resolved    INTEGER,
    fetched_at  TEXT DEFAULT (datetime('now'))
);
