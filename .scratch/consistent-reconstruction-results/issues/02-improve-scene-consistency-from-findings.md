# 02 — Improve scene consistency based on the failure review

**What to build:** Apply a verified correction at the stage identified by the failure review, so dense urban images produce more coherent scenes while clear-building examples retain their quality. Address model generalization only if the review shows that raw predictions are the source of failure.

**Blocked by:** 01 — Create a repeatable reconstruction failure review.

**Status:** needs-info

- [ ] The failure review identifies the stage responsible for the targeted inconsistency.
- [ ] The correction improves dense-city scene coherence on the review set.
- [ ] Clear-building examples retain their existing scene quality.
- [ ] Changes do not conceal model errors or present unverified predictions as measured accuracy.
- [ ] Any model-generalization changes are supported by representative training or validation data.

## Comments

Implementation is waiting on representative dense-city semantic labels. The failure review isolates the divergence to raw semantic predictions for New York and Mexico City, but its inputs have no aligned reference raster. The saved checkpoint's GAMUS validation report does not validate these target images, and no labeled training/validation rasters are present in this checkout. Changing scene postprocessing or substituting height-based building regions would mask semantic errors without verifying improved coherence. Provide aligned building/semantic labels for representative dense-city imagery before choosing and validating a model correction.
