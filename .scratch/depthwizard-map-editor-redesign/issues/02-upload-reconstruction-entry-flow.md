# 02 — Move the upload flow into the new workspace

**What to build:** Present the complete New reconstruction entry flow inside the map-editor shell, including the empty upload state, drag-and-drop, file picker, processing state, prediction failure and retry state, supported formats, and the GAMUS example action.

**Blocked by:** 01 — Build the map-editor workspace shell

**Status:** ready-for-agent

- [ ] Idle upload state is visually integrated into the dark editor-side workspace without changing accepted formats or upload behavior.
- [ ] Drag-and-drop, file selection, processing feedback, retry behavior, and error messaging continue to work.
- [ ] The GAMUS example action still starts a prediction through the existing backend contract.
- [ ] Empty, processing, and error states remain readable and usable on narrow viewports.
