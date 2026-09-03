"""Pick an MIT-licensed UI component to build a page around.

Sourced from the component libraries' own GitHub repos rather than from
21st.dev. 21st.dev is the nicer catalogue, but its robots.txt disallows /r/ and
/api/ -- the registry endpoints that hold the actual code -- and the sanctioned
route (their Magic MCP) is on a paid plan. The libraries it indexes are MIT on
GitHub, so we take the same components from the source that licenses them.

Discovery goes through the git tree API instead of hardcoded file paths: Magic
UI's components live at apps/www/registry/magicui/*.tsx today, and a guessed
path like registry/magicui/animated-beam.tsx 404s. Listing the tree means a
repo reorganising does not silently break the picker.
"""
import json
import os
import random
import sys
import time
import urllib.request

REPOS = [
    {
        "name": "Magic UI",
        "repo": "magicuidesign/magicui",
        "branch": "main",
        "dir": "apps/www/registry/magicui/",
        "site": "https://magicui.design",
        "license": "MIT",
    },
    {
        # Verified against the git tree, not guessed: the components live under
        # apps/v4/registry/new-york-v4/ui/, and "aceternity/ui" -- the obvious
        # guess for the other library everyone indexes -- is not a real repo.
        "name": "shadcn/ui",
        "repo": "shadcn-ui/ui",
        "branch": "main",
        "dir": "apps/v4/registry/new-york-v4/ui/",
        "site": "https://ui.shadcn.com",
        "license": "MIT",
    },
]

CACHE = os.environ.get("SCROLLREEL_CACHE", ".cache")
UA = {"User-Agent": "codeaz-scrollreel (+https://github.com/codeaz-org)"}


def _get(url, as_json=True, attempts=4):
    """Retried: the connection to GitHub drops often enough on a VPN that a
    single RemoteDisconnected was taking whole runs down after the component
    had already been chosen."""
    for attempt in range(1, attempts + 1):
        try:
            return _get_once(url, as_json)
        except Exception as e:  # noqa: BLE001
            if attempt == attempts:
                raise
            wait = 2 ** attempt
            print(f"[components] {type(e).__name__} on {url.split('/')[-1]}; "
                  f"retry {attempt}/{attempts - 1} in {wait}s", file=sys.stderr)
            time.sleep(wait)


def _get_once(url, as_json=True):
    headers = dict(UA)
    # Unauthenticated GitHub allows 60 requests an hour and listing two trees
    # burns through that fast enough to fail mid-session. A token raises it to
    # 5000; without one the cache below carries the run.
    token = (os.environ.get("GITHUB_TOKEN") or "").strip()
    if token and "api.github.com" in url:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req, timeout=45) as r:
        raw = r.read()
    return json.loads(raw) if as_json else raw.decode("utf-8", "replace")


def _cached_tree(source, max_age_seconds=86400):
    """Component listings change on the order of weeks, so a day-old tree is
    fine and keeps a run working through a rate limit."""
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, source["repo"].replace("/", "_") + ".tree.json")
    if os.path.exists(path) and (time.time() - os.path.getmtime(path)) < max_age_seconds:
        with open(path) as f:
            return json.load(f)
    try:
        tree = _get(f"https://api.github.com/repos/{source['repo']}/git/trees/"
                    f"{source['branch']}?recursive=1")
    except Exception:
        if os.path.exists(path):          # stale beats nothing
            print(f"[components] {source['name']}: using stale cache", file=sys.stderr)
            with open(path) as f:
                return json.load(f)
        raise
    with open(path, "w") as f:
        json.dump(tree, f)
    return tree


def list_components(source):
    """Component files in one repo, via the git tree so paths are never guessed."""
    tree = _cached_tree(source)
    out = []
    for node in tree.get("tree", []):
        path = node.get("path", "")
        if not path.startswith(source["dir"]) or not path.endswith(".tsx"):
            continue
        name = os.path.basename(path)[:-4]
        # Demos and index files are wrappers, not the component itself.
        if name.endswith("-demo") or name.startswith("__"):
            continue
        out.append({"name": name, "path": path})
    return out


def fetch_source(source, path):
    url = f"https://raw.githubusercontent.com/{source['repo']}/{source['branch']}/{path}"
    return _get(url, as_json=False)


def pick(used=(), seed=None):
    """One component not already used. Repos are tried in random order so the
    first library in the list does not get mined dry while the rest wait --
    the same trap the clipping pipeline hit with a fixed channel order."""
    rng = random.Random(seed)
    repos = list(REPOS)
    rng.shuffle(repos)
    for source in repos:
        try:
            items = list_components(source)
        except Exception as e:  # noqa: BLE001 -- a dead repo must not stop the run
            print(f"[components] {source['name']} unavailable: {e}", file=sys.stderr)
            continue
        fresh = [c for c in items if f"{source['repo']}:{c['name']}" not in used]
        if not fresh:
            continue
        chosen = rng.choice(fresh)
        code = fetch_source(source, chosen["path"])
        return {
            "id": f"{source['repo']}:{chosen['name']}",
            "name": chosen["name"],
            "library": source["name"],
            "license": source["license"],
            "site": source["site"],
            "source_url": f"https://github.com/{source['repo']}/blob/{source['branch']}/{chosen['path']}",
            "code": code,
        }
    return None


if __name__ == "__main__":
    c = pick()
    if not c:
        sys.exit("no component available")
    print(f"{c['library']} / {c['name']}  ({c['license']})")
    print(c["source_url"])
    print(f"{len(c['code'])} chars of source")
