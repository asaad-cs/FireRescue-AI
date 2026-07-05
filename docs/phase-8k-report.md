# Phase 8K — Engineering Report

**Title:** Simulation camera experience + Vision Panel as a live camera monitor
**Date:** 2026-07-04
**Status:** Complete — implemented, tested, live-verified. Awaiting user approval for checkpoint commit.
**Baseline:** `v2.0-phase-8j` (`4c5c1dd`)

---

## 1. Goal

Improve the simulation camera experience and the dashboard vision system
before continuing AI training (D-Fire merge + 50-epoch run remain the next
AI milestone). Phase 8K addresses three of the intentionally-open known
issues:

1. Images could repeat between rooms during the same mission.
2. Consecutive missions produced near-identical image sequences
   (fixed seed 42, fresh provider per mission).
3. The Vision Panel was image-oriented instead of behaving like a live
   camera monitor.

No architecture change, no model retraining, no dataset pipeline edits,
no replay or API breakage.

---

## 2. What Changed

### 2.1 Backend — mission-scoped image pool (`simulation/camera/provider.py`)

`ZoneImageProvider` lives exactly one mission (`make_data_source()` builds a
fresh one per mission), so per-instance state is mission-scoped by
construction. Three additions:

- **No-repeat pool.** With `randomize: true`, an image already served this
  mission is excluded from selection until every image of its category
  folder has been used; only then does the pool recycle (logged at INFO).
  Pools are keyed by the folder actually served, so categories reached via
  the fallback chain (`fire_person` → `fire`) share their pool with direct
  requests — no back-door repeats.
- **Sticky zone assignments.** A zone keeps the image it was assigned on
  first visit for the rest of the mission: rooms do not change appearance
  between frames, and repeat visits do not drain the pool.
- **Selection modes.** `CameraConfig.seed` is now `Optional[int]`:

  | Mode | Config | Behaviour |
  |---|---|---|
  | Fixed (strict test) | `randomize: false` | Always the first image, sorted by name (unchanged) |
  | Deterministic | `randomize: true`, `seed: <int>` | Seeded random, reproducible across runs (unchanged semantics + no-repeat pool) |
  | **Normal random (new default)** | `randomize: true`, `seed: null` | Fresh 63-bit entropy seed drawn per mission and exposed as `provider.effective_seed` |

  The effective seed is logged at mission start
  (`Camera | enabled | … mode=random effective_seed=N …`), so **any**
  normal-mode mission can be reproduced exactly by pinning that number as
  `seed:` — randomness never costs reproducibility.

`simulation/camera/simulation_camera.yaml` now ships `seed: null` (normal
random mode) with all three modes documented inline.
`backend/ingestion/camera_adapter.py` logs mode + effective seed. No other
backend file changed; `Frame`, REST, WebSocket, and replay contracts are
untouched (imagery still rides inside `MissionState.vision`, so replay
carries the exact analysed frames regardless of camera randomness).

### 2.2 Frontend — MissionCamera as a live camera monitor

`frontend/src/components/dashboard/MissionCamera.tsx` (+2 keyframes in
`index.css`, +1 prop pass-through in `MainWorkspace.tsx`):

- **Monitor chrome (HUD).** Corner brackets, `ZONE x_y_f` + UTC clock
  chips (top-left), `FRAME #n` (top-right), `SIM-CAM-01 · SIMULATED FEED`
  (bottom-left), plus subtle scanlines + vignette on the stage. New frames
  fade in (220 ms) so ticks read as a feed, not an image swap.
- **Edge-aware detection labels.** Label pills flip inside the box when
  the box touches the top edge (`y1/h < 6%`) and right-align when the box
  hugs the right edge (`x1/w > 70%`) — closes the known "labels overflow
  the image edge" issue.
