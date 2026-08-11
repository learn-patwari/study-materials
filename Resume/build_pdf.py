"""
PDF builder matching the base resume design exactly.
Usage: python build_pdf_base_design.py <SLUG>
"""
import re, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
from reportlab.lib import colors

slug = sys.argv[1] if len(sys.argv) > 1 else 'LamResearch'
BASE = "/home/user/study-materials/Resume/Tailored"
MD   = f"{BASE}/AkshayPatwari_8years_{slug}.md"
OUT  = f"{BASE}/AkshayPatwari_8years_{slug}.pdf"

doc = SimpleDocTemplate(OUT, pagesize=A4,
      leftMargin=18*mm, rightMargin=18*mm, topMargin=14*mm, bottomMargin=14*mm)

BLK = colors.black

s_name    = ParagraphStyle('name',    fontName='Helvetica-Bold', fontSize=22, leading=26,
                            alignment=TA_CENTER, spaceAfter=2)
s_subtitle= ParagraphStyle('subtitle',fontName='Helvetica',      fontSize=10, leading=13,
                            alignment=TA_CENTER, spaceAfter=1)
s_contact = ParagraphStyle('contact', fontName='Helvetica-Bold', fontSize=10, leading=13,
                            alignment=TA_CENTER, spaceAfter=1)
s_links   = ParagraphStyle('links',   fontName='Helvetica',      fontSize=9,  leading=12,
                            alignment=TA_CENTER, spaceAfter=4)
s_sec     = ParagraphStyle('sec',     fontName='Helvetica-Bold', fontSize=11, leading=14,
                            alignment=TA_LEFT,   spaceBefore=8, spaceAfter=1)
s_body    = ParagraphStyle('body',    fontName='Helvetica',      fontSize=9.5, leading=13,
                            alignment=TA_JUSTIFY, spaceAfter=3)
s_org     = ParagraphStyle('org',     fontName='Helvetica-Bold', fontSize=10, leading=13,
                            alignment=TA_LEFT,   spaceBefore=5, spaceAfter=0)
s_date    = ParagraphStyle('date',    fontName='Helvetica',      fontSize=9,  leading=12,
                            alignment=TA_LEFT,   spaceAfter=2)
s_sub     = ParagraphStyle('sub',     fontName='Helvetica-Bold', fontSize=9.5, leading=13,
                            alignment=TA_LEFT,   spaceBefore=3, spaceAfter=1)
s_bullet  = ParagraphStyle('bullet',  fontName='Helvetica',      fontSize=9.5, leading=13,
                            alignment=TA_JUSTIFY,
                            leftIndent=16, firstLineIndent=-11, spaceAfter=3)

def bold(text):
    """Convert **x** to ReportLab <b>x</b>. Works across the full string."""
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', text, flags=re.DOTALL)

def hr():
    return HRFlowable(width='100%', thickness=0.75, color=BLK,
                      spaceBefore=1, spaceAfter=4)

# ── Load and strip HTML comment ──────────────────────────────────────────────
with open(MD, encoding='utf-8') as f:
    raw = f.read()
raw = re.sub(r'<!--.*?-->', '', raw, flags=re.DOTALL).strip()
lines = raw.splitlines()

# ── Pre-pass: collect logical blocks ────────────────────────────────────────
# Each block is {'type': ..., 'text': ...}
blocks = []
i = 0

def join_continuation(lines, start):
    """Collect lines that continue a paragraph/bullet (not blank, not heading, not new bullet)."""
    parts = []
    j = start
    while j < len(lines):
        s = lines[j].strip()
        if s == '' or s.startswith('#') or s == '---' or s.startswith('- ') or s.startswith('* '):
            break
        parts.append(s)
        j += 1
    return ' '.join(parts), j

