# 01 — Add draggable elevation pin to the reconstruction viewer

**What to build:** Add a bottom-left pin tool that lets users click-drag across the 3D reconstruction, samples the selected height-grid cell, and shows an attached meter callout using the correct relative or absolute label.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] The bottom-left scene-control rail contains an accessible pin tool with active and inactive states.
- [ ] Activating the tool enables click-drag placement over the render and temporarily suspends camera dragging.
- [ ] The selected point is clamped to the available height grid and samples the raw `heightData` value without visual exaggeration.
- [ ] The pin remains at the last selected point after release, can be repositioned while the tool remains active, and can be exited with the control or Escape.
- [ ] The attached callout displays `Elevation · X.X m` for absolute calibrated results and `Estimated height · X.X m` for relative nDSM results.
- [ ] Pin placement and route-point selection cannot be active simultaneously.
- [ ] Frontend typecheck and production build pass.
