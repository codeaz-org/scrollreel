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

# The browser window in the artwork. Everything else is derived from this, and
# the same numbers drive the CSS and the ffmpeg overlay position.
#
# Sized and placed so the window occupies the middle band with the title above
# and a caption below. The first pass put a 960x600 window at y=470 and left
# the bottom third of a 1920px canvas empty, which on a phone reads as a small
# picture floating in a lot of nothing -- the same failure the clipping
# pipeline had with its letterboxed 16:9 sources.
WIN_X, WIN_Y = 40, 470
WIN_W = W - (WIN_X * 2)          # 1000
BAR_H = 44                        # title bar height
BORDER = 2
INNER_X = WIN_X + BORDER
INNER_Y = WIN_Y + BAR_H
INNER_W = WIN_W - (BORDER * 2)
# Source viewport ratio, held exactly so the page is never distorted.
SRC_W, SRC_H = 1024, 850   # must match record.VIEWPORT
INNER_H = round(INNER_W * SRC_H / SRC_W)
WIN_BOTTOM = WIN_Y + BAR_H + INNER_H + BORDER

FONT = "'Inter', 'Segoe UI', system-ui, -apple-system, sans-serif"


def _shell(html, path, transparent=False):
    with sync_playwright() as p:
        b = p.chromium.launch(channel="chrome")
        pg = b.new_page(viewport={"width": W, "height": H}, device_scale_factor=1)
        pg.set_content(html, wait_until="networkidle")
        pg.screenshot(path=path, omit_background=transparent)
        b.close()


def _bg_html(title, subtitle, stack="", kicker="Website concept", built_note="concept site"):
    caption_top = WIN_BOTTOM + 56
    return f"""
<style>
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;600;800&display=swap');
  *{{margin:0;box-sizing:border-box}}
  body{{width:{W}px;height:{H}px;font-family:{FONT};color:#e8ecf1;
       background:radial-gradient(120% 80% at 50% 0%,#1d2634 0%,#0b0d10 60%)}}
  .wrap{{padding:110px 64px 0}}
  .kicker{{font-size:26px;letter-spacing:.28em;text-transform:uppercase;color:#7f8ea3;font-weight:600}}
  h1{{font-size:82px;line-height:1.02;font-weight:800;margin-top:24px;letter-spacing:-.025em}}
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


def _chrome_html():
    """Window bezel only. The inner rect stays transparent so the recorded
    footage shows through when this is overlaid on top of it."""
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
<div class="win">
  <div class="bar">
    <div class="dot" style="background:#ff5f57"></div>
    <div class="dot" style="background:#febc2e"></div>
    <div class="dot" style="background:#28c840"></div>
    <div class="url">localhost:4500</div>
  </div>
</div>
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


def build_assets(out_dir, title, subtitle, component, source_url, stack="", kicker="Website concept", outro_line="This site was built by CodeAZ",
                 built_note="concept site"):
    os.makedirs(out_dir, exist_ok=True)
    paths = {
        "bg": os.path.join(out_dir, "bg.png"),
        "chrome": os.path.join(out_dir, "chrome.png"),
        "outro": os.path.join(out_dir, "outro.png"),
    }
    _shell(_bg_html(title, subtitle, stack, kicker, built_note), paths["bg"])
    _shell(_chrome_html(), paths["chrome"], transparent=True)
    _shell(_outro_html(component, source_url, outro_line), paths["outro"])
    return paths


def compose(frames_dir, out_path, assets, fps=30, outro_seconds=2.5):
    """One ffmpeg pass: scale footage into the window, stack the layers, then
    concat the outro. Done as a single filtergraph so there is no intermediate
    re-encode to lose quality to."""
    body = os.path.join(os.path.dirname(out_path), "_body.mp4")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-loop", "1", "-i", assets["bg"],
        "-framerate", str(fps), "-i", os.path.join(frames_dir, "f%05d.png"),
        "-loop", "1", "-i", assets["chrome"],
        "-filter_complex",
        (f"[1:v]scale={INNER_W}:{INNER_H}[page];"
         f"[0:v][page]overlay={INNER_X}:{INNER_Y}:shortest=1[withpage];"
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