while i < len(lines):
    raw_line = lines[i]
    s = raw_line.strip()

    if s == '':
        i += 1; continue

    if s == '---':
        blocks.append({'type': 'hr'})
        i += 1; continue

    if s.startswith('# ') and not s.startswith('## '):
        blocks.append({'type': 'name', 'text': s[2:].strip()})
        i += 1; continue

    if s.startswith('## '):
        blocks.append({'type': 'section', 'text': s[3:].strip()})
        i += 1; continue

    if s.startswith('### '):
        blocks.append({'type': 'org', 'text': s[4:].strip()})
        i += 1; continue

    # Italic date line
    if re.match(r'^\*[^*].+[^*]\*$', s) and re.search(r'20\d\d', s):
        blocks.append({'type': 'date', 'text': s.strip('*')})
        i += 1; continue

    # Bold-only subtitle (platform name)
    if s.startswith('**') and s.endswith('**') and '|' not in s and '+91' not in s \
       and 'Bengaluru' not in s and len(s) > 4:
        blocks.append({'type': 'sub', 'text': re.sub(r'\*\*', '', s)})
        i += 1; continue

    # Title+location line: **Role** · Bengaluru, India
    if re.match(r'^\*\*.+\*\*\s*·', s):
        role = re.sub(r'\*\*', '', s.split('·')[0]).strip()
        blocks.append({'type': 'subtitle', 'text': role.upper()})
        # Next line should be phone/email — combine with Bengaluru
        i += 1
        if i < len(lines):
            next_s = lines[i].strip()
            if '+91' in next_s:
                # Extract location from original split
                loc_part = s.split('·')[1].strip() if '·' in s else 'Bengaluru, India'
                blocks.append({'type': 'contact', 'text': f"{loc_part} | {next_s}"})
                i += 1
        continue

    # Phone/email standalone (if not consumed above)
    if '+91' in s and not s.startswith('#'):
        blocks.append({'type': 'contact', 'text': s})
        i += 1; continue

    # Links line
    if 'LinkedIn:' in s or ('linkedin.com' in s.lower() and 'Portfolio:' in s):
        blocks.append({'type': 'links', 'text': s})
        i += 1; continue

    # Bullet
    if s.startswith('- '):
        text, i = join_continuation(lines, i)
        # join_continuation starts from i and doesn't consume the first '- '
        # Actually let's handle it: first line is s[2:], then continue
        # Re-do: start fresh
        first = s[2:]
        j = i + 1
        cont_parts = [first]
        while j < len(lines):
            ns = lines[j].strip()
            if ns == '' or ns.startswith('#') or ns == '---' or ns.startswith('- '):
                break
            cont_parts.append(ns)
            j += 1
        blocks.append({'type': 'bullet', 'text': ' '.join(cont_parts)})
        i = j
        continue

    # Body paragraph — collect continuation lines
    body_parts = [s]
    j = i + 1
    while j < len(lines):
        ns = lines[j].strip()
        if ns == '' or ns.startswith('#') or ns == '---' or ns.startswith('- '):
            break
        body_parts.append(ns)
        j += 1
    blocks.append({'type': 'body', 'text': ' '.join(body_parts)})
    i = j

# ── Render blocks ────────────────────────────────────────────────────────────
story = []
prev_type = None

for blk in blocks:
    t   = blk['type']
    txt = blk.get('text', '')

    if t == 'name':
        story.append(Paragraph(txt, s_name))
    elif t == 'subtitle':
        story.append(Paragraph(txt, s_subtitle))
    elif t == 'contact':
        story.append(Paragraph(f'<b>{txt}</b>', s_contact))
    elif t == 'links':
        story.append(Paragraph(txt, s_links))
    elif t == 'hr':
        pass  # skip md hrs
    elif t == 'section':
        story.append(Paragraph(txt, s_sec))
        story.append(hr())
    elif t == 'org':
        story.append(Paragraph(bold(txt), s_org))
    elif t == 'date':
        story.append(Paragraph(txt, s_date))
    elif t == 'sub':
        story.append(Paragraph(bold(txt), s_sub))
    elif t == 'bullet':
        story.append(Paragraph(u'• ' + bold(txt), s_bullet))
    elif t == 'body':
        story.append(Paragraph(bold(txt), s_body))

    prev_type = t

doc.build(story)
print(f"Written: {OUT}")
