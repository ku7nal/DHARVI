# 01 — Create a repeatable reconstruction failure review

**What to build:** A repeatable review set for clear-building and dense-city images that shows the input, height prediction, semantic labels, building footprints, and final scene in alignment. Each case records the earliest stage where the result diverges, so follow-up work targets the actual cause.

**Blocked by:** None — can start immediately.

**Status:** resolved

- [x] The review set includes clear-building and dense-city examples, including the supplied New York and Mexico City images.
- [x] Each case presents aligned input, height, semantic, footprint, and final-scene views.
- [x] Each case records the earliest stage where the output visibly diverges from the source image.
- [x] Review results distinguish visual assessment from reference-backed accuracy measurements.

## Answer

Added a repeatable inference review command and captured aligned visual stages plus live application scenes for the Zaalima clear-building case and the supplied New York and Mexico City dense-city images. Zaalima first loses detail in the height prediction; both dense-city examples show their clearest failure in semantic classification. Mexico City's scene-grid mask labels 83.4% as `others` and 2.4% as `building`. Findings are qualitative because no aligned reference raster is available. See [the review report](../review/index.html) and [reproduction notes](../review/README.md).
