"""Stage a finished video on TikTok as a Buffer DRAFT.

Separate command, never called by main.py. The clipping pipeline taught this
the expensive way: it posted three clips nobody had watched, and they had to be
deleted by hand. Here the build and the publish are two decisions.

Drafts only, enforced rather than configured. These pages are concept sites for
invented businesses; a draft means a person approves each one before it appears
on the account. Setting BUFFER_MODE=shareNow does not override it -- the check
below refuses to run.

  python post.py out/halden-auto           # stage that build
  python post.py out/halden-auto --caption "..."   # override the copy
"""
import argparse
import json
import os
import sys

import buffer_client


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

    if not buffer_client.enabled():
        sys.exit("BUFFER_ACCESS_TOKEN is not set")
    draft = (os.environ.get("BUFFER_DRAFT") or "").strip().lower() in ("1", "true", "yes")
    if not draft:
        sys.exit("BUFFER_DRAFT must be 1: scrollreel stages drafts, it does not publish. "
                 "Approve the post in Buffer once you have watched it.")

    caption = args.caption or caption_for(meta)
    print(f"video   : {video}")
    print(f"business: {meta['business']} ({meta['trade']}, {meta['city']})")
    print("caption :\n" + caption)
    if not args.yes:
        if input("\nstage this as a Buffer draft? [y/N] ").strip().lower() != "y":
            sys.exit("cancelled")

    hosted = buffer_client.host_file(video)
    post_id = buffer_client.publish(
        video, caption, title=meta["business"], video_url=hosted,
        env_suffix=os.environ.get("BUFFER_ENV_SUFFIX", "codeaz"),
    )
    print(f"staged as Buffer draft: {post_id}")

    meta.setdefault("posts", []).append({"buffer_post_id": post_id, "draft": True})
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2)


if __name__ == "__main__":
    main()
