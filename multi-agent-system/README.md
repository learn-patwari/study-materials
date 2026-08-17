# Pattu — personal desktop assistant

A draggable mascot that lives on your desktop. Click it and a chat window
opens; ask a question and Pattu spins up whichever subagent it needs.

- **Jira** — every open ticket assigned to you, bugs first
- **Bitbucket** — open PRs across the repos you monitor, plus repo inspection
- **Confluence** — create and list pages in your personal space
- **Bug cross-check** — a Jira bug is matched to its repo via `BUG_REPO_MAP`,
  the repo is inspected, and a fix is suggested

All three share a SQLite memory at `~/.pattu/memory.db`, so results and
conversation survive restarts. The LLM is **your own OpenAI-compatible
server** — no Anthropic API involved.

---

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env
```

Then edit `.env`. **Only the three `LLM_` variables are required** — the app
will not start without them:

```ini
LLM_BASE_URL=http://localhost:11434/v1   # your local server
LLM_API_KEY=your-local-api-key
LLM_MODEL=your-model-name
```

Everything else is optional. Leave a credential block blank and that agent
simply reports itself unavailable; the rest keep working.

| Block | Variables |
|---|---|
| Jira | `JIRA_BASE_URL`, `JIRA_USER_EMAIL`, `JIRA_API_TOKEN`, `JIRA_PROJECT_KEY` |
| Bitbucket | `BITBUCKET_USERNAME`, `BITBUCKET_APP_PASSWORD`, `BITBUCKET_WORKSPACE`, `BITBUCKET_REPOS` |
| Confluence | `CONFLUENCE_BASE_URL`, `CONFLUENCE_USERNAME`, `CONFLUENCE_PASSWORD` |
| Bug mapping | `BUG_REPO_MAP=jira-component:bitbucket-repo,...` |

`.env` is gitignored — keep your real credentials out of the repo.

## Running

```bash
python app.py
```

Pattu appears near the bottom-right of the screen and waves. Drag to move,
click to open the chat, and the tray icon offers **Open Chat**, **Daily
Brief** and **Quit**. Closing the chat hides it; Pattu stays on the desktop.

## Packaging for Windows

```bash
pip install pyinstaller
pyinstaller pattu.spec
```

Produces `dist/Pattu.exe` with the artwork bundled.

## Tests

```bash
python -m pytest tests/ -q
```

130 tests, all HTTP mocked — no real credentials needed. Tests that need a Qt
display skip themselves automatically on a headless machine.

## Layout

```
app.py                     entry point — wires mascot, chat and tray together
core/
  orchestrator.py          Pattu's tool-use loop
  memory.py                shared SQLite memory
  llm_client.py            OpenAI-compatible client
agents/
  jira_agent.py            Jira REST v3
  bitbucket_agent.py       Bitbucket REST 2.0 + repo inspection
  confluence_agent.py      Confluence REST
gui/
  mascot_widget.py         the floating character — drag and click
  mascot_states.py         which pose appears, and when
  mascot_animator.py       cross-fades, idle drift, breathing
  chat_window.py           the chat panel
  theme.py                 all colours and stylesheets
  assets.py                asset lookup
  tray_icon.py             system tray
tools/
  prepare_assets.py        build-time artwork pipeline
assets/
  raw/                     original artwork (build-time input)
  mascot/                  processed animation frames
  icons/                   tray, taskbar, profile, .exe icons
docs/
  CUSTOMIZING_UI.md        how to change the avatars, animation and colours
```

To change how Pattu looks or behaves, start with
[`docs/CUSTOMIZING_UI.md`](docs/CUSTOMIZING_UI.md).
