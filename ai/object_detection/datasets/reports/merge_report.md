# Dataset Merge Report

- **Merged:** 2026-07-02T21:03:54+00:00
- **Output:** `C:\Users\Administrator\Desktop\FireRescue-AI\ai\object_detection\datasets\merged`
- **Images:** 12545
- **Annotations:** 32783

## Class distribution (unified ids)

| Class | Boxes |
|---|---|
| fire | 12043 |
| smoke | 9963 |
| person | 10777 |

## Per-source results

| Source | Found | Merged | Dup skipped | Corrupt | Malformed | No label | Negatives | Boxes in | Boxes kept | Unmapped dropped | Invalid dropped |
|---|---|---|---|---|---|---|---|---|---|---|
| figshare_fire_smoke | 11021 | 9852 | 1169 | 0 | 0 | 0 | 2 | 24815 | 22006 | 0 | 0 |
| coco_person | 2693 | 2693 | 0 | 0 | 0 | 0 | 0 | 10777 | 10777 | 0 | 0 |

## Skipped sources (not downloaded)

- `dfire` — see `docs/download_instructions.md`

## Standardization rules applied

- Unified class ids: 0 fire · 1 smoke · 2 person (configs/dataset.yaml)
- Per-source class id mappings come from configs/sources.yaml; boxes of unmapped classes are dropped and counted above
- COCO pixel boxes were converted to normalized YOLO format; crowd regions (iscrowd=1) were excluded
- Byte-identical images (md5) are merged once; later copies are recorded as duplicates
- Exact duplicate annotation lines within a label file are collapsed to one
- Merged files are renamed `<source>__<original-stem>.<ext>`; full provenance is in `merged/provenance.json`
