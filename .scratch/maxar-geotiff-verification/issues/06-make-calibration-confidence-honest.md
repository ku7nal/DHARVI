# 06 — Make calibration confidence honest about anchor uncertainty

**What to build:** The calibration confidence value returned with a metric DSM reflects only the model's internal ground-pixel consistency, not the uncertainty of the user-supplied ground-elevation anchor — so a DSM anchored to a guessed elevation still reports 0.99+ confidence. Users reading that number as real-world accuracy are misled.

Verified during the Maxar exercise (ticket 04): all three fixtures reported confidence 0.996–0.9999 even though the elevation anchors (10 m / 15 m / 550 m) were plausible guesses whose error the DSM silently inherits.

**Blocked by:** None — can start immediately.

**Status:** ready-for-agent

- [ ] Calibration response distinguishes internal consistency confidence from anchor-source confidence (or documents the distinction in the response schema).
- [ ] When evidence comes from a user-supplied scalar elevation with no stated provenance, the reported confidence or an accompanying field makes clear the anchor itself is unverified.
- [ ] GCP-based calibration residual error is reported against the fitted surface in a way that cannot be confused with absolute-accuracy claims.
- [ ] Backend tests cover the new response shape; existing tests updated.
