# UI Design

Operator dashboard design for the FireRescue AI MVP prototype.

---

## 1. User Persona

### Primary User — Incident Operations Coordinator (IOC)

**Who they are:**
The Incident Operations Coordinator is stationed at an outside command post — a vehicle, a tent, or a temporary command station positioned at the perimeter of the incident. They are not inside the building. They have radio contact with firefighter teams and are responsible for directing the rescue operation based on the information the system provides.

The IOC is a trained firefighter or rescue coordinator with operational experience. They are not a software engineer. They understand building layouts, fire behavior, and search-and-rescue procedures, but they should not need to understand the software system to use the dashboard effectively.

**Their environment:**
- High stress. Time is measured in lives.
- The command post may be physically uncomfortable — outdoors, in dim light, in a vehicle cab.
- They may be standing, not sitting. The screen may be viewed from a short distance.
- They are managing radio communication simultaneously with monitoring the dashboard.
- Loud environment. Auditory alerts may be missed (future consideration).

**Their responsibilities:**
- Decide where to direct firefighter teams inside the building
- Identify which zones are too dangerous to enter
- Identify zones where victims are likely present
- Communicate victim locations and hazard zones to the entry team over radio
- Decide when to end a mission or call a retreat
- Document what happened during the operation for after-action review

**Decisions they need to make:**
1. Is it safe to send a team into Zone X right now?
2. Where is the most likely victim location?
3. Which zones should be prioritized for search?
4. Is the situation getting worse or improving?
5. When should the mission end?

**Information that matters most:**
The IOC does not need a beautiful interface. They need accurate information organized by urgency. The single most important question at any moment is: *is there a victim somewhere, and can we get to them?* Everything else supports answering that question.

---

## 2. Dashboard Goals

The dashboard exists to answer six questions. Every design decision should serve at least one of them.

| Goal | Question answered |
|---|---|
| **G1 — Hazard awareness** | Which zones are safe, dangerous, or impassable right now? |
| **G2 — Victim awareness** | Where are potential victims, and how certain are we? |
| **G3 — Drone awareness** | Where is the drone, and where has it been? |
| **G4 — Alert monitoring** | Has anything changed that requires immediate action? |
| **G5 — Mission control** | Is the mission active? How long has it been running? |
| **G6 — Sensor monitoring** | What are the current environmental readings? |
| **G7 — Mission review** | What happened and in what order? |

The dashboard does not need to look impressive. It needs to answer these questions faster than the IOC could ask them.

---

## 3. Screen Layout

The dashboard uses a fixed three-region layout that does not scroll or rearrange. All information is visible at all times. No information is hidden behind tabs, modals, or drill-downs during an active mission.

```
┌─────────────────────────────── TOP BAR ────────────────────────────────────┐
│ Mission status · Timer · Mission ID · START / END controls                 │
├───────────────────────────┬────────────────────────────────────────────────┤
│                           │                                                │
│    FLOOR MAP              │    ALERTS PANEL                               │
│    (primary view)         │    (highest priority, most vertical space)    │
│                           │                                                │
│                           ├────────────────────────────────────────────────┤
│                           │                                                │
│                           │    DRONE STATUS PANEL                         │
│                           │    (position + current sensor readings)       │
│                           │                                                │
│                           ├────────────────────────────────────────────────┤
│                           │                                                │
│                           │    VICTIM PANEL                               │
│                           │    (zones with elevated victim probability)   │
│                           │                                                │
├───────────────────────────┴────────────────────────────────────────────────┤
│ MISSION TIMELINE                                                           │
│ Scrollable event log                                                       │
└────────────────────────────────────────────────────────────────────────────┘
```

### 3.1 Top Bar

**Purpose:** Permanent status strip. The operator can determine the mission status and elapsed time with a single glance, without reading anything in the panels.

**Content:**
- Application name: `FIRERESCUE AI`
- Status indicator: colored dot + text label (`IDLE`, `ACTIVE`, `ENDED`, `CONNECTION LOST`)
- Mission timer: `HH:MM:SS` elapsed, starts at 00:00:00 when mission begins
- Mission ID: short identifier for logging and radio communication (`M-2026-001`)
- Primary action button: `START MISSION` (idle) or `END MISSION` (active)

**Behavior:**
- The status dot pulses slowly when the mission is ACTIVE, is static when IDLE or ENDED, and flashes red when CONNECTION LOST
- The timer stops and freezes when the mission ends
- The END MISSION button requires a confirmation step to prevent accidental termination

**Why this exists:** The IOC must always know whether the system is live. If they look up from a radio call and the screen has gone dark or stale, they need to see that immediately without hunting for a status indicator.

---

### 3.2 Floor Map (Left Column — Primary View)

**Purpose:** The single most important view in the dashboard. The floor plan is the IOC's mental model of the rescue operation. Every other panel is supplemental to this view.

**Content:**
- 2D grid of the building floor plan, divided into labeled zones
- Each zone is colored according to its current hazard level
- The drone's current position is marked with a distinct symbol `[D]`
- Zones where victim probability exceeds the alert threshold are marked `[V]`
- Zones the drone has not yet visited are marked as unobserved (distinct from CLEAR)
- Zone labels (e.g., A1, B2, C3) are displayed in each cell
- A legend is fixed to a corner of the map

