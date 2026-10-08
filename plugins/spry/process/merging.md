---
title: Reviewing and merging
summary: How a closed slice's pull request is reviewed against its work order, and how it is merged — never red, never stale, never without a yes.
audience: 8
---
# Reviewing and merging

Run by `review` and `merge`. Tone: audience 8. The pull request's slice is found from the argument
(`SL-n` or a PR number), or from the current branch's `open` / `closed` slice.

## Review — `/spry:review`

For whoever reviews: a teammate, or the author before asking for one. **Reads and comments; never
changes the code and never merges.**

1. **Read *For the reviewer* first** — at the top of the PR body: the criteria in words, any that
   changed, what falsify could not show, what QA checks by hand. Then the work order, then the diff (`gh pr diff <n>`). The question is not "is this good
   code" but "is this what the work order said, and nothing it said not to do".
2. **Check, in order:**
   - **Plan** — every file it named changed as described; any file changed that it did not name is
     explained in `What changed`.
   - **Must not** — each linked rule still holds in the diff.
   - **Tests** — one per covered criterion at least, each name citing `<story>/AC-<n>`, each
     asserting what the criterion's *Then* says, not something nearby.
   - **Falsify** — every row `caught`; a `survived` or `skipped` row has a reason you accept.
   - **Conventions** — the areas the diff touches (`spry/knowledge/conventions/INDEX.md`).
   - **Demo** — run it when it can run locally; say so if you did not.
3. **Write the review** as findings, each `path:line — what — why`, grouped `Blocker` · `Should` ·
   `Nit`. Show it to the person first.
4. **Post it only on a yes:** `gh pr review <n> --request-changes` when there is a blocker,
   `--comment` otherwise, `--approve` only when the person says to approve.

## Merge — `/spry:merge`

**Every step, every time.** Each exists because skipping it once went wrong.

1. **Checks are green:** `gh pr checks <n>`. Red → stop and say which. Pending → wait, or stop and
   say so. **Never merge a red or pending PR.** Nothing on the platform may stop it, so this step is
   the only guard.
2. **The slice is ready:** on the PR's branch,
   `python3 spry/tool/spry.py merge-check SL-<n> --base origin/<main>`.
   `✗` → stop and say what to do. `!` → say it, and carry it to step 6. It blocks when:
   - a control the diff adds has no falsify row — the agent never leaves one out;
   - the branch changes a criterion and code together, and the slice has no
     `criteria_approved_by: <name>` from the story's owner. Show them the old and new text; only
     their yes, in their words, puts that line in — never the agent's judgement.
3. **The PR body is the slice file's:** `spry.py pr-body SL-<n> --base origin/<main>` against
   `gh pr view <n> --json body`; refresh it with `gh pr edit <n> --body-file -` when they differ.
4. **Approval:** with a team configured, `gh pr view <n> --json reviewDecision` is `APPROVED`. Solo
   projects skip this.
5. **The base has not moved under it:** `git fetch`; if the main branch gained commits since the
   branch was cut and they touch any file this PR touches (`git diff --name-only`), the PR's green
   checks are against an old base — ask to rebase, push, and start again at step 1.
6. **Ask:** one line — what merges, the trailer it carries — and each `!` item as something the person
   accepts: a survivor or skipped control with its reason, a criterion with no test. Merge only on
   a yes given in this conversation, for this PR.
7. **Merge:** first note the PR's head, `head=$(gh pr view <n> --json headRefOid -q .headRefOid)`,
   for step 8. Squash, with the commit from `spry.py merge-message SL-<n>` — its subject as
   `--subject`, the rest as `--body`; the `Slice:` trailer lives in the commit, because a squash
   keeps nothing else. `gh pr merge <n> --squash --subject "…" --body "…" --delete-branch`.
8. **After the merge:**
   - `git checkout <main> && git pull --ff-only && git fetch --prune`; delete the local branch with
     `git branch -D` (a squash merge makes `-d` refuse).
   - **Did the main branch move under it?** `python3 spry/tool/spry.py changed --base "$head"`
     compares the PR's head with the main branch as it is now.
     - `code=false`: the main branch's code is exactly what the PR's checks passed — the only
       commits it gained were documents. **Run nothing**, and say so in the report.
     - `code=true`: it gained code the PR's checks never saw, and a PR green against its base can
       be red against the main branch it landed on. **Wait for CI on the main branch** — it runs
       the full suite there; never run it again here.
       `gh run list --branch <main> --commit $(git rev-parse HEAD) --json databaseId`, then
       `gh run watch <id> --exit-status`. No CI on push → run the full suite once
       (`/spry:test-all`), and say why. Red → say so at once, and offer a bug or a revert — never
       leave it.
   - Report: what merged; what is unblocked now (items whose `blocked_by` named this slice or its
     parent, and the next `planned` slice); each `!` from step 2 as a `[Test]` for QA.
9. **Never:** force-push the main branch, merge with `--admin` to skip checks, or merge a PR the
   person has not named.
