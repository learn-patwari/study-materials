from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from pathlib import Path
import json


GANTT_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ background:#0f1420; color:#e8ecf0; margin:0; padding:16px; font-family:sans-serif; font-size:12px; }}
  .gantt-container {{ overflow-x:auto; }}
  table {{ border-collapse:collapse; width:100%; }}
  th {{ background:#1a2133; padding:6px 8px; text-align:left; border-bottom:1px solid #2a3a55; color:#8a9bb0; }}
  td {{ padding:4px 8px; border-bottom:1px solid #1a2133; }}
  .bar {{ height:16px; border-radius:3px; display:inline-block; }}
  .bar-dev {{ background:#4a90d9; }}
  .bar-integ {{ background:#f0a030; }}
  .bar-test {{ background:#3ab06a; }}
  .legend {{ margin-bottom:12px; }}
  .legend-item {{ display:inline-block; margin-right:16px; }}
  .dot {{ width:10px; height:10px; border-radius:2px; display:inline-block; margin-right:4px; vertical-align:middle; }}
</style>
</head>
<body>
<div class="legend">
  <span class="legend-item"><span class="dot" style="background:#4a90d9"></span>Dev</span>
  <span class="legend-item"><span class="dot" style="background:#f0a030"></span>Integration Tests</span>
  <span class="legend-item"><span class="dot" style="background:#3ab06a"></span>Test Days</span>
</div>
{content}
<script>
var data = {data_json};
var totalDays = data.total_days || 10;
var container = document.querySelector('.gantt-container');
if (!container) {{
  container = document.createElement('div');
  container.className = 'gantt-container';
  document.body.appendChild(container);
}}
var table = document.createElement('table');
var thead = '<thead><tr><th style="width:220px">Task</th>';
for (var d=1; d<=totalDays; d++) thead += '<th>' + d + '</th>';
thead += '</tr></thead>';
table.innerHTML = thead;
var tbody = document.createElement('tbody');
(data.rows || []).forEach(function(row) {{
  var tr = document.createElement('tr');
  var tdName = document.createElement('td');
  tdName.textContent = row.name;
  tr.appendChild(tdName);
  for (var d=1; d<=totalDays; d++) {{
    var td = document.createElement('td');
    if (d >= row.start && d <= row.end) {{
      var bar = document.createElement('div');
      bar.className = 'bar bar-' + (row.type || 'dev');
      bar.style.width = '100%';
      td.appendChild(bar);
    }}
    tr.appendChild(td);
  }}
  tbody.appendChild(tr);
}});
table.appendChild(tbody);
container.appendChild(table);
</script>
</body>
</html>"""


class TimelineView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self._view = QWebEngineView()
        layout.addWidget(self._view)
        self._view.setHtml(
            "<body style='background:#0f1420;color:#8a9bb0;padding:20px'>Load sprint to see timeline.</body>"
        )

    def render_gantt(self, sprint, tasks):
        total_days = (sprint.dev_days or 8) + (sprint.test_days or 2)
        rows = []
        day = 1
        for t in tasks:
            if t.task_type == "integration_test":
                continue
            dur = max(1, round(t.estimated_hrs / 8)) if t.estimated_hrs else 1
            rows.append({"name": t.title[:40], "start": day, "end": min(day + dur - 1, sprint.dev_days or 8), "type": "dev"})
            day = min(day + dur, sprint.dev_days or 8)

        integ_start = (sprint.dev_days or 8) - 1
        for t in tasks:
            if t.task_type != "integration_test":
                continue
            dur = max(1, round(t.estimated_hrs / 8)) if t.estimated_hrs else 1
            rows.append({"name": t.title[:40], "start": integ_start, "end": min(integ_start + dur - 1, total_days), "type": "integ"})
            integ_start += dur

        test_start = (sprint.dev_days or 8) + 1
        rows.append({"name": "Test Days", "start": test_start, "end": total_days, "type": "test"})

        data = {"total_days": total_days, "rows": rows}
        html = GANTT_HTML.format(content='<div class="gantt-container"></div>', data_json=json.dumps(data))
        self._view.setHtml(html)
