# 03 — Improve semantic preview fidelity

**What to build:** The inspector shows the aligned semantic mask without exaggerated pixelation, clearly distinguishes categorical semantic output from continuous height output, and preserves accurate class colors and dimensions.

**Blocked by:** 02 — Clean semantic masks and building footprints

**Status:** ready-for-agent

- [ ] The semantic preview no longer applies CSS pixelation that exaggerates block boundaries.
- [ ] The displayed semantic image, semantic data, and scene grid share the same coordinate frame and dimensions.
- [ ] Class colors remain categorical and authoritative; the preview is not blurred into misleading intermediate classes.
- [ ] The inspector communicates that semantic output is a discrete mask while height output is continuous.
- [ ] Frontend typecheck, build, and relevant UI/scene checks pass.
