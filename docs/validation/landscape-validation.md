# Landscape-stratified validation

The Examples workspace reports four landscape groups: urban, sparse, hilly, and forested. Each group includes aligned input, reference, prediction, and absolute-error previews plus height and semantic metrics:

- height RMSE, MAE, and Pearson correlation;
- semantic mean IoU, building IoU, and building-boundary F1 where labels are available.

## Evidence status

The current fixtures are deterministic visual stress cases. They are useful for exercising the comparison contract and UI, but they are not held-out survey measurements. Their height reference is therefore labelled `relative`, and the UI must not describe them as validated metric DSM evidence. A result may be labelled validated only when the reference is an aligned metric DSM/DTM product, its coordinate and vertical datum are documented, and the tile belongs to a held-out evaluation split.

GAMUS is urban-focused in this repository. Sparse, hilly, and forested groups currently document coverage gaps rather than claiming dataset-backed generalization. Replace each fixture with held-out labelled tiles before publishing group-level numbers.

## Known failure cases and limitations

- Hilly terrain can be confused with building height when the model lacks enough relief context.
- Forest canopy produces a surface model rather than bare-earth terrain and can be penalized by a DTM-style reference.
- Sparse and low-contrast scenes provide fewer building edges and make boundary F1 unstable.
- Relative or nDSM references cannot support absolute elevation claims without geospatial calibration.
- Aggregate metrics can hide localized roof-edge, vegetation, and occlusion errors; retain the visual comparison alongside every score.
