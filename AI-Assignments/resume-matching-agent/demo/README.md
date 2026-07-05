# Demo video

`resume_matching_agent_demo.webm` — a ~73 second walkthrough of the agent:

1. Title card
2. The graph structure (`START → Parse JD → ... → END`)
3. Launching the CLI (default JD, top-10 shortlist)
4. Natural-language query: "find candidates with React and 3+ years experience"
5. "compare top 3"
6. "why did C001 rank higher than C002"
7. Iterative refinement: "require Next.js and 5+ years" (shows the
   `CHANGES SINCE LAST RANKING` diff)
8. Multi-round screening (`screen`)
9. The test suite passing (8/8)

**How it was produced:** every line of terminal output in the video is real —
captured by piping the exact commands above into `python cli.py` and
`python tests/test_scenarios.py`, then replayed with a typing/reveal animation
in a self-contained HTML page and recorded to video with Playwright (no
external screen-recording software, no fabricated output). See
`build_video.md` in this folder for the reproduction steps if you want to
regenerate it (e.g. after code changes) or extend it to a longer cut.
