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
