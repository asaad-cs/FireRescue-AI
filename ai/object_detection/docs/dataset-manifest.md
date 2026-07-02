# Object Detection Dataset Manifest

Selected sources for the unified FireRescue AI detection dataset
(classes: `0 fire · 1 smoke · 2 person`). Selection was researched on
2026-07-02; the criteria were research-friendly licensing, annotation
quality, YOLO compatibility, and indoor-scene coverage.

Exact post-merge counts (after deduplication, cleaning, and class
standardization) always live in `datasets/reports/merge_report.md` and
`datasets/reports/quality_report.md` — the figures below describe each
source as published.

---

## 1. Fire-Smoke Image Dataset (Figshare / CQUniversity) — SELECTED, auto-downloaded

| Field | Value |
|---|---|
| Name | Annotated Fire-Smoke Image Dataset for fire detection Using YOLO |
| Source | CQUniversity Acquire (Figshare), S. Partheepan et al., updated 2025-04 |
| License | **CC BY 4.0** (Figshare publication license) |
| Download URL | https://ndownloader.figshare.com/files/53486522 (545 MB zip, md5 `fd9ed42cd67fd5f7c016ca127985e245`) |
| Landing page | https://doi.org/10.25946/28747046 |
| Classes | `fire` (0), `smoke` (1) — same order as our unified scheme |
| Images | 11,027 (640×640, letterboxed Roboflow YOLOv8 export, pre-split 80/10/10) |
| Annotations | ≈25,000 boxes (per the publication: ~12,600 fire + ~12,200 smoke) |

**Strengths:** permissive published license with a citable DOI; native
YOLO labels (no conversion); diverse real-world scenes including
indoor/CCTV footage; direct, checksummed, fully automatable download.

**Weaknesses:** images are pre-resized to 640×640 with black
letterboxing (original resolution lost); the embedded Roboflow
metadata says `license: undefined` for the upstream project — we rely
on the CC BY 4.0 grant of the Figshare publication; no `person` class.

**Reason for inclusion:** the highest-quality *directly downloadable*
fire+smoke detection dataset found: correct task (detection, not
classification), correct format, permissive license, meaningful indoor
coverage.

---

## 2. D-Fire (Gaia, solutions on demand) — SELECTED, manual download required

| Field | Value |
|---|---|
| Name | D-Fire: an image dataset for fire and smoke detection |
| Source | https://github.com/gaia-solutions-on-demand/DFireDataset |
| License | Research use — see the repository `LICENSE` file |
| Download URL | OneDrive links in the repository README (login required); Kaggle mirror `sayedgamal99/smoke-fire-detection-yolo` (account required) |
| Classes | `smoke` (0), `fire` (1) — **reversed vs. our scheme**; remapped by `configs/sources.yaml` |
| Images | 21,527 (1,164 fire only · 5,867 smoke only · 4,658 both · 9,838 negatives) |
| Annotations | 26,557 boxes (14,692 fire + 11,865 smoke) |

**Strengths:** the de-facto benchmark for fire/smoke detection; large;
native YOLO labels; includes 9,838 curated negative images (extremely
valuable for false-positive suppression, which matters for the
FireRescue use case); widely validated by third-party research.

**Weaknesses:** hosted on OneDrive/Kaggle behind logins — cannot be
fetched unattended (automation returns HTTP 401); mostly outdoor and
surveillance viewpoints; class order must be verified after download.

**Reason for inclusion:** best-in-class fire/smoke corpus; the
pipeline merges it automatically the moment its files appear under
`datasets/raw/dfire/` (see `docs/download_instructions.md`).

---

## 3. COCO 2017 — person class only — SELECTED, auto-downloaded

| Field | Value |
|---|---|
| Name | COCO 2017 (val split), `person` category |
| Source | https://cocodataset.org/#download |
| License | Annotations **CC BY 4.0**; images retain their original Flickr terms |
| Download URL | http://images.cocodataset.org/zips/val2017.zip (778 MB, md5 `442b8da7639aecaf257c1dceb8ba8c80`) + http://images.cocodataset.org/annotations/annotations_trainval2017.zip (241 MB, md5 `f4bbac642086de4f52a3fdda2de5fa2c`) |
| Classes | `person` → unified id 2 (all 79 other categories dropped) |
| Images | 5,000 in val2017; ≈2,700 contain at least one non-crowd person |
| Annotations | ≈11,000 person boxes (crowd regions excluded) |

**Strengths:** gold-standard annotation quality; enormous person pose /
occlusion / lighting variety including indoor scenes; fully automatable
checksummed download; industry-standard licensing.

**Weaknesses:** COCO JSON needs conversion to YOLO (handled by
`data_tools/coco.py`); no fire/smoke context — persons rarely co-occur
with fire here, so fire+person co-occurrence remains under-represented;
val2017 alone is modest in size (train2017 is a documented scale-up
path in `download_instructions.md`).

**Reason for inclusion:** victims are the single most important class
for FireRescue AI; COCO person is the highest-quality person source in
existence and its val split keeps the download tractable.

---

## Considered and rejected

| Dataset | Why rejected |
|---|---|
| **FLAME** (IEEE DataPort) | Aerial/UAV *forest* fire imagery, primarily classification/segmentation, login-gated — wrong perspective and task for indoor object detection. |
| **Roboflow Universe fire/smoke projects** (e.g. `fire-smoke-detection-yolov11`, `continuous_fire`) | API-key-gated downloads; per-project licenses often "undefined"; heavy overlap with D-Fire/Figshare images; quality varies wildly between projects. |
| **Kaggle fire mirrors** (`phylake1337/fire-dataset`, etc.) | Classification-only (no boxes) or unlicensed re-uploads of the sources above; Kaggle requires authenticated download. |
| **HuggingFace `badsaarow/d-fire`** | Unofficial parquet re-encoding of D-Fire with no license metadata; prefer the original raw files with provenance. |
| **DFS / Boreal Forest Fire datasets** | Aerial or non-commercial-restricted; outdoor wildfire focus adds little for indoor rescue scenarios. |

---

## Class standardization summary

| Source | Source ids | Mapping to unified ids |
|---|---|---|
| figshare_fire_smoke | 0 fire, 1 smoke | 0→0, 1→1 (identity) |
| dfire | 0 smoke, 1 fire | 0→1, 1→0 (swap) |
| coco_person | category `person` | person→2; all other categories dropped; `iscrowd=1` regions excluded |

Mappings are enforced by `configs/sources.yaml` and applied during the
merge; every dropped box is counted in `merge_report.md`.
