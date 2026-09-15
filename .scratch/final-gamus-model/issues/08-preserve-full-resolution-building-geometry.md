# 08 — Preserve Full-Resolution Building Geometry in the Scene

**What to build:** The website's 3D output uses the highest practical model-resolution predictions for building extraction before reducing data for terrain rendering. Small structures, clean footprints, holes, local ground heights, roof-height variation, and building boundaries survive the model-to-scene transition without sacrificing browser responsiveness.

**Blocked by:** 06 — Integrate the Production Checkpoint and Full-Image Inference.

**Status:** ready-for-agent

- [ ] Building extraction happens before coarse terrain-grid reduction whenever a higher-resolution prediction is available.
- [ ] Small legitimate buildings are retained while isolated noise is removed, and meaningful footprint holes and irregular outlines remain usable.
- [ ] Walls are grounded to local terrain and procedural roofs connect to wall tops without floating, sinking, or façade texture smearing.
- [ ] Distant buildings use reduced geometry while nearby buildings retain detailed footprints and roofs.
- [ ] Vegetation and tree geometry remain bounded and the scene stays within the target browser performance budget.