**Hazard level color coding:**

| Level | Zone Fill Color | Text/Symbol Color | Description |
|---|---|---|---|
| UNOBSERVED | Dark background, no tint | Muted gray | Drone has not passed through this zone |
| CLEAR | Dark green fill | Light green | No hazard detected |
| LOW | Muted green fill | Green | Minor hazard, safe for entry |
| MODERATE | Amber fill | Bright amber | Caution required, approach carefully |
| HIGH | Orange-red fill | Bright orange | Dangerous, entry only with full protection |
| CRITICAL | Bright red fill | White | Do not enter, extreme hazard |

**Behavior:**
- Zone colors update within 500 ms of each new sensor reading
- The drone marker animates to its new position on each update
- Victim markers appear on zones where probability exceeds the configured threshold (default: 60%)
- Hovering over a zone (future: clicking) shows the last known readings for that zone
- The map does not scroll or zoom in the MVP — the entire floor plan is always visible

**Why this exists:** The floor map is the primary operational view. If the IOC can read only one thing, it should be the map. All other panels answer questions that arise from looking at the map.

---

### 3.3 Alert Panel (Right Column — Top)

**Purpose:** Surface information that requires immediate attention. Alerts are the only content that the IOC should not have to seek out — they must be impossible to miss.

**Content:**
- Scrollable list of alerts, newest first
- Each alert shows: severity icon, timestamp, zone label, alert type, and a short description
- An unread badge count on the panel header
- Visual distinction between unacknowledged and acknowledged alerts

**Sizing:** The Alert Panel receives the most vertical space in the right column because alerts carry the highest priority information. It should accommodate at least six visible alert rows without scrolling.

**Why this exists:** The IOC may be looking at the map or talking on the radio when a critical event occurs. The alert panel guarantees that event is visible and prioritized when they return their attention to the screen.

---

### 3.4 Drone Status Panel (Right Column — Middle)

**Purpose:** Confirm where the drone is and what it is currently reading.

**Content:**
- Current zone label (e.g., "Zone C3")
- Grid coordinates (x, y) and floor number
- Three sensor readings with visual level bars:
  - Temperature (°C)
  - CO Level (ppm)
  - Smoke Density (0–100%)
- Each reading includes a level bar that shows position within the safe/warning/critical range
- Last update timestamp ("Updated 0.8s ago")

**Why this exists:** The map shows hazard history across all zones. The Drone Status Panel shows what the drone is reading right now. These are different. The IOC needs both: where has been dangerous (map) and what is happening at this exact location right now (drone panel).

---

### 3.5 Victim Panel (Right Column — Bottom)

**Purpose:** Show which zones have elevated victim presence probability and how confident the system is.

**Content:**
- List of zones where victim probability exceeds a minimum display threshold (default: 30%)
- Each entry shows: zone label, probability percentage, a confidence bar
- Entries are sorted by probability, highest first
- If no zones exceed the display threshold: "No detections above threshold."
- If victim probability exceeds the alert threshold (60%): the zone entry is highlighted in amber
- If victim probability exceeds the critical threshold (80%): the zone entry is highlighted in red with an indicator

**Language note:** The panel is labeled "VICTIM SIGNALS" not "VICTIMS DETECTED". The system estimates probability. The label should not imply certainty the system cannot provide.

**Why this exists:** Victim information is the mission's primary objective. It deserves its own dedicated panel, separate from hazard alerts. The IOC needs to see victim probability at a glance without reading alert descriptions.

---

### 3.6 Mission Timeline (Bottom Bar)

**Purpose:** Chronological log of every significant event during the mission. Supports post-mission review and provides the IOC with a narrative of what has happened.

**Content:**
- Scrollable horizontal strip (or vertical list) of timestamped events
- Events include: mission started, drone moved to zone, hazard level change, alert generated, mission ended
- Each event has a short label and timestamp
- Color-coded by event type (information, warning, critical)

**Behavior:**
- Auto-scrolls to show the most recent event
- The IOC can scroll back through history
- During a live mission the IOC is not expected to read this carefully; it is primarily for post-mission review

**Why this exists:** After a mission ends, the IOC needs to brief command on what happened and when. The timeline provides this record without requiring the IOC to take manual notes during the operation.

---

## 4. Wireframes

### 4.1 Main Dashboard — Idle State

