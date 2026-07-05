"""
Splits the captured CLI transcript (demo/_captured/full_session.txt, produced
by capture.sh) into per-command segments for the video-builder, and folds in
the test-run transcript as a final segment. Run: python demo/segment.py
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURED = os.path.join(HERE, "_captured")

with open(os.path.join(CAPTURED, "full_session.txt"), "r", encoding="utf-8") as f:
    text = f.read()

commands = [
    "find candidates with React and 3+ years experience",
    "compare top 3",
    "why did C001 rank higher than C002",
    "require Next.js and 5+ years",
    "screen",
    "quit",
]

parts = text.split("you > ")
banner = parts[0].rstrip("\n")
assert len(parts) - 1 == len(commands), f"expected {len(commands)} prompts, got {len(parts)-1}"

segments = [{"type": "banner", "text": banner}]
for cmd, chunk in zip(commands, parts[1:]):
    # chunk currently starts right after "you > " and ends right before the next "you > "
    # (or EOF for the last one). Strip a single leading newline from the echoed input.
    out = chunk
    if out.startswith("\n"):
        out = out[1:]
    out = out.rstrip("\n")
    segments.append({"type": "command", "command": cmd, "output": out})

with open(os.path.join(CAPTURED, "tests.txt"), "r", encoding="utf-8") as f:
    tests_out = f.read().rstrip("\n")
segments.append({
    "type": "command",
    "command": "python tests/test_scenarios.py",
    "output": tests_out,
    "prompt": "$ ",
})

with open(os.path.join(CAPTURED, "segments.json"), "w", encoding="utf-8") as f:
    json.dump(segments, f, indent=2)

print(f"Wrote {len(segments)} segments")
for s in segments:
    if s["type"] == "banner":
        print("banner:", len(s["text"]), "chars")
    else:
        print("cmd:", repr(s["command"]), "->", len(s["output"]), "chars output")
