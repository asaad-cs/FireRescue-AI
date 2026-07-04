# Dataset Quality Report

- **Dataset:** `C:\Users\Administrator\Desktop\FireRescue-AI\ai\object_detection\datasets\processed`
- **Generated:** 2026-07-04T03:03:32+00:00
- **Total images:** 12545
- **Total annotations:** 32783
- **Negative samples:** 2

## Images and annotations per class

| Class | Images containing it | Annotations |
|---|---|---|
| fire | 6629 | 12043 |
| smoke | 5857 | 9963 |
| person | 2693 | 10777 |

## Per split

| Split | Images | Negatives | fire | smoke | person (boxes) |
|---|---|---|---|---|---|
| test | 1247 | 1 | 1178 | 1010 | 1059 |
| train | 8783 | 1 | 8467 | 6968 | 7603 |
| val | 2515 | 0 | 2398 | 1985 | 2115 |

## Dataset balance

- Largest/smallest images-per-class ratio: **2.46x**

## Deduplication and cleaning (from merge)

- Duplicate images skipped: 1169
- Corrupted images excluded: 0
- Malformed label files excluded: 0
- Boxes dropped (unmapped classes): 0
- Boxes dropped (invalid geometry): 0

## Validation findings

- Errors: **0** · Warnings: **2** (details in `dataset_report.md`)
- Broken images: 0
- Missing labels: 0

## Potential issues

- none detected

## Recommendations

- dataset is structurally clean — proceed to Phase 8D (first training run)
- review per-class sample images before training to catch annotation quality problems automation cannot see
