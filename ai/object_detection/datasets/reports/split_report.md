# Dataset Split Report

- **Created:** 2026-07-02T21:06:41+00:00
- **Seed:** 42 (deterministic — identical inputs always reproduce this split)
- **Ratios:** train 70% / val 20% / test 10%
- **Total images:** 12545

## Images per split

| Split | Images | Share |
|---|---|---|
| train | 8781 | 70.0% |
| val | 2509 | 20.0% |
| test | 1255 | 10.0% |

## Stratification by class signature

Images are grouped by the set of classes they contain and each
group is split independently, so every split sees a similar
class mixture.

| Signature | Train | Val | Test |
|---|---|---|---|
| fire | 2795 | 799 | 399 |
| fire+smoke | 1845 | 527 | 264 |
| negative | 1 | 0 | 1 |
| person | 1885 | 539 | 269 |
| smoke | 2255 | 644 | 322 |
