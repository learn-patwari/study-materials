# Customizing Pattu's look and behaviour

Everything visual is deliberately separated from the agent logic, so you can
retune the mascot and the chat window without touching Jira, Bitbucket or
Confluence code.

| I want to change... | Edit this |
|---|---|
| Which artwork is used | `assets/raw/` + re-run the prep script |
| **When** a pose appears | `gui/mascot_states.py` |
| **How** a pose change is animated | `gui/mascot_animator.py` |
| Chat window colours and fonts | `gui/theme.py` |
| Tray menu entries | `gui/tray_icon.py` |
| Drag/click feel, mascot placement | `gui/mascot_widget.py` |
| Status text next to a running agent | `TOOL_LABELS` in `gui/chat_window.py` |

---

## 1. Swapping the avatars

Artwork lives in two places:

```
assets/raw/       the original art, exactly as supplied — never loaded at runtime
assets/mascot/    the processed frames the app actually loads
assets/icons/     tray / taskbar / profile / .exe icons
```

To change the character:

1. Drop your new PNGs into `assets/raw/`, keeping the existing filenames.
2. Re-run the pipeline:
   ```bash
   pip install Pillow          # build-time only, not needed to run the app
   python tools/prepare_assets.py
   ```
3. Commit what lands in `assets/mascot/` and `assets/icons/`.

The app never needs Pillow — it only reads the processed output.

### What the script does, and what it assumes

The supplied art has its **filename burned into the picture** as caption text
along the bottom (and the top of the celebrating pose). The script strips that,
then fits every pose to a common canvas.

A band of the image is treated as a caption when **all three** hold:

| Rule | Constant | Default |
|---|---|---|
| Sits entirely in the top or bottom edge zone | `CAPTION_EDGE_FRAC` | 10% |
| Is no taller than | `CAPTION_MAX_HEIGHT_FRAC` | 6% of image height |
| Is at least this much wider than tall | `CAPTION_MIN_ASPECT` | 6× |

All three matter. The figure legitimately breaks into several detached pieces —
torso, legs, shoes — and in this artwork the caption actually contains *more*
ink than the shoes do, so "keep the biggest piece" would amputate the legs.
Only a line of text is simultaneously thin, wide and pinned to an edge.

**If your art has no caption**, the rules simply never match and nothing is
removed. **If your art has a caption of a different shape**, adjust the three
constants at the top of `tools/prepare_assets.py`.

### Frame size

```python
CANVAS_W = 240
CANVAS_H = 260
```

Every pose is scaled to fit this box and anchored **bottom-centre**, so the
character's feet stay planted and it neither jumps nor resizes mid-animation.
Raise these for a bigger mascot, then re-run the script — the widget sizes
itself from the frames, so nothing else needs changing.

---

## 2. Changing when a pose appears

Open `gui/mascot_states.py`. It is plain Python with no Qt imports.

**Point a subagent at a different pose:**

```python
TOOL_STATES = {
    "run_jira_agent":         MascotState.WORKING,
    "bitbucket_inspect_repo": MascotState.IDEA,     # <- change the pose here
    ...
}
```

Every tool in `core/orchestrator.py` must appear here. A test enforces it, so
adding a tool without a pose fails the suite instead of quietly freezing the
mascot mid-animation.

**Make a pose momentary or permanent:**

```python
TRANSIENT_STATES = frozenset({
    MascotState.GREETING, MascotState.SUCCESS,
    MascotState.CELEBRATING, MascotState.IDEA,
})
STATE_HOLD_MS = 4_000     # how long a momentary pose holds
```

Anything listed here reverts to `IDLE` after `STATE_HOLD_MS`. Anything *not*
listed holds until something replaces it — which is why `THINKING` and
`WORKING` last exactly as long as the work does.

**Change the ambient idle loop:**

```python
IDLE_CYCLE = (
    MascotState.IDLE, MascotState.READY,
    MascotState.IDLE, MascotState.GREETING,
)
```

