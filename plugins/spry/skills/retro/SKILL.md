---
name: retro
description: Look back at how the project is running — where slices' time went and what the agent's memory keeps repeating — and propose what to change in the process, the config, spry or the project, one proposal per finding with its evidence. Runs the pace and memory-check readings together; report only, and a proposal starts its skill only on the person's yes. Use for a regular look back, or when slices feel slow and the agent seems to keep relearning a rule.
argument-hint: "[--since YYYY-MM-DD | --last N | --compare POINT, optional — passed to spry pace]"
---

# spry — retro

`/spry:pace` reads the time; `/spry:memory-check` audits the agent's memory. This skill reads both
and joins them: a rule the agent keeps relearning, and slices that still lose time to it, is one
finding. It changes nothing, commits nothing, and prunes no memory.

1. **The numbers:** do step 1 of the `pace` skill with `$ARGUMENTS` — `spry pace`, which writes
   `.spry/view/pace.md`. Always the page, never one slice: a look back needs every slice, and
   `spry pace <SL-n>` is only the detail the fresh agent asks for. No slice time found → say so; the memory half alone is `/spry:memory-check`,
   so stop and offer it.
2. **The memory:** run `git fetch -q origin`, then `python3 spry/tool/spry.py memory-check --json`.
   No memory folder → go on with the numbers alone and say so in `FYI`.
3. **A fresh agent reads both** — a new agent, never this session or a fork of it (§2). Give it what
   steps 2–4 of the `pace` skill give theirs (the page, `spry/knowledge/process-changes.md`, `pace`
   in the config, `spry pace <SL-n>` for each flagged slice) and the memory report with the memory
   files it names. It returns findings and proposals as the `pace` skill's step 3 and 4 define them,
   and for each says whether a memory bears on it.
4. **When a memory bears on a finding:** all three hold —
   - a pace finding already stands on its own evidence;
   - the memory is a `repeats` finding (text a process or knowledge file already holds), or states
     a workaround for a step of the process;
   - it is about the same step — the agent names the rule and the file that holds it.
   Then the finding says so, and the proposal is aimed at why the rule is not followed: make it
   plainer in the file that owns it (`/spry:process-change`), switch on a hook that says it at the
   moment of the mistake (`hooks.*`), or fix the tool if the rule is wrong.
5. **A memory alone is not a finding.** It is per person and per checkout, so a memory that repeats
   a rule, or a stale one, with no pace finding behind it is one `FYI` line — how many, and that
   `/spry:memory-check` deals with them. No proposal is made from it.
6. **Reply** per `spry/process/chat.md`, at the tone in `.spry/tone`, else 7:
   - `DONE` — `[Checked]` the slices and range, the median active time, and how many memories;
   - `[Found]` one bullet per finding: the pace evidence, the memory that bears on it if one does,
     then the proposal and the skill that carries it out;
   - `FYI` — what had too few slices to tell, the flags that are only notes, and the memories that
     repeat or have gone stale without a finding behind them;
   - `ASK` 1 — which proposals to start: a. all the process and config changes, one after the other
     (recommended) · b. only the ones you name · c. none.
   Nothing starts before the answer. A process or config change starts `/spry:process-change` with the
   finding as its sentence; a bug in spry or the project starts `/spry:contribute`, `/spry:bug` or
   `/spry:task`.
7. **Later:** after a change lands, run this again; the page's **Before and after each change** says
   whether the slices got faster, and the memory report whether the agent stopped repeating the rule.
