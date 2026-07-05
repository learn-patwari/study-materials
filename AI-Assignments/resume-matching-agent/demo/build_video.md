# Reproducing the demo video

Every line of terminal output in `resume_matching_agent_demo.webm` is real —
captured from an actual run of the agent, then replayed with an animation and
recorded to video. Nothing is hand-typed or fabricated. To regenerate it
(e.g. after changing the agent):

```bash
cd AI-Assignments/resume-matching-agent
python -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

cd demo
./capture.sh          # runs the real CLI + test suite, saves transcripts to _captured/
python segment.py     # splits the transcript into per-command segments -> _captured/segments.json
python build_html.py  # renders segments.json into a self-contained animated terminal page -> index.html
npm install            # playwright (points at an existing Chromium if PLAYWRIGHT_BROWSERS_PATH is set)
node record.js         # opens index.html, records it, writes resume_matching_agent_demo.webm
```

## How it works

- `capture.sh` pipes the exact demo commands into `python cli.py` and runs
  `tests/test_scenarios.py`, saving raw stdout.
- `segment.py` splits that transcript on the `you > ` prompt into one segment
  per command (command text + the real output that followed it).
- `build_html.py` renders those segments into `index.html`: a single
  self-contained page (no CDN/network dependencies) that "types" each command
  and reveals its real output with a terminal-style typing/scroll animation,
  plus a title card and an architecture card describing the LangGraph state
  machine. A `window.__DONE__` flag is set when the animation finishes.
- `record.js` opens `index.html` in Chromium via Playwright with
  `recordVideo` enabled (Playwright's built-in screencast-to-webm pipeline —
  no external screen-recording tool needed), waits for `__DONE__`, then closes
  the browser context, which flushes the finished `.webm` to disk.

## Adjusting length / content

- Edit the command list and captions in `segment.py` / `build_html.py`
  (`CAPTIONS` dict) to change what's shown.
- Timing is controlled by the `sleep(...)` calls in the JS animation inside
  `build_html.py` (typing speed, per-line reveal speed, hold time per
  segment) — there's no fixed frame count or duration; `record.js` just waits
  for the animation to finish, however long that takes.
