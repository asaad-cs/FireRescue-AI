# Simulation Image Master Library

The permanent, curated source of every image the FireRescue AI
simulated drone camera can "see". The simulator itself **never reads
this folder** — it reads the generated runtime folder
`simulation/camera/images/`, which is built from here with the export
tool (see "Regenerating the runtime folder" below).

```
Master library (permanent, curated)      Runtime folder (generated)
assets/simulation_dataset/   ── export ─▶  simulation/camera/images/
```

## Folder structure

Top level = detection category (must match the categories
`simulation_camera.yaml` maps zones to). Second level = optional scene
sub-folders used to organise and selectively export images:

```
assets/simulation_dataset/
├── safe/                    nothing burning, nobody present
│   ├── office/  corridor/  warehouse/  parking/  stairs/
│   └── dataset/             (unclassified images from the training dataset)
├── fire/                    visible flames
│   ├── office/  warehouse/  electrical/  kitchen/
│   └── dataset/
├── smoke/                   smoke without visible flames
│   ├── office/  corridor/  warehouse/
│   └── dataset/
├── person/                  at least one visible person, no fire/smoke
│   ├── standing/  walking/  sitting/  lying/
│   └── dataset/
├── fire_person/             combinations — flat (add scene folders as needed)
├── smoke_person/
├── fire_smoke/
│   └── dataset/
└── fire_smoke_person/
```

- A category folder may hold images directly (kept as-is on export) or
  in scene sub-folders (flattened with a `<subcategory>__` name prefix).
- `dataset/` sub-folders hold images sampled from the training dataset
  whose scene context has not been classified; prefer the named scene
  folders for newly curated images.
- New scene sub-folders can be added freely — the export tool discovers
  them automatically.

## Naming conventions

`<source>__<short-descriptor>.<ext>` — lowercase, hyphens inside the
descriptor, double underscore between source and descriptor.
Examples: `figshare_fire_smoke__01108.jpg`, `mysite__server-rack-blaze.jpg`.
Never reuse a name inside one folder; the source prefix keeps
provenance visible after flattening.

## Supported image formats

`.jpg`, `.jpeg`, `.png` (aligned with `simulation_camera.yaml:
extensions`). No video — the camera is images-only by design.

## Recommended resolution

Shorter side ≥ 640 px (the detector's input size is 640×640; smaller
images are upscaled and lose detail). Any aspect ratio is fine — the
detector letterboxes. Keep files under ~2 MB; the analysed image also
travels to the dashboard.

## Licensing recommendations

Only add images you may redistribute. Prefer CC0 / CC BY (keep the
attribution: put the source in the filename prefix and, for new
sources, a note in this README). Images seeded from the project's
training dataset inherit its licensing (see
`ai/object_detection/docs/dataset-manifest.md` — Figshare fire/smoke:
CC BY 4.0; COCO person: CC BY 4.0 annotations, Flickr terms for
images). Do not add scraped images of identifiable private
individuals.

## How to add new images

1. Drop the files into the right `<category>/<scene>/` folder using
   the naming convention above (create the scene folder if needed).
2. Re-export the runtime folder (below).
3. Optional sanity check: run the simulator or
   `python -m pytest simulation/tests/test_camera.py -q`.

## Regenerating the runtime folder

```bash
# Full rebuild of every category (deletes and re-exports each one):
python -m ai.object_detection.data_tools.export_simulation_library --clean

# Only fire and smoke, at most 20 images each, seeded random pick:
python -m ai.object_detection.data_tools.export_simulation_library \
    --categories fire smoke --limit 20 --random --seed 7 --clean

# Only curated office scenes, keep whatever already exists:
python -m ai.object_detection.data_tools.export_simulation_library \
    --subcategories office
```

`--clean` fully regenerates the selected categories; without it,
existing runtime files are kept (add `--overwrite` to replace them).
The master library is never modified by the export tool.

---

## Target Library Structure (planning)

*Added Phase 10A.2. Describes where this library is headed — it does not
change the folder structure documented above, and none of the folders below
exist yet unless already listed in "Folder structure."*

Two orthogonal axes, both already present in concept in the folder structure
above — this section names the **full target list**, most of which is
currently unpopulated:

- **Category** (unchanged, existing top level): `safe`, `fire`, `smoke`,
  `person`, and their four combinations.
- **Tier 1 — Environment** (building type; one per scenario): `warehouse`,
  `office`, `hospital`, `shopping_mall`, `school`, `residential`,
  `industrial`, `outdoor`. The first five match the simulator's five live
  scenarios one-to-one; `residential`, `industrial`, and `outdoor` are
  broader buckets already represented in the training-dataset content
  identified during Phase 9A/9B.
- **Tier 2 — Scene** (room/context type within an environment; optional,
  refines Tier 1): `corridor`, `kitchen`, `electrical`, `parking`, `stairs`,
  plus the existing person-pose scenes `standing`, `walking`, `sitting`,
  `lying`. These are exactly the scene sub-folder names already scaffolded
  (empty) under `safe/`, `fire/`, `smoke/`, and `person/` above.