Pattu drifts through these while nothing is happening. To stop the drift
entirely, set `IDLE_CYCLE = (MascotState.IDLE,)`.

---

## 3. Retiming the animation

All in `gui/mascot_animator.py`:

```python
FADE_DURATION_MS = 220   # length of a pose change; 0-ish for an instant cut
FADE_STEPS       = 14    # smoothness of the cross-fade
IDLE_CYCLE_MS    = 9_000 # gap between ambient pose changes
BOB_PERIOD_MS    = 3_200 # one breathing cycle
BOB_PIXELS       = 3     # vertical travel — set to 0 to disable the bob
BOB_INTERVAL_MS  = 50    # bob redraw rate
```

Want the mascot completely still? `BOB_PIXELS = 0` and
`IDLE_CYCLE = (MascotState.IDLE,)`.

---

## 4. Adding a new pose

Three edits:

1. **Art** — put `assets/raw/MASCOT_MY_POSE.png` in place and add it to
   `MASCOT_MAP` in `tools/prepare_assets.py`:
   ```python
   "MASCOT_MY_POSE.png": "my_pose.png",
   ```
   Re-run `python tools/prepare_assets.py`.

2. **State** — add it to the enum in `gui/mascot_states.py`:
   ```python
   MY_POSE = "my_pose.png"
   ```

3. **Trigger** — decide when it shows: add it to `TOOL_STATES`, to
   `IDLE_CYCLE`, or emit it directly from `gui/chat_window.py`:
   ```python
   self.mascot_state.emit(MascotState.MY_POSE)
   ```

The tests pick the new state up automatically and will fail if step 1 is
missing.

---

## 5. Recolouring the chat window

`gui/theme.py` holds the palette, and the stylesheets are built from it — so
changing `ACCENT` restyles the user bubbles and the Send button together.

```python
BG      = "#1A1A1A"   # chat background
ACCENT  = "#0078D4"   # user bubbles, primary button
TEXT    = "#E0E0E0"
ERROR   = "#FF6B6B"
AVATAR_SIZE = 28      # profile icon beside Pattu's messages
```

For a light theme, invert `BG`/`TEXT` and lighten `BG_BUBBLE_PATTU` and
`BG_INPUT`. No widget code needs to change.

---

## 6. Icons

| File | Where it shows |
|---|---|
| `assets/icons/tray.png` | system tray |
| `assets/icons/taskbar.png` | window and taskbar button |
| `assets/icons/profile.png` | avatar beside Pattu's chat messages |
| `assets/icons/pattu.ico` | the built `.exe` |

Replace the corresponding file in `assets/raw/` and re-run the prep script.
`pattu.ico` is generated from `LOGO_APPLICATION_EXE.png` at 16/24/32/48/64/128/256
so Windows picks the right size everywhere.

**On Windows**, `app.py` sets an explicit AppUserModelID:

```python
APP_USER_MODEL_ID = "AkshayPatwari.Pattu.Assistant.1"
```

Without it Windows treats the app as generic Python and shows the Python icon
in the taskbar instead of yours. If you change the icon and Windows keeps
showing the old one, bump the trailing number — the shell caches per ID.

---

## 7. Where the mascot starts

`gui/mascot_widget.py`:

```python
DRAG_THRESHOLD_PX = 5     # movement below this counts as a click, not a drag
GREETING_MS       = 3_000 # how long the launch wave holds
```

`_place_bottom_right()` sets the launch position — currently 40px from the
right edge and 80px up from the bottom of the available screen area.

---

## 8. Checking your changes

```bash
python -m pytest tests/ -q
```

The mascot tests confirm every state has a frame, every tool maps to a pose,
all frames share one canvas size, and the cross-fade stays transparent. The
animator tests skip automatically if PyQt6 or a Qt platform plugin is missing,
so the suite still runs on a headless machine.

Then run it for real:

```bash
python app.py
```