System is running but no mission is active. The operator has not yet started a mission.

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  FIRERESCUE AI              ●  IDLE  ·  No active mission      [START MISSION]  ║
╠══════════════════════════════════════╦═══════════════════════════════════════════╣
║  BUILDING MAP   Floor 1              ║  ALERTS                             (0)  ║
║  ─────────────────────────────────  ║  ─────────────────────────────────────   ║
║                                      ║                                          ║
║   A     B     C     D     E          ║  No alerts.                             ║
║  ┌─────┬─────┬─────┬─────┬─────┐   ║  Alerts will appear here once           ║
║ 1│     │     │     │     │     │   ║  a mission is started.                  ║
║  │ A1  │ B1  │ C1  │ D1  │ E1  │   ║                                          ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║                                          ║
║ 2│     │     │     │     │     │   ╠═══════════════════════════════════════════╣
║  │ A2  │ B2  │ C2  │ D2  │ E2  │   ║  DRONE STATUS                            ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  ─────────────────────────────────────  ║
║ 3│     │     │     │     │     │   ║  Zone         —                          ║
║  │ A3  │ B3  │ C3  │ D3  │ E3  │   ║  Position     —                          ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  Temperature  —                          ║
║ 4│     │     │     │     │     │   ║  CO Level     —                          ║
║  │ A4  │ B4  │ C4  │ D4  │ E4  │   ║  Smoke        —                          ║
║  └─────┴─────┴─────┴─────┴─────┘   ╠═══════════════════════════════════════════╣
║                                      ║  VICTIM SIGNALS                          ║
║  Legend:  □ UNOBSERVED               ║  ─────────────────────────────────────  ║
║           ░ CLEAR   ▒ LOW            ║  No detections.                         ║
║           ▓ MODERATE  HIGH  CRIT     ║                                          ║
║  [D] Drone          [V] Victim sig.  ║                                          ║
╠══════════════════════════════════════╩═══════════════════════════════════════════╣
║  MISSION TIMELINE                                                               ║
║  No events recorded.                                                            ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

### 4.2 Mission Initializing

Operator clicked START MISSION. Backend is creating the mission record and connecting to the data source. No sensor data has arrived yet.

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  FIRERESCUE AI        ◌  INITIALIZING  ·  M-2026-001  ·  00:00:00    [  ...  ] ║
╠══════════════════════════════════════╦═══════════════════════════════════════════╣
║  BUILDING MAP   Floor 1              ║  ALERTS                             (0)  ║
║  ─────────────────────────────────  ║  ─────────────────────────────────────   ║
║                                      ║  Awaiting data source connection...     ║
║   A     B     C     D     E          ║                                          ║
║  ┌─────┬─────┬─────┬─────┬─────┐   ║                                          ║
║ 1│     │     │     │     │     │   ║                                          ║
║  │ A1  │ B1  │ C1  │ D1  │ E1  │   ║                                          ║
║  ├─────┼─────┼─────┼─────┼─────┤   ╠═══════════════════════════════════════════╣
║ 2│     │     │     │     │     │   ║  DRONE STATUS                            ║
║  │ A2  │ B2  │ C2  │ D2  │ E2  │   ║  ─────────────────────────────────────  ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  Connecting...                          ║
║ 3│     │     │     │     │     │   ║                                          ║
║  │ A3  │ B3  │ C3  │ D3  │ E3  │   ║                                          ║
║  ├─────┼─────┼─────┼─────┼─────┤   ╠═══════════════════════════════════════════╣
║ 4│     │     │     │     │     │   ║  VICTIM SIGNALS                          ║
║  │ A4  │ B4  │ C4  │ D4  │ E4  │   ║  ─────────────────────────────────────  ║
║  └─────┴─────┴─────┴─────┴─────┘   ║  Awaiting data...                       ║
║                                      ║                                          ║
║       [ Connecting to data source ]  ║                                          ║
╠══════════════════════════════════════╩═══════════════════════════════════════════╣
║  MISSION TIMELINE                                                               ║
║  00:00:00  Mission M-2026-001 created  ·  Scenario: Building Alpha             ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

### 4.3 Active Mission — Mid-Operation

Mission is running. The drone has covered part of the building. A HIGH hazard has been detected in zones C3 and D3. A victim signal has been detected in zone B2. The drone is currently in zone C3.

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  FIRERESCUE AI         ●  MISSION ACTIVE  ·  M-2026-001  ·  00:07:14  [END ▼] ║
╠══════════════════════════════════════╦═══════════════════════════════════════════╣
║  BUILDING MAP   Floor 1              ║  ALERTS                             (4)  ║
║  ─────────────────────────────────  ║  ─────────────────────────────────────   ║
║                                      ║  ██ 07:02  CRITICAL — Zone D3           ║
║   A     B     C     D     E          ║     Hazard reached CRITICAL level       ║
║  ┌─────┬─────┬─────┬─────┬─────┐   ║  ── 06:18  CRITICAL — Victim Signal     ║
║ 1│░░░░░│░░░░░│░░░░░│     │     │   ║     Zone B2 · Probability: 82%          ║
║  │ A1  │ B1  │ C1  │ D1  │ E1  │   ║  ▒▒ 04:45  WARNING — Zone C3            ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║     Hazard elevated to HIGH             ║
║ 2│░░░░░│▒▒▒▒▒│▓▓▓▓▓│     │     │   ║  ── 00:03  INFO — Mission started       ║
║  │ A2  │[V]  │ C2  │ D2  │ E2  │   ║                                          ║
║  ├─────┼─────┼─────┼─────┼─────┤   ╠═══════════════════════════════════════════╣
║ 3│░░░░░│▒▒▒▒▒│█████│█████│     │   ║  DRONE STATUS   Zone C3                 ║
║  │ A3  │ B3  │[D]  │ D3  │ E3  │   ║  ─────────────────────────────────────  ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  Position     C3  (x:2, y:2)  Floor 1  ║
║ 4│     │░░░░░│▒▒▒▒▒│     │     │   ║                                          ║
║  │ A4  │ B4  │ C4  │ D4  │ E4  │   ║  Temperature  348 °C  ████████████ HIGH ║
║  └─────┴─────┴─────┴─────┴─────┘   ║  CO Level     940 ppm ████████████ HIGH ║
║                                      ║  Smoke         0.81   ███████████░ HIGH ║
║  [D] Drone  [V] Victim signal        ║  Updated 0.4s ago                      ║
║  □ Unobserved  ░ CLEAR  ▒ LOW        ╠═══════════════════════════════════════════╣
║  ▓ MODERATE  ████ HIGH  ████ CRIT   ║  VICTIM SIGNALS                         ║
║                                      ║  ─────────────────────────────────────  ║
║                                      ║  !! B2  82%  ██████████████████  CRIT  ║
║                                      ║     A2  34%  ██████                    ║
╠══════════════════════════════════════╩═══════════════════════════════════════════╣
║  MISSION TIMELINE                                                               ║
║  07:14 Drone → C3   07:02 ██ CRITICAL D3   06:18 ██ Victim B2   04:45 ▒ C3   ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

