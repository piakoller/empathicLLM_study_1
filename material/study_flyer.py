"""study_flyer.py — build the recruitment poster and the tri-fold A4 flyer.

    python study_flyer.py

Writes, next to this file:
    Poster_A3.pdf         for the waiting room; QR code to scan with a phone
    Flyer_A4.pdf          A4 landscape, 2 pages, 3 columns (tri-fold / Wickelfalz)

Everything printed comes from CONFIG below. Change a value there and re-run;
nothing is typed into the layout by hand. A field still holding its placeholder
is printed in red with a warning on the console, so an unfilled poster cannot
be sent to the printer unnoticed.

Logos
-----
Put the official files from the two corporate-design portals next to this
script and name them in CONFIG. SVG is best for print; PNG at 600 dpi or more
also works. Until a file is there, a dashed box with the institution's name is
printed in its place, so the gap is visible rather than silently empty.

Both institutions publish rules for their mark — minimum size, clear space
around it, which version may sit on a coloured ground. That is why the logo
strip here is white and generously spaced: it keeps the marks on white, at a
size well above the usual minimum, whatever their guidelines turn out to say.
Check the current version of both guidelines before printing a run.

Printing the flyer
------------------
Duplex, flip on the LONG edge, A4 landscape. Fold into three panels (Wickelfalz / Z-Falz):
Sheet 1: [Innenklappe (Panel 5) | Rückseite/Kontakt (Panel 6) | Titelseite (Panel 1)]
Sheet 2: [Innenseite Links (Panel 2) | Innenseite Mitte (Panel 3) | Innenseite Rechts (Panel 4)]
Do one test print before the print run.

The accent colour is the app's own (#0097a7, from .streamlit/config.toml), so
the page a patient reaches after scanning looks like the poster they scanned.
"""

from __future__ import annotations

import base64
import io
import mimetypes
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent

# --------------------------------------------------------------------------
# Everything that appears on the printed material.
# --------------------------------------------------------------------------
CONFIG = {
    # The address the QR code points to. Must be reachable from a phone on
    # mobile data — a link that only resolves inside the hospital network will
    # fail in the waiting room.
    "url": "https://empathicllmstudy1.streamlit.app/",

    "clinic": "Universitätsklinik für Nuklearmedizin, Inselspital Bern",              # e.g. Universitätsklinik für Nuklearmedizin, Inselspital Bern
    "study_lead": "Pia Koller",
    "contact_email": "pia.koller@unibe.ch",
    "contact_phone": "",                          # optional, leave empty to omit
    # One complete sentence about the ethics review, printed verbatim — or
    # nothing at all when this is empty. Free text and empty by default: a study
    # without an approval must not carry a line claiming one, and a project the
    # committee declared out of scope needs different wording than an approved
    # one. Examples:
    #   "Bewilligt durch die Kantonale Ethikkommission Bern — KEK-Nr. 2026-XXXXX"
    #   "Die Kantonale Ethikkommission Bern hat das Projekt als nicht dem "
    #   "Humanforschungsgesetz unterstellt beurteilt (Ref. …, TT.MM.JJJJ)."
    "ethics_line": "",

    # Official logo files, from the two corporate-design portals. Relative to
    # this script. Leave empty to print the placeholder box instead.
    # Raster files are trimmed to the mark itself before placing, so that empty
    # canvas around a logo does not shrink it next to the other one.
    "logo_1": "Logo_Universität_Bern.svg.webp",
    "logo_1_name": "Universität Bern",
    "logo_1_scale": 1.0,           # stacked mark: needs the full height
    "logo_2": "Inselspital.svg.webp",
    "logo_2_name": "Inselspital",
    "logo_2_scale": 0.60,          # wide mark: shorter, so both read as equal weight
    "logo_height_mm": 22.0,        # poster; the brochure scales it down

    # How the answers are stored, in one sentence a patient can check. Adjust it
    # to what is actually true of your deployment before printing.
    "storage_sentence": "Die Antworten werden auf einem zugriffsgeschützten "
                        "Server gespeichert und nur von der Studienleitung ausgewertet.",
}

# The two institutional colours, sampled from the supplied logo files:
#   #e3003a  Universität Bern, red
#   #00956c  Inselspital, green (the emblem)
#   #667079  Inselspital, blue-grey (the wordmark)
UNIBE_RED = "#e3003a"
INSEL_GREEN = "#00956c"
INSEL_BLUE = "#667079"

# Background of the coloured field on poster and flyer cover. One of:
#   "teal"      the app's own colour, as before — the page a patient reaches
#               after scanning looks like the paper they scanned
#   "red-green" Uni Bern red to Inselspital green
#   "red-blue"  Uni Bern red to the Inselspital blue-grey
HERO_BACKGROUND = "red-blue"

_HERO = {
    "teal": "#0097a7",
    "red-green": f"linear-gradient(145deg, {UNIBE_RED} 0%, #8f4a52 52%, {INSEL_GREEN} 100%)",
    "red-blue": f"linear-gradient(145deg, {UNIBE_RED} 0%, #a4385a 48%, {INSEL_BLUE} 100%)",
}
HERO_BG = _HERO[HERO_BACKGROUND]

