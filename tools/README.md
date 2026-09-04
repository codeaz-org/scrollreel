# Triggering the daily build

GitHub's scheduler has never once delivered a scheduled trigger to this repo.
It asked for `0 9`, then `23 8`, then `23 8` and `47 15` with a guard, and every
slot passed with nothing. This is not registration latency and not a permission
problem: the sibling clipping repo's cron does fire, three and a half hours
late, on the same account and the same org. Schedule delivery is best-effort
and this repo keeps losing.

So there are three chances at a build each day and at most one video:

| trigger | where | reliable |
|---|---|---|
| `cron: "23 8 * * *"` | GitHub | no, free |
| `cron: "47 15 * * *"` | GitHub | no, free |
| `scrollreel-daily.timer` | this machine | yes, while the machine runs |

Two things stop that producing three videos:

- the workflow's own guard reads the last timestamp out of `state.json` and
  makes a schedule run a no-op if today is already built. It deliberately does
  NOT apply to `workflow_dispatch`, because a person pressing Run workflow
  means it.
- `daily-trigger.sh` therefore does its own check before dispatching, counting
  any run from today that succeeded or is still going. A run in progress counts:
  two concurrent builds would race each other committing `state.json`.

## The timer

Installed with:

    systemctl --user daemon-reload
    systemctl --user enable --now scrollreel-daily.timer

`Persistent=true` matters more than the hour does. This is a laptop and it will
be off at 12:30 on plenty of days; persistent means the timer fires when the
machine comes back rather than skipping the day. `Linger=yes` is already set on
this user, so it runs when logged out too.

A systemd unit gets none of the login shell's PATH, and `gh` lives in
`~/.local/bin` here. That is why the unit sets PATH explicitly, and why the
script checks for `gh` and writes to a log rather than dying silently: a
trigger that quietly stops triggering is worse than one that never worked.

    systemctl --user list-timers scrollreel-daily.timer
    tail ~/.local/state/scrollreel-daily.log

## If this machine is not enough

The timer only fires when the machine is on. For something that does not depend
on that, the same one-line `gh workflow run` belongs on anything always-on: a
Cloudflare Worker cron trigger is free and needs no server. That needs a token
with `workflow` scope on the repo, which is a decision for a human rather than
something to leave lying in a file.
