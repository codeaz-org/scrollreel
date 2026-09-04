"""Validate the workflow the way GitHub does, not the way PyYAML does.

yaml.safe_load accepts DUPLICATE MAPPING KEYS and silently keeps the last one.
GitHub rejects the file outright. That difference cost a day of missed builds:
a patch added a second `if:` to a step that already had one, the local check
passed, and every push since produced an "invalid workflow file" run with no
jobs and no logs -- which looks nothing like a broken workflow and is easy to
read as the scheduler simply not firing.
"""
import sys
import yaml


class Strict(yaml.SafeLoader):
    pass


def _no_dupes(loader, node, deep=False):
    seen = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise yaml.YAMLError(
                f"duplicate key {key!r} at line {key_node.start_mark.line + 1} "
                f"(first seen at line {seen[key] + 1})")
        seen[key] = key_node.start_mark.line
    return yaml.SafeLoader.construct_mapping(loader, node, deep)


Strict.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _no_dupes)


def check(path):
    problems = []
    with open(path) as f:
        text = f.read()
    try:
        doc = yaml.load(text, Strict)
    except yaml.YAMLError as e:
        return [f"{path}: {e}"]
    triggers = doc.get("on") or doc.get(True)
    if not triggers:
        problems.append(f"{path}: no triggers")
    for job_name, job in (doc.get("jobs") or {}).items():
        for i, step in enumerate(job.get("steps") or []):
            if "uses" not in step and "run" not in step:
                problems.append(f"{path}: {job_name} step {i} has neither run nor uses")
    return problems


if __name__ == "__main__":
    bad = []
    for path in (sys.argv[1:] or [".github/workflows/build.yml"]):
        bad += check(path)
    for b in bad:
        print(b)
    print("workflow ok" if not bad else f"{len(bad)} problem(s)")
    sys.exit(1 if bad else 0)