### 4.4 Mission Completed

Operator ended the mission. All panels are frozen. Data is preserved for review.

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  FIRERESCUE AI        ■  MISSION ENDED  ·  M-2026-001  ·  00:12:47  [REVIEW]  ║
╠══════════════════════════════════════╦═══════════════════════════════════════════╣
║  BUILDING MAP   Floor 1   [FROZEN]   ║  ALERTS                             (6)  ║
║  ─────────────────────────────────  ║  ─────────────────────────────────────   ║
║                                      ║  ██ 11:34  CRITICAL — Zone D3  (final) ║
║   A     B     C     D     E          ║  ── 10:12  CRITICAL — Victim B2        ║
║  ┌─────┬─────┬─────┬─────┬─────┐   ║  ▒▒ 09:05  WARNING — Zone C3            ║
║ 1│░░░░░│░░░░░│░░░░░│░░░░░│░░░░░│   ║  ░░ 07:38  WARNING — Zone D2            ║
║  │ A1  │ B1  │ C1  │ D1  │ E1  │   ║  ── 05:21  INFO — Zone A2 clear         ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  ── 00:03  INFO — Mission started       ║
║ 2│░░░░░│▒▒▒▒▒│▓▓▓▓▓│░░░░░│░░░░░│   ╠═══════════════════════════════════════════╣
║  │ A2  │[V]  │ C2  │ D2  │ E2  │   ║  FINAL DRONE POSITION                   ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  ─────────────────────────────────────  ║
║ 3│░░░░░│▒▒▒▒▒│█████│█████│░░░░░│   ║  Zone  E4  (x:4, y:3)  Floor 1         ║
║  │ A3  │ B3  │ C3  │ D3  │ E3  │   ║  Mission ended at 00:12:47              ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  Frames recorded: 764                  ║
║ 4│░░░░░│░░░░░│░░░░░│░░░░░│[D]  │   ╠═══════════════════════════════════════════╣
║  │ A4  │ B4  │ C4  │ D4  │[E4] │   ║  VICTIM SIGNALS  (at mission end)       ║
║  └─────┴─────┴─────┴─────┴─────┘   ║  ─────────────────────────────────────  ║
║                                      ║  !! B2  88%  ██████████████████  CRIT  ║
║  Mission complete.                   ║     A2  41%  ████████                  ║
║  All zones surveyed.                 ║     C4  31%  ██████                    ║
╠══════════════════════════════════════╩═══════════════════════════════════════════╣
║  MISSION TIMELINE   (scrollable — 12:47 total)                                 ║
║  12:47 Mission ended   12:33 Drone→E4   11:34 ██ CRITICAL D3   10:12 ██ B2  ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

### 4.5 Connection Lost

The WebSocket connection to the backend has dropped. The last known state is displayed but clearly marked as stale.

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  FIRERESCUE AI    ▲  CONNECTION LOST  ·  M-2026-001  ·  00:04:11  [RECONNECT] ║
╠══════════════════════════════════════╦═══════════════════════════════════════════╣
║  BUILDING MAP   Floor 1              ║  ┌────────────────────────────────────┐ ║
║  ─────────────────────────────────  ║  │  ⚠  CONNECTION LOST               │ ║
║                                      ║  │                                    │ ║
║  ┌───────────────────────────────┐   ║  │  Last update: 4 seconds ago       │ ║
║  │                               │   ║  │  Data shown may be outdated.      │ ║
║  │   STALE DATA — LAST KNOWN     │   ║  │                                    │ ║
║  │   STATE FROM 00:04:07         │   ║  │  Attempting to reconnect...       │ ║
║  │   Data may not reflect        │   ║  │  [ ● ○ ○ ]                        │ ║
║  │   current building conditions │   ║  │                                    │ ║
║  │                               │   ║  │  [RECONNECT NOW]                  │ ║
║  └───────────────────────────────┘   ║  └────────────────────────────────────┘ ║
║                                      ╠═══════════════════════════════════════════╣
║  ░░░░░│▒▒▒▒▒│▓▓▓▓▓│█████│           ║  DRONE STATUS   (STALE — 4s ago)        ║
║   A2  │ B2  │ C2  │ D2  │           ║  ─────────────────────────────────────  ║
║                                      ║  Last known zone:  C3                   ║
║                                      ║  Last reading:     348°C / 940ppm       ║
║  Do not rely on this map             ║  Connection lost — data frozen          ║
║  until connection is restored.       ╠═══════════════════════════════════════════╣
║                                      ║  VICTIM SIGNALS  (STALE)                ║
║                                      ║  B2  82%  (last known)                  ║
╠══════════════════════════════════════╩═══════════════════════════════════════════╣
║  MISSION TIMELINE                                                               ║
║  04:11 ▲ CONNECTION LOST   04:07 Drone→C3   04:02 ██ CRITICAL D3             ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

