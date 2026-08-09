from PyQt6.QtWidgets import QWidget, QVBoxLayout
import json
import datetime


GANTT_HTML = """<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ background:#0f1420; color:#e8ecf0; margin:0; padding:12px; font-family:sans-serif; font-size:12px; }}
  .legend {{ margin-bottom:10px; }}
  .legend-item {{ display:inline-block; margin-right:14px; }}
  .dot {{ width:10px;height:10px;border-radius:2px;display:inline-block;margin-right:4px;vertical-align:middle; }}
  .gantt-container {{ overflow-x:auto; }}
  table {{ border-collapse:collapse; min-width:100%; }}
  th {{ background:#1a2133; padding:5px 6px; text-align:center; border:1px solid #2a3a55; color:#8a9bb0; white-space:nowrap; }}
  th.label-col {{ text-align:left; width:240px; }}
  td {{ padding:2px 4px; border:1px solid #1a2133; }}
  td.label-col {{ white-space:nowrap; overflow:hidden; max-width:240px; }}
  .bar {{ height:14px; border-radius:3px; display:block; width:100%; }}
  .bar-srs   {{ background:#223355; border:1px solid #4a90d9; }}
  .bar-dev   {{ background:#4a90d9; }}
  .bar-integ {{ background:#f0a030; }}
  .bar-test  {{ background:#3ab06a; }}
  .row-srs td {{ background:#131e30; font-weight:bold; }}
  .row-sub td {{ background:#0f1420; }}
  .row-test td {{ background:#0f1420; }}
  .lbl-srs {{ color:#7ab0f0; font-weight:bold; }}
  .lbl-sub {{ color:#e8ecf0; padding-left:16px; }}
  .lbl-meta {{ color:#8a9bb0; font-size:10px; display:inline; margin-left:6px; }}
</style>
</head>
<body>
<div class="legend">
  <span class="legend-item"><span class="dot" style="background:#4a90d9"></span>Dev task</span>
  <span class="legend-item"><span class="dot" style="background:#f0a030"></span>Integration test</span>
  <span class="legend-item"><span class="dot" style="background:#3ab06a"></span>Test days</span>
</div>
<div class="gantt-container">
<table id="gantt"></table>
</div>
<script>
var data = {data_json};
var totalDays = data.total_days || 10;
var rows = data.rows || [];
var sprintStart = data.sprint_start ? new Date(data.sprint_start) : null;

function dayLabel(d) {{
  if (!sprintStart) return d;
  var dt = new Date(sprintStart);
  dt.setDate(dt.getDate() + d - 1);
  return (dt.getMonth()+1)+'/'+dt.getDate();
}}

var table = document.getElementById('gantt');
// Header
var hrow = '<tr><th class="label-col">Task</th>';
for (var d=1; d<=totalDays; d++) hrow += '<th>' + dayLabel(d) + '</th>';
hrow += '</tr>';
table.innerHTML = '<thead>' + hrow + '</thead><tbody>';

var tbody = document.createElement('tbody');
rows.forEach(function(row) {{
  var tr = document.createElement('tr');
  tr.className = row.kind === 'srs' ? 'row-srs' : (row.kind === 'test' ? 'row-test' : 'row-sub');

  var tdLabel = document.createElement('td');
  tdLabel.className = 'label-col';
  var span = document.createElement('span');
  span.className = row.kind === 'srs' ? 'lbl-srs' : 'lbl-sub';
  span.textContent = row.name;
  tdLabel.appendChild(span);
  if (row.meta) {{
    var m = document.createElement('span');
    m.className = 'lbl-meta';
    m.textContent = row.meta;
    tdLabel.appendChild(m);
  }}
  tr.appendChild(tdLabel);

  for (var d=1; d<=totalDays; d++) {{
    var td = document.createElement('td');
    if (d >= row.start && d <= row.end) {{
      var bar = document.createElement('div');
      bar.className = 'bar bar-' + (row.type || 'dev');
      td.appendChild(bar);
    }}
    tr.appendChild(td);
  }}
  tbody.appendChild(tr);
}});
table.appendChild(tbody);
</script>
</body>
</html>"""


