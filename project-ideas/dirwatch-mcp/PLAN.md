# dirwatch-mcp — Detailed Plan

## What this is

A Go binary that exposes itself as an **MCP server** (Model Context Protocol, stdio transport).
It watches a configured directory for new files and, when one appears, uploads it to a
configured REST API project. Claude Desktop or any MCP-capable AI agent can configure and
control it through structured tool calls.

---

## Problem

Developers and teams often need a lightweight, always-on bridge between a local folder
(downloads, exports, scans, screenshots) and a cloud API project. Current options require
heavyweight integrations or manual uploads. A local MCP server solves this without a
third-party sync service and makes the tool AI-controllable out of the box.

---

## Requirements (confirmed)

| Parameter | Description |
|---|---|
| `apikey` | Bearer token for authenticating to the API |
| `project` | Project identifier — listed live from the API based on the token |
| `path` | Absolute path to the directory to monitor |
| `action` | `upload_file` — POST new files to the project; extensible to `mcp_dispatch` |

Additional clarified decisions:
- **Language:** Go (single binary, no runtime)
- **Platform:** Linux — runs as a **systemd user service** (auto-start on login)
- **MCP role:** The tool IS an MCP server; Claude / agents control it via MCP tools
- **File events:** `CREATE` only (file added); modify/delete ignored by default
- **Debounce:** 100 ms — rapid partial-writes coalesced before upload

---

## Architecture

```
Claude Desktop / AI agent
        │  MCP over stdio (JSON-RPC 2.0)
        ▼
┌────────────────────────────────────────┐
│           dirwatch-mcp (Go binary)     │
│                                        │
│  ┌──────────────────────────────────┐  │
│  │  MCP Server  (mark3labs/mcp-go)  │  │  ← exposes 5 tools
│  └──────────────┬───────────────────┘  │
│                 │                      │
│  ┌──────────────▼───────────────────┐  │
│  │  Config (YAML, ~/.config/…)      │  │  ← apikey, project, path, action
│  └──────────────┬───────────────────┘  │
│                 │                      │
│  ┌──────────────▼───────────────────┐  │
│  │  Watcher  (fsnotify / inotify)   │  │  ← watches path; debounce 100ms
│  └──────────────┬───────────────────┘  │
│                 │ CREATE event         │
│  ┌──────────────▼───────────────────┐  │
│  │  Action Router                   │  │  ← reads action type from config
│  └──────────────┬───────────────────┘  │
│                 │                      │
│  ┌──────────────▼───────────────────┐  │
│  │  upload.go — multipart POST      │  │  ← stdlib net/http
│  └──────────────────────────────────┘  │
└────────────────────────────────────────┘
        ▲
  systemd user service (auto-start on login, restart on crash)
```

---

## MCP tools (API surface)

| Tool | Arguments | What it does |
|---|---|---|
| `list_projects` | `apikey`, `api_base_url` | GET /projects with Bearer token; returns name+id list |
| `set_config` | `apikey`, `api_base_url`, `project`, `watch_path`, `action_type` | Validates token, writes config, (re)starts watcher |
| `watch_start` | — | Begin fsnotify watch on configured path; idempotent |
| `watch_stop` | — | Stop active watch (config preserved) |
| `get_status` | — | Returns: watching(bool), path, project, last_event timestamp |

---

## Config file

Location: `~/.config/dirwatch-mcp/config.yaml`

```yaml
apikey: "tok_xxxxxxxxxxxxxxx"
api_base_url: "https://api.example.com"
project: "proj_abc123"
watch_path: "/home/user/uploads"
action:
  type: upload_file        # future: mcp_dispatch
  on_conflict: skip        # skip | overwrite (PUT)
  include_hidden: false    # watch dotfiles?
  recursive: false         # watch subdirectories?
```

---

## Upload API contract