### 4.6 Active Mission — No Victim Signals

The drone has surveyed a significant portion of the building. No zone has produced a victim probability above the display threshold. The system is functioning normally.

```
╔══════════════════════════════════════════════════════════════════════════════════╗
║  FIRERESCUE AI         ●  MISSION ACTIVE  ·  M-2026-001  ·  00:03:52  [END ▼] ║
╠══════════════════════════════════════╦═══════════════════════════════════════════╣
║  BUILDING MAP   Floor 1              ║  ALERTS                             (1)  ║
║  ─────────────────────────────────  ║  ─────────────────────────────────────   ║
║                                      ║  ── 00:03  INFO — Mission started       ║
║   A     B     C     D     E          ║                                          ║
║  ┌─────┬─────┬─────┬─────┬─────┐   ║                                          ║
║ 1│░░░░░│░░░░░│░░░░░│     │     │   ║                                          ║
║  │ A1  │ B1  │ C1  │ D1  │ E1  │   ║                                          ║
║  ├─────┼─────┼─────┼─────┼─────┤   ╠═══════════════════════════════════════════╣
║ 2│░░░░░│░░░░░│░░░░░│     │     │   ║  DRONE STATUS   Zone C2                 ║
║  │ A2  │ B2  │[D]  │ D2  │ E2  │   ║  ─────────────────────────────────────  ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  Position     C2  (x:2, y:1)  Floor 1  ║
║ 3│     │     │     │     │     │   ║                                          ║
║  │ A3  │ B3  │ C3  │ D3  │ E3  │   ║  Temperature   42 °C  ██░░░░░░░░░ LOW   ║
║  ├─────┼─────┼─────┼─────┼─────┤   ║  CO Level      85 ppm ██░░░░░░░░░ LOW   ║
║ 4│     │     │     │     │     │   ║  Smoke          0.11  ██░░░░░░░░░ LOW   ║
║  │ A4  │ B4  │ C4  │ D4  │ E4  │   ║  Updated 0.3s ago                      ║
║  └─────┴─────┴─────┴─────┴─────┘   ╠═══════════════════════════════════════════╣
║                                      ║  VICTIM SIGNALS                         ║
║  9 / 20 zones surveyed               ║  ─────────────────────────────────────  ║
║  No hazards above LOW detected.      ║  No signals above detection threshold.  ║
║                                      ║  Continue surveying remaining zones.    ║
╠══════════════════════════════════════╩═══════════════════════════════════════════╣
║  MISSION TIMELINE                                                               ║
║  03:52 Drone→C2   03:38 Drone→B2   03:24 Drone→A2   03:10 Drone→A1   00:03 ▶ ║
╚══════════════════════════════════════════════════════════════════════════════════╝
```

---

## 5. User Flow

The following describes the complete operator journey from opening the dashboard to completing a mission.

```
LAUNCH DASHBOARD
     │
     │  Operator opens the browser to the dashboard URL.
     │  The frontend connects to the backend WebSocket.
     │  The backend sends the current MissionState (status: IDLE if no mission exists).
     ▼
IDLE STATE
     │
     │  The operator sees the building map (all zones unobserved).
     │  All panels show "—" or "No data".
     │  The START MISSION button is active.
     ▼
CLICK START MISSION
     │
     │  The frontend sends POST /mission/start to the backend REST API.
     │  The backend creates a mission record and activates the data source.
     │  The dashboard transitions to INITIALIZING state immediately (optimistic UI).
     │  The START MISSION button changes to a spinner / disabled state.
     ▼
INITIALIZING
     │
     │  The backend connects to the simulation and begins receiving Frames.
     │  The first MissionState push arrives via WebSocket.
     │  The mission timer begins.
     │  The map shows zones as UNOBSERVED; drone position appears at the starting zone.
     ▼
MISSION RUNNING — EARLY PHASE
     │
     │  Frames arrive at the configured tick rate.
     │  Each Frame produces an updated MissionState.
     │  The drone marker moves across the map.
     │  Zones visited by the drone update from UNOBSERVED to their hazard level.
     │  All readings are LOW or CLEAR. No alerts are generated.
     │  The IOC monitors the map and watches the drone progress.
     ▼
HAZARD DETECTED
     │
     │  The drone enters a zone with elevated temperature and CO.
     │  MissionState updates: that zone's hazard_level changes to MODERATE or HIGH.
     │  The zone color on the map changes.
     │  If the threshold is crossed, an alert is generated and appears in the Alert Panel.
     │  The unread alert badge increments.
     │  The IOC reads the alert and identifies the affected zone on the map.
     ▼
VICTIM SIGNAL DETECTED
     │
     │  The drone passes through a zone with a significant victim signal.
     │  MissionState updates: victim_probability for that zone rises above threshold.
     │  The zone is marked [V] on the map.
     │  A CRITICAL alert appears at the top of the Alert Panel.
     │  The Victim Panel shows the zone with its probability percentage.
     │  The IOC radios the entry team with the zone location.
     ▼
MISSION RUNNING — LATE PHASE
     │
     │  The drone continues surveying remaining zones.
     │  The IOC monitors whether hazard levels are spreading.
     │  Additional alerts may appear as more of the building is covered.
     │  The IOC uses the map to decide whether to direct teams to victim zones.
     ▼
DECISION TO END MISSION
     │
     │  The IOC decides to end the mission (all zones surveyed, or conditions are
     │  too dangerous to continue, or a victim has been located and retrieved).
     │  The IOC clicks END MISSION in the top bar.
     ▼
END MISSION CONFIRMATION
     │
     │  A confirmation prompt appears: "End mission M-2026-001? This cannot be undone."
     │  The IOC confirms.
     │  The frontend sends POST /mission/end to the backend REST API.
     ▼
MISSION COMPLETED
     │
     │  The backend stops the data source and marks the mission as ENDED.
     │  MissionState status changes to ENDED.
     │  All panels freeze at the final state.
     │  The map shows the complete coverage and final hazard state.
     │  The timer stops.
     │  The IOC can review the timeline and final alert list.
     ▼
POST-MISSION REVIEW
     │
     │  The IOC scrolls through the Mission Timeline.
     │  They can see the full sequence of events, hazard escalations, and victim signals.
     │  This data is used for after-action review and briefings.
     │  Starting a new mission resets the dashboard to IDLE.
     ▼
(END)
```

