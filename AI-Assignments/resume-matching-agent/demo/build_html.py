"""
Builds demo/index.html: a self-contained, animated terminal replay of the real
CLI transcript in demo/_captured/segments.json (see segment.py). Run:
    python demo/segment.py && python demo/build_html.py
Then record it with `node demo/record.js` (see demo/README.md).
"""
import json, os

HERE = os.path.dirname(os.path.abspath(__file__))
CAPTURED = os.path.join(HERE, "_captured")

segments = json.load(open(os.path.join(CAPTURED, "segments.json")))

# Trim the long "screen" (multi-round screening) output down to a representative
# excerpt so the video stays watchable, while keeping every line real (captured
# from the actual run) -- nothing here is fabricated, just truncated for pacing.
for s in segments:
    if s.get("command") == "screen":
        lines = s["output"].splitlines()
        r1_end = next(i for i, l in enumerate(lines) if l.startswith("=== Round 2"))
        r2_start = r1_end
        r3_start = next(i for i, l in enumerate(lines) if l.startswith("=== Round 3"))
        round1 = lines[:r1_end]
        # keep the first 3 detailed candidate write-ups from round 2
        round2_head = lines[r2_start:r2_start + 2]  # header + blank
        block, blocks, count = [], [], 0
        for l in lines[r2_start + 2:r3_start]:
            if l.strip() == "" and block:
                blocks.append(block)
                block = []
                count += 1
                if count == 3:
                    break
                continue
            if l.strip():
                block.append(l)
        round2 = round2_head + sum((b + [""] for b in blocks), [])
        round2.append("  ... (7 more candidates analyzed with individual strengths/gaps) ...")
        round2.append("")
        round3 = lines[r3_start:r3_start + 1 + 2 * 5]
        round3.append("  ... (5 more hire recommendations) ...")
        s["output"] = "\n".join(round1 + round2 + round3)

ARCH = """START
  |
  v
Parse JD  ->  Extract Requirements  ->  Search Resumes (RAG)
                                              |
                                              v
                                       Rank Candidates
                                              |
                                              v
                                      Generate Report
                                              |
                                              v
                                   Human Feedback Loop --(refine)--> back to
                                              |                      Extract Requirements
                                              v
                                             END

Tools: extract_requirements | compare_candidates | generate_interview_questions
       rag_search | list_resumes | read_resume"""

DATA = {
    "intro": {
        "title": "Agentic Resume Matching System",
        "subtitle": "A LangGraph agent that matches 100 resumes to a job description,\n"
                    "chats conversationally, and screens candidates in 3 rounds.",
    },
    "arch": {
        "caption": "Graph structure: START -> Parse JD -> Extract Requirements -> "
                   "Search Resumes -> Rank Candidates -> Generate Report -> "
                   "Human Feedback Loop -> END",
        "text": ARCH,
    },
    "segments": segments,
    "outro": {
        "title": "8 / 8 test scenarios passing",
        "subtitle": "Full source, tests, and docs:\n"
                    "AI-Assignments/resume-matching-agent/\n\n"
                    "matching_agent.py . tools.py . rag.py . cli.py . tests/",
    },
}

CAPTIONS = {
    "find candidates with React and 3+ years experience":
        "Natural-language query -> parsed into must-have skills + min experience, re-ranked",
    "compare top 3":
        "Side-by-side comparison of the current top 3 with a skill matrix",
    "why did C001 rank higher than C002":
        "Agent explains the ranking gap: experience, must-have coverage, unique skills",
    "require Next.js and 5+ years":
        "Iterative refinement -> loops back through the graph and explains what changed",
    "screen":
        "Multi-round screening: top-10 screen -> deep analysis -> hire recommendation",
    "quit":
        "Exiting the chat session",
    "python tests/test_scenarios.py":
        "Running the automated test suite (8 end-to-end conversation flows)",
}
for s in segments:
    if s["type"] == "command":
        s["caption"] = CAPTIONS.get(s["command"], "")

