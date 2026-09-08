# 02 — Fixture-backed reconstruction upload

**What to build:** A user can upload a supported image or choose a GAMUS example, receive a synchronous fixture-backed prediction, and see processing, success, and error states.

**Blocked by:** 01 — Application shell and local workspace

**Status:** ready-for-agent

- [ ] The upload workspace accepts PNG and JPEG files.
- [ ] A user can select a built-in GAMUS example without uploading a file.
- [ ] The frontend sends the input through the prediction API seam.
- [ ] The backend returns a fixture-backed prediction result with input asset, estimated nDSM asset, dimensions, value range, result type, and processing status.
- [ ] The frontend displays a visible processing state while the request is active.
- [ ] A successful response transitions the workspace into a result state.
- [ ] Failed requests produce an actionable user-facing error.
- [ ] The original input image is preserved for later comparison.