---

## 6. Mission States

The dashboard has seven distinct states. Each state produces a specific visual configuration.

### State 1 — IDLE

**When it occurs:** No mission has been started, or the previous mission has ended and no new mission has been created.

**What the operator sees:**
- Top bar: gray status dot, "IDLE", no timer, no mission ID
- Map: all zones shown as empty outlines (UNOBSERVED), no drone marker
- Alert Panel: "No alerts. Start a mission."
- Drone Status: all fields show "—"
- Victim Panel: "No detections."
- Timeline: empty or shows the final events of the last mission (if one ran earlier)
- Button: `[START MISSION]` — active and clickable

**Operator action available:** Start a new mission.

---

### State 2 — INITIALIZING

**When it occurs:** The operator has clicked START MISSION. The backend has received the request and is connecting to the data source. No Frames have arrived yet.

**What the operator sees:**
- Top bar: pulsing dot, "INITIALIZING", timer at 00:00:00, mission ID assigned
- Map: all zones UNOBSERVED, no drone marker, a subtle "Connecting..." overlay
- Alert Panel: "Awaiting data source connection..."
- Drone Status: "Connecting..."
- Button: disabled spinner (prevents double-click)

**Duration:** Typically under 1 second. If this state persists beyond 5 seconds, the operator should be informed that something is wrong.

---

### State 3 — MISSION ACTIVE

**When it occurs:** Frames are arriving and the mission is running normally.

**What the operator sees:**
- Top bar: green pulsing dot, "MISSION ACTIVE", running timer, mission ID
- Map: zones coloring as the drone visits them; drone marker moving in real time; victim markers appearing when thresholds are crossed
- Alert Panel: live list of alerts, newest first; unread badge count visible
- Drone Status: live position and sensor readings updating every tick
- Victim Panel: live list of zones above detection threshold, sorted by probability
- Timeline: scrolling with new events at the right/bottom
- Button: `[END MISSION]` — active

**Operator action available:** Monitor the situation; end the mission when appropriate.

---

### State 4 — MISSION PAUSED

**When it occurs:** The data source has temporarily stopped producing Frames but the mission has not been ended. (This state is defined for future use; the MVP simulation does not support pause.)

**What the operator sees:**
- Top bar: amber dot, "PAUSED"
- Map: frozen at last known state; a subtle amber tint overlay with "DATA PAUSED" label
- All panels: last known data, labeled "(PAUSED)"
- A notification in the Alert Panel: "Data stream paused. Awaiting next Frame."

---

### State 5 — MISSION ENDED

**When it occurs:** The operator has explicitly ended the mission via the END MISSION button and confirmed the action.

**What the operator sees:**
- Top bar: gray dot, "MISSION ENDED", final elapsed time frozen, mission ID
- Map: frozen at the final state; "[MISSION ENDED]" label; full coverage visible
- Alert Panel: complete alert list from the mission, all read
- Drone Status: last known position and readings; labeled "Final position"
- Victim Panel: final probability readings at mission end
- Timeline: complete event log, scrollable
- Button: `[NEW MISSION]` or `[REVIEW]`

---

### State 6 — CONNECTION LOST

**When it occurs:** The WebSocket connection to the backend has dropped unexpectedly while a mission was active.

**What the operator sees:**
- Top bar: red flashing indicator, "CONNECTION LOST"
- A prominent full-width warning banner at the top of the main content area: "CONNECTION LOST — Data is stale. Last update: Xs ago."
- Map: visible but grayed out or overlaid with a warning pattern; last known state shown
- All panels: last known data, labeled "(STALE — Xs ago)"
- Alert Panel: shows a CONNECTION LOST alert at the top (red, unacknowledgeable)
- A RECONNECT button visible in the top bar and in the connection overlay

