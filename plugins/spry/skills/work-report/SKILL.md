---
name: work-report
description: Report what one person built between two dates — each story, task and bug they worked on with a two-to-three-line summary of their part, the slices under it by ID and title, and what they are building now — from the slices' owners and closed dates. Report only; never edits the repository. Use when asked what someone did, for a person's weekly or monthly report, or for a review of their work.
argument-hint: "<person> [from YYYY-MM-DD] [to YYYY-MM-DD]"
---

# spry — work-report

1. **Who and when:** from `$ARGUMENTS` — a person (their `team.members` name or GitHub login) and
   a range. A range in words ("last week", "October") becomes two dates, said back in the reply.
   No person → ask; no range → the last 7 days, to today.
2. Run `python3 spry/tool/spry.py work <person> --since <from> --until <to> --json`. It lists the
   person's slices closed in the range under the story, task or bug each builds, newest first; what
   they are building now; and what it could not count. A slice counts for its `owner:` — who built
   it — and its `closed:` date, never git.
3. **Summarise each item from the files, never the diff:** for every item, read its `doc` (the
   story's, task's or bug's opening) and, for each of the person's slices, its *Summary* and *What
   changed* under *Close summary*. Write 2–3 lines on what this person's slices did for the item —
   what someone can now do or see — not how. Where `others` is not empty, the lines cover only
   this person's part.
4. **Reply** per `spry/process/chat.md`, at the tone in `.spry/tone`, else 5 — as the report itself:
   - a heading per item: `<ID> <title>` · type · where it stands (the `progress` given), then the
     summary lines, then one bullet per slice: `<SL-n> <title>` and the day it closed — nothing more
     about a slice;
   - *In progress now*: one bullet per slice;
   - `[Note]` bullets for what the tool could not count: `unowned` slices (closed in the range with
     no owner — they may be this person's), `undated` ones (left out). For unowned slices,
     `/spry:update` names the one-time fill from pull requests (CH-40).
   - Nothing closed and nothing open → say so, and name the owners the tool lists, in case the
     name was spelled another way.
5. **Write nothing** to the repository. Asked for a file → `.spry/reports/work-<person>-<from>-<to>.md`
   (gitignored), and say where.
6. Never invent work: an item, slice or date not in the tool's output is not in the report.
