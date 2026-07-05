# Phase 9B Promotion Manifest — Simulation Library Curation

**Date:** 2026-07-05
**Scope:** Roadmap step 10A.4 only (promotion of already-reviewed Phase 9B staging
results). No other roadmap step was executed. No AI logic, simulation selection
logic, or runtime camera pipeline was touched — verified below.

**Source:** `...\scratchpad\phase9b_staging\` (235 staged copies, matching the
Phase 9B report exactly — re-verified by direct count before promotion).
**Destination:** `assets/simulation_dataset/_curation/{approved,manual_review,rejected}/`
— a new subtree inside the existing master library. The leading underscore is
not cosmetic: `export_simulation_library.py:99-101` explicitly skips any
top-level directory starting with `.` or `_` when enumerating categories, so
this entire subtree is structurally invisible to the existing export
tool/runtime pipeline. Nothing here can be pulled into `simulation/camera/images/`
without a deliberate, separate future step.

---

## How Approved vs. Manual Review vs. Rejected was decided

No new curation judgment was made in this pass. Every file's tier was
determined by re-checking this conversation's own record of what was actually
done during Phase 9A/9B:

- **Approved** = the exact file was individually opened and visually confirmed
  (by filename match against this session's tool-call history) as suitable,
  real, structural/building content, with no defect found.
- **Manual Review** = the file was staged based on a filename-cluster pattern
  or a representative random sample, but was **not** individually opened this
  session — or it was opened but flagged in the Phase 9B report as needing a
  human judgment call (caption/content mismatch).
- **Rejected** = an individually-opened file with a confirmed, specific defect
  (toy/miniature model, visible watermark, near-duplicate/augmented copy,
  multi-panel collage).

One cross-tier conflict was found and resolved: `WELLInvolvedHouseFireAggressiveAttack4513`
is a real, confirmed residential fire (part of the 58-file Residential cluster)
**but** carries a visible "FireCam.com" watermark. It was excluded from Approved
and counted only once, under Rejected/watermarked — not double-promoted.

One mis-tiering from the original Phase 9B staging was found and corrected in
the counting (not in content): `recycling-plant-fire` had been copied to *two*
staging locations in Phase 9B (as an approved Factory candidate, and separately
as a letterboxing example). It is promoted once, under Approved/Factory; it is
not re-counted as Rejected. See "Special case" below for the one file that
stayed mis-tiered and was deliberately left alone.

---

## 1. Total promoted

**234 unique image files** now in the repository under `assets/simulation_dataset/_curation/`
(235 staged copies in Phase 9B, minus 1 duplicate copy of the same source file
now counted once).

| Tier | Files |
|---|---:|
| Approved | 14 |
| Manual Review | 165 |
| Rejected (preserved, not deleted) | 55 |
| **Total** | **234** |

## 2. Promoted by category (hazard/content type)

| Category | Approved | Manual Review | Rejected |
|---|---:|---:|---:|
| Residential fire | 7 | 51 | 0 |
| Indoor training-facility structural | 3 | 15 | 0 |
| Factory exterior structural | 2 | 0 | 0 |
| Vehicle fire | 1 | 17 | 0 |
| Outdoor wildfire | 0 | 25 | 0 |
| Outdoor industrial (flare/rig) | 0 | 30 | 0 |
| Person, outdoor general | 0 | 25 | 0 |
| Person, indoor domestic | 1 | 0 | 0 |
| Unknown/ambiguous | 0 | 1 | 0 |
| Special case (good content, technical defect) | 0 | 1 | 0 |
| Toy/miniature model house fires | 0 | 0 | 49 |
| Watermarked | 0 | 0 | 2 |
| Near-duplicate/augmented | 0 | 0 | 3 |
| Multi-panel collage | 0 | 0 | 1 |

## 3. Promoted by environment

| Environment | Approved | Manual Review | Total in repo now |
|---|---:|---:|---:|
| Residential Building | 7 | 51 | 58 |
| Indoor Training Facility (generic, unnamed building) | 3 | 15 | 18 |
| Factory | 2 | 0 | 2 |
| Vehicle (not a building environment; own bucket) | 1 | 17 | 18 |
| Outdoor Wildfire | 0 | 25 | 25 |
| Outdoor Industrial | 0 | 30 | 30 |
| Person (outdoor general, no environment) | 0 | 25 | 25 |
| Person (indoor domestic) | 0 | 1 | 1 |
| Unknown | 0 | 1 | 1 |

## 4. Remaining empty environments (unchanged by this promotion — no content exists for these anywhere)

**Warehouse, Office, Hospital, Shopping Mall, School, Hotel, Airport, Parking Garage** —
all confirmed at zero real images in the prior Phase 9A/9B/10-audit passes, and
this promotion did not change that: nothing was found or searched for in this
pass (per instruction), so these remain exactly as documented before.
`Indoor Training Facility` (18 images, 3 approved) is the closest existing
proxy for Warehouse/Factory interiors but is explicitly not the same thing —
see the Phase 10 gap analysis, Gap 1.

## 5. Images still requiring manual review — 165 total

| Location | Count | Why it needs review |
|---|---:|---|
| `manual_review/residential_building/fire/` | 51 | Staged on filename-cluster confidence (100% hit rate across 8 sampled files from the same clusters), never individually opened |
| `manual_review/indoor_training_facility/` | 15 | 13 never individually opened; 2 (`hotel-fire`, `Firefighterhelmetcaminteriorattack131`) were opened but flagged in the Phase 9B report for a caption/provenance judgment call |
| `manual_review/vehicle_fire/` | 17 | Representative random sample; genre confirmed via a different exact file, not these specific ones |
| `manual_review/outdoor_wildfire/` | 25 | Representative random sample |
| `manual_review/outdoor_industrial/` | 30 | Representative random sample |
| `manual_review/person/outdoor_general/` | 25 | Representative random sample (COCO; low risk, but not individually verified per-file) |
| `manual_review/unknown/` | 1 | Confirmed ambiguous/unclassifiable close-up; needs a keep-or-discard decision, not a suitability check |
| `manual_review/special_case_needs_decision/` | 1 | `kitchenfire` — a genuine, real indoor kitchen-fire photo, the only one in the entire dataset. It was mis-tiered in the original Phase 9B staging as a "letterboxing example" rather than approved content. Left exactly where Phase 9B put it, per instruction not to make new curation calls in this pass — **flagging prominently for your decision**: promote as-is, crop the black bars first, or leave in review. |

## 6. Rejected images — 55 total, all preserved, none deleted

| Location | Count | Reason |
|---|---:|---|
| `rejected/toy_miniature_models/` | 49 | Confirmed miniature/craft-model house fires (popsicle-stick, plastic toy, foam-core with toy fire truck) — visually convincing at a glance, would look absurd in the live dashboard |
| `rejected/watermarked/` | 2 | Visible "gettyimages" branding; visible "FireCam.com" branding (the latter also a genuine residential fire — excluded from Approved for this reason alone) |
| `rejected/near_duplicate_or_augmented/` | 3 | Same base candle photograph, augmented/re-exported 3× under different Roboflow hashes |
| `rejected/multi_panel_collage/` | 1 | 3-panel news composite with burned-in Nepali captions — breaks the "one camera, one frame" simulation contract |

## 7. Existing-asset overwrite check

**Zero overwrites.** Pre-flight filename comparison against every existing file
in `assets/simulation_dataset/` (including the pre-existing `dataset/`
catch-alls and the three `Gemini_Generated_Image_*` placeholders) found **zero
collisions** before any copy occurred. Nothing pre-existing was touched,
renamed, or replaced.

---

## What was explicitly NOT done in this step (by instruction)

- No new images were sourced or searched for.
- No AI/model training.
- No change to `simulation/camera/provider.py`, `simulation_camera.yaml`, or
  `backend/ingestion/camera_adapter.py` — the selection logic remains
  hazard-category-only, exactly as verified in the prior read-only audit.
- No change to the runtime folder `simulation/camera/images/` or to what the
  export tool would produce by default.
- The 165 Manual Review files were not adjudicated — that is future work,
  either by a human pass or a later phase.
- The 55 Rejected files were not deleted — preserved exactly as instructed.
- No git commit was made.