ACCENT = "#0097a7"
ACCENT_DEEP = "#00707c"
INK = "#12232a"
INK2 = "#4a5b61"
INK3 = "#7c8b90"
PAPER = "#ffffff"
TINT = "#eef6f7"
WARN = "#c2361b"

PLACEHOLDER = re.compile(r"«[^»]*»")


def qr_svg(data: str, px: int = 1000, dark: str = INK) -> str:
    """The QR as an inline <svg>, so it stays sharp at any print size."""
    import qrcode
    from qrcode.image.svg import SvgPathImage

    img = qrcode.make(data, image_factory=SvgPathImage, box_size=20, border=2,
                      error_correction=qrcode.constants.ERROR_CORRECT_M)
    buf = io.BytesIO()
    img.save(buf)
    svg = buf.getvalue().decode("utf-8")
    svg = svg[svg.index("<svg"):]
    svg = re.sub(r'width="[^"]*"', f'width="{px}"', svg, count=1)
    svg = re.sub(r'height="[^"]*"', f'height="{px}"', svg, count=1)
    return svg.replace("<path ", f'<path fill="{dark}" ')


def _trimmed_png(p: Path) -> str | None:
    """Crop a raster logo to the mark itself and return it as a data URI.

    The two files supplied sit on differently sized canvases — one is a tight
    1280x405 crop, the other a 1280x1280 square with the mark in one corner.
    Placed at the same height they would look nothing like the same size, so
    the surrounding empty canvas is removed first. Only canvas is removed; the
    mark is not altered, and the clear space around it is added back in CSS.
    """
    try:
        from PIL import Image, ImageChops
    except ImportError:
        return None
    im = Image.open(p)
    im = im.convert("RGBA")
    alpha = im.getchannel("A")
    if alpha.getextrema()[0] < 250:          # real transparency: trim on it
        bbox = alpha.getbbox()
    else:                                     # opaque: trim the white margin
        rgb = im.convert("RGB")
        bg = Image.new("RGB", rgb.size, (255, 255, 255))
        bbox = ImageChops.difference(rgb, bg).convert("L").point(
            lambda v: 255 if v > 8 else 0).getbbox()
    if bbox:
        im = im.crop(bbox)
    buf = io.BytesIO()
    im.save(buf, format="PNG")
    return "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode("ascii")


def logo(path_value: str, name: str, height_mm: float) -> str:
    """The official file if it is there, a visible gap if it is not.

    No attempt is made to draw either mark. An institution's logo is its own
    file; an approximation of it is a different thing wearing its name.
    """
    p = (HERE / path_value) if path_value else None
    if p and p.is_file():
        if p.suffix.lower() == ".svg":
            src = ("data:image/svg+xml;base64,"
                   + base64.b64encode(p.read_bytes()).decode("ascii"))
        else:
            src = _trimmed_png(p)
            if src is None:                   # no Pillow: place the file as it is
                mime = mimetypes.guess_type(p.name)[0] or "image/png"
                src = (f"data:{mime};base64,"
                       + base64.b64encode(p.read_bytes()).decode("ascii"))
        return (f'<img class="logo" alt="{name}" '
                f'style="height:{height_mm}mm" src="{src}">')
    return (f'<div class="logo-missing" style="height:{height_mm}mm">'
            f'<span>Logo {name}<br><em>Datei fehlt</em></span></div>')


# Simple line symbols, drawn here rather than loaded: a camera, a person, a
# pointing hand, a tick. Generic pictograms, no brand marks.
ICON = {
    "scan": '<path d="M3 8V5a2 2 0 0 1 2-2h3M16 3h3a2 2 0 0 1 2 2v3M21 16v3a2 2 0 0 1-2 2h-3'
            'M8 21H5a2 2 0 0 1-2-2v-3"/><circle cx="12" cy="12" r="3.2"/>',
    "person": '<circle cx="12" cy="8" r="3.4"/><path d="M5.5 20a6.5 6.5 0 0 1 13 0"/>',
    "tap": '<path d="M9 11V6a1.8 1.8 0 0 1 3.6 0v6"/>'
           '<path d="M12.6 12V9.6a1.7 1.7 0 0 1 3.4 0V12"/>'
           '<path d="M16 11.4a1.7 1.7 0 0 1 3.4 0V15a6 6 0 0 1-6 6h-1.6a5 5 0 0 1-3.8-1.8L5 15.4'
           'a1.8 1.8 0 0 1 2.6-2.4L9 14.4"/>',
    "check": '<circle cx="12" cy="12" r="9"/><path d="M8 12.4l2.7 2.6L16 9.6"/>',
    "clock": '<circle cx="12" cy="12" r="9"/><path d="M12 7v5.3l3.4 2"/>',
    "lock": '<rect x="4.5" y="10.5" width="15" height="10" rx="2"/>'
            '<path d="M8.2 10.5V7.8a3.8 3.8 0 0 1 7.6 0v2.7"/>',
    "shield": '<path d="M12 3l7 2.8v5.4c0 4.3-2.9 8-7 9.8-4.1-1.8-7-5.5-7-9.8V5.8z"/>',
}


