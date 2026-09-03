"""Composite recorded page frames into a 1080x1920 video with an outro.

The template is HTML rendered through the same Chrome that recorded the page,
not an ffmpeg filtergraph. Two reasons: the layout is design work and CSS is
the right language for it, and the geometry that positions the footage is then
computed once, in Python, and shared by both the template and the overlay --
so the browser window in the artwork and the video underneath it cannot drift
apart.

Layers, bottom to top:
  bg.png      opaque backdrop, title, CodeAZ mark
  footage     the recorded scroll, scaled into the window's inner rect
  chrome.png  window bezel and title bar, transparent over the inner rect
"""
import json
import os
import subprocess

from playwright.sync_api import sync_playwright

W, H = 1080, 1920

# Three ways of presenting the same footage. One is chosen per build, so a
# week of videos does not look like one video made seven times.
#
#   window     a browser chrome with a title bar. Reads as "a real site".
#   flush      no chrome, footage larger and rounded. Reads as a product shot.
#   editorial  title beneath the footage, which sits high. Reads as a magazine.
#
# Geometry is per template and shared by the CSS and the ffmpeg overlay, so the
# artwork and the video underneath it cannot drift apart.
TEMPLATES = {
    "window":    {"x": 40, "y": 470, "bar": 44, "title_top": 110, "title_at": "top"},
    "flush":     {"x": 24, "y": 430, "bar": 0,  "title_top": 96,  "title_at": "top"},
    "editorial": {"x": 40, "y": 190, "bar": 0,  "title_top": 0,   "title_at": "bottom"},
}
BORDER = 2
# Source viewport ratio, held exactly so the page is never distorted.
SRC_W, SRC_H = 1024, 850   # must match record.VIEWPORT


def geometry(template="window"):
    """Every number the CSS and the overlay both need, derived from one place."""
    t = TEMPLATES.get(template, TEMPLATES["window"])
    win_x, win_y, bar = t["x"], t["y"], t["bar"]
    win_w = W - win_x * 2
    inner_w = win_w - BORDER * 2
    inner_h = round(inner_w * SRC_H / SRC_W)
    return {
        **t, "template": template,
        "WIN_X": win_x, "WIN_Y": win_y, "WIN_W": win_w, "BAR_H": bar,
        "INNER_X": win_x + BORDER, "INNER_Y": win_y + bar,
        "INNER_W": inner_w, "INNER_H": inner_h,
        "WIN_BOTTOM": win_y + bar + inner_h + BORDER,
    }


FONT = "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif"


def _shell(html, path, transparent=False):
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.set_content(html, wait_until="networkidle")
        pg.screenshot(path=path, omit_background=transparent)
        b.close()