def _date_to_day(base_date: str, target_date: str) -> int:
    """Return 1-indexed sprint day from ISO date strings."""
    try:
        base = datetime.date.fromisoformat(base_date[:10])
        target = datetime.date.fromisoformat(target_date[:10])
        return max(1, (target - base).days + 1)
    except Exception:
        return 1


class TimelineView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        from PyQt6.QtWebEngineWidgets import QWebEngineView
        self._view = QWebEngineView()
        layout.addWidget(self._view)
        self._view.setHtml(
            "<body style='background:#0f1420;color:#8a9bb0;padding:20px'>Load sprint to see timeline.</body>"
        )

    def render_gantt(self, sprint, groups):
        """
        groups: list of {ticket, tasks} dicts (from sprint_panel).
                tasks are Task objects with start_date / end_date set.
        Also accepts a flat list of Task objects for backwards compat.
        """
        total_days = (sprint.dev_days or 8) + (sprint.test_days or 2)
        sprint_start = sprint.start_date or ""
        rows = []

        # Handle both grouped and flat input
        if groups and isinstance(groups[0], dict) and "ticket" in groups[0]:
            # Grouped by SRS ticket
            day_cursor = 1
            for group in groups:
                ticket = group["ticket"]
                tasks = group["tasks"]
                if not tasks:
                    continue

                grp_hrs = sum(t.estimated_hrs or 0 for t in tasks)
                grp_start = day_cursor
                grp_end = day_cursor

                # SRS header row
                srs_row_start = day_cursor
                sub_rows = []
                for t in tasks:
                    if t.task_type == "integration_test":
                        continue
                    dur = max(1, round((t.estimated_hrs or 4) / 8))
                    t_end = min(day_cursor + dur - 1, sprint.dev_days or 8)
                    sub_rows.append({
                        "kind": "sub",
                        "name": t.title[:55],
                        "meta": f"{t.estimated_hrs or 0:.0f}h · {t.status}",
                        "start": day_cursor,
                        "end": t_end,
                        "type": "dev",
                    })
                    grp_end = max(grp_end, t_end)
                    day_cursor = min(t_end + 1, sprint.dev_days or 8)

                rows.append({
                    "kind": "srs",
                    "name": f"{ticket.jira_key} — {ticket.title[:40]}",
                    "meta": f"{grp_hrs:.0f}h",
                    "start": srs_row_start,
                    "end": grp_end,
                    "type": "srs",
                })
                rows.extend(sub_rows)
        else:
            # Flat list fallback
            day_cursor = 1
            for t in (groups or []):
                if hasattr(t, "task_type") and t.task_type == "integration_test":
                    continue
                dur = max(1, round((t.estimated_hrs or 4) / 8))
                end = min(day_cursor + dur - 1, sprint.dev_days or 8)
                rows.append({"kind": "sub", "name": t.title[:55], "meta": "", "start": day_cursor, "end": end, "type": "dev"})
                day_cursor = min(end + 1, sprint.dev_days or 8)

        # Integration test rows
        integ_cursor = (sprint.dev_days or 8)
        for group in (groups if groups and isinstance(groups[0], dict) else []):
            for t in group.get("tasks", []):
                if t.task_type != "integration_test":
                    continue
                dur = max(1, round((t.estimated_hrs or 2) / 8))
                t_end = min(integ_cursor + dur, total_days)
                rows.append({"kind": "sub", "name": f"  {t.title[:50]}", "meta": f"{t.estimated_hrs}h", "start": integ_cursor, "end": t_end, "type": "integ"})
                integ_cursor = t_end

        # Test days bar
        test_start = (sprint.dev_days or 8) + 1
        rows.append({"kind": "test", "name": "Test Days", "meta": f"{sprint.test_days}d", "start": test_start, "end": total_days, "type": "test"})

        data = {
            "total_days": total_days,
            "sprint_start": sprint_start,
            "rows": rows,
        }
        html = GANTT_HTML.format(data_json=json.dumps(data))
        self._view.setHtml(html)
