"""Put a video in the account's own TikTok drafts (the app's inbox).

Adapted from apps/mpt/tiktok.py, which established the parts that are not
obvious and were paid for with live failures:

  * Use /v2/post/publish/content/init/ with post_mode=MEDIA_UPLOAD, NOT
    /v2/post/publish/inbox/video/init/. The inbox endpoint's body accepts only
    source_info, so an attached post_info is dropped silently -- that is why
    drafts used to arrive with no caption and no hashtags, with no error.
  * A 200 from init means the job was accepted, not that it succeeded. Status
    has to be fetched before believing it.

What is different here: the source is FILE_UPLOAD, not PULL_FROM_URL. Nothing
to host, no gh-pages branch, no URL property to verify, and the mp4 never has
to be public.

That trade is not free, and it is measured, not assumed. Tried live on
2026-09-03, content/init answers FILE_UPLOAD with:

    400 invalid_params "Invalid media_type or post_mode"

so the captioned endpoint takes video only via PULL_FROM_URL, and this module
falls back to inbox/video/init, whose body accepts source_info alone. The draft
therefore arrives with NO caption and the copy has to be pasted in the app.

To get the caption pre-filled, host the mp4 and switch the source back:
verify the hosting domain once at developers.tiktok.com -> Content Posting API
-> URL properties (mpt's gesimuse.github.io is verified; codeaz-org.github.io
is not), then send PULL_FROM_URL with post_info as mpt does.

The draft lands unpublished in the TikTok app with the caption pre-filled. A
person opens it, adds audio, and posts -- which is the intended review step,
not a limitation: these are concept sites for invented businesses.
"""
import os
import time

import requests

API = "https://open.tiktokapis.com/v2"
# TikTok requires each chunk to be at least 5MB unless it is the whole file.
CHUNK = 10 * 1024 * 1024


def log(msg):
    print(f"[tiktok] {msg}", flush=True)


def enabled(suffix="CODEAZ"):
    return all(os.environ.get(k) for k in
               ("TIKTOK_CLIENT_KEY", "TIKTOK_CLIENT_SECRET",
                f"TIKTOK_REFRESH_TOKEN_{suffix.upper()}"))


def access_token(suffix="CODEAZ"):
    r = requests.post(
        f"{API}/oauth/token/",
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        data={
            "client_key": os.environ["TIKTOK_CLIENT_KEY"],
            "client_secret": os.environ["TIKTOK_CLIENT_SECRET"],
            "grant_type": "refresh_token",
            "refresh_token": os.environ[f"TIKTOK_REFRESH_TOKEN_{suffix.upper()}"],
        },
        timeout=60,
    )
    r.raise_for_status()
    data = r.json()
    if "access_token" not in data:
        raise RuntimeError(f"no access_token in refresh response: {str(data)[:300]}")
    return data["access_token"]


def _upload_chunks(upload_url, path, size):
    with open(path, "rb") as f:
        sent = 0
        while sent < size:
            chunk = f.read(CHUNK)
            last = sent + len(chunk) >= size
            end = sent + len(chunk) - 1
            r = requests.put(
                upload_url,
                headers={
                    "Content-Range": f"bytes {sent}-{end}/{size}",
                    "Content-Type": "video/mp4",
                    "Content-Length": str(len(chunk)),
                },
                data=chunk, timeout=600,
            )
            if r.status_code not in (200, 201, 206):
                raise RuntimeError(f"chunk upload failed at {sent}: "
                                   f"{r.status_code} {r.text[:200]}")
            sent += len(chunk)
            log(f"uploaded {sent // 1024}KB / {size // 1024}KB"
                + (" (final)" if last else ""))


def status(publish_id, token):
    r = requests.post(f"{API}/post/publish/status/fetch/",
                      headers={"Authorization": f"Bearer {token}",
                               "Content-Type": "application/json; charset=UTF-8"},
                      json={"publish_id": publish_id}, timeout=60)
    r.raise_for_status()
    return r.json().get("data", {})


def publish_draft(video_path, caption, title=None, suffix="CODEAZ", wait=True):
    """Upload the file and leave it as an unpublished draft. Returns publish_id."""
    if not enabled(suffix):
        raise RuntimeError(
            f"TikTok not configured: needs TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET "
            f"and TIKTOK_REFRESH_TOKEN_{suffix.upper()}")
    size = os.path.getsize(video_path)
    token = access_token(suffix)
    headers = {"Authorization": f"Bearer {token}",
               "Content-Type": "application/json; charset=UTF-8"}

    # One chunk unless the file is genuinely large: TikTok rejects a final
    # chunk under 5MB when there is more than one.
    chunk_size = size if size <= CHUNK else CHUNK
    total_chunks = 1 if size <= CHUNK else -(-size // CHUNK)

    body = {
        "source_info": {
            "source": "FILE_UPLOAD",
            "video_size": size,
            "chunk_size": chunk_size,
            "total_chunk_count": total_chunks,
        },
        "post_mode": "MEDIA_UPLOAD",     # unpublished draft in the app's inbox
        "media_type": "VIDEO",
        "post_info": {
            "title": (title or caption.splitlines()[0])[:90],
            "description": caption[:4000],
        },
    }
    r = requests.post(f"{API}/post/publish/content/init/", headers=headers,
                      json=body, timeout=60)
    if not r.ok:
        # Same reasoning as mpt's: a draft with no caption still beats losing
        # the video. Logged loudly so a permanent fallback is visible.
        log(f"WARNING: content/init rejected the upload ({r.status_code} "
            f"{r.text[:200]}); falling back to inbox/video/init, which cannot "
            f"carry a caption")
        r = requests.post(f"{API}/post/publish/inbox/video/init/", headers=headers,
                          json={"source_info": body["source_info"]}, timeout=60)
        r.raise_for_status()

    data = r.json()["data"]
    publish_id, upload_url = data["publish_id"], data["upload_url"]
    log(f"init ok, publish_id={publish_id}")
    _upload_chunks(upload_url, video_path, size)

    if wait:
        # A 200 from init only means accepted. Ask what actually happened.
        for _ in range(20):
            time.sleep(3)
            st = status(publish_id, token)
            state = st.get("status")
            if state in ("SEND_TO_USER_INBOX", "PUBLISH_COMPLETE"):
                log(f"draft is in the TikTok app: {state}")
                return publish_id
            if state == "FAILED":
                raise RuntimeError(f"TikTok reported FAILED: {st}")
        log(f"still processing after 60s; check the app. publish_id={publish_id}")
    return publish_id
