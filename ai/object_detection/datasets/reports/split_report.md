# Dataset Split Report

- **Created:** 2026-07-04T03:00:00+00:00
- **Seed:** 42 (deterministic — identical inputs always reproduce this split)
- **Ratios:** train 70% / val 20% / test 10%
- **Total images:** 12545

## Images per split

| Split | Images | Share |
|---|---|---|
| train | 8783 | 70.0% |
| val | 2515 | 20.0% |
| test | 1247 | 9.9% |

## Leakage prevention (scene-aware assignment)

Export variants of the same original photograph (Roboflow
`.rf.<hex>` copies — augmented or recompressed) are grouped
into one scene, and every scene is assigned to exactly one
split, so no photograph can appear in both train and val/test.

- Scenes: 9956 (1061 with more than one image, covering 3650 images)
- Largest scene: 22 images

## Stratification by class signature

Scenes are grouped by the dominant set of classes their
images contain and each group is split independently, so every
split sees a similar class mixture.

| Signature | Train | Val | Test |
|---|---|---|---|
| fire | 2846 | 813 | 406 |
| fire+smoke | 1840 | 531 | 257 |
| negative | 1 | 0 | 0 |
| person | 1885 | 539 | 269 |
| smoke | 2211 | 632 | 315 |
