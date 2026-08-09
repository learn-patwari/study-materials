import datetime
from PyQt6.QtWidgets import QWidget, QScrollArea, QVBoxLayout, QSizePolicy
from PyQt6.QtCore import Qt, QRect
from PyQt6.QtGui import QPainter, QColor, QFont, QPen


# ── colour tokens ──────────────────────────────────────────────────────────
C_BG       = QColor("#0f1420")
C_PANEL    = QColor("#1a2133")
C_BORDER   = QColor("#2a3a55")
C_TEXT     = QColor("#e8ecf0")
C_MUTED    = QColor("#8a9bb0")
C_DEV      = QColor("#4a90d9")
C_SRS_BG   = QColor("#223355")
C_SRS_BDR  = QColor("#4a90d9")
C_INTEG    = QColor("#f0a030")
C_TEST     = QColor("#3ab06a")
C_ROW_ALT  = QColor("#131e30")

ROW_H   = 22   # px per row
COL_W   = 36   # px per day column
LABEL_W = 240  # px for the task-name column
HDR_H   = 28   # header row height


class _GanttCanvas(QWidget):
    """Pure-QPainter Gantt chart — no WebEngine required."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._rows = []
        self._total_days = 10
        self._sprint_start = ""
        self.setMinimumHeight(HDR_H + ROW_H * 3)

    def set_data(self, rows, total_days, sprint_start):
        self._rows = rows
        self._total_days = max(total_days, 1)
        self._sprint_start = sprint_start
        needed_w = LABEL_W + self._total_days * COL_W + 2
        needed_h = HDR_H + len(self._rows) * ROW_H + 2
        self.setMinimumSize(needed_w, needed_h)
        self.setFixedHeight(needed_h)
        self.update()

    def _day_label(self, day: int) -> str:
        try:
            base = datetime.date.fromisoformat(self._sprint_start[:10])
            dt = base + datetime.timedelta(days=day - 1)
            return f"{dt.month}/{dt.day}"
        except Exception:
            return str(day)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing, False)
        w = self.width()
        h = self.height()

        # Background
        p.fillRect(0, 0, w, h, C_BG)

        # ── header row ────────────────────────────────────────────────────
        p.fillRect(0, 0, LABEL_W, HDR_H, C_PANEL)
        p.setPen(C_BORDER)
        p.drawRect(0, 0, LABEL_W - 1, HDR_H - 1)

        hdr_font = QFont()
        hdr_font.setPixelSize(11)
        hdr_font.setBold(True)
        p.setFont(hdr_font)
        p.setPen(C_MUTED)
        p.drawText(QRect(6, 0, LABEL_W - 8, HDR_H), Qt.AlignmentFlag.AlignVCenter, "Task")

        for d in range(1, self._total_days + 1):
            x = LABEL_W + (d - 1) * COL_W
            p.fillRect(x, 0, COL_W, HDR_H, C_PANEL)
            p.setPen(C_BORDER)
            p.drawRect(x, 0, COL_W - 1, HDR_H - 1)
            p.setPen(C_MUTED)
            p.setFont(hdr_font)
            p.drawText(QRect(x, 0, COL_W, HDR_H), Qt.AlignmentFlag.AlignCenter, self._day_label(d))

        # ── data rows ─────────────────────────────────────────────────────
        row_font = QFont()
        row_font.setPixelSize(11)
        sub_font = QFont()
        sub_font.setPixelSize(11)

        for i, row in enumerate(self._rows):
            y = HDR_H + i * ROW_H
            kind = row.get("kind", "sub")
            row_bg = C_ROW_ALT if kind in ("srs", "test") else C_BG

            # Label cell
            p.fillRect(0, y, LABEL_W, ROW_H, row_bg)
            p.setPen(C_BORDER)
            p.drawRect(0, y, LABEL_W - 1, ROW_H - 1)

            label_color = C_DEV if kind == "srs" else C_MUTED if kind == "test" else C_TEXT
            f = QFont()
            f.setPixelSize(11)
            f.setBold(kind == "srs")
            p.setFont(f)
            p.setPen(label_color)
            indent = 4 if kind == "srs" else 20
            name = row.get("name", "")
            meta = row.get("meta", "")
            p.drawText(QRect(indent, y, LABEL_W - indent - 4, ROW_H), Qt.AlignmentFlag.AlignVCenter, name)

            if meta:
                mf = QFont(); mf.setPixelSize(10)
                p.setFont(mf)
                p.setPen(C_MUTED)
                # Draw meta right-aligned inside label cell
                p.drawText(QRect(4, y, LABEL_W - 8, ROW_H), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignRight, meta)

            # Day cells + bar
            bar_color = {"dev": C_DEV, "srs": C_SRS_BG, "integ": C_INTEG, "test": C_TEST}.get(row.get("type", "dev"), C_DEV)
            bar_start = row.get("start", 0)
            bar_end   = row.get("end", 0)

            for d in range(1, self._total_days + 1):
                x = LABEL_W + (d - 1) * COL_W
                p.fillRect(x, y, COL_W, ROW_H, row_bg)
                p.setPen(C_BORDER)
                p.drawRect(x, y, COL_W - 1, ROW_H - 1)

                if bar_start <= d <= bar_end:
                    pad = 3
                    bar_rect = QRect(x + pad, y + pad, COL_W - pad * 2, ROW_H - pad * 2)
                    p.fillRect(bar_rect, bar_color)
                    if kind == "srs":
                        p.setPen(C_SRS_BDR)
                        p.drawRect(bar_rect)

        p.end()


class TimelineView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(False)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._scroll.setStyleSheet("QScrollArea { border: none; background: #0f1420; }")

        self._canvas = _GanttCanvas()
        self._canvas.set_data([], 10, "")
        self._scroll.setWidget(self._canvas)
        layout.addWidget(self._scroll)

    def render_gantt(self, sprint, groups):
        total_days = (sprint.dev_days or 8) + (sprint.test_days or 2)
        sprint_start = sprint.start_date or ""
        rows = []

        if groups and isinstance(groups[0], dict) and "ticket" in groups[0]:
            day_cursor = 1
            for group in groups:
                ticket = group["ticket"]
                tasks = group["tasks"]
                if not tasks:
                    continue
                grp_hrs = sum(t.estimated_hrs or 0 for t in tasks)
                grp_start = day_cursor
                grp_end = day_cursor
                sub_rows = []
                for t in tasks:
                    if t.task_type == "integration_test":
                        continue
                    dur = max(1, round((t.estimated_hrs or 4) / 8))
                    t_end = min(day_cursor + dur - 1, sprint.dev_days or 8)
                    sub_rows.append({
                        "kind": "sub", "name": t.title[:55],
                        "meta": f"{t.estimated_hrs or 0:.0f}h",
                        "start": day_cursor, "end": t_end, "type": "dev",
                    })
                    grp_end = max(grp_end, t_end)
                    day_cursor = min(t_end + 1, sprint.dev_days or 8)

                rows.append({
                    "kind": "srs",
                    "name": f"{ticket.jira_key} — {ticket.title[:38]}",
                    "meta": f"{grp_hrs:.0f}h",
                    "start": grp_start, "end": grp_end, "type": "srs",
                })
                rows.extend(sub_rows)
        else:
            day_cursor = 1
            for t in (groups or []):
                if hasattr(t, "task_type") and t.task_type == "integration_test":
                    continue
                dur = max(1, round((t.estimated_hrs or 4) / 8))
                end = min(day_cursor + dur - 1, sprint.dev_days or 8)
                rows.append({"kind": "sub", "name": t.title[:55], "meta": "", "start": day_cursor, "end": end, "type": "dev"})
                day_cursor = min(end + 1, sprint.dev_days or 8)

        # Integration test rows
        integ_cursor = sprint.dev_days or 8
        for group in (groups if groups and isinstance(groups[0], dict) else []):
            for t in group.get("tasks", []):
                if t.task_type != "integration_test":
                    continue
                dur = max(1, round((t.estimated_hrs or 2) / 8))
                t_end = min(integ_cursor + dur, total_days)
                rows.append({"kind": "sub", "name": f"  {t.title[:50]}", "meta": f"{t.estimated_hrs}h", "start": integ_cursor, "end": t_end, "type": "integ"})
                integ_cursor = t_end

        test_start = (sprint.dev_days or 8) + 1
        rows.append({"kind": "test", "name": "Test Days", "meta": f"{sprint.test_days}d", "start": test_start, "end": total_days, "type": "test"})

        self._canvas.set_data(rows, total_days, sprint_start)
