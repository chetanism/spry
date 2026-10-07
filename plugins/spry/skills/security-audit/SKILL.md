---
name: security-audit
description: Review the product, a milestone, an area or a branch for security problems against the project's security rules — access, sign-in, input, personal data, secrets, dependencies, external services — and write a report whose findings become bugs or tasks. Reports only; never fixes.
argument-hint: "[scope: product | milestone ID | area | branch]"
---

# spry — security-audit

- **Procedure:** `spry/process/audits.md` → *Start*, *Security audit*, *Finish*. Read `chat.md` beside it.
- **Template:** `spry/process/templates/audit.md`.
- **Scope:** `$ARGUMENTS`, or ask.
- **Never fix in passing,** however small — a finding becomes a bug or task the person approves.
- Run only commands that read: audits, greps, builds. Ask before anything that sends data out.
