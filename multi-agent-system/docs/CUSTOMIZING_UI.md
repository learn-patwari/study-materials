# Customizing Pattu's look and behaviour

Everything visual is deliberately separated from the agent logic, so you can
retune the mascot and the chat window without touching Jira, Bitbucket or
Confluence code.

| I want to change... | Edit this |
|---|---|
| Which artwork is used | `assets/raw/` + re-run the prep script |
| **When** a pose appears | `gui/mascot_states.py` |
| **How** a pose change is animated | `gui/mascot_animator.py` |
| What Pattu says, and when | `GREETING_MESSAGES` in `gui/mascot_states.py` |
| Autonomous walking around the desktop | `gui/mascot_roamer.py` |
| Chat window colours and fonts | `gui/theme.py` |
| Tray menu entries | `gui/tray_icon.py` |
| Drag/click feel, mascot placement | `gui/mascot_widget.py` |
| Status text next to a running agent | `TOOL_LABELS` in `gui/chat_window.py` |

---

## 1. Swapping the avatars

Artwork lives in a few places:

```
assets/raw/mascot/         a poster (single still) pose per state
assets/raw/animations/     a looping animation per state (.webp)
assets/raw/icons/          tray / taskbar / profile / .exe source art
assets/mascot/             processed poster frames the app falls back to
assets/mascot_frames/      processed animation loops the app actually plays
assets/icons/              processed tray / taskbar / profile / .exe icons
```

To change the character:

1. Drop your new art into `assets/raw/mascot/<state>.png` and
   `assets/raw/animations/<state>.webp` (one of each per pose — see
   `MascotState` in `gui/mascot_states.py` for the full list of state names).
2. Re-run the pipeline:
   ```bash
   pip install Pillow          # build-time only, not needed to run the app
   python tools/prepare_assets.py
   ```
3. Commit what lands in `assets/mascot/`, `assets/mascot_frames/` and
   `assets/icons/`.

The app never needs Pillow — it only reads the processed output.

**A state without an animation still works** — the animator falls back to
showing its poster pose as a static image, cross-fading into and out of it
like any other pose. Animation is additive, not required.

### Why WEBP, not GIF

`assets/raw/animations/` must be **WEBP**, even though the source pack may
also ship GIFs as a fallback. GIF only supports 1-bit transparency, and in
practice every frame after the first comes back fully opaque — the mascot
would show a black box behind everything but its very first frame. WEBP
carries real per-frame alpha, so this doesn't happen. If you're pulling art
from a tool that only exports GIF, convert it to animated WEBP first.

### What the script does, and what it assumes

Some art packs bake their **filename into the picture** as caption text along
an edge. `strip_caption` removes it when present and does nothing otherwise,
so it's safe to run on clean art too (like the pack this project ships with).

A band of the image is treated as a caption when **all three** hold:

| Rule | Constant | Default |
|---|---|---|
| Sits entirely in the top or bottom edge zone | `CAPTION_EDGE_FRAC` | 10% |
| Is no taller than | `CAPTION_MAX_HEIGHT_FRAC` | 6% of image height |
| Is at least this much wider than tall | `CAPTION_MIN_ASPECT` | 6× |

All three matter — a figure that legitimately breaks into detached pieces
(torso, legs, shoes) can otherwise be mistaken for a caption by mass alone.
Only a line of text is simultaneously thin, wide and pinned to an edge.

### Frame size

```python
CANVAS_W = 240
CANVAS_H = 260
```

Every pose — poster and every frame of its animation — is scaled to fit this
box and anchored **bottom-centre**, so the character's feet stay planted and
it neither jumps nor resizes, whether switching poses or mid-loop within one.
Raise these for a bigger mascot, then re-run the script — the widget sizes
itself from the frames, so nothing else needs changing.

A sequence's frames all share **one** crop and scale, computed from the union
of every frame's ink rather than each frame's own bounding box — otherwise a
frame with the character's arm tucked in would recentre on its own smaller
silhouette and appear to drift sideways relative to the frame before it.

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
FADE_DURATION_MS   = 220   # length of a pose change; 0-ish for an instant cut
FADE_STEPS         = 14    # smoothness of the cross-fade
IDLE_CYCLE_MS      = 9_000 # gap between ambient pose changes
BOB_PERIOD_MS      = 3_200 # one breathing cycle
BOB_PIXELS         = 3     # vertical travel — set to 0 to disable the bob
BOB_INTERVAL_MS    = 50    # bob redraw rate
SEQUENCE_FRAME_MS  = 70    # playback rate of a pose's own animation loop
```

`SEQUENCE_FRAME_MS` only matters for poses with a prepared animation — it's
how fast the typing motion, the wave, etc. play once the cross-fade into
them settles. Lower is faster/smoother; the shipped art loops at 22 frames,
so 70ms is about a 1.5 second loop.

Want the mascot completely still? `BOB_PIXELS = 0` and
`IDLE_CYCLE = (MascotState.IDLE,)`.

---

## 3b. Wandering the desktop

`gui/mascot_roamer.py` makes Pattu walk to a new spot on its own every so
often — like a classic desktop-mascot app — instead of sitting still in one
corner. It never moves during a drag or while a real task (thinking, working,
explaining) is running.

```python
ROAM_MIN_INTERVAL_MS = 15_000   # shortest gap between walks
ROAM_MAX_INTERVAL_MS = 35_000   # longest gap between walks
WALK_STEP_PX         = 3        # pixels per tick — walking speed
WALK_TICK_MS         = 16       # tick rate
SCREEN_MARGIN_PX     = 40       # stays this far from the screen edges
WAVE_CHANCE          = 0.4      # odds of a wave after arriving
```

Turn wandering off entirely by not calling `self._roamer.start()` in
`MascotWidget.__init__`, or set `WAVE_CHANCE = 0` to keep the walk but drop
the wave. The character faces the direction it's walking automatically —
`MascotWidget.set_facing_left()` mirrors whatever frame is currently showing,
so it works with any pose the animator happens to be on.

---

## 4. Adding a new pose

Three edits:

1. **Art** — add `assets/raw/mascot/my_pose.png` (a poster still) and,
   optionally, `assets/raw/animations/my_pose.webp` (a looping animation —
   skip it and the pose just plays as a static image). Then add the state
   name to `STATES` in `tools/prepare_assets.py` and re-run
   `python tools/prepare_assets.py`.

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

Replace the corresponding file in `assets/raw/icons/` and re-run the prep
script. `pattu.ico` is generated from `assets/raw/icons/application_exe.png`
at 16/24/32/48/64/128/256 so Windows picks the right size everywhere.

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
