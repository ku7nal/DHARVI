# 04 — Responsive verification and rollback checkpoint

**What to build:** Make the Dharvi editor usable at smaller widths, verify the complete redesign, and create a frontend-only git checkpoint that can restore the pre-redesign state without absorbing unrelated work.

**Blocked by:** 02 — Functional layers and style controls; 03 — Light reconstruction workspace and editor chrome.

**Status:** ready-for-agent

- [ ] The narrow rail remains usable while the wide panel collapses into an accessible drawer without horizontal overflow.
- [ ] Desktop and mobile layouts preserve access to navigation, layer controls, upload, viewer, and inspector behavior.
- [ ] Frontend type checking and production build pass after the redesign.
- [ ] The checkpoint commit contains only Dharvi frontend changes/assets and excludes unrelated backend, scratch, and documentation changes.
- [ ] The checkpoint commit hash is recorded for rollback.

