# Dataset Audit — Manual Deep Analysis (2026-07-03)

Read-only audit of `datasets/processed/` performed before the D-Fire merge
and the 50-epoch training run. Complements the pipeline-generated reports
(`dataset_report.md`, `quality_report.md`) with perceptual-hash duplicate
analysis and visual sample inspection that automation does not cover.

**Method:** full scan of all 12,545 images (PIL header + 64px decode):
resolutions, box geometry, brightness, dHash near-duplicate clustering;
plus visual inspection of stratified 18-image contact sheets per class
signature. No project files were modified by the audit itself.

---

## Headline findings

1. 🔴 **Train/val/test near-duplicate leakage.** *(FIXED 2026-07-04 —
   see addendum at the end of this report.)* The pipeline dedupes by
   md5 (byte-identical only). dHash finds **1,038 clusters of visually
   identical images (2,617 images, 20.9%)** — Roboflow augmented variants
   and adjacent video frames. Because the split is per-image:
   **423/2,509 val images (16.9%) and 196/1,255 test images (15.6%) have a
   near-duplicate in train** (visually confirmed — identical scenes across
   splits). All val/test metrics (incl. Phase 8D mAP50 0.509) are inflated;
   estimate ~5–10 mAP50 points. **Fix before trusting any metric:** split
   by hash-cluster/scene group, not by image (`data_tools/split.py`).
2. 🔴 **Zero fire+person / smoke+person co-occurrence.** Fire/smoke come
   only from Figshare (no person labels), persons only from COCO (no fire).
   Unlabeled firefighters visible in fire images actively teach
   "person near fire ≠ person". This is the biggest gap vs. the mission.
3. 🟠 **2 negative samples.** No false-positive suppression signal —
   explains the known spurious detections in safe zones.
4. 🟠 **Heavily outdoor.** Fire/smoke ≈85–90% outdoor (wildfire, aerial
   plumes, gas flares). Indoor structural fire (room/office/warehouse/
   kitchen/electrical) is scarce; dense interior smoke absent.
5. 🟠 **No lying/collapsed/crawling victims.** COCO poses are civilian
   (standing/sitting/sports).
6. 🟡 Junk samples observed: stock watermarks, caption-burned thumbnails,
   ≥1 synthetic composite, baked-in augmentations (rotated/flipped copies
   with black corners — also the source of the duplicate clusters).

## Key numbers

- 12,545 images / 32,783 boxes / 3 classes; splits 8,781/2,509/1,255
  (70/20/10, stratified — class mixture consistent across splits).
- Images containing class: fire 6,629 · smoke 5,857 · person 2,693.
  Boxes: fire 12,043 · smoke 9,963 · person 10,777 (person: 4.0 boxes/img,
  concentrated in 21.5% of images).
- Resolutions: 78.7% 640×640 (Figshare letterboxed, original res lost);
  rest COCO natives.
- Box sizes (COCO buckets): fire 3.6% small / 34.6% med / 61.9% large
  (median 14,760 px²); smoke 1.6/13.3/85.1 (42,600 px²); person
  29.7/34.5/35.7 (3,756 px², 7.8% tiny <12px). Small distant fires
  barely represented.
- Brightness: 4.5% very dark, 18% dark, 75% mid, 2.3% bright (median
  luma 104); 602 dark images contain fire — decent night coverage.
- Structural quality: 0 corrupted / malformed / invalid / out-of-bounds
  (independent scan agrees with pipeline validator).

## Training-readiness verdict (dataset as-is)

Sufficient for a mid-quality generalist outdoor fire/smoke detector; NOT
sufficient for a high-quality mission model. Expected at 50 epochs:
mAP50 ≈0.70–0.80 on current val, honest generalization ≈0.62–0.72 after
discounting leakage. Precision is the weakest axis (no negatives);
recall weakest for person-in-emergency, lying victims, small fires.

## D-Fire (not yet downloaded)

Would add 21,527 imgs incl. **9,838 negatives** → biggest available win
for precision/FP suppression + doubles smoke boxes. Would NOT fix:
person co-occurrence, lying victims, indoor scarcity, split leakage
(D-Fire is partly video-derived — may add its own clusters; fix the
split method in the same pass). **Recommendation: merge D-Fire before
the 50-epoch run.**

## Recommendations (highest impact first)

1. ~~Cluster-aware split (fix leakage)~~ — **done 2026-07-04, see addendum**
2. Merge D-Fire (negatives → precision); verify 0=smoke/1=fire order
3. Label persons already visible in fire images (fire+person co-occurrence)
4. Add lying/collapsed-pose victim imagery
5. Add indoor structural fire imagery (matches simulator categories)
6. Scale persons via COCO train2017 subset (documented path)
7. Prune junk/baked-augmentation samples (dup clusters give the list)
8. Threshold calibration on the cleaned split after training

---

## Addendum 2026-07-04 — Finding 1 fixed (scene-aware split)

`data_tools/split.py` now assigns whole **scenes** (merged file name
with the Roboflow `.rf.<32-hex>` export suffix stripped) instead of
single images, stratified by dominant class signature, deterministic
under seed 42. The dataset was regenerated via the full pipeline
(merge → split → build → validate → quality) and re-verified:

- New split: **8,783 / 2,515 / 1,247** (70.0 / 20.0 / 9.9%), 12,545
  images unchanged, validator verdict CLEAN (0 errors; the 2 warnings
  are the 2 known negative samples).
- **Scene leakage: 0** — 9,956 scenes (1,061 multi-image, covering
  3,650 images; largest 22), none spans more than one split.
- Class balance held: per-class image-share spread across splits
  ≤ 0.6% for fire, ≤ 0.2% for smoke/person.
- **Residual near-duplicate overlap** (exact-dHash match with train,
  same 64-bit dHash method as this audit): val **201/2,515 (8.0%,
  was 16.9%)**, test **77/1,247 (6.2%, was 15.6%)**. The remainder
  are visually identical images whose file names share no Roboflow
  stem (adjacent video frames, re-uploads) — invisible to the scene
  key. Fully eliminating them requires hash-cluster grouping or
  pruning (recommendation 7).
- Consequence: **metrics on the new val/test are not comparable to
  Phase 8D numbers** (mAP50 0.509 was measured on the old, leakier
  split). Re-evaluate any model on the new split only.

Full details: `split_fix_2026-07-04.md` in this directory.