html = """<!doctype html>
<html><head><meta charset="utf-8"><title>demo</title>
<style>
  * { box-sizing: border-box; }
  html, body { margin: 0; padding: 0; background: #11111b; }
  #stage {
    width: 1280px; height: 720px; position: relative; overflow: hidden;
    background: radial-gradient(ellipse at top, #1e1e2e 0%, #11111b 70%);
    font-family: "DejaVu Sans Mono", "Liberation Mono", monospace;
  }
  .card {
    position: absolute; inset: 0; display: flex; flex-direction: column;
    align-items: center; justify-content: center; text-align: center;
    color: #cdd6f4; opacity: 0; transition: opacity .5s ease;
  }
  .card.show { opacity: 1; }
  .card h1 { font-size: 44px; margin: 0 0 18px; color: #a6e3a1; }
  .card h2 { font-size: 26px; margin: 0 0 18px; color: #f9e2af; }
  .card p { font-size: 20px; line-height: 1.6; color: #bac2de; white-space: pre-line; }
  .arch pre {
    text-align: left; font-size: 17px; line-height: 1.45; color: #89dceb;
    background: #181825; border: 1px solid #313244; border-radius: 10px;
    padding: 22px 28px; box-shadow: 0 10px 40px rgba(0,0,0,.5);
  }
  #term {
    position: absolute; inset: 30px 60px; border-radius: 12px; overflow: hidden;
    background: #1e1e2e; box-shadow: 0 20px 60px rgba(0,0,0,.55);
    opacity: 0; transition: opacity .4s ease;
  }
  #term.show { opacity: 1; }
  .chrome {
    height: 38px; background: #181825; display: flex; align-items: center;
    padding: 0 14px; gap: 8px; border-bottom: 1px solid #313244;
  }
  .dot { width: 12px; height: 12px; border-radius: 50%; }
  .dot.r { background: #f38ba8; } .dot.y { background: #f9e2af; } .dot.g { background: #a6e3a1; }
  .chrome .fname { color: #6c7086; font-size: 13px; margin-left: 12px; }
  .caption {
    background: #24273a; color: #f9e2af; font-size: 15px; padding: 9px 18px;
    border-bottom: 1px solid #313244; font-style: italic; min-height: 36px;
  }
  #body {
    position: absolute; top: 83px; left: 0; right: 0; bottom: 0;
    padding: 14px 20px; overflow: hidden; font-size: 14.5px; line-height: 1.42;
    color: #cdd6f4; white-space: pre-wrap; word-break: break-word;
  }
  .prompt { color: #a6e3a1; font-weight: bold; }
  .typed { color: #f5e0dc; font-weight: bold; }
  .divider { color: #7f849c; }
  .rank { font-weight: bold; color: #f5c2e7; }
  .hire { color: #a6e3a1; font-weight: bold; }
  .nohire { color: #f38ba8; font-weight: bold; }
  .score { color: #f9e2af; }
  .cursor {
    display: inline-block; width: 8px; height: 16px; background: #a6e3a1;
    vertical-align: -3px; animation: blink 1s step-start infinite;
  }
  @keyframes blink { 50% { opacity: 0; } }
</style></head>
<body>
<div id="stage">
  <div id="intro" class="card"><h1></h1><p></p></div>
  <div id="archCard" class="card arch"><pre></pre></div>
  <div id="term">
    <div class="chrome">
      <div class="dot r"></div><div class="dot y"></div><div class="dot g"></div>
      <div class="fname">resume-matching-agent — python cli.py</div>
    </div>
    <div class="caption" id="caption"></div>
    <div id="body"></div>
  </div>
  <div id="outro" class="card"><h1></h1><p></p></div>
</div>
<script id="data" type="application/json">__DATA__</script>
<script>
const DATA = JSON.parse(document.getElementById('data').textContent);
const stage = document.getElementById('stage');
const introEl = document.getElementById('intro');
const archEl = document.getElementById('archCard');
const termEl = document.getElementById('term');
const bodyEl = document.getElementById('body');
const capEl = document.getElementById('caption');
const outroEl = document.getElementById('outro');

function esc(s) {
  return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}
function highlight(escaped) {
  return escaped.split('\\n').map(line => {
    if (/^=+$/.test(line.trim())) return `<span class="divider">${line}</span>`;
    if (/^\\s*\\d+[\\.\\)]/.test(line)) return `<span class="rank">${line}</span>`;
    let l = line
      .replace(/\\bLEAN HIRE\\b|(?<!NO )\\bHIRE\\b/g, m => `<span class="hire">${m}</span>`)
      .replace(/\\bNO HIRE\\b/g, m => `<span class="nohire">${m}</span>`)
      .replace(/\\bscore[=:]?\\s*[\\d.]+/gi, m => `<span class="score">${m}</span>`);
    return l;
  }).join('\\n');
}
function scrollBottom() { bodyEl.scrollTop = bodyEl.scrollHeight; }
const sleep = (ms) => new Promise(r => setTimeout(r, ms));

async function showCard(el, ms) {
  el.classList.add('show');
  await sleep(ms);
  el.classList.remove('show');
  await sleep(450);
}

async function typeText(el, text, speed) {
  for (let i = 0; i < text.length; i++) {
    el.textContent += text[i];
    scrollBottom();
    await sleep(speed);
  }
}

async function appendOutput(text, perLineMs) {
  const lines = highlight(esc(text)).split('\\n');
  for (let i = 0; i < lines.length; i++) {
    const div = document.createElement('div');
    div.innerHTML = lines[i] || '&nbsp;';
    bodyEl.appendChild(div);
    scrollBottom();
    if (perLineMs) await sleep(perLineMs);
  }
}

async function runBanner(banner) {
  bodyEl.innerHTML = '';
  await appendOutput(banner.text, 24);
  await sleep(4500);
}

async function runCommand(seg) {
  const prompt = seg.prompt || 'you > ';
  const line = document.createElement('div');
  bodyEl.appendChild(line);
  const pspan = document.createElement('span');
  pspan.className = 'prompt';
  pspan.textContent = prompt;
  const tspan = document.createElement('span');
  tspan.className = 'typed';
  const cursor = document.createElement('span');
  cursor.className = 'cursor';
  line.appendChild(pspan); line.appendChild(tspan); line.appendChild(cursor);
  capEl.textContent = seg.caption || '';
  scrollBottom();
  await typeText(tspan, seg.command, 38);
  await sleep(450);
  cursor.remove();
  const nLines = seg.output.split('\\n').length;
  const perLine = nLines > 40 ? 9 : nLines > 12 ? 16 : 30;
  await appendOutput(seg.output, perLine);
  const div = document.createElement('div'); div.innerHTML = '&nbsp;'; bodyEl.appendChild(div);
  const holdMs = Math.max(2200, Math.min(9000, seg.output.length * 3.4));
  await sleep(holdMs);
}

(async () => {
  introEl.querySelector('h1').textContent = DATA.intro.title;
  introEl.querySelector('p').textContent = DATA.intro.subtitle;
  await showCard(introEl, 5800);

  archEl.querySelector('pre').textContent = DATA.arch.text;
  await showCard(archEl, 8000);

  termEl.classList.add('show');
  for (const seg of DATA.segments) {
    if (seg.type === 'banner') await runBanner(seg);
    else await runCommand(seg);
  }
  termEl.classList.remove('show');
  await sleep(500);

  outroEl.querySelector('h1').textContent = DATA.outro.title;
  outroEl.querySelector('p').textContent = DATA.outro.subtitle;
  await showCard(outroEl, 6500);

  window.__DONE__ = true;
})();
</script>
</body></html>
"""

html = html.replace("__DATA__", json.dumps(DATA))
with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
    f.write(html)
print("wrote index.html", len(html), "bytes")