def _bg_html(title, subtitle, stack="", kicker="Website concept",
             built_note="concept site", g=None):
    g = g or geometry()
    W_, H_ = W, H
    if g["title_at"] == "bottom":
        # editorial: footage high, the naming underneath it.
        wrap_top = g["WIN_BOTTOM"] + 70
        caption_top = wrap_top + 300
    else:
        wrap_top = g["title_top"]
        caption_top = g["WIN_BOTTOM"] + 56
    title_size = 82 if len(title) < 22 else 66
    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
  *{{margin:0;box-sizing:border-box}}
  body{{width:{W}px;height:{H}px;font-family:{FONT};color:#e8ecf1;
       background:radial-gradient(120% 80% at 50% 0%,#1d2634 0%,#0b0d10 60%)}}
  .wrap{{position:absolute;top:{wrap_top}px;left:0;right:0;padding:0 64px}}
  .kicker{{font-size:26px;letter-spacing:.28em;text-transform:uppercase;color:#7f8ea3;font-weight:600}}
  h1{{font-size:{title_size}px;line-height:1.02;font-weight:800;margin-top:24px;letter-spacing:-.025em}}
  .sub{{font-size:31px;color:#9fb0c3;margin-top:24px;font-weight:400}}
  /* Sits in what used to be dead canvas under the window. */
  .caption{{position:absolute;top:{caption_top}px;left:64px;right:64px;
            display:flex;align-items:center;gap:18px;flex-wrap:wrap}}
  .pill{{border:1px solid #2b323d;border-radius:999px;padding:12px 22px;
         font-size:24px;color:#9fb0c3;background:#12161c}}
  .mark{{position:absolute;bottom:74px;left:64px;font-size:32px;font-weight:800;letter-spacing:-.01em}}
  .mark span{{color:#5b8cff}}
  .built{{position:absolute;bottom:80px;right:64px;font-size:24px;color:#6b7a8d}}
</style>
<div class="wrap">
  <div class="kicker">{kicker}</div>
  <h1>{title}</h1>
  <div class="sub">{subtitle}</div>
</div>
<div class="caption">{stack}</div>
<div class="mark">code<span>AZ</span></div>
<div class="built">{built_note}</div>
"""


def _chrome_html(g=None):
    """Window bezel only. The inner rect stays transparent so the recorded
    footage shows through when this is overlaid on top of it.

    With bar=0 (flush, editorial) there is no title bar and the frame is just
    a rounded edge and a shadow -- the footage reads as a product shot rather
    than as a browser."""
    g = g or geometry()
    WIN_X, WIN_Y, WIN_W = g["WIN_X"], g["WIN_Y"], g["WIN_W"]
    BAR_H, INNER_H = g["BAR_H"], g["INNER_H"]
    bar = ("""
  <div class="bar">
    <div class="dot" style="background:#ff5f57"></div>
    <div class="dot" style="background:#febc2e"></div>
    <div class="dot" style="background:#28c840"></div>
    <div class="url">localhost:4500</div>
  </div>""" if BAR_H else "")
    return f"""
<style>
  *{{margin:0;box-sizing:border-box}}
  body{{width:{W}px;height:{H}px;background:transparent}}
  .win{{position:absolute;left:{WIN_X}px;top:{WIN_Y}px;width:{WIN_W}px;
        height:{BAR_H + INNER_H + BORDER}px;border:{BORDER}px solid #2b323d;
        border-radius:18px;overflow:hidden;
        box-shadow:0 40px 90px rgba(0,0,0,.55)}}
  .bar{{height:{BAR_H}px;background:#171b21;display:flex;align-items:center;
        gap:9px;padding:0 18px;border-bottom:1px solid #2b323d}}
  .dot{{width:12px;height:12px;border-radius:50%}}
  .url{{margin-left:16px;font:500 15px {FONT};color:#7f8ea3}}
</style>
<div class="win">{bar}</div>
"""


def _outro_html(component, source_url, outro_line="This site was built by CodeAZ"):
    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
  *{{margin:0;box-sizing:border-box}}
  body{{width:{W}px;height:{H}px;font-family:{FONT};color:#e8ecf1;
       background:radial-gradient(120% 80% at 50% 40%,#1d2634 0%,#0b0d10 65%);
       display:flex;flex-direction:column;align-items:center;justify-content:center;gap:26px}}
  .mark{{font-size:96px;font-weight:800;letter-spacing:-.03em}}
  .mark span{{color:#5b8cff}}
  .line{{font-size:34px;color:#9fb0c3}}
  .meta{{font-size:22px;color:#6b7a8d;margin-top:40px;text-align:center;line-height:1.6}}
  .cta{{font-size:27px;color:#5b8cff;font-weight:600;margin-top:6px}}
</style>
<div class="mark">code<span>AZ</span></div>
<div class="line">{outro_line}</div>
<div class="cta">Want one for your business?</div>
<div class="meta">Built with {component} &middot; {source_url}</div>
"""


def build_assets(out_dir, title, subtitle, component, source_url, stack="",
                 kicker="Website concept", outro_line="This site was built by CodeAZ",
                 built_note="concept site", template="window"):
    g = geometry(template)
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "bg": os.path.join(out_dir, "bg.png"),
        "chrome": os.path.join(out_dir, "chrome.png"),
        "outro": os.path.join(out_dir, "outro.png"),
    }
    _shell(_bg_html(title, subtitle, stack, kicker, built_note, g), paths["bg"])
    _shell(_chrome_html(g), paths["chrome"], transparent=True)
    _shell(_outro_html(component, source_url, outro_line), paths["outro"])
    paths["geometry"] = g
    return paths


def compose(frames_dir, out_path, assets, fps=30, outro_seconds=2.5, g=None):
    """One ffmpeg pass: scale footage into the window, stack the layers, then
    concat the outro. Done as a single filtergraph so there is no intermediate
    re-encode to lose quality to."""
    g = g or assets.get("geometry") or geometry()
    body = os.path.join(os.path.dirname(out_path), "_body.mp4")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", assets["bg"],
        "-framerate", str(fps), "-i", os.path.join(frames_dir, "f%05d.png"),
        "-loop", "1", "-i", assets["chrome"],
        "-filter_complex",
        (f"[1:v]scale={g['INNER_W']}:{g['INNER_H']}[page];"
         f"[0:v][page]overlay={g['INNER_X']}:{g['INNER_Y']}:shortest=1[withpage];"
         f"[withpage][2:v]overlay=0:0:shortest=1,format=yuv420p[v]"),
        "-map", "[v]", "-r", str(fps),
        "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-movflags", "+faststart",
        body,
    ]
    subprocess.run(cmd, check=True)

    outro = os.path.join(os.path.dirname(out_path), "_outro.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-t", str(outro_seconds), "-i", assets["outro"],
        "-r", str(fps), "-c:v", "libx264", "-preset", "medium", "-crf", "18",
        "-pix_fmt", "yuv420p", outro,
    ], check=True)

    lst = os.path.join(os.path.dirname(out_path), "_concat.txt")
    with open(lst, "w") as f:
        f.write(f"file '{os.path.abspath(body)}'\nfile '{os.path.abspath(outro)}'\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
                    "-i", lst, "-c", "copy", "-movflags", "+faststart", out_path], check=True)
    for tmp in (body, outro, lst):
        os.remove(tmp)
    return out_path