```
POST {api_base_url}/projects/{project}/files
Authorization: Bearer {apikey}
Content-Type: multipart/form-data

  file      = <binary content>
  filename  = <original filename>
  rel_path  = <path relative to watch_path>
  added_at  = <RFC3339 timestamp>
```

Responses:
- `201 Created` — success
- `409 Conflict` — file exists; honour `on_conflict` (skip or retry as PUT)
- `4xx/5xx` — logged; retry with exponential back-off (1s, 2s, 4s, max 3 attempts)

---

## Watcher behaviour details

- Uses `fsnotify.Watcher` on Linux (backed by inotify)
- Only `fsnotify.Create` events forwarded to action router
- Debounce: 100 ms timer reset on each event for the same path
- Skips directories and hidden files (`.` prefix) unless `include_hidden: true`
- One level deep; `recursive: true` adds watches for subdirectories as they appear

---

## File structure

```
project-ideas/dirwatch-mcp/
├── PLAN.md                          ← this file
├── README.md                        ← setup + usage
├── go.mod
├── cmd/
│   └── dirwatch-mcp/
│       └── main.go                  ← wire MCP server + start watcher
├── internal/
│   ├── config/
│   │   └── config.go                ← load/save/validate YAML config
│   ├── watcher/
│   │   └── watcher.go               ← fsnotify wrapper + debounce
│   ├── actions/
│   │   └── upload.go                ← multipart POST + retry
│   └── mcp/
│       └── server.go                ← MCP tool handlers
└── systemd/
    └── dirwatch-mcp.service         ← systemd user unit template
```

---

## Go dependencies

| Module | Purpose |
|---|---|
| `github.com/fsnotify/fsnotify v1.7` | inotify-backed directory events |
| `github.com/mark3labs/mcp-go v0.20` | MCP server over stdio (JSON-RPC 2.0) |
| `gopkg.in/yaml.v3` | Config file read/write |
| `net/http` (stdlib) | HTTP client for API calls + multipart upload |
| `os`, `path/filepath` (stdlib) | File I/O, path manipulation |

---

## systemd unit

File: `systemd/dirwatch-mcp.service` (install to `~/.config/systemd/user/`)

```ini
[Unit]
Description=dirwatch-mcp directory monitor MCP server
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/dirwatch-mcp
Restart=on-failure
RestartSec=5s
Environment=HOME=%h

[Install]
WantedBy=default.target
```

Install steps:
```bash
go build -o ~/.local/bin/dirwatch-mcp ./cmd/dirwatch-mcp
cp systemd/dirwatch-mcp.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now dirwatch-mcp
```

---

## Claude Desktop integration

Add to `~/.config/claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "dirwatch": {
      "command": "/home/<YOUR_USER>/.local/bin/dirwatch-mcp"
    }
  }
}
```

Then restart Claude Desktop. You'll see `list_projects`, `set_config`, `watch_start`,
`watch_stop`, `get_status` in the tool palette.

---

## Build & test

```bash
# Build
go build -o ~/.local/bin/dirwatch-mcp ./cmd/dirwatch-mcp

# Unit tests (no network, no Docker)
go test ./internal/...

# What the tests cover
#  config_test.go  — round-trip YAML load/save; missing-field validation
#  watcher_test.go — create temp file; assert event fires within 500 ms
#  upload_test.go  — mock httptest.Server; assert correct multipart fields + auth header
```

---

## Future extensions (out of scope for v1)

| Extension | Notes |
|---|---|
| `mcp_dispatch` action | Instead of uploading, call a named MCP tool on another server |
| Windows support | `fsnotify` already works; add a NSSM or Task Scheduler install script |
| macOS support | `fsnotify` already works; add a LaunchAgent plist install script |
| File-type filters | Only trigger on `*.pdf`, `*.png`, etc. — add `include_patterns` to config |
| Webhook action | POST file metadata (not content) to an arbitrary URL |
| Retry queue | SQLite-backed queue for offline resilience |
