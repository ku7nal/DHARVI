# 02 — Harden pin interaction across modes and viewports

**What to build:** Make the elevation pin reliable across camera movement, presentation/debug modes, new predictions, narrow layouts, touch input, and keyboard interaction.

**Blocked by:** 01 — Add draggable elevation pin to the reconstruction viewer

**Status:** ready-for-agent

- [ ] The screen-space pin stays aligned with its sampled terrain point while the camera is moved or changed between supported view modes.
- [ ] The pin resets cleanly when a new reconstruction is loaded and does not appear before a point has been placed.
- [ ] Pin placement works in presentation and debug modes without breaking existing scene inspection or route workflows.
- [ ] The control rail and pin callout remain usable at narrow viewport widths and with touch pointers.
- [ ] The pin control exposes an understandable accessible name, pressed state, focus styling, and Escape behavior.
- [ ] Regression checks cover placement, value labeling, mode conflicts, camera movement, and responsive interaction.
- [ ] Frontend typecheck, production build, and relevant scene checks pass.