- **Link-state awareness.** New optional props `wsStatus` (default
  `'connected'`) and `isStale` (default `false`) — both fed from state the
  layout already tracked, so the component stays pure UI and fully
  backward compatible:
  - live + connected → red **LIVE** pulse (unchanged);
  - frame frozen by a dropped link → amber **STALE** indicator, an
    on-stage "FEED STALE — showing last frame #n" chip, and the telemetry
    Link field turns STALE;
  - no frame + link down → **ACQUIRING SIGNAL** stage (distinct from the
    detector fallback);
  - no frame + connected → the existing "No camera inference available"
    stage, restyled with monitor chrome and a STANDBY chip.
- **Richer telemetry.** The bar adds **Targets** (detection count, red
  when non-zero) and **Link** (SIMULATED/STALE) to the existing seven
  fields. The header gains a contacts chip (`3 CONTACTS` / `NO CONTACTS`).
- **History rail polish.** Thumbnails show class-colored detection dots
  and a detections count in the tooltip.

The `CameraMediaSource` abstraction (`image` | `video` | `stream`) is
untouched: video remains typed, reserved, and unimplemented by design —
all Phase 8K chrome lives outside `CameraMedia`, so a future video player
slots into the same stage, HUD, overlay, and telemetry without redesign.

### 2.3 Files touched

| File | Change |
|---|---|
| `simulation/camera/provider.py` | Optional seed, effective_seed, no-repeat pool, sticky zones |
| `simulation/camera/simulation_camera.yaml` | `seed: null` default + mode documentation |
| `backend/ingestion/camera_adapter.py` | Mode + effective-seed logging |
| `simulation/tests/test_camera.py` | +10 tests (pool, modes, reproducibility) |
| `frontend/src/components/dashboard/MissionCamera.tsx` | Live-monitor redesign |
| `frontend/src/components/layout/MainWorkspace.tsx` | Pass `wsStatus`/`isStale` |
| `frontend/src/index.css` | `camera-frame-in` keyframe/utility |
| `frontend/src/components/dashboard/__tests__/MissionCamera.test.tsx` | +9 tests (link states, HUD, edge labels) |
| `docs/phase-8k-report.md` | This report |
| `docs/session-context.md`, `docs/project-status.md`, `docs/handoff-report.md` | Phase 8K sections |

---

## 3. Verification

### 3.1 Test suites (all green)

```
Backend:    619 passed + 50 subtests   (was 609 — +10 Phase 8K camera tests)
Frontend:   328 passed / 17 files      (was 319 — +9 Phase 8K MissionCamera tests)
            all 295 MVP tests and all pre-8K tests pass UNMODIFIED
TypeScript: 0 errors (npx tsc --noEmit)
```

### 3.2 Requirement verification (scripted, against the real committed config + Warehouse Alpha)

- **No repeats within a mission until exhaustion:** across all categories
  used in a 20-zone mission, every folder served `min(selections,
  available)` distinct images with a max reuse spread of 1 (balanced
  recycling). The only recycling category was `safe` (2 images for 15
  safe zones — the known D-Fire negatives gap, unchanged by this phase).
- **Different missions differ in normal mode:** two missions drew
  distinct entropy seeds and chose different imagery in 10/20 zones.
- **Deterministic mode intact:** `seed: 42` reproduced identical
  zone→image assignments across two runs.
- **Random mode is reproducible after the fact:** re-running with a
  mission's logged `effective_seed` reproduced that mission exactly.

### 3.3 Live end-to-end demo (dashboard running)

Backend launched via the throwaway YOLO launcher (committed default stays
`ground_truth`), Vite on :5173:

- Mission 1: `mode=random effective_seed=5760332099133308447`; the
  `safe` pool recycled with INFO logs exactly as designed; final frame =
  Loading Dock (`4_3_1`) with **fire 0.92** from the ONNX model; vision
  payload verified over the WebSocket (zone, frame #, detector `yolo`,
  model name, 24.5 ms inference, base64 JPEG).
- Mission 2 (restart): `effective_seed=3087058742335454541` — a
  different seed and different imagery, proving per-mission variety live.

---

## 4. Constraints Audit

