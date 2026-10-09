---
title: Merging
summary: How a closed slice's pull request is merged — never red, never stale, never without a yes.
audience: 8
---
# Merging

Run by `merge`; reviewing is `reviewing.md`. Tone: audience 8. The pull request's slice is found
from the argument (`SL-n` or a PR number), or from the current branch's `open` / `closed` slice.

## Merge — `/spry:merge`

**Every step, every time.** Each exists because skipping it once went wrong.

1. **Checks are green:** `gh pr checks <n>`. Red → stop and say which. Pending → wait, or stop and
   say so. **Never merge a red or pending PR.** Nothing on the platform may stop it, so this step is
   the only guard.
   - **A check that never ran is not green, and not red.** CI could not start — a billing lock, used-up
     minutes, an outage: its jobs failed with no step run
     (`gh run view <run> --json jobs -q '.jobs[] | [.name, .conclusion, (.steps | length)]'` shows
     `0`), or the PR has no checks though the repository has CI. A job that ran a step and failed is
     red.
   - Then **the gate stands in for CI**, on the PR's head: the branch checked out, the working tree
     clean, `git rev-parse HEAD` equal to `headRefOid`. Run `spry.py check --base origin/<main>`, then
     `spry.py gate` — a green stamp for this exact code counts, so a gate that just passed is not run
     again. Red → stop, as for red CI. Green → carry `CI did not run (<reason>); gate green locally`
     to step 6, and pass `--ci-local "<reason>"` to `merge-message` at step 7.
   - Never from memory: each merge looks at its own checks. CI that was down yesterday may be up.
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
   accepts: a survivor or skipped control with its reason, a criterion with no test, CI that did
   not run. Merge only on a yes given in this conversation, for this PR.
   - **Already answered** when the person chose *fix, then merge* in a review of this PR
   (`reviewing.md` §5a) and every `!` here was in that review's report. Anything new — a `!` the
   report did not name, CI that did not run — is asked, as above.
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
       `gh run watch <id> --exit-status`. No CI on push, or CI that cannot run (step 1) → run
       the full suite once (`/spry:test-all`), and say why. Red → say so at once, and offer a bug or a revert — never
       leave it.
   - Report: what merged; what is unblocked now (items whose `blocked_by` named this slice or its
     parent, and the next `planned` slice); each `!` from step 2 as a `[Test]` for QA.
9. **Never:** force-push the main branch, merge with `--admin` to skip checks, or merge a PR the
   person has not named.