def icon(name: str, mm: float = 6.0) -> str:
    return (f'<svg class="ico" viewBox="0 0 24 24" style="width:{mm}mm;height:{mm}mm" '
            f'fill="none" stroke="currentColor" stroke-width="1.8" '
            f'stroke-linecap="round" stroke-linejoin="round">{ICON[name]}</svg>')


def mark(value: str) -> str:
    """Placeholders are printed, but in red — an unfilled field must be obvious."""
    if PLACEHOLDER.search(value):
        return (f'<span style="color:{WARN};font-weight:700;background:#fff;'
                f'padding:0 1.2mm;border-radius:1mm;white-space:nowrap">{value}</span>')
    return value


def pretty_url(url: str) -> str:
    return re.sub(r"^https?://", "", url).rstrip("/")


def badges(items, cls: str = "") -> str:
    """Time, anonymity, no effect on treatment — as marks, not as a sentence.

    Printed with the same line pictograms as everything else rather than with
    emoji: an emoji in a print PDF renders in whatever colour font the printer
    happens to substitute, which on a clinical document looks like an accident.
    """
    cells = "".join(
        f'<div class="badge">{icon(ic, 4.6)}<span>{txt}</span></div>' for ic, txt in items)
    return f'<div class="badges {cls}">{cells}</div>'


def phone(qr: str, screen_note: str) -> str:
    """A phone outline with the QR on its screen — the instruction as a picture."""
    return f"""<div class="phone">
      <div class="phone-notch"></div>
      <div class="phone-screen">
        <div class="phone-qr">{qr}</div>
        <div class="phone-note">{screen_note}</div>
      </div>
    </div>"""


CSS = f"""
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{ font-family: Arial, 'Liberation Sans', Helvetica, sans-serif;
        color: {INK}; background: {PAPER}; -webkit-print-color-adjust: exact;
        print-color-adjust: exact; }}
.page {{ position: relative; overflow: hidden; page-break-after: always; background: {PAPER}; }}
.eyebrow {{ letter-spacing: .1em; text-transform: uppercase; font-weight: 700; }}
.muted {{ color: {INK2}; }}
.faint {{ color: {INK3}; }}

.logos {{ display: flex; align-items: center; justify-content: space-between; width: 100%; }}
.logo {{ width: auto; display: block; }}
.logo-missing {{ display: flex; align-items: center; justify-content: center;
    padding: 0 6mm; border: .5mm dashed {WARN}; border-radius: 1.5mm;
    color: {WARN}; font-size: 8pt; line-height: 1.25; text-align: center; }}
.logo-missing em {{ font-style: normal; font-weight: 700; }}

/* phone */
.phone {{ background: #fff; border: 1.6mm solid {INK}; border-radius: 7mm;
          padding: 4mm 3.5mm 5mm; position: relative; }}
.phone-notch {{ width: 22%; height: 1.6mm; background: {INK}; border-radius: 1mm;
                margin: 0 auto 3.5mm; }}
.phone-screen {{ background: {TINT}; border-radius: 3.5mm; padding: 4mm; text-align: center; }}
.phone-qr svg {{ width: 100%; height: auto; display: block; }}
.phone-note {{ font-weight: 700; color: {ACCENT_DEEP}; }}

ol.steps {{ list-style: none; counter-reset: s; }}
ol.steps li {{ counter-increment: s; position: relative; }}
.badges {{ display: flex; gap: 3mm; flex-wrap: wrap; }}
.badge {{ display: flex; align-items: center; gap: 2mm; padding: 2mm 3.5mm;
          border-radius: 10mm; background: {TINT}; color: {INK};
          font-size: 8pt; font-weight: 700; line-height: 1.15; }}
.badge svg {{ flex: none; color: {ACCENT_DEEP}; }}
ol.steps li::before {{
    content: counter(s); position: absolute; left: 0; top: 0;
    display: flex; align-items: center; justify-content: center;
    border-radius: 50%; background: {ACCENT}; color: #fff; font-weight: 700; }}
"""


# ---------------------------------------------------------------- poster ---
def poster_html(c: dict) -> str:
    url, h = c["url"], c["logo_height_mm"]
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<style>{CSS}
@page {{ size: 297mm 420mm; margin: 0; }}
.page {{ width: 297mm; height: 420mm; display: flex; flex-direction: column; }}

.top {{ padding: 14mm 22mm 12mm; display: flex; justify-content: space-between;
        align-items: center; }}

.hero {{ flex: 1; background: {HERO_BG}; color: #fff; padding: 18mm 22mm 20mm;
         display: flex; flex-direction: column; justify-content: center; }}
