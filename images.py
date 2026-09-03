"""Photos for the business site, downloaded locally before the page is built.

A tradesman's website with no photographs looks like a mock, and the video is
supposed to look like a site someone paid for. But the page is captured from
file:// and a remote image that has not decoded by screenshot time records as
a blank box, so nothing may be fetched at render time: the files are on disk
first, and the page references them relatively.

Pexels, because the licence permits commercial use without attribution and
codeaz-mpt already uses the same key. Falls back to Picsum (no key) and then to
no photos at all, in which case the builder is told to draw with CSS instead of
leaving holes in the layout.
"""
import json
import os
import time
import urllib.parse
import urllib.request

UA = {"User-Agent": "codeaz-scrollreel"}


def _download(url, dest, headers=None, attempts=3):
    """Retried for the same reason as components._get: a dropped connection
    part-way through a photo set should cost a second, not the run."""
    for attempt in range(1, attempts + 1):
        try:
            req = urllib.request.Request(url, headers={**UA, **(headers or {})})
            with urllib.request.urlopen(req, timeout=60) as r, open(dest, "wb") as f:
                f.write(r.read())
            return dest
        except Exception:  # noqa: BLE001
            if attempt == attempts:
                raise
            time.sleep(2 ** attempt)


def fetch(query, out_dir, count=5):
    """Returns [{file, alt, credit}] with `file` relative to the page."""
    img_dir = os.path.join(out_dir, "img")
    os.makedirs(img_dir, exist_ok=True)
    key = (os.environ.get("PEXELS_API_KEY") or "").strip()

    if key:
        try:
            url = ("https://api.pexels.com/v1/search?"
                   + urllib.parse.urlencode({"query": query, "per_page": count,
                                             "orientation": "landscape", "size": "large"}))
            req = urllib.request.Request(url, headers={**UA, "Authorization": key})
            with urllib.request.urlopen(req, timeout=45) as r:
                data = json.loads(r.read())
            out = []
            for i, photo in enumerate(data.get("photos", [])[:count]):
                src = photo["src"].get("large") or photo["src"].get("original")
                name = f"img/p{i}.jpg"
                _download(src, os.path.join(out_dir, name))
                out.append({"file": name,
                            "alt": (photo.get("alt") or query)[:80],
                            "credit": f"Photo by {photo.get('photographer')} on Pexels"})
            if out:
                print(f"[images] {len(out)} photos from Pexels for {query!r}")
                return out
        except Exception as e:  # noqa: BLE001
            print(f"[images] Pexels failed ({e}); falling back")

    try:
        out = []
        for i in range(count):
            name = f"img/p{i}.jpg"
            _download(f"https://picsum.photos/seed/{urllib.parse.quote(query)}{i}/1600/1000",
                      os.path.join(out_dir, name))
            out.append({"file": name, "alt": query, "credit": "Lorem Picsum"})
        print(f"[images] {len(out)} photos from Picsum for {query!r}")
        return out
    except Exception as e:  # noqa: BLE001
        print(f"[images] no photos available ({e}); the page will be drawn in CSS")
        return []
