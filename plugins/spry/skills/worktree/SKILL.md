---
name: worktree
description: Move this session into a worktree of its own, so several sessions build side by side. Use when starting a second session.
argument-hint: "[index | name | new]"
---

# spry — worktree

- **Rules:** `spry/process/slicing.md` → *Worktrees*. Replies: `chat.md`.
- **No `worktrees` block** in `spry/spry.config.json` → say so, show the block from
  `slicing.md` *Worktrees*, and stop. Never write it without the person's yes.

1. **Which one.**
   - `$ARGUMENTS` is a name or an index → step 2 with it.
   - `new`, or a name `worktree list` does not show → `python3 spry/tool/spry.py worktree new [name]`.
     It makes the worktree on its home branch at the main branch's head and runs `worktrees.setup`
     there. A failed set-up is said and stops here: the person fixes it.
   - Empty → `python3 spry/tool/spry.py worktree list`, then ask which, as numbered asks — each
     free one, and *a new one* while under `worktrees.max`. One `(recommended)`: the lowest free
     index. A claimed one is never offered.
2. **Claim it:** `python3 spry/tool/spry.py worktree claim <name|index>`. Refused because another
   live session holds it → say whose, and go back to step 1. A stale claim taken → say so.
3. **Move the session there.** The tool's last line is the worktree's path.
   - In Claude Code, enter it with the `EnterWorktree` tool, given that path; every command after
     runs there.
   - Where the session cannot move, print the path and tell the person to start a session in it
     (`cd <path> && claude`), then `release` the claim here: the new session claims it itself.
4. **Report** in two lines: the worktree, its index and branch; what the next slice is
   (`spry.py backlog --section ready --rows 1 --plain`) or the open slice its branch builds.

- **Never** enter a worktree another session claimed, run `worktree release --force` without the
  person's yes, or delete a worktree: `worktree prune` removes only falsify's scratch trees and the
  records of worktrees already gone.
