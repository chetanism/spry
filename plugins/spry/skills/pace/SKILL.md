---
name: pace
description: Read where slices' time went and propose what to change — a process change, a config change, a bug or task, or nothing — one proposal per finding, each with its evidence. A fresh agent judges; the numbers come from spry pace. Report only; never edits. Use when slices feel slow, after a process change to see if it helped, or when asked what to improve.
argument-hint: "[SL-n | --since YYYY-MM-DD | --last N | --compare POINT, optional]"
---

# spry — pace

`spry pace` measures and never judges (§17). This skill judges. It changes nothing, commits nothing,
and writes nothing but what `spry pace` keeps under `.spry/`.

1. **The numbers:** run `python3 spry/tool/spry.py pace $ARGUMENTS`, which writes
   `.spry/view/pace.md`. For one slice it prints that slice and stops; use the page for the rest.
   No page, or "no slice time found" → say that no session or step log names a slice yet, and stop.
2. **A fresh agent reads them** — a new agent, never this session or a fork of it (§2). Give it the
   page, `spry/knowledge/process-changes.md` and `pace` in `spry/spry.config.json`, and for each
   flagged slice `spry pace <SL-n>`. It reads those and not the session logs, which hold everything the
   agent saw. It returns, for each finding: the evidence (slice and number), what it means, and one
   proposal.
3. **What counts as a finding:**
   - a flag on the page, with the slices it names — a flag on one slice is a note, on several a finding;
   - a category whose share is high across the slices, or that moved after a dated change;
   - **Before and after each change** shows *too few slices to tell* → no finding from it. Say so, and
     name how many slices are still needed. Never read a difference into fewer than 10 a side.
4. **One proposal per finding**, each of these and nothing else:
   - **process change** — a rule, a template or a step in `spry/process/` → `/spry:process-change`;
   - **config change** — a key in `spry/spry.config.json` (`falsify.parallel`, `falsify.setup`,
     `pace.flags`, `hooks.*`, `tests.*`), with the value;
   - **a bug in spry** — a flag the page itself calls a spry bug, such as tests run again on code
     that had passed → `/spry:contribute`;
   - **a bug or task in the project** — a slow or flaky test, a slow gate step → `/spry:bug`,
     `/spry:task`;
   - **nothing** — the time is where the work is. Say so; a clean page is a result.
   A proposal with no evidence behind it is not made. Flags describe; the agent decides what to
   propose, and says how sure it is.
5. **Reply** per `spry/process/chat.md`, at the tone in `.spry/tone`, else 7:
   - `DONE` — `[Checked]` how many slices and the range, and the median active time;
   - `[Found]` one bullet per finding: the evidence, then the proposal and the skill that carries it out;
   - `FYI` — what had too few slices to tell, and the flags that are only notes;
   - `ASK` 1 — which proposals to start: a. all the process and config changes, one after the other
     (recommended) · b. only the ones you name · c. none.
   A process change starts `/spry:process-change` with the finding as its sentence; a config
   change is made there too; a bug in spry or the project starts the skill named. Nothing starts
   before the answer.
6. **Later:** after a process change lands, run this again; **Before and after each change** then sets
   the slices closed after it against the same number before, and says whether it helped.