.hero-row {{ display: flex; gap: 14mm; align-items: center; margin-top: 12mm; }}
.hero-text {{ flex: 1; }}
.hero .eyebrow {{ font-size: 13pt; color: #bdf0f5; }}
h1 {{ font-size: 46pt; line-height: 1.08; letter-spacing: -.02em; margin-top: 5mm; }}
h1 em {{ font-style: normal; color: #ffe9a8; }}
.sub {{ font-size: 20pt; line-height: 1.42; color: #e8fbfd; }}
.badges.on-colour {{ margin-top: 9mm; gap: 3mm; flex-direction: column;
          align-items: flex-start; }}
.badges.on-colour .badge {{ background: rgba(255,255,255,.93); font-size: 13pt;
          padding: 3.2mm 6mm; gap: 3.5mm; }}
.badges.on-colour .badge svg {{ width: 6.2mm !important; height: 6.2mm !important;
          stroke-width: 1.6; }}
.quote {{ margin-top: 11mm; padding: 7mm 8mm 6.5mm 16mm; position: relative;
          background: #fff; border-radius: 3mm; border-left: 2.4mm solid {ACCENT_DEEP};
          box-shadow: 0 1.2mm 3mm rgba(0,0,0,.14);
          font-size: 19pt; line-height: 1.3; font-style: italic;
          font-weight: 700; color: {INK}; }}
.quote::before {{ content: "“"; position: absolute; left: 5mm; top: 2.5mm;
          font-size: 44pt; font-style: normal; line-height: 1; color: {ACCENT};
          font-weight: 700; }}
.quote .cap {{ font-size: 11.5pt; font-style: normal; font-weight: 400;
          color: {INK2}; margin-top: 3mm; }}
.pill {{ background: rgba(255,255,255,.17); border: .4mm solid rgba(255,255,255,.5);
         border-radius: 14mm; padding: 3mm 7mm; font-size: 14pt; font-weight: 700; }}

.phone {{ width: 96mm; flex: none;
          box-shadow: 0 0 0 3mm rgba(255,255,255,.35), 0 3mm 9mm rgba(0,0,0,.22); }}
.to-qr {{ display: flex; align-items: center; gap: 3mm; margin-top: 9mm;
          font-size: 16pt; font-weight: 700; color: #ffe9a8; }}
.to-qr svg {{ width: 14mm; height: 7mm; flex: none; }}
.phone-qr svg {{ width: 78mm; margin: 0 auto; }}
.phone-note {{ font-size: 13pt; margin-top: 3.5mm; line-height: 1.3; }}

.bottom {{ padding: 13mm 22mm 14mm; }}
ul.isteps {{ display: flex; gap: 12mm; margin: 0; list-style: none; }}
ul.isteps li {{ display: flex; gap: 4mm; align-items: flex-start; }}
ul.isteps .ico-wrap {{ flex: none; border-radius: 50%; background: {ACCENT}; color: #fff;
        display: flex; align-items: center; justify-content: center; }}
ul.isteps li {{ flex: 1; margin: 0; }}
ul.isteps .ico-wrap {{ width: 12mm; height: 12mm; }}
ul.isteps .txt {{ font-size: 14.5pt; line-height: 1.38; padding-top: 1.6mm; }}
.urlline {{ margin-top: 10mm; font-size: 16pt; }}
.foot {{ margin-top: 9mm; padding-top: 6mm; border-top: .4mm solid #d8e0e2;
         font-size: 11pt; line-height: 1.5; display: flex; justify-content: space-between; gap: 10mm; }}
</style></head><body>
<div class="page">

  <div class="top">
    <div class="logos">
      {logo(c['logo_1'], c['logo_1_name'], h * c['logo_1_scale'])}
      {logo(c['logo_2'], c['logo_2_name'], h * c['logo_2_scale'])}
    </div>
  </div>

  <div class="hero">
    <div class="eyebrow">Kurze Befragung · PSMA-Therapie</div>
    <h1>Helfen Sie mit,<br>die Zukunft des<br><em>Arztgesprächs zu gestalten</em></h1>
    <div class="hero-row">
      <div class="hero-text">
        <p class="sub">Wir entwickeln ein Computersystem, das Fragen zur
        PSMA-Therapie beantwortet. Ob seine Antworten verständlich sind und
        ob sie guttun, können nur Sie beurteilen.<br><br>
        <strong>Sagen Sie uns, wie sie auf Sie wirken.</strong></p>
        {badges([("clock", "5–7 Minuten"),
                 ("lock", "anonym — kein Name, keine Krankengeschichte"),
                 ("shield", "ohne Einfluss auf Ihre Behandlung")], "on-colour")}
        <div class="to-qr"><span>Hier geht es los</span>
          <svg viewBox="0 0 48 24" fill="none" stroke="currentColor" stroke-width="3"
               stroke-linecap="round" stroke-linejoin="round">
            <path d="M2 12h40M34 4l8 8-8 8"/></svg></div>
        <div class="quote">Bin ich nach der Entlassung gefährlich
          für meine Mitmenschen?
          <div class="cap">Eine der 20 Fragen, die Sie bewerten.</div>
        </div>
      </div>
      {phone(qr_svg(url), "Code scannen —<br>hier geht es los")}
    </div>
  </div>

  <div class="bottom">
    <ul class="isteps">
      <li><span class="ico-wrap">{icon('scan', 7)}</span><span class="txt">
        Handy-Kamera auf den Code halten</span></li>
      <li><span class="ico-wrap">{icon('tap', 7)}</span><span class="txt">
        20 Antworten lesen und je eine Aussage antippen</span></li>
      <li><span class="ico-wrap">{icon('check', 7)}</span><span class="txt">
        Fertig — nichts eingeben, nichts zurückgeben</span></li>
    </ul>

    <div class="urlline muted">Kein QR-Scanner zur Hand? Im Browser eingeben:
      <strong style="color:{ACCENT_DEEP}">{mark(pretty_url(url))}</strong></div>

    <div class="foot">
      <div class="muted">
        Ihre Teilnahme ist freiwillig. Sie hat keinen Einfluss auf Ihre Behandlung,<br>
        und Sie können jederzeit abbrechen.<br>
        {'<span class="faint">' + c['ethics_line'] + '</span>' if c['ethics_line'] else ''}
      </div>
      <div class="muted" style="text-align:right">
        {mark(c['clinic'])}<br>
        {mark(c['study_lead'])}<br>{mark(c['contact_email'])}
        {('<br>' + c['contact_phone']) if c['contact_phone'] else ''}
      </div>
    </div>
  </div>
</div>
</body></html>"""


# --------------------------------------------------------------- flyer ---
def flyer_html(c: dict) -> str:
    url, h = c["url"], c["logo_height_mm"] * 0.50
    phone_line = f"<br>{c['contact_phone']}" if c["contact_phone"] else ""
    return f"""<!doctype html><html lang="de"><head><meta charset="utf-8">
<style>{CSS}
@page {{ size: 297mm 210mm; margin: 0; }}
.flyer-page {{ width: 297mm; height: 210mm; display: flex; overflow: hidden; page-break-after: always; background: {PAPER}; }}
/* Wickelfalz: the panel that rolls innermost must be narrower, or the flyer
   does not close flat. Left to right on the outside sheet:
   inner flap 98 mm · back 99 mm · front cover 100 mm = 297 mm.
   The same physical columns keep these widths on the inside sheet. */
.flyer-page > .flyer-panel:nth-child(1) {{ width: 98mm; }}
.flyer-page > .flyer-panel:nth-child(2) {{ width: 99mm; }}
.flyer-page > .flyer-panel:nth-child(3) {{ width: 100mm; }}
.flyer-panel {{ width: 99mm; height: 210mm; padding: 10mm 8.5mm; display: flex; flex-direction: column; flex-shrink: 0; flex-grow: 0; position: relative; }}
.flyer-panel + .flyer-panel {{ border-left: .25mm dashed #cfd9db; }}

.flyer-panel .eyebrow {{ font-size: 7.5pt; color: {ACCENT}; }}
/* Each panel opens with a tinted band that bleeds to its edges, so the three
   sections are visible as sections the moment the flyer is unfolded. */
.flyer-panel .badges {{ flex-direction: column; align-items: flex-start; gap: 1.8mm; }}
.flyer-panel .badge {{ font-size: 7.6pt; padding: 1.8mm 3.5mm; gap: 2.2mm;
                       background: #fff; border: .3mm solid #d3e3e6; }}
.flyer-panel .badge svg {{ width: 4mm !important; height: 4mm !important; }}
.panel-head {{ background: {TINT}; margin: -10mm -8.5mm 4mm; padding: 7mm 8.5mm 5mm;
               border-bottom: .8mm solid {ACCENT}; }}
.panel-head .eyebrow {{ display: block; margin-bottom: 1.5mm; }}
.panel-head h2 {{ margin: 0 !important; }}
.flyer-panel h2 {{ font-size: 13pt; line-height: 1.18; margin: 2mm 0 2.8mm; letter-spacing: -.01em; }}
.flyer-panel h3 {{ font-size: 9pt; margin: 3mm 0 1.5mm; color: {ACCENT_DEEP}; }}
.flyer-panel p, .flyer-panel li {{ font-size: 8.3pt; line-height: 1.45; }}
.flyer-panel p + p {{ margin-top: 2.2mm; }}

/* Steps carry a symbol instead of a bare number: at a glance you see camera,
   person, tap, done — the shape of the task before a word is read. */
ul.isteps {{ list-style: none; margin: 1mm 0 0; }}
ul.isteps li {{ display: flex; gap: 3.5mm; align-items: flex-start; margin-bottom: 3.4mm; }}
ul.isteps .ico-wrap {{ flex: none; width: 9mm; height: 9mm; border-radius: 50%;
    background: {ACCENT}; color: #fff; display: flex; align-items: center;
    justify-content: center; }}
ul.isteps .txt {{ flex: 1; font-size: 8.3pt; line-height: 1.38; padding-top: .8mm; }}
.flyer-panel ol.steps {{ margin: 2mm 0 0; }}
.flyer-panel ol.steps li {{ padding-left: 7.5mm; margin-bottom: 2.5mm; font-size: 8.1pt; line-height: 1.35; }}
.flyer-panel ol.steps li::before {{ width: 4.8mm; height: 4.8mm; font-size: 7.5pt; }}

/* Three of the twenty questions, quoted verbatim. Nothing describes the study
   as economically as the questions themselves — and unlike a sample answer,
   a question gives nothing away about how the answers should be judged. */
.pull {{ margin: 2.5mm 0 3mm; padding-left: 4mm; border-left: 1.2mm solid {ACCENT};
          font-size: 9.2pt; line-height: 1.32; font-weight: 700; color: {INK}; }}
.aims {{ margin-top: 4mm; padding: 4mm 4.5mm; border-radius: 1.5mm;
          background: {TINT}; border-left: 1.2mm solid {ACCENT}; }}
.aims-title {{ font-size: 8.6pt; font-weight: 700; color: {ACCENT_DEEP}; margin-bottom: 2mm; }}
.aims ul {{ list-style: none; margin: 0; }}
.aims li {{ position: relative; padding-left: 4.5mm; margin-bottom: 1.8mm;
            font-size: 8.1pt; line-height: 1.38; }}
.aims li::before {{ content: "→"; position: absolute; left: 0; color: {ACCENT};
                    font-weight: 700; }}
.qblock {{ margin: 3mm 0 4mm; }}
.qblock .q {{ position: relative; padding: 2.6mm 3mm 2.6mm 7mm; margin-bottom: 2.2mm;
    background: {TINT}; border-radius: 1.5mm; font-size: 8.4pt; line-height: 1.35;
    color: {INK}; font-style: italic; }}
.qblock .q::before {{ content: "“"; position: absolute; left: 2mm; top: 1.4mm;
    font-size: 15pt; font-style: normal; line-height: 1; color: {ACCENT}; font-weight: 700; }}
.qblock .cap {{ font-size: 7.4pt; color: {INK3}; margin-top: 1.6mm; }}
.flyer-panel .box {{ padding: 3mm 4mm; border-radius: 1.5mm; margin-top: auto; font-size: 7.5pt;
                    line-height: 1.38; background: {TINT}; border-left: 1.2mm solid {ACCENT}; }}
.flyer-panel .contact {{ margin-top: auto; padding-top: 3mm; border-top: .3mm solid #d8e0e2;
                        font-size: 7.8pt; line-height: 1.4; }}
.flyer-panel .small {{ font-size: 7pt; line-height: 1.3; }}
.flyer-panel .backlogos {{ margin-top: 3.5mm; }}

/* cover */
.flyer-cover {{ padding: 0; background: {HERO_BG}; color: #fff; }}
.flyer-cover .inner {{ flex: 1; padding: 7.5mm 8.5mm 6.5mm; display: flex; flex-direction: column; }}
.flyer-cover .logobar {{ background: #fff; padding: 4.5mm 8.5mm; display: flex; align-items: center;
                        justify-content: space-between; }}
.flyer-cover h1 {{ font-size: 16pt; line-height: 1.14; letter-spacing: -.015em; margin-top: 3mm; }}
.flyer-cover h1 em {{ font-style: normal; color: #ffe9a8; }}
.flyer-cover .lead {{ font-size: 8.3pt; line-height: 1.42; margin-top: 3mm; color: #e8fbfd; }}
.flyer-cover .eyebrow {{ color: #bdf0f5; font-size: 7.2pt; }}
.badges.on-cover {{ flex-direction: column; align-items: flex-start;
                    gap: 1.8mm; margin-top: 4mm; }}
.badges.on-cover .badge {{ background: rgba(255,255,255,.93); font-size: 7.6pt;
                    padding: 1.8mm 3.5mm; gap: 2.2mm; }}
.badges.on-cover .badge svg {{ width: 4mm !important; height: 4mm !important; }}
.flyer-cover .phone {{ width: 44mm; margin: auto auto 0; border-color: #fff;
                      background: rgba(255,255,255,.12); padding: 2.5mm 2mm 3mm;
                      border-width: 1.1mm; border-radius: 4.5mm;
                      box-shadow: 0 0 0 1mm rgba(255,255,255,.2); }}
.flyer-cover .phone-notch {{ width: 22%; height: 1.1mm; background: #fff; border-radius: .8mm; margin: 0 auto 2mm; }}
.flyer-cover .phone-screen {{ background: #fff; border-radius: 2.5mm; padding: 2.5mm; text-align: center; }}
.flyer-cover .phone-qr svg {{ width: 31mm; margin: 0 auto; display: block; }}
.flyer-cover .phone-note {{ font-size: 7.2pt; margin-top: 1.8mm; line-height: 1.25; }}
.flyer-cover .u {{ text-align: center; font-size: 7.5pt; margin: 2mm 0 1mm; color: #d6f3f6;
                  word-break: break-all; }}
</style></head><body>

<!-- SHEET 1 (AUSSENSEITE):  Innenklappe (links) | Rückseite (mitte) | Titelseite (rechts) -->
<div class="flyer-page">

  <!-- Panel 5: Innenklappe -->
  <div class="flyer-panel">
    <div class="panel-head"><span class="eyebrow">Ihre Teilnahme</span><h2>Freiwillig &amp; Anonym</h2></div>
    <p>Ihre Teilnahme an dieser Befragung ist <strong>vollständig freiwillig</strong>.</p>
    <p>Ob und wie Sie antworten, hat <strong>keinen Einfluss auf Ihre Behandlung</strong>
    und wird Ihrem Behandlungsteam nicht mitgeteilt. Sie können die Befragung jederzeit abbrechen.</p>
    
    <h3>Wissenschaftliche Auswertung</h3>
    <p>Die Ergebnisse werden ausschliesslich zusammengefasst in der Forschung ausgewertet
    und wissenschaftlich publiziert. Rückschlüsse auf Ihre Person sind ausgeschlossen.</p>

    <div class="aims">
      <div class="aims-title">Was wir herausfinden wollen</div>
      <ul>
        <li>Ob die Antworten verständlich sind — und ob sie guttun.</li>
        <li>Ob einfühlsam formulierte Antworten genauso verlässlich bleiben.</li>
        <li>Wo Ärztinnen und Ärzte anders urteilen als Betroffene.</li>
      </ul>
    </div>

    <div class="box">
      <strong>Wichtig:</strong> Die Texte stammen von einem Computersystem in Entwicklung
      und dienen der Forschung. Sie sind <strong>keine medizinische Auskunft</strong>.
      Bei Behandlungsfragen wenden Sie sich bitte an Ihr Behandlungsteam.
    </div>
  </div>

  <!-- Panel 6: Rückseite / Kontakt & Datenschutz -->
  <div class="flyer-panel">
    <div class="panel-head"><span class="eyebrow">Kontakt &amp; Datenschutz</span><h2>Ihre Daten</h2></div>
    {badges([("lock", "kein Name, keine Adresse"),
             ("shield", "nichts aus Ihrer Krankengeschichte"),
             ("clock", "5–7 Minuten, dann fertig")])}
    <p style="margin-top:3.5mm">Wir erheben <strong>keinen Namen, keine Adresse und
    keine Kontaktdaten</strong> sowie keine Daten aus Ihrer Krankengeschichte.</p>
    <p>Gespeichert werden ausschliesslich: Ihre Rolle (Patient:in / Ärzt:in),
    Ihre Altersgruppe, Geschlecht, Ihre Bewertungen der Modellantworten und die Bearbeitungszeit.</p>
    <p>{c['storage_sentence']}</p>
    <p class="small faint">Weil alle Daten anonym sind, lässt sich eine Teilnahme nachträglich nicht einzeln zuordnen oder löschen.</p>

    <div class="contact">
      <strong>{mark(c['study_lead'])}</strong><br>
      {mark(c['clinic'])}<br>
      {mark(c['contact_email'])}{phone_line}
      {'<div class="small faint" style="margin-top:2mm">' + c['ethics_line'] + '</div>'
       if c['ethics_line'] else ''}
      <div class="logos backlogos">
        {logo(c['logo_1'], c['logo_1_name'], h * c['logo_1_scale'])}
        {logo(c['logo_2'], c['logo_2_name'], h * c['logo_2_scale'])}
      </div>
    </div>
  </div>

  <!-- Panel 1: Titelseite / Front Cover -->
  <div class="flyer-panel flyer-cover">
    <div class="logobar">
      <div class="logos">
        {logo(c['logo_1'], c['logo_1_name'], h * c['logo_1_scale'])}
        {logo(c['logo_2'], c['logo_2_name'], h * c['logo_2_scale'])}
      </div>
    </div>
    <div class="inner">
      <div class="eyebrow">Kurze Befragung · PSMA-Therapie</div>
      <h1>Helfen Sie mit, die Zukunft des <em>Arztgesprächs zu gestalten</em></h1>
      <p class="lead">Eine PSMA-Therapie wirft viele Fragen auf. Helfen Sie uns,
      die Antworten darauf verständlicher zu machen — für die Patientinnen und
      Patienten nach Ihnen.</p>
      {badges([("clock", "5–7 Minuten"),
               ("lock", "anonym, ohne Anmeldung"),
               ("shield", "ohne Einfluss auf Ihre Behandlung")], "on-cover")}
      {phone(qr_svg(url), "Code scannen")}
      <div class="u">{mark(pretty_url(url))}</div>
    </div>
  </div>

</div>

<!-- SHEET 2 (INNENSEITE):  Links (Panel 2) | Mitte (Panel 3) | Rechts (Panel 4) -->
<div class="flyer-page">

  <!-- Panel 2: Worum es geht -->
  <div class="flyer-panel">
    <div class="panel-head"><span class="eyebrow">Hintergrund &amp; Ziel</span><h2>Verständlich ist nicht dasselbe wie richtig</h2></div>
    <p>Fragen zur PSMA-Therapie werden heute oft online gestellt — abends,
    zwischen Terminen, wenn gerade niemand da ist, den man fragen kann.</p>
    <p>Wir entwickeln ein Computersystem, das solche Fragen beantwortet, gestützt
    auf aktuelle medizinische Leitlinien.</p>
    <p>Eine Antwort kann fachlich präzise sein und trotzdem unverständlich bleiben,
    zu kühl wirken oder Angst machen.</p>
    
    <h3>Warum Ihre Stimme zählt</h3>
    <p>Ob eine Formulierung gut verständlich ist, Vertrauen schafft und guttut,
    kann kein Computer selbst beurteilen — <strong>sondern nur Sie</strong>.</p>

    <h3>Warum wir das jetzt untersuchen</h3>
    <div class="pull">Verständlich ist nicht dasselbe wie richtig — wir prüfen,
    ob eine wärmere Antwort genauso verlässlich bleibt.</div>
    <p>Solche Systeme beantworten heute schon medizinische Fragen, meist ohne
    dass jemand geprüft hätte, wie das auf Betroffene wirkt. Wir wollen das
    wissen, <strong>bevor</strong> solche Texte in der Betreuung eingesetzt
    werden — nicht danach.</p>
  </div>

  <!-- Panel 3: Was Sie sehen werden -->
  <div class="flyer-panel">
    <div class="panel-head"><span class="eyebrow">Die Befragung</span><h2>Was Sie sehen werden</h2></div>
    <p>Sie lesen <strong>20 Fragen</strong>, wie sie im Patientenalltag
    wirklich gestellt werden:</p>
    <div class="qblock">
      <div class="q">Werden mir durch die PSMA-Therapie die Haare ausfallen?</div>
      <div class="q">Bin ich nach der Entlassung gefährlich für meine Mitmenschen?</div>
      <div class="q">Mein PSA-Wert steigt trotzdem weiter an. Ist das ein Problem?</div>
      <div class="cap">… und 17 weitere zu Ablauf, Strahlenschutz und Nebenwirkungen.</div>
    </div>
    <p>Zu jeder Frage sehen Sie jeweils <strong>eine vom Computer verfasste Antwort</strong>
    und wählen die Aussage, die Ihren Eindruck am ehesten beschreibt.</p>
    <p>Es gibt <strong>keine richtigen oder falschen Antworten</strong> — Ihr persönliches
    Empfinden steht im Mittelpunkt.</p>
  </div>

  <!-- Panel 4: Ablauf -->
  <div class="flyer-panel">
    <div class="panel-head"><span class="eyebrow">Ablauf</span><h2>In 5–7 Minuten erledigt</h2></div>
    <ul class="isteps">
      <li><span class="ico-wrap">{icon('scan', 5.2)}</span><span class="txt">
        <strong>Scannen:</strong> QR-Code mit der Kamera scannen (keine App, keine Anmeldung).</span></li>
      <li><span class="ico-wrap">{icon('person', 5.2)}</span><span class="txt">
        <strong>Start:</strong> Kurze Angaben zu Ihrer Rolle und Altersgruppe.</span></li>
      <li><span class="ico-wrap">{icon('tap', 5.2)}</span><span class="txt">
        <strong>Bewerten:</strong> 20 Antworten lesen und jeweils antippen.</span></li>
      <li><span class="ico-wrap">{icon('check', 5.2)}</span><span class="txt">
        <strong>Abschluss:</strong> Kurzes Feedback — fertig. Kein Einsenden nötig.</span></li>
    </ul>
    <div class="box">
      <strong>Flexibel teilnehmen:</strong> Sie können den Fragebogen direkt im Wartezimmer
      oder in aller Ruhe zu Hause auf dem Handy ausfüllen.
    </div>
  </div>

</div>
</body></html>"""


# Backwards compatibility alias
brochure_html = flyer_html


def render(html: str, out: Path, width_mm: float, height_mm: float) -> None:
    from playwright.sync_api import sync_playwright

    tmp = out.with_suffix(".html")
    tmp.write_text(html, encoding="utf-8")
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(tmp.resolve().as_uri())
        page.pdf(path=str(out), width=f"{width_mm}mm", height=f"{height_mm}mm",
                 print_background=True,
                 margin={"top": "0", "bottom": "0", "left": "0", "right": "0"})
        browser.close()
    tmp.unlink()


def main() -> int:
    missing = sorted(k for k, v in CONFIG.items()
                     if isinstance(v, str) and PLACEHOLDER.search(v))
    logos_missing = [CONFIG[f"logo_{i}_name"] for i in (1, 2)
                     if not CONFIG[f"logo_{i}"] or not (HERE / CONFIG[f"logo_{i}"]).is_file()]

    render(poster_html(CONFIG), HERE / "Poster_A3.pdf", 297, 420)
    render(flyer_html(CONFIG), HERE / "Flyer_A4.pdf", 297, 210)
    print("wrote Poster_A3.pdf (297x420 mm) and Flyer_A4.pdf (A4 landscape, 3-panel tri-fold)")

    if logos_missing:
        print("\n!! logo files not found, dashed boxes printed instead:")
        for i in (1, 2):
            p = CONFIG[f"logo_{i}"]
            if not p or not (HERE / p).is_file():
                print(f"     {CONFIG[f'logo_{i}_name']}: expected {HERE / p if p else '(no filename set)'}")
        print("   Download them from the two corporate-design portals (SVG preferred)")
        print("   and drop them next to this script.")
    if missing:
        print("\n!! NOT READY TO PRINT — still placeholders, shown in red on the page:")
        for k in missing:
            print(f"     CONFIG[{k!r}] = {CONFIG[k]}")
        print("   Fill them in at the top of this file and run it again.")
    if missing or logos_missing:
        return 1
    print("flyer: duplex, flip on the LONG edge, then tri-fold (Wickelfalz / Z-Falz).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
