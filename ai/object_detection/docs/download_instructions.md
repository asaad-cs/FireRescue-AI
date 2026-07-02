# Dataset Download Instructions

Two of the three selected sources download automatically:

```bash
python -m ai.object_detection.data_tools.download
```

That command fetches, checksum-verifies, and unpacks:

| Source | Archive | Size | Destination |
|---|---|---|---|
| figshare_fire_smoke | `MyData_Fire.zip` | 545 MB | `datasets/raw/figshare_fire_smoke/` (extracted to `extracted/`) |
| coco_person | `val2017.zip` | 778 MB | `datasets/raw/coco_person/val2017/` |
| coco_person | `annotations_trainval2017.zip` | 241 MB | `datasets/raw/coco_person/annotations/` |

Re-running is safe: verified files are never fetched twice.

The third source — **D-Fire** — sits behind a OneDrive/Kaggle login and
**must be downloaded manually once**. The pipeline runs fine without
it and will automatically include it in the next merge after its files
appear.

---

## D-Fire — manual download

### Option A: OneDrive (official)

1. Open the repository page:
   https://github.com/gaia-solutions-on-demand/DFireDataset
2. In the README's "Download links" section, click
   **"Images and labels"**:
   https://1drv.ms/u/c/c0bd25b6b048b01d/EbLgD7bES4FDvUN37Grxn8QBF5gIBBc7YV2qklF08GCiBw
3. Sign in with any Microsoft account if prompted, press **Download**,
   and save the zip anywhere.
4. Extract the zip into `ai/object_detection/datasets/raw/dfire/`.

### Option B: Kaggle mirror

1. Sign in at https://www.kaggle.com and open
   https://www.kaggle.com/datasets/sayedgamal99/smoke-fire-detection-yolo
2. Press **Download** (or use the CLI with an API token:
   `kaggle datasets download sayedgamal99/smoke-fire-detection-yolo`).
3. Extract into `ai/object_detection/datasets/raw/dfire/`.

### Expected final structure

Any YOLO-style layout under `raw/dfire/` works — the pipeline
discovers `images`/`labels` directory pairs and side-by-side
`image.jpg` + `image.txt` files recursively. Typical result:

```
ai/object_detection/datasets/raw/dfire/
├── train/
│   ├── images/*.jpg
│   └── labels/*.txt
└── test/
    ├── images/*.jpg
    └── labels/*.txt
```

### Verify the class order (IMPORTANT)

`configs/sources.yaml` maps D-Fire ids as `0 → smoke, 1 → fire` (the
documented D-Fire convention, the reverse of ours). After downloading,
confirm against the bundled README/`data.yaml` (or by spot-checking a
few obviously-fire images) that class `1` is fire. If the copy you
downloaded uses the opposite order, fix the `dfire: class_map` entry in
`configs/sources.yaml` before merging.

### After the download

```bash
python -m ai.object_detection.data_tools.pipeline
```

re-merges everything, re-splits deterministically, rebuilds
`datasets/processed/`, and regenerates every report. Check
`datasets/reports/merge_report.md` to confirm the `dfire` row appears.

---

## Optional scale-up: COCO train2017

val2017 provides ≈2,700 person images. For a bigger person corpus:

1. Download http://images.cocodataset.org/zips/train2017.zip
   (**19 GB**, md5 `cced6f7f71b7629ddf16f17bbcfab6b2`) into
   `datasets/raw/coco_person/` and extract it there
   (`datasets/raw/coco_person/train2017/`).
2. Edit the `coco_person` entry in `configs/sources.yaml`:
   `images: train2017` and
   `annotations: annotations/instances_train2017.json`.
3. Re-run the pipeline. Expect ≈64,000 person images — consider
   sampling if the class balance tips too far toward `person`.
