---
name: memory-check
description: Audit Claude Code's auto-memory for this checkout — the index against its files, and every memory's claims against the repository, the plan and GitHub — then propose keep, update or delete for each stale one with its reason, and change nothing until the person approves. Use when asked to check, clean up or prune the agent's memory, or when MEMORY.md has grown long.
argument-hint: "[memory folder, optional — default: this checkout's]"
---

# spry — memory-check

Claude Code keeps its memory outside the repository, in one folder per checkout that every worktree
shares: `MEMORY.md`, the index loaded into every session, and one file per fact. Nothing in it is
checked, so it goes stale. Its files are the person's, not the project's: this skill commits nothing.

1. **The facts the tool can settle:** run `git fetch -q origin`, then
   `python3 spry/tool/spry.py memory-check --json` (with `--dir $ARGUMENTS` when given; it follows
   `autoMemoryDirectory` in Claude Code's settings). It reads:
   - the index against the files — dead lines, files no line points at, size against the budget;
   - front-matter, and dates that have passed in a clause still to do ("queued", "decides 10-17");
   - the plan items, pull requests and issues (through `gh`), commits and paths each memory names, and
     whether each still exists, is closed or is merged;
   - text a repository file already holds, and memories that overlap.
   No folder → say so and stop.
2. **Read the index and every memory**, not only the flagged ones. The tool cannot tell what a sentence
   claims; you can. Check each claim about this project against what is true now:
   - the code and documents on `origin/<main_branch>`, not the working tree;
   - `spry status`, `spry backlog` and the items it names;
   - `gh` for pull requests, issues and settings a memory states — branch protection is
     `gh api repos/{owner}/{repo}/branches/<branch>/protection`;
   - `AGENTS.md`, `spry/knowledge/` and `spry/process/`: a memory that repeats them, or a rule they now
     hold, is not worth keeping (memory is for what the repository does not record).
   A `user` or `feedback` memory is kept unless the evidence says it changed; a `project` or
   `reference` memory is where staleness lives.
3. **Decide each memory:** `keep`, `update` (with the new text — and its index line, under the budget)
   or `delete`, each with a one-line reason that names its evidence (`#1626 merged 2026-10-30`,
   `SL-412 closed`, `now in AGENTS.md §Merging`). Two overlapping memories → one update and one delete.
   An index over its budget or a line over `line_chars` is an `update` of that memory's index line —
   shorter, the detail left in its file — even when the memory itself is current. A file the index
   misses is an `update` that adds its line, or a `delete`.
   Sort every change into one of two kinds:
   - **obvious** — the evidence settles it: a dead index line, a file the index misses, a reminder or
     decision whose day has passed and whose work is done, an item or pull request now closed or
     merged, a path renamed with one clear successor, text the repository holds word for word;
   - **tricky** — it needs a judgement: a claim only partly true, a preference that may still hold, a
     merge of two memories, deleting a `user` or `feedback` memory, a date passed with no sign the
     thing happened, anything you would want to ask about.
4. **Reply** per `spry/process/chat.md`, at the tone in `.spry/tone`, else 7:
   - `DONE` — `[Checked]` how many memories, and the index's size against its budget;
   - `[Found]` one bullet per change: the file, `update` or `delete`, the reason;
   - `FYI` — the memories kept, in one bullet, by count;
   - `ASK` 1 — the obvious changes, numbered in the bullets above:
     a. apply them all (recommended) · b. apply all but the ones you name · c. apply none;
   - one further ask per tricky change, its current and proposed text quoted:
     a. you edit it yourself, from the text proposed here (recommended) · b. I apply it as proposed ·
     c. keep it as it is.
5. **Apply only what was approved**, nothing else: edit or delete those memory files, and change only
   their lines in `MEMORY.md` — a deleted file's line removed, an approved line rewritten as
   `- [Title](file.md) — hook`. Every other line stays as it is. Never write a memory that was not
   approved, and never touch the repository.
6. **Run step 1 again** and report what is left, as `[Fixed]` and `[Note]` bullets.
