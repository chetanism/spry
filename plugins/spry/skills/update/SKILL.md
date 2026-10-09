---
name: update
description: Bring a spry project up to date with what spry has gained since it was set up — each change offered and explained in the project's own terms, ported only if chosen, adapted to the project, and recorded. Use after updating the spry plugin.
disable-model-invocation: true
---

# spry — update

- **Plugin root:** two folders above this file's folder (`…/plugins/spry`).
- **Procedure:** `<plugin root>/process/updating.md` — the **plugin's** copy, not `spry/process/`'s,
  which is the old one. Read `<plugin root>/process/chat.md` too.
- **The newest spry first** (§0): an installed plugin cannot see a newer one. Update the marketplace
  and the plugin, then read everything — this procedure included — from the new version's folder;
  `/reload-plugins` after.
- **No spry here?** If `spry/spry.config.json` is missing, stop and offer `/spry:init` or `/spry:adopt`.
- Changes nothing before the person has answered every ask.