**Future extensibility:** adding a new Tier 1 or Tier 2 value requires no
code or export-tool change — `export_simulation_library.py` already
discovers and flattens any named sub-folder automatically (see "How to add
new images" above). Extending this taxonomy is a documentation and curation
task, not an engineering one.

---

## Target Image Counts (planning only — not yet met)

*Added Phase 10A.2. These are forward-looking targets, derived from the
Phase 8K empirical finding that a single ~20-zone mission can draw one
category up to ~15 times. They describe what "done" looks like, not current
reality. See "Current Status" below for what actually exists today.*

| Tier 1 environment | Current (real images, any tier) | Target minimum | Target recommended | Gap |
|---|---:|---:|---:|---:|
| Warehouse | 0 | 80 | 160 | 160 |
| Office | 0 | 80 | 160 | 160 |
| Hospital | 0 | 80 | 160 | 160 |
| Shopping Mall | 0 | 80 | 160 | 160 |
| School | 0 | 80 | 160 | 160 |
| Residential | 58 | 80 | 160 | 102 |
| Industrial / Factory | 2 | 80 | 160 | 158 |
| Outdoor | 0 (not yet organized by environment tag; ~10,650 exist unclassified in the training dataset per Phase 9A) | 80 | 160 | 0 (oversupplied once tagged) |

Minimum/recommended totals are spread across the four core hazard
categories (`safe`/`fire`/`smoke`/`person`, ~20/40 images each) per
environment — not a single bucket. These targets apply to **new** curated
content; nothing here retroactively obligates re-curating existing library
images.

---

## Acceptance Rules

*Added Phase 10A.2, consolidating criteria already applied during Phase 9B
curation — no new restriction is introduced beyond what was already used to
accept or reject real candidates.*

An image qualifies for promotion into the official simulation library only
if it meets **all** of the following:

| Rule | Rationale |
|---|---|
| Real-world photograph, not a synthetic/AI-generated image | Simulation imagery should read as an authentic camera feed. **Note:** three pre-existing placeholder images (`Gemini_Generated_Image_*`, added Phase 8H) predate this rule and are grandfathered — no change is made to them here; whether to replace them is a separate future decision. |
| Suitable perspective — a scene a drone/eye-level camera could plausibly capture | Rules out extreme close-ups with no spatial context (e.g., a cigarette-lighter flame filling the frame) |
| Adequate quality — meets the format/resolution rules already documented above | No new bar; references the existing "Supported image formats" / "Recommended resolution" sections |
| Correctly classified environment and hazard category | An image must actually depict what its folder claims |
| No visible watermarks or branding baked into the pixels | Found and rejected during Phase 9B (e.g., stock-photo and news-camera watermarks) |
| No multi-panel collages | Breaks the "one camera, one frame" simulation contract; found and rejected during Phase 9B |
| No obvious near-duplicates or sequential video-frame bursts | A burst of frames from the same real event should be thinned to representative frames, not curated as if independent scenes |
| No toy, miniature, or craft-model scenes | The single most important lesson from Phase 9B — a 49-image cluster of dollhouse/toy-model "house fires" looked convincing at a glance and was caught only by individual visual review |
| Letterboxed (black-bar padded) images are discouraged, not automatically disqualified | ~79% of the current training dataset has this defect (a side effect of its original 640×640 export); crop before promotion where feasible, but its mere presence does not reject otherwise-good content on its own |

---

## Dataset Curation Workflow

*Added Phase 10A.2. Describes the official lifecycle for any future
contribution.*

```
Candidate  ──▶  Manual Review  ──▶  Approved  ──▶  Runtime Library
                     │
                     ▼
                  Rejected  (preserved, never deleted)
```

1. **Candidate** — any image proposed for the library, from any source.
2. **Manual Review** — an individual, visual check against every rule in
   "Acceptance Rules" above. An image staged by pattern-matching or batch
   sampling (not individually opened) stays at this stage until someone
   actually looks at it.
3. **Approved** — passed review with no defect found. Ready for promotion.
4. **Runtime Library** — the live, exported folders under this directory
   that `export_simulation_library.py` actually scans and that
   `simulation/camera/images/` is generated from. Promotion here is a
   distinct, deliberate step — passing review does not mean an image is
   already live.
5. **Rejected** — failed one or more rules. Kept, not deleted, so the
   reasoning stays visible and nothing is silently lost.

**`_curation/` is intentionally isolated from the runtime pipeline until
explicitly promoted.** `assets/simulation_dataset/_curation/` (added Phase
9B) holds Candidate/Manual-Review/Approved/Rejected staging in exactly this
shape. Its leading underscore is not cosmetic —
`export_simulation_library.py`'s category scan explicitly skips any
`.`/`_`-prefixed top-level folder, so nothing inside `_curation/` can reach
`simulation/camera/images/` without a separate, deliberate future step
(promoting the actual files into a real, non-underscore-prefixed
environment folder). This document does not perform that promotion.

---

## Current Status (2026-07-05)

- **Library maturity:** early. The hazard-category taxonomy, licensing
  policy, and export tooling are complete and working; the environment
  (Tier 1/Tier 2) taxonomy above is a target, not yet populated in the live
  library.
- **Completed:** Phase 9A dataset assessment; Phase 9B curation staging;
  promotion of 234 unique images into `_curation/` — **14 Approved**, **165
  Manual Review**, **55 Rejected** (breakdown in
  `ai/object_detection/datasets/reports/phase9b_promotion_manifest_2026-07-05.md`).
- **Remaining gaps:** none of the 234 promoted images have been moved into
  the live/exported library yet (`simulation/camera/images/` is unchanged);
  Warehouse, Office, Hospital, Shopping Mall, School, Hotel, Airport, and
  Parking Garage remain at zero real images; 165 images still need
  individual manual review; one flagged special case (a genuine kitchen-fire
  photo currently mis-tiered as a letterboxing example) needs a decision.
