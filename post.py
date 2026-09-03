"""Put a finished video into the account's own TikTok drafts.

Separate command, never called by main.py. The clipping pipeline taught this
the expensive way: it posted three clips nobody had watched, and they had to be
deleted by hand. Here the build and the publish are two decisions.

A TikTok draft, not a Buffer draft: the video lands unpublished in the TikTok
app itself, caption pre-filled, and a person adds audio and posts it. Buffer's
draft would only ever sit in Buffer.

Uploading is the only mode offered here -- there is no publish path in this
file at all. These are concept sites for invented businesses, so a human
approving each one is the point rather than a limitation.

  python post.py out/halden-auto           # stage that build
  python post.py out/halden-auto --caption "..."   # override the copy
"""
import argparse
import json
import os
import sys

import tiktok


def caption_for(meta):
    """The copy that sells the service, not the component. The component is an
    implementation detail nobody outside this repo cares about."""
    trade = meta["trade"]
    # "a auto repair shop" shipped in the first staged draft. Vowel test, not a
    # dictionary: every trade in businesses.py is a plain noun phrase.
    article = "an" if trade[0].lower() in "aeiou" else "a"
    return (
        f"A website concept for {meta['business']} — {article} {trade} in {meta['city']}.\n\n"
        f"Built from scratch by CodeAZ: scroll-driven, real content, "
        f"loads fast, works on a phone.\n\n"
        f"Want one for your business? Get in touch.\n\n"
        f"#webdesign #smallbusiness #websitedesign #webdeveloper #codeaz"
    )


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("build_dir", help="a directory under out/, e.g. out/halden-auto")
    ap.add_argument("--caption")
    ap.add_argument("--yes", action="store_true", help="skip the confirmation")
    args = ap.parse_args()

    meta_path = os.path.join(args.build_dir, "meta.json")
    if not os.path.exists(meta_path):
        sys.exit(f"no meta.json in {args.build_dir}")
    with open(meta_path) as f:
        meta = json.load(f)
    video = meta["video"]
    if not os.path.exists(video):
        sys.exit(f"video missing: {video}")

    suffix = os.environ.get("TIKTOK_ENV_SUFFIX", "CODEAZ")
    if not tiktok.enabled(suffix):
        sys.exit(f"TikTok not configured: needs TIKTOK_CLIENT_KEY, TIKTOK_CLIENT_SECRET "
                 f"and TIKTOK_REFRESH_TOKEN_{suffix.upper()}")

    caption = args.caption or caption_for(meta)
    print(f"video   : {video}")
    print(f"business: {meta['business']} ({meta['trade']}, {meta['city']})")
    print("caption :\n" + caption)
    if not args.yes:
        if input("\nupload to TikTok drafts? [y/N] ").strip().lower() != "y":
            sys.exit("cancelled")

    publish_id = tiktok.publish_draft(video, caption, title=meta["business"], suffix=suffix)
    print(f"in TikTok drafts: {publish_id}")
    print("Open TikTok -> inbox notification -> add audio -> post.")

    meta.setdefault("posts", []).append({"tiktok_publish_id": publish_id, "draft": True})
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
