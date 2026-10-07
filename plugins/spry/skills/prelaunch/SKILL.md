---
name: prelaunch
description: A go / no-go review before a release — every story proven, no blocker bugs, a recent security audit, manual rule checks done, production configuration, data, alerting and build contents checked — written as a report with a verdict. Never deploys.
argument-hint: "[milestone ID or release name]"
disable-model-invocation: true
---

# spry — prelaunch

- **Procedure:** `spry/process/audits.md` → *Start*, *Pre-launch review*, *Finish*. Read `chat.md` beside it.
- **Template:** `spry/process/templates/audit.md`.
- **Scope:** `$ARGUMENTS` — the milestone or release; or ask.
- **Never deploy,** and never change production configuration. The verdict is the person's to act on.