| Constraint | Status |
|---|---|
| No architecture redesign | ✅ Provider/adapter/panel internals only; all seams unchanged |
| No AI retraining | ✅ Model untouched (still the 5-epoch baseline) |
| No dataset pipeline edits | ✅ `ai/` untouched |
| Replay unbroken | ✅ Vision rides inside recorded `MissionState`; recorder/replay code untouched |
| No API changes | ✅ REST + WebSocket contracts identical; frontend still receives only `MissionState` |
| All existing tests pass | ✅ 100% of pre-8K tests pass unmodified |

---

## 5. Known Issues Updated

- ~~Images repeat between rooms in one mission~~ → fixed (mission-scoped pool).
- ~~Consecutive missions look identical~~ → fixed (`seed: null` normal mode, logged effective seed).
- ~~Vision Panel is image-oriented~~ → redesigned as a live monitor; video/stream still typed + reserved (intentional).
- Image library variety is still limited (2 `safe` images, empty person-combination folders) — unchanged; the real fix arrives with D-Fire.
- Deployed model is still the 5-epoch baseline — unchanged by design.

## 6. Recommended Next Phase

Unchanged from the Phase 8J handoff: **manual D-Fire download → pipeline
re-run (also enriching the simulation library, esp. `safe/`) → 50-epoch
GPU training on the scene-aware split → threshold calibration → consider
flipping `perception_detector` to `yolo`.**

---

## 7. Phase 8K.1 — UX fix pass (2026-07-04, after visual verification)

A full visual verification (screenshots in
`Desktop\firerescue-8k-screenshots\`) surfaced three UX defects; all
three were fixed **frontend-only** (`MissionCamera.tsx` +
`MainWorkspace.tsx` prop wiring; backend, AI pipeline, replay engine,
and APIs untouched):

1. **Mission-scoped history.** The history rail cleared on a new
   `mission_id` (new optional `missionId` prop). Previous-mission frames
   can no longer appear in a new mission; an active history review also
   exits on mission change.
2. **Replay awareness.** New optional `isReplaying` prop (from the
   existing replay slice): during replay the header shows a blue
   **REPLAY** badge instead of the red LIVE pulse, and replayed frames
   are displayed but **not recorded** into the history rail (the live
   mission's history stays frozen while scrubbing). LIVE / STALE /
   SIGNAL LOST / standby behavior is unchanged.
3. **HUD/label overlap eliminated structurally.** The on-stage HUD chips
   moved into dedicated top/bottom HUD bands that frame the media
   viewport — HUD text now lives *outside* the image area, so it can
   never collide with detection labels regardless of box geometry
   (the previous absolute-positioned chips could overlap labels of
   boxes hugging the top-left corner). Edge-aware label flipping kept
   (threshold 6% → 8%).

**Verification:** frontend suite **334 passed** (328 + 6 new tests:
history reset ×2, replay awareness ×3, HUD/label separation ×1), all
pre-existing tests unmodified; `tsc` 0 errors; verified live in the
browser (screenshots `08-new-mission-empty-history.png`,
`09-replay-indicator.png`, `10-hud-bands-no-overlap.png`): a new mission
railed only `#0/#1/#2`, replay showed the REPLAY badge with LIVE hidden
and history frozen at the live mission's last five frames, and a
full-bleed detection label sat cleanly below the HUD band.

**Discovered pre-existing backend issue (out of scope, not fixed —
"do not change the backend"):** the mission restart path
(`backend/api/routes.py`, start-from-ENDED branch) replaces
`app.state.adapter` without stopping the old adapter, and
`POST /mission/end` never stops it either. Ending a mission **mid-run**
and restarting therefore leaves the old simulation runner ticking, and
its frames (stamped with the *new* mission id) interleave into the new
mission until the old BFS completes. Invisible in normal operation
(missions end naturally when the runner completes; the runner then
stops itself) and invisible to the frontend (the leaked frames carry
the current mission id). Recommended future fix: `await`/schedule
`old_adapter.stop()` before installing the new adapter in the restart
path, and optionally stop the adapter on `/mission/end`.