**Critical:** The IOC must be immediately aware that the data is not live. Displaying stale data as if it were live could lead to incorrect decisions in a real scenario.

**Operator action available:** Click RECONNECT to attempt to restore the WebSocket connection. If reconnection succeeds, the dashboard transitions back to MISSION ACTIVE with a full MissionState sync from the backend.

---

### State 7 — SIMULATION ERROR

**When it occurs:** The backend has detected that the simulation runner crashed or produced an invalid Frame that could not be processed.

**What the operator sees:**
- Top bar: red dot, "SYSTEM ERROR"
- A prominent error overlay: "Simulation error detected. The data source has stopped."
- The map is frozen at the last valid state
- An error alert appears in the Alert Panel: "SYSTEM ERROR — Data source stopped. Mission data may be incomplete."
- Button: `[END MISSION]` — still active, allowing the operator to formally close the mission record

---

## 7. Alert System

### Alert Levels

The dashboard uses four alert levels. The level determines color, placement, and dismissal behavior.

---

#### Level 1 — INFO (Blue)

**Meaning:** A normal operational event that the operator should be aware of but does not require immediate action.

**Examples:**
- "Mission M-2026-001 started"
- "Drone entered zone C3"
- "Zone A1 status: CLEAR"

**Display behavior:**
- Appears at the bottom of the alert list
- No badge increment on the panel header (informational events are logged, not alerted)
- Small left border: blue
- Does not expand automatically

**Dismiss behavior:** Does not require acknowledgement. Remains in the list for the mission timeline.

---

#### Level 2 — WARNING (Amber)

**Meaning:** A condition that requires monitoring. The situation may worsen. The operator should note the zone and watch for escalation.

**Examples:**
- "Zone B2 — Hazard level elevated to MODERATE"
- "Zone C3 — Temperature rising: 180°C"
- "Drone survey 50% complete — unobserved zones remain in the northern section"

**Display behavior:**
- Appears in the alert list, sorted above INFO alerts
- Badge on panel header increments (+1 unread)
- Left border: amber
- Amber text on zone label
- Does not expand automatically

**Dismiss behavior:** The operator can mark as acknowledged (background dims, moves below new alerts). Acknowledged alerts remain in the list and timeline.

---

#### Level 3 — CRITICAL (Red)

**Meaning:** A condition that requires immediate attention. A significant hazard has been detected or a victim signal is strong.

**Examples:**
- "Zone D3 — Hazard level: CRITICAL (temp: 420°C, CO: 1100ppm)"
- "Zone B2 — Victim probability: 82%"

**Display behavior:**
- Appears at the top of the alert list, above all lower-level alerts
- Alert entry is expanded by default to show full details
- Badge increments and turns red
- Left border and background: red
- The affected zone on the map pulses briefly to draw attention
- If the operator is not looking at the screen, a browser notification is displayed (future)

**Dismiss behavior:** Requires explicit acknowledgement — the operator must click "Acknowledge" on the alert. Once acknowledged, it moves to the acknowledged section but remains visible and in the timeline. Unacknowledged CRITICAL alerts are always shown at the top.

---

#### Level 4 — EMERGENCY (Flashing Red / White)

**Meaning:** Reserved for a condition where an immediate withdrawal or evacuation decision may be required. Multiple CRITICAL zones, or a CRITICAL zone containing a victim signal.

**Examples:**
- "EMERGENCY — Zone C3: CRITICAL hazard AND victim signal present. Entry is extremely dangerous."
- "EMERGENCY — Rapid fire spread detected. Zones C3, D3, D4 reached CRITICAL within 60 seconds."

**Display behavior:**
- Overrides the entire alert panel — EMERGENCY alert is pinned to the top, all other alerts scroll below it
- The alert entry has a flashing red/white border animation (CSS pulsing; no JavaScript animation required)
- The top bar's status dot changes to flashing red regardless of mission state
- The affected zones on the map flash briefly

**Dismiss behavior:** Cannot be dismissed — only acknowledged. EMERGENCY alerts remain pinned at the top until the mission ends.

---

### Alert Color Reference

| Level | Background | Border | Text | Badge Color |
|---|---|---|---|---|
| INFO | Transparent | Blue | Blue | — |
| WARNING | Amber tint | Amber | Amber | Amber |
| CRITICAL | Red tint | Red | White | Red |
| EMERGENCY | Flashing red | Flashing red/white | White (bold) | Red (flashing) |

---

### Alert De-duplication Rule

The same alert is never generated twice for the same zone during the same mission. If zone B2 reaches CRITICAL and then falls to HIGH and rises to CRITICAL again, only the second escalation generates a new alert. The rule is enforced by the backend; the frontend displays whatever alerts are in `MissionState.active_alerts`.

---

## 8. Information Hierarchy

Every piece of information the dashboard displays is assigned to a tier. Higher tiers receive more visual prominence, more screen space, and are shown closer to the top-left of the layout (where the eye naturally goes first).

### Tier 1 — Life Safety (Top priority — must be impossible to miss)

| Information | Source in MissionState | Why it is Tier 1 |
|---|---|---|
| Active CRITICAL and EMERGENCY alerts | `active_alerts` (severity=CRITICAL) | Require immediate decision or action |
| Victim signals above 60% probability | `zone_states[*].victim_probability` | The primary objective of the mission |
| Zones at CRITICAL hazard level | `zone_states[*].hazard_level=CRITICAL` | May indicate imminent danger to entry teams |

