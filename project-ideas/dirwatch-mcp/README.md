# dirwatch-mcp

A Go binary that watches a local directory and uploads new files to a configured REST API
project. It exposes itself as an **MCP server** (Model Context Protocol) so Claude Desktop
or any MCP-capable AI agent can configure and control it through natural language.

---

## Quick start

```bash
# 1. Build
go build -o ~/.local/bin/dirwatch-mcp ./cmd/dirwatch-mcp

# 2. Install as a systemd user service (auto-starts on login)
cp systemd/dirwatch-mcp.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now dirwatch-mcp

# 3. Add to Claude Desktop (~/.config/claude/claude_desktop_config.json)
{
  "mcpServers": {
    "dirwatch": { "command": "/home/<user>/.local/bin/dirwatch-mcp" }
  }
}
```

---

## MCP tools

| Tool | What it does |
|---|---|
| `list_projects(apikey, api_base_url)` | Fetch available projects from the API |
| `set_config(apikey, api_base_url, project, watch_path, action_type)` | Save config and (re)start watch |
| `watch_start()` | Begin watching the configured path |
| `watch_stop()` | Pause watching (config preserved) |
| `get_status()` | Show current state, path, last event |

---

## Config

Stored at `~/.config/dirwatch-mcp/config.yaml` — created automatically by `set_config`.

```yaml
apikey: "tok_xxxxxxx"
api_base_url: "https://api.example.com"
project: "proj_abc123"
watch_path: "/home/user/uploads"
action:
  type: upload_file
  on_conflict: skip
```

---

## How it works

1. `fsnotify` (inotify on Linux) watches the configured directory.
2. On a `CREATE` event (new file added), a 100 ms debounce fires.
3. The file is POSTed as multipart/form-data to `{api_base_url}/projects/{project}/files`
   with `Authorization: Bearer {apikey}`.
4. Transient failures are retried up to 3 times with exponential back-off.

See [PLAN.md](PLAN.md) for full architecture, API contract, and extension roadmap.
