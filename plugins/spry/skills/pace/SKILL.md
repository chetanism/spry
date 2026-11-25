---
name: pace
description: Read where slices' time and tokens went and propose what to change, each with its evidence. Report only. Use when slices feel slow.
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
   - **tokens:** spend per 100 lines well above the median of the slice's own row in *By size*, in
     several slices; a context entering close that is most of the peak, so every turn of the close
     pays for it; subagents holding most of the spend with no fall in the main session's. Spend
     is in input-token equivalents, not money — compare slices, never quote a price;
   - **falsify:** many controls `unreliable`, or many seconds a control, across slices;
   - **reruns:** full gates on code a full gate had already tested, or minutes lost to quiet
     retries, across slices;
   - **red checks:** a rule in *Red checks* that failed the gate in several slices — a convention
     the agent has not been taught (`/spry:record`), or a rule the linter can fix by itself
     (a `fix` on its `checks.fast` entry). A check red in most slices with no rule named is run too late: the fast gate
     while building;
   - **subagents:** one kind in *Subagents* holding most of the subagents' time or spend with
     nothing to show for it in *Findings* — reviews that find nothing, fixes longer than the
     build;
   - **findings:** design-review Blockers that keep coming (the stories leave shapes open), a
     review at close that still finds Blockers after a design review, findings recorded and not
     fixed. No `### Review` line in most slices → say the counts are missing, not that the
     reviews found nothing;
   - **bugs filed later:** bugs whose `introduced_by` names a slice — what got past both reviews.
     Several against slices of one size, or against slices whose reviews found nothing, is a
     finding. The slices after a change have had less time for their bugs to be found: a lower
     count there is not yet an improvement. `–` means no bug in the plan names a slice — say the
     field is unused, not that nothing escaped;
   - **size:** judge a change by the rows under *Slices of one size*, never by the medians of all
     slices when their sizes differ. A row with fewer than 10 slices after the change is a
     reading, not a difference;
   - **Before and after each change** shows *too few slices to tell* → no finding from it. Say so, and
     name how many slices are still needed. Never read a difference into fewer than 10 a side.
4. **One proposal per finding**, each of these and nothing else:
   - **process change** — a rule, a template or a step in `spry/process/` → `/spry:process-change`;
   - **config change** — a key in `spry/spry.config.json` (`falsify.parallel`, `falsify.setup`,
     `checks.lock`, `checks.generated`, `pace.flags`, `hooks.*`, `tests.*`), with the value;
   - **a bug in spry** — a flag the page itself calls a spry bug, such as tests run again on code
     that had passed → `/spry:contribute`;
   - **a bug or task in the project** — a slow or flaky test, a slow gate step → `/spry:bug`,
     `/spry:task`;
   - **nothing** — the time is where the work is. Say so; a clean page is a result.
   A proposal with no evidence behind it is not made. Flags describe; the agent decides what to
   propose, and says how sure it is.
5. **Reply** per `spry/process/chat.md`, at the tone in `.spry/tone`, else 7:
   - `DONE` — `[Checked]` how many slices and the range, the median active time, and the median
     spend when the page has one;
   - `[Found]` one bullet per finding: the evidence, then the proposal and the skill that carries it out;
   - `FYI` — what had too few slices to tell, and the flags that are only notes;
   - `ASK` 1 — which proposals to start: a. all the process and config changes, one after the other
     · b. only the ones you name · c. none — recommend *a* when every proposal's evidence stands,
     *b* naming the ones that do when some are thin, *c* when none does; the line says which evidence.
   A process change starts `/spry:process-change` with the finding as its sentence; a config
   change is made there too; a bug in spry or the project starts the skill named. Nothing starts
   before the answer.
6. **Later:** after a process change lands, run this again; **Before and after each change** then sets
   the slices closed after it against the same number before, and says whether it helped.
