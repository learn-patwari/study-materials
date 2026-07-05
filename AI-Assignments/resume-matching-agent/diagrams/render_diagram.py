"""Regenerate the state-machine diagram from the live compiled graph.

    python diagrams/render_diagram.py

Writes `diagrams/state_machine.mmd` (Mermaid source). If network access to
mermaid.ink is available it also writes `diagrams/state_machine.png`.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from matching_agent import build_graph  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def main() -> None:
    graph = build_graph().get_graph()
    mmd = graph.draw_mermaid()
    with open(os.path.join(HERE, "state_machine.mmd"), "w", encoding="utf-8") as fh:
        fh.write(mmd)
    print("wrote state_machine.mmd")
    try:  # optional PNG (needs network to mermaid.ink)
        png = graph.draw_mermaid_png()
        with open(os.path.join(HERE, "state_machine.png"), "wb") as fh:
            fh.write(png)
        print("wrote state_machine.png")
    except Exception as e:  # noqa: BLE001
        print(f"(skipped PNG render: {e})")


if __name__ == "__main__":
    main()
