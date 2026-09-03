# scrollreel

A website per video. Each run invents a local business — an auto shop, a
gardener, a bakery — builds it a real scroll-driven site around an MIT-licensed
UI component, records the scroll, and wraps it in a CodeAZ frame ending on
"this site was built by CodeAZ".

The component is not the subject. The website is. The component is chosen
because its idea suits that business's one memorable moment: a before/after
wiper for a car restoration, a marquee for a bakery's daily bakes.

## What runs

```
businesses.py   the trade, its services, tone, memorable moment, photo query
components.py   MIT components from Magic UI / shadcn, via the git tree API
images.py       Pexels photos, downloaded to disk BEFORE the page is built
page_builder.py Gemini writes the site; scroll-craft's rules distilled + verify()
record.py       Playwright drives real Chrome, eased scroll, frame-exact capture
compose.py      CodeAZ template, service pills, outro — HTML, rendered by Chrome
main.py         orchestrates; keeps page, photos, video and meta.json
post.py         stages one finished video as a Buffer draft for TikTok
```

## Build one

```bash
cp .env.example .env      # fill in GEMINI_API_KEY and PEXELS_API_KEY
python -m venv .venv && ./.venv/bin/pip install playwright requests
./.venv/bin/python main.py                       # random unused trade
./.venv/bin/python main.py --trade "artisan bakery"
```

Everything lands in `out/<business-slug>/`: `page.html`, `img/`, `video.mp4`,
`meta.json`. The page source is kept because the video claims the site exists,
so it has to.

## Post one

```bash
./.venv/bin/python post.py out/halden-auto
```

The video lands in the **TikTok app's own drafts** (inbox), not in Buffer.
There is no publish path in `post.py` at all — you open TikTok, add audio, and
post it yourself. Building and publishing are two separate decisions on
purpose: the clipping pipeline this grew out of posted three clips nobody had
watched, and they had to be deleted by hand.

**The caption is not pre-filled.** Measured live: `content/init` (the endpoint
that carries `post_info`) rejects `FILE_UPLOAD` with *"Invalid media_type or
post_mode"*, so uploads fall back to `inbox/video/init`, whose body accepts
only `source_info`. Paste the caption `post.py` prints, or host the mp4 and
verify that domain under Content Posting API → URL properties to use
`PULL_FROM_URL` with `post_info` instead.

## Things that will bite

- **Real Chrome, not bundled Chromium.** Chromium ships without the h264
  decoder, so any video on a page silently fails to paint and you record
  posters. `record.py` uses `channel="chrome"`.
- **Photos are downloaded first.** A remote `<img>` that has not decoded by
  screenshot time records as a blank box, so nothing is fetched at render time
  and `verify()` rejects a page that links one.
- **Capture geometry is a matched pair.** `record.VIEWPORT` and
  `compose.SRC_W/SRC_H` must agree or the footage is stretched. 1024x850 is
  chosen so the page scales into the window at 0.97 — at 1440 it was 0.69 and
  17px body text arrived at 12px, unreadable on a phone.
- **These businesses are fictional.** Names come from a word list and the copy
  invents founding years, prices and addresses. The frame says "concept site".

## Not done yet

No music bed (the video is silent), no scheduling, no YouTube posting, and
`verify()` only catches provable faults — whether a page actually looks good
still needs a person to watch it.