**Visual treatment:** Red color. Top of the alert panel. Pinned, not scrolled away. Distinct from everything else on screen.

---

### Tier 2 — Situational Awareness (Monitor actively during the mission)

| Information | Source in MissionState | Why it is Tier 2 |
|---|---|---|
| Drone current position | `drone_pose` | Indicates what is being observed right now |
| Zone hazard levels (all) | `zone_states[*].hazard_level` | Provides the spatial picture of the incident |
| Current sensor readings | `latest_readings` | Context for interpreting the drone's current location |
| Mission elapsed time | `elapsed_seconds` | Pacing — time pressure is real in rescue operations |
| Mission status | `status` | Is the system live? Is data current? |
| Victim signals 30–60% | `zone_states[*].victim_probability` | Potential victims, worth monitoring |

**Visual treatment:** Standard white/light text. Main panels. Visible at a glance without reading carefully.

---

### Tier 3 — Reference and Review (Available but not demanded during live operation)

| Information | Source | Why it is Tier 3 |
|---|---|---|
| Mission timeline events | Backend event log | Primarily useful post-mission |
| Zone last-observed timestamp | `zone_states[*].last_observed_at` | Useful to know how stale a zone's reading is |
| Mission ID | `mission_id` | Radio communication reference; not operationally critical |
| Acknowledged alerts (history) | `active_alerts` (acknowledged) | Already acted on |
| Victim signals below 30% | `zone_states[*].victim_probability` | Low confidence, not actionable |

**Visual treatment:** Muted text. Bottom of the screen (timeline) or secondary position in panels. Not shown during EMERGENCY conditions.

---

### Why This Ordering

The ordering is derived from a single question: *what happens if the operator misses this information?*

- Missing a CRITICAL alert or victim signal can result in a preventable death or a team entering a lethal zone.
- Missing the drone's position or current readings delays decision-making but does not immediately cause harm.
- Missing the mission timeline during a live operation has no immediate consequence.

The dashboard is designed so that the most dangerous information to miss is the hardest to miss.

---

## 9. Design Principles Applied

### Dark Theme

The dashboard uses a dark background throughout. Emergency command operations often occur in partially darkened environments (vehicle interiors, night incidents). A dark background:
- Reduces eye strain during extended monitoring
- Creates higher contrast for the bright hazard colors (red, amber, green on dark is more distinct than on white)
- Reduces glare on outdoor or vehicle-mounted screens

### High Contrast

Every element that carries operational meaning uses a color from the defined hazard or alert palette. Decorative colors are not used. An operator with color vision deficiency should still be able to read every label. Color is used to reinforce meaning, not to be the sole carrier of it.

### No Hover-Only Information

All information visible on hover must also be visible in the fixed panels. The IOC may be using the dashboard on a touchscreen or at a distance. No critical information is hidden behind interactions.

### No Modal Interruptions During Active Mission

The only modal allowed during an active mission is the END MISSION confirmation dialog. Everything else — alerts, zone updates, victim signals — arrives in the panels without interrupting the operator's view of the map.

---

## 10. Future UI Ideas

The following interface features are intentionally excluded from the MVP. They are documented here so that engineers building future phases have a starting reference.

| Feature | Why excluded from MVP | What it would require |
|---|---|---|
| **3D building model** | Requires building geometry data and a 3D rendering library. Adds implementation complexity without improving the MVP demonstration. | Three.js or similar; 3D floor plan asset |
| **Thermal camera feed overlay** | Requires the thermal channel in the Frame schema to be populated. The MVP simulation only generates the environmental channel. | Thermal sensor hardware or simulation; image rendering on the map |
| **LiDAR point cloud view** | Same reason as thermal feed. Future hardware may provide this. | LiDAR hardware; 3D point cloud rendering |
| **Multiple drone tracking** | The current MissionState schema supports multiple drones but the MVP only deploys one. UI would need a drone selector and simultaneous markers. | Multi-drone simulation; per-drone state panels |
| **AR overlay for field teams** | Would require a mobile interface and connection to field devices. Completely out of scope for the MVP. | Mobile app; device location tracking |
| **Voice alerts** | The IOC may miss visual alerts in loud environments. Audio would help. | Browser audio API; alert severity mapping to tones |
| **Team collaboration / shared view** | Multiple operators seeing the same mission simultaneously. Requires user identity and session management. | Authentication; multi-client broadcast filtering |
| **Live video feed from drone camera** | Requires camera hardware and video streaming infrastructure. | Video capture hardware; RTSP or WebRTC streaming |
| **Historical mission comparison** | View two missions side by side or replay a past mission. | Mission replay API; timeline scrubber |
| **Configurable alert thresholds in the UI** | Currently thresholds are server-side configuration. Exposing them in the UI allows in-operation tuning. | Settings panel; backend config API |
| **Floor selector (multi-floor buildings)** | The MVP models one floor. A floor selector tab or dropdown would support multi-floor scenarios. | Multi-floor building model; per-floor map views |
| **Exportable mission report** | Generate a PDF or structured log from a completed mission. | PDF generation; structured data export endpoint |
