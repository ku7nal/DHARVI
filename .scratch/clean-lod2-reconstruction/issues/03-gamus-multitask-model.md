# 03 — Train and evaluate the GAMUS multitask model

**What to build:** A reproducible training and evaluation path produces a checkpoint that predicts both estimated nDSM height and GAMUS semantic classes, with metrics that show whether building boundaries improve without materially worsening height quality.

**Blocked by:** 02 — Add a semantic scene contract

**Status:** ready-for-agent

- [ ] GAMUS images, heights, and classes are discovered, validated for alignment, and split geographically into train and validation data.
- [ ] The model retains the current height branch initialization and adds a separately initialized semantic branch.
- [ ] Training uses masked weighted height loss, height-gradient loss, and class-balanced semantic loss.
- [ ] Evaluation reports height RMSE, MAE, correlation, semantic mIoU, building F1, and building-boundary F1 using full-image tiled inference.
- [ ] Baseline and multitask checkpoints remain separately identifiable.
