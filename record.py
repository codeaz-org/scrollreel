"""Record a smooth scroll of a local page as a frame sequence.

scroll-craft's own shoot.mjs walks N discrete scroll positions and screenshots
each one -- that is a verification contact sheet, not footage. This drives the
scroll continuously and captures every frame, because the whole point of the
video is the motion between positions.

Frames, not a video file, on purpose: Playwright's built-in recorder writes
webm at a frame rate it chooses, and scroll-driven pages stutter visibly when
the recorder and the scroll disagree. Stepping the scroll ourselves and
screenshotting once per step makes the output frame-exact and lets compose.py
pick the frame rate.

Uses the INSTALLED Chrome (channel="chrome"), not bundled Chromium: Chromium
ships without the h264 decoder, so any scrub video on the page silently fails
to paint and you record a page of posters. That is scroll-craft's warning and
it applies just as much here.
"""
import argparse
import math
import os
import shutil

from playwright.sync_api import sync_playwright

# Sized so the capture is scaled almost 1:1 into the 996px window: at 1440 the
# scale was 0.69 and 17px body text landed at ~12px, at 1152 it was 0.86, and
# at 1024 it is 0.97 -- text arrives at the size it was designed at. Still a
# desktop layout; 1024 is above the tablet breakpoint every framework uses.
#
# The height is deliberately tall (850, not 720): the window's height in the
# template is derived from this ratio, and a squatter source left the bottom
# third of the 1920px canvas empty.
VIEWPORT = {"width": 1024, "height": 850}


def ease_in_out(t):
    """Scroll that starts and ends at rest. A linear scroll reads as a machine
    dragging a scrollbar; easing reads as someone looking at the page."""
    return 0.5 * (1 - math.cos(math.pi * t))


def record(url, out_dir, seconds=12.0, fps=30, settle_ms=400,
           lead_frames=3, tail_frames=12):
    frames_dir = os.path.join(out_dir, "frames")
    shutil.rmtree(frames_dir, ignore_errors=True)
    os.makedirs(frames_dir, exist_ok=True)

    total = int(seconds * fps)
    written = 0

    with sync_playwright() as p:
        browser = p.chromium.launch(channel="chrome", args=["--hide-scrollbars",
                                                            "--force-device-scale-factor=1"])
        page = browser.new_page(viewport=VIEWPORT, device_scale_factor=2)
        page.goto(url, wait_until="networkidle")
        # Fonts and lazy assets land after networkidle often enough to matter.
        page.wait_for_timeout(settle_ms)
        page.evaluate("() => document.fonts && document.fonts.ready")

        height = page.evaluate("() => document.documentElement.scrollHeight")
        travel = max(0, height - VIEWPORT["height"])
        print(f"[record] page height {height}px, travel {travel}px, {total} frames @ {fps}fps")

        # A brief hold, not a long one. 15 frames plus the ease-in meant ~1.5s
        # of nothing at the top, which on a feed is the entire window you have
        # to stop someone scrolling past.
        for _ in range(lead_frames):
            page.screenshot(path=os.path.join(frames_dir, f"f{written:05d}.png"))
            written += 1

        for i in range(total):
            y = travel * ease_in_out(i / max(1, total - 1))
            # Instant, not smooth: we are stepping the timeline ourselves, and
            # a smooth-behaviour scroll would still be animating when the
            # screenshot fires, producing duplicated and skipped frames.
            page.evaluate("y => window.scrollTo({top: y, behavior: 'instant'})", y)
            page.wait_for_timeout(1000 // fps // 2)
            page.screenshot(path=os.path.join(frames_dir, f"f{written:05d}.png"))
            written += 1

        # The tail hold stays: the last frame is where the eye lands before
        # the outro card cuts in.
        for _ in range(tail_frames):
            page.screenshot(path=os.path.join(frames_dir, f"f{written:05d}.png"))
            written += 1

        browser.close()

    print(f"[record] wrote {written} frames to {frames_dir}")
    return frames_dir, written


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--url", required=True)
    ap.add_argument("--out", default="lab")
    ap.add_argument("--seconds", type=float, default=12.0)
    ap.add_argument("--fps", type=int, default=30)
    a = ap.parse_args()
    record(a.url, a.out, seconds=a.seconds, fps=a.fps)
