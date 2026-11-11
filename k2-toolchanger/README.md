# K2 Plus multi-toolhead conversion: feasibility and build plan

Researched 2026-11-11. Every source below was accessed that day unless a date is given.

**Labels used throughout**

- **[F] fact**: read in a primary source (repo, vendor page, official doc).
- **[E] informed estimate**: reasoned from sourced facts.
- **[G] guess**: no usable source; my judgement.
- *(snippet)* after a label means it came from a search summary, not an opened page.

**Assumptions I made instead of asking**

- "Zero-purge" means no flush between materials; a small prime tower is acceptable.
- You are on US 120 V mains and outside or indifferent to warranty.
- You can print ASA/ABS or a filled nylon for structural brackets.
- 10 hands-on hours per week when converting hours to calendar time.

---

## 0. What changed since your notes

No community project puts a toolchanger on a K2, but something adjacent exists that changes the whole plan: open firmware now runs on the K2 Plus's own mainboard.

| Your starting belief | What I found | Label and source |
|---|---|---|
| Motors use a proprietary RS-485 protocol through Creality's controller | The closed-loop motors take ordinary STEP/DIR from the main MCU. RS-485 only handles wake-up, addressing, stall homing, protection and tuning. | [F] [K2-OpenKlipper MOTOR-CONTROLLER.md](https://github.com/grant0013/K2-OpenKlipper/blob/main/docs/MOTOR-CONTROLLER.md); `config/k2/printer.cfg` in [Jacob10383/kalico](https://github.com/Jacob10383/kalico) |
| Rooting project archived; forks only do Cartographer/Fluidd | Two open stacks run on the stock board with stock MCU firmware: [Jacob10383/k2-plus-custom-firmware](https://github.com/Jacob10383/k2-plus-custom-firmware) (Kalico fork, first releases 6 and 8 Nov 2026) and [grant0013/K2-OpenKlipper](https://github.com/grant0013/K2-OpenKlipper) (upstream Klipper, K2 Plus tested on one machine since 31 Oct 2026). Both are reversible. | [F] repo docs and release pages |
| A toolchanger needs mainline Klipper on a board you control, so a brain transplant | You can run Klipper/Kalico you control on the stock board. No board swap needed. | [F] same |
| INDX dev kit status unknown | On sale: INDX Toolhead $390, tools $45 each, listed "available on backorder". Kalico supports it natively, and the K2 Kalico fork already contains the module and the toolboard firmware build. | [F] [Bondtech INDX shop](https://www.bondtech.se/product-category/indx/); local clone of Jacob10383/kalico at commit `089cf65` |
| Nobody has done this on a K2 Plus | Still true. Eight researchers and eight fact-checkers found none. Reddit, Discord and YouTube were not directly searchable. One [Creality forum thread](https://forum.creality.com/t/can-we-please-get/46562) only asks for it. | [E] absence of evidence |
| You own an "E3D Obsidian High Flow hotend" | It is a nozzle (integrated nozzle and heatbreak) for the stock K2 heater block, not a hotend. | [F] [E3D product page](https://e3d-online.com/products/high-flow-obxidian-creality-k2-plus-nozzles) |
| Creality has no toolchanger | Creality K3 with "KliTek" 4-nozzle changer is on pre-order at $849, 260 mm cube. No K2 retrofit announced. | [F] [Creality store](https://store.creality.com/products/k3-multi-material-multicolor-3d-printer), [KliTek FAQ](https://www.creality.com/blog/klitek-nozzle-changer-faq) |

---

## 1. Verdict

**Feasible, as an INDX retrofit on open firmware, built in stages. The "Voron inside a Creality shell" version is no longer the right plan.**

The firmware barrier you expected is gone: Kalico runs on the stock board, the motors are plain step/dir, and Kalico ships native support for Bondtech's INDX head, which is a single USB device. What remains is mechanical and integration work that nobody has done on this printer: a carriage adapter, a dock mount, filament tube routing, and reworking a firmware config that assumes the stock toolhead. Budget about $750 and 50–90 hands-on hours to reach a two-tool proof, with two free go/no-go gates before you spend anything. The firmware stack is days old and you would be first, so treat this as a project, not an upgrade.

| Option | Verdict | One-line reason |
|---|---|---|
| C. INDX on open firmware | **Feasible** (recommended) | Native firmware support, one USB board, passive $45 tools, small docks |
| B alone. Open firmware, stock toolhead | **Feasible** (it is Phase 1) | Free, reversible, gives slicer-controlled flush volumes on its own |
| C2. StealthChanger on open firmware | Feasible but dumb | Full-size tools in a frame with no spare travel, 4+ MCUs on a maxed CPU, PSU short |
| A. Brain transplant | Not needed | Solves a problem that no longer exists; fallback only |
| D. IDEX | Feasible but dumb | New gantry for two tools; worse result than INDX for more work |
| E. Buy instead | Sensible if you want it to just work | Bambu H3C, $2,499, 9 tools, 330 mm class, 65°C chamber |

**Caveats that should weigh on the decision**

- **No abrasives on INDX today.** Bondtech's nozzles shipped softer than specified ("Nozzlegate", about 30–32 HRC), and Prusa's kit page says non-abrasive only. If CF or GF nylon in the heated chamber is why you own a K2 Plus, the stock toolhead stays your abrasives head. [F] [Bondtech statement 2026-07-29](https://www.bondtech.se/2026/07/29/indx-hardened-nozzles-update/), [Prusa kit page](https://www.prusa3d.com/product/indx-4-tool-conversion-kit-for-core-one-l/)
- **The CFS is retired in option C.** Each INDX tool carries its own filament and there is no cutter.
- **The honest "sell it" answer:** if your time is worth more than about $20/hour to you and you do not want the project itself, sell the K2 Plus Combo and buy an H3C. Net outlay is roughly $1,650–1,800 [G].

---

## 2. Architecture options

### A. Full brain transplant (new board, mainline Klipper)

- **What it is:** replace the Creality mainboard with a third-party controller and host, then add toolchanger hardware.
- **Kept:** frame, gantry mechanics, bed, enclosure.
- **Lost:** CFS, stock screen, belt-tensioner control, nozzle load-cell probe, power-loss recovery, everything Creality. Cameras survive only as USB webcams on the new host.
- **Unknown:** whether the closed-loop motors can be kept. They take step/dir, but a new board would also need an RS-485 transceiver and the open wake-up module. No source confirms anyone has done it. [G]
- **Status:** unnecessary. Keep it as the fallback if the stock board dies or the open firmware is abandoned.

### B. Hybrid (keep the Creality mainboard)

- **Is it possible given RS-485? Yes.** RS-485 was never the obstacle; the closed host software was. On stock Creality firmware a second extruder or toolchanger is not practical, because the motor, probe and CFS code are compiled blobs and Creality's `master-server` drives the printer. [F] [CrealityOfficial/K2_Series_Klipper](https://github.com/CrealityOfficial/K2_Series_Klipper) (latest commit 2025-10-22, `.so` blobs)
- **What it actually looks like:** replace the host software, not the board. Tool electronics attach as extra USB MCUs, which is ordinary Klipper.

| | B1. Jacob10383 firmware | B2. grant0013 K2-OpenKlipper |
|---|---|---|
| Base | Kalico fork, custom kernel and rootfs in a second firmware slot | Upstream Klipper on the stock OS |
| K2 Plus status | Built for the K2 Plus; first releases 6 and 8 Nov 2026; 39 stars, 1 open issue [F] | Alpha; one K2 Plus tester, no CFS, since 31 Oct 2026 [F] |
| Back to stock | `swap` command, reboots into stock [F] | `uninstall.sh` [F] |
| INDX | Module and toolboard firmware already in the fork [F] | Needs `BondtechAB/indx_klipper` (3 commits, no README) [F] |
| StealthChanger | Not supported: StealthChanger docs say Kalico "No, not at the moment" [F] | Supported in principle (mainline Klipper) |
| USB serial devices | Cartographer runs on `/dev/ttyACM0` [F] | Stock kernel needed a userspace USB bridge for Cartographer on the K2 Plus [F] |
| CPU relief | Not documented | External-host mode: Klipper on a separate PC over the board's mini-USB [F] |
| Assumes | Cartographer mount and 5.8 mm Y spacer by default; `bootstrap --probe prtouch` switches to the stock probe [F] | Creality firmware 1.1.7.0, specific board IDs [F] |

- **Kept:** mainboard, closed-loop motors, bed, chamber heater, motorised belt tensioners, CFS (with the stock toolhead), chamber camera, touchscreen hardware, stock firmware as a fallback.
- **Lost:** Creality Cloud and app, Creality Print integration, stock touchscreen UI (replaced by HelixScreen or Hark Screen), nozzle-camera flow calibration, maintenance counters. [F] [OpenKlipper PROJECT-STATUS.md](https://github.com/grant0013/K2-OpenKlipper/blob/main/docs/PROJECT-STATUS.md)
- **Unknown:** how either stack behaves over months; whether your board revision is covered.

### C. INDX retrofit on B1 (recommended)

- **What INDX is:** one active "Smart Head" stays on the carriage (induction coil, IR temperature sensor, extruder, load cell, accelerometer). Tools are passive nozzle units with no wires, held by a kinematic coupling and parked in small docks. Each tool keeps its own filament loaded. [F] [BondtechAB/INDX README](https://github.com/BondtechAB/INDX)
- **On top of B1 it takes:**
  - a carriage adapter from the K2 X carriage to the Smart Head's 4-bolt pattern (design from Bondtech's reference STEP)
  - a rigid dock rail bolted to the frame, front or rear
  - 24 V and USB to Bondtech's Link Board, then one Link Cable to the head
  - a reworked printer config: extruder, heater, fans, probe and accelerometer move from the stock nozzle board to the INDX board; CFS, cutter and stock probe sections come out
  - one PTFE path per tool from spool to dock, with slack to reach the whole bed
- **Kept:** everything in B except the items below.
- **Lost:** CFS feeding, the nozzle camera, the cutter, the stock load-cell probe (replaced by INDX's), abrasive-filament capability for now.
- **Unknown:** carriage geometry and belt width; lid clearance for a head about 152 mm tall; where a dock rail can bolt on; whether Jacob's modules start cleanly without the stock nozzle board; CPU headroom with one more USB MCU.

**INDX numbers that drive the design** [F] BondtechAB/INDX README

| Parameter | Value |
|---|---|
| Gantry clearance needed | 50 mm in X, 44 mm in Y |
| Head height | about 152 mm including strain relief |
| Head mass | 345 g including one tool; each tool 25 g |
| Dock size | about 70 mm tall, 28.5 mm wide (X), 25 mm deep (Y) |
| Tool pitch | 34 mm bare, 41 mm with Bondtech part cooling |
| Y clearance beyond docks | at least 26 mm; stated worst-case Y loss 28.5 mm |
| Power | 24 V maximum, about 60 W; Link Board has a 4 A fuse |
| Cable limit | USB plus Link Cable no more than 2 m combined |
| Limits | 300°C nozzle, 60°C ambient, 40 mm³/s |
| Firmware | Kalico recommended; USB only on Klipper/Kalico |

**What that means on a K2 Plus** [E]

- X travel is about 356 mm, so up to 8 tools fit at 41 mm pitch.
- The K2 Plus has almost no travel outside the bed (about 6 mm in front; a rear zone to Y380 only between X132 and X230), so the dock row sits inside the bed envelope. Plan on losing 30–55 mm of Y.
- The 350 W, 24 V supply is not stressed: INDX's 60 W replaces the stock hotend heater, and the bed and chamber heaters are on AC.
- Docked tools are unheated, so there is no standby power and no ooze from parked tools.

### C2. StealthChanger on B2

- **Kept and lost:** as C, but each tool is a complete hotend, extruder and toolboard.
- **Why it is the worse fit:**
  - needs mainline Klipper, so the less-tested stack (B2)
  - tool pitch 60–76 mm, so about 4 tools; designed around Voron extrusions and carriage [F] [StealthChanger Docks wiki](https://github.com/DraftShift/StealthChanger/wiki/Docks)
  - 4 extra USB MCUs on a host CPU that already runs above one full core, so an external host is effectively required [F] [EXTERNAL-HOST.md](https://github.com/grant0013/K2-OpenKlipper/blob/main/docs/EXTERNAL-HOST.md)
  - several heated tools on a 350 W supply; the closest precedent (Sovol SV08) needed a PSU swap [F] [Teaching Tech SV08 build](https://teachingtechyt.github.io/sv08toolchanger.html)
  - the per-tool dock kit is sold out at West3D [F]
- **One real advantage:** hardened nozzles and any hotend you like, so abrasives work.

### D. IDEX

- **Needs:** a new X beam with two carriages, at least one extra motor on the gantry, re-routed belts, and `hybrid_corexy` with `dual_carriage`. It also needs open firmware, so it sits on top of B anyway. [F] Kalico config reference; [E] for the K2-specific part
- **Result:** two tools, less X travel, and the closed-loop motors and belt tensioners no longer match the gantry.
- **Precedent:** none on an enclosed consumer CoreXY. RatRig V-Core 4 IDEX is the reference open design. *(snippet)*
- **Status:** more work than C for a worse result. Skip.

### E. Leave the K2 alone and buy something

| Machine | Tools | Volume (mm) | Heated chamber | US price | Availability | Label |
|---|---|---|---|---|---|---|
| Bambu Lab H3C AMS Combo | 9 full tools | 330×320×325 | 65°C | $2,499 | launched 2026-11-03 | [E] several outlets and Bambu's forum; store page not opened |
| Prusa INDX kit for CORE One L/L+ | 4 or 8 | 298×275×330 after install | 60°C | $763.80 / $995.28, kit only | new orders ship after Feb 2027 | [F] Prusa kit pages |
| Prusa XL+ 5-tool enclosure bundle | 5 | 360 class | passive enclosure | about $3,925 | 4–5 weeks | [E] *(snippet)* |
| Snapmaker U1 | 4 | 270 cube | none | $699 (Black Friday) | on sale | [F] Snapmaker blog |
| Creality K3 (KliTek) | 4 nozzle units | 260 cube | none | $849 | pre-order, ships early Dec | [F] Creality store |
| Bambu Lab H2C Combo | nozzle swap | 330×320×325 | 65°C | $1,899 (Black Friday) | on sale | [F] secondary source; about 58% less purge, not zero |
| Voron 2.4 350 + StealthChanger, 4 tools | 4–6 | 350 cube | passive | $2,200–3,000 | DIY | [G]; LDO kit alone $1,399.99 *(snippet)* |

- **Matches the K2 Plus on size and heated chamber:** only the H3C comes close, and it is a closed ecosystem.
- **K2 Plus Combo resale:** new is $1,099 on Creality's store [F]; used asks run $730–1,050 [E] *(snippets)*; expect $700–850 actually realised [G].
- **Waiting on Creality:** a Sept 2025 AMA said K2-series upgrade kits were planned; a secondary report says staff ruled out a KliTek kit for older printers. Nothing official either way. [F] [AMA](https://www.creality.com/blog/creality-reddit-ama-campaign-2025); [E] makers101

### What each option keeps

| | Stock | B: open firmware | C: INDX | C2: StealthChanger | A: new board |
|---|---|---|---|---|---|
| CFS | yes | yes | no | no | no |
| Chamber camera | yes | yes | yes | yes | as USB webcam |
| Nozzle camera and flow calibration | yes | not ported | removed | removed | no |
| Motorised belt tensioning | yes | yes | yes | implemented, not yet run on a Plus | no |
| Closed-loop motors | yes | yes | yes | yes | unknown |
| Z probe | nozzle load cell | same, open driver | INDX load cell | optical tap per tool | your choice |
| Touchscreen | stock UI | HelixScreen / Hark Screen | same | same | replace |
| Creality Cloud / Creality Print | yes | no | no | no | no |
| Warranty | yes | at risk | assume gone | assume gone | gone |
| Back to stock | n/a | one command | one command plus remounting the toolhead | same | days |

---

## 3. Bill of materials

Prices exclude tax. Bondtech prices are from the [INDX category page](https://www.bondtech.se/product-category/indx/) and the [toolhead page](https://www.bondtech.se/product/bondtech-indx-toolhead/). Machine-readable copy: [`bom.csv`](bom.csv).

### Option C (INDX): must buy

| Item | Unit price | 1 tool | 2 tools | 4 tools | Label |
|---|---|---|---|---|---|
| Bondtech INDX Toolhead (Smart Head, Link Board, crimp kit) | $390.00 | 1 | 1 | 1 | [F] on backorder, no lead time given |
| INDX Link Cable XT30 | from $20.90 | 1 | 1 | 1 | [F] price; may already be included with the toolhead (pages disagree) |
| INDX Radial Part Cooling | $28.90 | 1 | 1 | 1 | [F] |
| INDX Nozzle Silicone Sock, 5-pack | $4.90 | 1 | 1 | 1 | [F] |
| INDX Passive Tool (Steel CHT, or 0.4 Standard Flow) | $45.00 | 1 | 2 | 4 | [F] |
| INDX Tool Dock 1515 | $14.90 | 0 | 2 | 4 | [F] printable from Bondtech's repo instead |
| INDX Tool Dock Hardware Accessories | $4.90 | 0 | 1 | 1 | [F] quantity per dock not confirmed |
| **Bondtech subtotal** | | **$489.70** | **$569.40** | **$689.20** | |
| USB cable, wire, ring terminals, fasteners, heat-set inserts | | $33 | $33 | $33 | [G] |
| PTFE tube and fittings | | $10 | $15 | $25 | [G] |
| 15×15 extrusion for the dock rail | | $0 | $15 | $15 | [G] |
| Shipping from Sweden | | $35 | $35 | $35 | [G] not researched |
| US import duty and brokerage, assumed 15% | | $73 | $85 | $103 | [G] not researched |
| **Total** | | **about $640** | **about $750** | **about $900** | |

- Eight tools: about $1,200 on the same basis. [E]
- Each tool added later: $59.90 plus duty, and shipping again if ordered separately. [F] prices
- A single tool needs no dock: Bondtech's docs let you seat T0 by hand with `MANUAL_TOOL_SEAT TOOL=0`. [F]

**Optional**

| Item | Price | When | Label |
|---|---|---|---|
| Raspberry Pi 5 4GB as external host | $110.00 at SparkFun, plus about $30 for supply, case, storage | only if the printer's CPU cannot keep up | [F] price; [G] extras |
| INDX Eddy Current Scanner and mount | $14.90 + $7.90 | faster bed meshing | [F] |
| Cover Set for INDX Development Kit | $9.90 | cosmetic | [F] |

### Option C: print yourself

| Part | CAD exists? | Notes |
|---|---|---|
| Carriage adapter, K2 X carriage to Smart Head | **Design from scratch** | Bondtech publishes a reference STEP for the mounting geometry and a printable MGN12H adapter for Voron belt paths with 6 mm belts. The K2 rail looks MGN12-class [E], but belt width and carriage pattern are unknown, so assume the Voron adapter does not drop in. |
| Dock rail bracket to the K2 frame | **Design from scratch** | Must be rigid; Bondtech says docks cannot be free-standing. |
| Dock bodies | Yes, [BondtechAB/INDX](https://github.com/BondtechAB/INDX) `CAD` folder | 1515 body and a community 2020 version. |
| Dock calibration tool | Yes, same repo | |
| Link Board mount, tube guides, cable-chain adapter | **Design from scratch** | |
| Parking bracket for the stock nozzle board | **Design from scratch** | See Phase 2: keeping the stock board plugged in simplifies the firmware migration. |
| K2 Plus body reference | Community STEP on Printables (model 1199432) | [E] *(snippet)*; reportedly panels only, no carriage. Expect to measure with calipers. |

Material: ASA or ABS at minimum; a filled nylon or PC for the carriage adapter, since the chamber reaches 60°C. Bondtech's own adapter is SLS nylon 12 GF. [F] for Bondtech's part; [E] for the recommendation

### Already own

| Item | Usable as tool 1? | What to do with it |
|---|---|---|
| E3D High Flow ObXidian nozzle | No. It only fits the stock K2 heater block. | Keep it in the stock toolhead, which becomes your abrasives head and your return-to-stock kit. |
| Creality K2 Plus extruder kit ($32.86–36.51 new) | No. K2-specific assembly. | Same: fit it to the stock toolhead, or sell it. |
| CroGrip and ice plates | Unaffected | Keep. |
| CFS | Not used in option C | Keep for stock-toolhead use, or sell. |

### Option C2 (StealthChanger): for comparison

| Item | Unit price | 2 tools | 4 tools | Label |
|---|---|---|---|---|
| LDO StealthChanger Base Kit (shuttle, 6+1 USB hub, probe) | $89.90 | 1 | 1 | [F] West3D |
| LDO Toolhead and Dock Kit (toolboard, tap sensor, fans, dock) | $59.90 | 2 | 4 | [F] West3D, **sold out** |
| TriangleLab Rapido ACE hotend | $79.99 | 2 | 4 | [F] West3D |
| LDO Orbiter Extruder V2.5 | $64.99 | 2 | 4 | [F] West3D; motor variant unclear |
| LDO NEMA14 pancake motor (LDO-36STH20-1004AHG) | $20.99 | 2 | 4 | [F] West3D; may be redundant |
| External host (Pi 5 and extras) | about $140 | 1 | 1 | [F]/[G] |
| 24 V PSU upgrade | about $40 | 0 | 1 | [G] not priced |
| Wire, PTFE, fasteners | | $60 | $80 | [G] |
| **Total** | | **about $740** | **about $1,250** | [E] |

Design from scratch: shuttle adapter for the K2 carriage, front dock bar mount, every umbilical path. The stock shuttle assumes a Voron carriage. [F]

### Option A (brain transplant): fallback, not fully priced

I stopped pricing this once the research showed it is unnecessary. Verified so far: BTT Manta M8P V2.0 $81.29 at 3DJake (ships from the EU, not a US vendor) and Raspberry Pi 5 4GB $110. Drivers, PSU, steppers, SSR, wiring and a screen are not priced. Rough total for the transplant alone: $400–600 [G], with toolchanger hardware from C or C2 on top.

### Option D (IDEX)

Not priced in detail. Rough parts cost $300–600 [G].

---

## 4. Skills and tooling

Ratings are for option C.

| Skill | What it involves here | Rating | Why |
|---|---|---|---|
| Root, SSH, installing and rolling back firmware | Enable root on the screen, run an installer, use `swap` | AI can carry me | You already do this for a living. |
| Klipper/Kalico config | Not from scratch. Edit a working K2 config to move toolhead functions to the INDX board. | AI helps, but I need hands-on reps | AI can write it; only you can test each change at the machine with a hand on the power switch. |
| Reading and patching klippy Python modules | Find and relax dependencies on the stock nozzle board | AI can carry me | It is ordinary Python and you are a developer. |
| Flashing a USB MCU | Build and flash the INDX toolboard firmware | AI can carry me | Documented, two commands. |
| CAN bus | Not needed. INDX uses USB on Kalico. | n/a | |
| Kinematics and travel limits | CoreXY is unchanged. New work is safe zones around the docks. | AI helps, but I need hands-on reps | Wrong limits crash the head into the dock. |
| Dock calibration | Dock height, `INDX_DOCK_MEASURE`, approach clearance | AI helps, but I need hands-on reps | Fractions of a millimetre, judged by feel and by watching. |
| Tool offset calibration | Per-tool XY and Z after pickup | AI helps, but I need hands-on reps | Simpler than StealthChanger: same head and coupling for every tool. |
| CAD for the carriage adapter and dock bracket | Parametric parts from your measurements and Bondtech's STEP | AI helps, but I need hands-on reps | AI cannot measure your carriage or judge stiffness. Expect 3–6 printed iterations [E]. |
| Wiring and crimping | 24 V tap at the PSU terminals, XT30 Link Cable, USB | AI helps, but I need hands-on reps | Small scope, and the kit includes a crimp set. No mains wiring is involved. |
| Load-cell and heater calibration | `CALIBRATE_LOAD_CELL`, `INDX_CALIBRATE` | AI can carry me | Scripted procedures. |
| Slicer profile | OrcaSlicer multi-tool profile, tool-change macro | AI can carry me | |
| Diagnosing timing faults | "Timer too close" on the printer's CPU; moving to an external host | AI helps, but I need hands-on reps | Log-reading is easy for AI; reproducing it is on you. |
| Module internals in Jacob's firmware | If the stack will not start without the stock toolhead | **Needs a human expert** | The author is the expert. Ask on the project's Discord before patching deeply. |

Tools you do not have to buy: nothing beyond calipers, a kitchen scale and what the kit includes. [E]

---

## 5. Timeline

All figures are [E] unless marked. Calendar time assumes 10 hours a week.

### Option C, to a working two-tool printer

| Scenario | Hands-on hours | Calendar | What happens |
|---|---|---|---|
| Best case | about 50 | about 8 weeks | Kit ships within 2 weeks. First adapter design fits. Firmware starts without the stock nozzle board after config edits only. |
| Realistic | about 90 | 12–16 weeks | Backorder of 4–8 weeks, plus the three blockers below. |
| Worst case | 110–130 before you stop | 4–5 months | You get to Phase 3 and cannot make tool pickup reliable in this frame. |

**Likely blockers in the realistic case**

1. **Carriage adapter and dock position take 4–5 iterations.** Adds about 12 hours.
2. **Jacob's modules expect the stock nozzle board.** Workaround is leaving it connected, or patching. Adds about 10 hours.
3. **The printer's CPU cannot take another USB device at speed.** Fix is an external host. Adds about 8 hours and about $140.

**Per phase**

| Phase | Best | Realistic | Gate |
|---|---|---|---|
| 0. Measure and read | 4 h | 5 h | Does INDX physically fit? |
| 1. Open firmware on the stock toolhead | 8 h | 14 h | Does the printer work on firmware you control? |
| 2. One INDX tool printing | 25 h | 45 h | Does the head probe and print reliably? |
| 3. Dock and second tool | 15 h | 28 h | Are tool changes reliable? |
| 4. Tools 3 and 4 | 6 h | 10 h | |

**Where you find out it is not going to work**

| If it fails at | Hours burned | Money burned |
|---|---|---|
| Phase 0 | about 5 | $0 |
| Phase 1 | about 20 | $0 |
| Phase 2 | about 70 | $640–750, partly recoverable by reselling the kit [G] |
| Phase 3 | 110–130 | $750–900, same |

### Other options, for scale

- **C2 StealthChanger:** 150–250 hours [G]. More CAD, more wiring, per-tool tuning, and an external host from day one.
- **A brain transplant:** adds 40–80 hours [G] before any toolchanger work starts.

---

## 6. Blockers and risk register

Ranked by likelihood times impact, for option C. Likelihood and cost figures are [E] unless marked.

| # | Risk | Likelihood | Impact | Mitigation | Cost if it hits |
|---|---|---|---|---|---|
| 1 | **Mechanical fit is first-of-kind.** Carriage adapter, dock rail and tube routing all need original design. | High | Schedule | Phase 0 measurements before buying. Design the adapter stiff first, light second. | 10–20 extra hours |
| 2 | **Firmware stack is days old.** Jacob's first releases are 6 and 8 Nov 2026; OpenKlipper is alpha with one K2 Plus tester. [F] | Medium-high | Failed prints, stalled project | Stay one release behind. Keep the stock slot intact. Use the Discord. | Hours; no money |
| 3 | **Stock nozzle board dependency.** The K2 config hangs the extruder, heater, fans, filament sensor, accelerometer and probe on it, and the motor module talks to the extruder through it. [F] local config | Medium-high | Phase 2 delay | Leave the stock board plugged in and parked for bring-up; migrate one function at a time. | About 10 hours |
| 4 | **Parts availability.** INDX Toolhead is on backorder with no date. [F] | High | Schedule only | Order once Phase 0 passes; do Phase 1 while waiting. | Weeks |
| 5 | **No abrasive filaments.** Nozzles are about 30–32 HRC. [F] | Certain today | Capability | Keep the stock toolhead for abrasives. Watch for hardened INDX tools (E3D is reported to be working on them). | A toolhead swap per abrasive job |
| 6 | **CPU and USB headroom.** Klipper already used about 108% of a core on this SoC in OpenKlipper's measurements. [F] | Medium | Timing shutdowns mid-print | External-host mode: 5% CPU on an old Celeron, 7.5-hour print clean. [F] | About $140, 8 hours |
| 7 | **Dock space and travel.** No spare travel, so docks eat bed area. | Certain | 30–55 mm of Y lost | Accept it; 350×300 is still large. Check the rear chute and front door in Phase 0. | Bed area |
| 8 | **Heated chamber.** INDX's ambient limit is 60°C, the same as the chamber's maximum. Prusa keeps a 60°C chamber with INDX on the CORE One L+. [F] both | Low-medium | Thermal faults, soft printed parts | Cap the chamber at 50–55°C at first. Link Board outside the chamber. Filled nylon for the adapter. | Reprints of brackets |
| 9 | **Failed tool change is unrecoverable.** Listed by Bondtech as a known limitation. [F] | Medium early, low once tuned | A lost print | Enable the seat check. Run a tool-change torture test before real prints. | Filament |
| 10 | **Losing the CFS.** | Certain in C | No auto spool switching, RFID or CFS storage | It comes back with the stock toolhead and `swap`. | About an hour per switch [G] |
| 11 | **Head clearance under the lid.** Head is about 152 mm tall; lid height above the gantry is unknown. | Unknown | Kills C if it does not fit | Phase 0 measurement. Printable lid risers exist for the K2 Plus. *(snippet)* | $0 if caught in Phase 0 |
| 12 | **Cable length.** USB plus Link Cable must stay within 2 m; longest Link Cable is 178 cm. [F] | Low-medium | Link Board must sit near the gantry entry | Measure the stock toolhead cable route in Phase 0. | Relocating the board |
| 13 | **Bricking.** Neither stack flashes the MCUs; Jacob's installs to the other firmware slot. No brick reports found, with limited search depth. [F]/[E] | Low | Printer down | Never write motor flash parameters (opcode 07). Do not enable the motor "FAL" setting. Both are documented hazards. [F] | $39.26 for a mainboard kit at worst [F] |
| 14 | **Reversibility.** | Low risk | | Do not cut the stock harness. Keep every stock part bagged. | An hour to revert [G] |
| 15 | **Frame rigidity.** INDX head is 345 g and docking forces are small. OpenKlipper measured frame resonance at 35–46 Hz on the smaller K2. [F] | Low | Ringing | Re-run input shaping with the INDX accelerometer. | An hour |
| 16 | **Power budget.** 350 W at 24 V; INDX's 60 W replaces the stock hotend heater; bed and chamber are on AC. [F] wiring diagram, not re-checked by the fact-checker | Low | | None needed for C. | n/a |
| 17 | **Creality OTA update overwrites the custom slot.** [F] | Low | An evening | Documented procedure: `swap`, update, re-run installer with "keep my setup". | 1–2 hours |
| 18 | **Bed heating on 120 V under OpenKlipper.** Documented gap on the K2; unverified on the Plus. [F] | Low for B1 | Bed never reaches 100°C | Use Jacob's stack; check in Phase 1. | Switch stacks |
| 19 | **Import cost uncertainty.** Duty and shipping are guesses. | Medium | $50–100 either way | Get the checkout total before committing. | |
| 20 | **Warranty.** Creality's text could not be retrieved; the open firmwares say it "may void". | Likely | Only matters inside the first year | `swap` back before any claim. | |

---

## 7. Phased plan with go/no-go gates

### Phase 0: confirm on paper and on your machine

- **Cost:** $0. **Hours:** 3–5.
- **Check on the printer:**
  - Firmware version (the open stacks target 1.1.7.0) and board ID.
  - Clearance around the X carriage: is there 50 mm in X and 44 mm in Y?
  - Height from nozzle tip to the underside of the lid: is there room for about 152 mm of head?
  - X rail size and block type, belt width, how belts anchor to the carriage, carriage bolt pattern. Photos and caliper numbers.
  - Length of the stock toolhead cable route, for the Link Cable.
  - Dock candidates, front and rear: which frame members could take a 15×15 rail; distance from the nozzle at Y-min to the door and at Y-max to the rear wall; what is in the way (waste chute, wipe pad, chamber heater outlet, cutter lever).
  - Where the external USB port is, and whether the PSU's 24 V terminals are reachable.
  - Where 2–4 PTFE tubes could enter and loop.
  - Your purge baseline: weigh the waste from one known two-colour print. No published per-swap figure exists for the K2 Plus.
- **Read:** [BondtechAB/INDX README](https://github.com/BondtechAB/INDX), [Kalico INDX doc](https://docs.kalico.gg/INDX.html), [Jacob's install, calibration and recovery docs](https://jacob10383.github.io/k2-plus-custom-firmware/), [K2-PLUS-BETA.md](https://github.com/grant0013/K2-OpenKlipper/blob/main/docs/K2-PLUS-BETA.md), [Teaching Tech's SV08 conversion](https://teachingtechyt.github.io/sv08toolchanger.html).
- **Pass:** the INDX envelope fits with at least 5 mm to spare, a rigid dock location exists, and the cable run is under about 1.8 m.
- **If you stop here:** nothing has changed.

### Phase 1: open firmware, stock toolhead

- **Cost:** $0. **Hours:** 8–15.
- **Do:**
  - Enable root, change the default password, back up your config.
  - Read the installer before running it; add `--no-telemetry` if you prefer.
  - Install Jacob's firmware and set the stock probe mode (`bootstrap --probe prtouch`), since you have no Cartographer.
  - Calibrate, then print three jobs: one short, one of 6+ hours, one CFS multi-colour.
  - Confirm the bed reaches 100°C and the chamber heater works.
  - `swap` to stock and back.
  - Plug in any USB serial device and confirm it appears as `/dev/ttyACM*`.
  - Watch CPU load and `klippy.log` during a print.
- **Pass:** three clean prints, a working round trip to stock, a USB device that enumerates, no timing errors.
- **If you stop here:** you have a K2 Plus on open firmware with the CFS working and flush volumes taken from OrcaSlicer, which stock firmware reportedly ignores. Or `swap` back and you are stock again. [F] Jacob's OrcaSlicer doc; [E] forum reports on stock behaviour

### Phase 2: one INDX tool

- **Cost:** about $640 for one tool, or about $750 if you order the second tool and docks now (recommended, to pay shipping once). **Hours:** 25–45.
- **Do:**
  - **2a, on the bench:** power the Link Board from 24 V, flash the toolboard, run `INDX_CALIBRATE`, heat and extrude. About 3–4 hours.
  - Design and print the carriage adapter; mount the head.
  - Copy the working config to a new profile. Leave the stock nozzle board connected and parked. Move extruder, heater, fans, accelerometer and probe to the INDX board; disable the CFS, cutter and stock-probe sections.
  - Calibrate the load cell, Z tilt, mesh and input shaper.
  - Seat one tool by hand and print.
- **Pass:** a 10-hour single-material print at stock-like quality; probe repeatability within about 0.02 mm; no thermal or timing faults at a 50°C chamber.
- **If you stop here:** you have a single-nozzle induction-heated K2 Plus, or you remount the stock toolhead, `swap`, and sell the kit.

### Phase 3: dock and second tool

- **Cost:** included above if ordered together. **Hours:** 15–28.
- **Do:** dock rail and bracket; dock calibration; Bondtech's tool-change macros; new Y limits; PTFE routing; OrcaSlicer profile; a tool-change torture test.
- **Pass:** 200 consecutive tool changes with no failed pickup, then a two-material print with nothing more than a prime tower.
- **If you stop here:** a two-material, no-flush K2 Plus.

### Phase 4: scale

- **Cost:** about $60 per tool plus duty. **Hours:** 6–10 for tools 3 and 4.
- **Do:** add tools and docks; optionally the eddy scanner; move to an external host if needed; decide what to do with the CFS.

---

## 8. Kill criteria

| Finding | When | Then |
|---|---|---|
| Less than about 152 mm of head height or 50×44 mm of carriage clearance, with no fix short of cutting the frame | Phase 0 | Stop. Run open firmware with tuned flush volumes, or buy (below). |
| No rigid place to mount a dock rail that the head can reach | Phase 0 | Same. |
| Toolhead cable route longer than about 1.8 m with nowhere closer for the Link Board | Phase 0 | Same. |
| Open firmware refuses your board revision, or cannot finish three prints | Phase 1 | `swap` back. Wait a few months for the stacks to mature, or buy. |
| Timing shutdowns persist even on an external host | Phase 1–2 | Stop; the platform is not ready. |
| INDX toolboard will not enumerate on the printer or on an external host | Phase 2a | Return or resell the kit. |
| Probe repeatability worse than 0.05 mm after three adapter revisions | Phase 2 | Stop at a single-tool printer, or revert. |
| Thermal faults at a 50°C chamber | Phase 2 | Run INDX unheated only, or revert. |
| More than 1 failed tool change per 100 after two dock-mount redesigns | Phase 3 | Stop at a single tool, or revert and sell the kit. |
| Past 120 hands-on hours or $1,200 without a two-tool print | Any | Stop. |
| Creality announces a K2 Plus tool-changing kit, or Bondtech lists a K2 integration | Any | Pause and reassess; either would cut your work sharply. |

**Where I would point you at that moment**

- **Want zero-purge at this size with a heated chamber, now:** Bambu Lab H3C, $2,499.
- **Want INDX on a supported machine and can wait:** Prusa CORE One L+ with the INDX kit; new kit orders ship after Feb 2027.
- **Want cheap and small:** Snapmaker U1 at $699.
- **Want to keep the K2 Plus:** open firmware plus flush tuning, and keep the CFS.

---

## Proposed repo layout

```
k2-toolchanger/
├── README.md                 this report
├── bom.csv                   machine-readable BOM
├── docs/
│   ├── phase0-measurements.md   caliper numbers and photos from the machine
│   ├── decisions.md             one line per decision, with date and reason
│   └── bringup-log.md           what was tried, what happened
├── cad/
│   ├── carriage-adapter/        parametric source and exported STEP/STL
│   ├── dock-bracket/
│   ├── tube-guides/
│   └── reference/               links to Bondtech's reference STEP (check licence before committing a copy)
└── klipper-config/
    ├── baseline/                Jacob's K2 config exactly as installed, for diffing
    └── indx/                    printer.cfg overlay, indx.cfg, tool-change macros
```

First session in the repo: fill in `docs/phase0-measurements.md`, then start `cad/carriage-adapter/` from those numbers.

---

## Research limits

- Reddit, Discord and YouTube could not be searched directly. A K2 toolchanger build could exist there.
- The Creality wiring diagram, warranty text and several news pages could not be re-opened by the fact-checkers.
- Shipping and import duty from Sweden were not researched; both are guesses.
- StealthChanger and brain-transplant BOMs are partial, because the research turned against both early.
- Open-firmware facts come from the projects' own docs. I read them directly, but nobody independent has verified their claims.

## Sources

**K2 open firmware**
- [Jacob10383/k2-plus-custom-firmware](https://github.com/Jacob10383/k2-plus-custom-firmware), [docs](https://jacob10383.github.io/k2-plus-custom-firmware/), releases 2026-11-06 and 2026-11-08
- [Jacob10383/kalico](https://github.com/Jacob10383/kalico), commit `089cf65`, 2026-11-06
- [grant0013/K2-OpenKlipper](https://github.com/grant0013/K2-OpenKlipper): [K2-PLUS-BETA](https://github.com/grant0013/K2-OpenKlipper/blob/main/docs/K2-PLUS-BETA.md), [MOTOR-CONTROLLER](https://github.com/grant0013/K2-OpenKlipper/blob/main/docs/MOTOR-CONTROLLER.md), [EXTERNAL-HOST](https://github.com/grant0013/K2-OpenKlipper/blob/main/docs/EXTERNAL-HOST.md), [PROJECT-STATUS](https://github.com/grant0013/K2-OpenKlipper/blob/main/docs/PROJECT-STATUS.md)
- [MzTechnology97/K2-OpenHost](https://github.com/MzTechnology97/K2-OpenHost)
- [CrealityOfficial/K2_Series_Klipper](https://github.com/CrealityOfficial/K2_Series_Klipper), latest commit 2025-10-22

**INDX**
- [BondtechAB/INDX](https://github.com/BondtechAB/INDX), [BondtechAB/indx_klipper](https://github.com/BondtechAB/indx_klipper)
- [Bondtech INDX shop category](https://www.bondtech.se/product-category/indx/), [INDX Toolhead](https://www.bondtech.se/product/bondtech-indx-toolhead/), [INDX overview](https://www.bondtech.se/indx-by-bondtech/)
- [Bondtech nozzle statement](https://www.bondtech.se/2026/07/29/indx-hardened-nozzles-update/), 2026-07-29
- [Kalico INDX documentation](https://docs.kalico.gg/INDX.html)
- [Prusa INDX 4-tool kit for CORE One L](https://www.prusa3d.com/product/indx-4-tool-conversion-kit-for-core-one-l/), [8-tool kit](https://www.prusa3d.com/product/indx-8-tool-conversion-kit-for-core-one-l/)

**StealthChanger and klipper-toolchanger**
- [DraftShift/StealthChanger](https://github.com/DraftShift/StealthChanger), [Docks wiki](https://github.com/DraftShift/StealthChanger/wiki/Docks), [software page](https://sdylewski.github.io/StealthChanger/SoftwareAndConfig/Software), [slicer page](https://sdylewski.github.io/StealthChanger/SoftwareAndConfig/Slicers)
- [viesturz/klipper-toolchanger](https://github.com/viesturz/klipper-toolchanger)
- [Teaching Tech SV08 toolchanger build](https://teachingtechyt.github.io/sv08toolchanger.html)
- [TeamFDM toolchanger comparison](https://www.teamfdm.com/blogs/entry/23-voron-toolchangers/), Aug 2026
- West3D: [base kit](https://west3d.com/products/stealthchanger-base-kit-sub-kit-1-of-3-by-ldo-motors-based-on-draftshift-design), [toolhead and dock kit](https://west3d.com/products/stealthchanger-toolhead-and-dock-kit-sub-kit-2-of-3-by-ldo-motors-based-on-draftshift-design), [Rapido ACE](https://west3d.com/products/trianglelab-rapido-ace-hotend-hot-end-hf-uhf-with-104nt-or-pt1000-thermistor), [Orbiter V2.5](https://west3d.com/products/ldo-orbiter-extruder-v2-5-orbiter-v2-5-and-v2-0-to-v2-5-upgrade-kit), [NEMA14 motor](https://west3d.com/products/ldo-nema14-36mm-pancake-stepper-motor-ldo-36sth20-1004ahg)

**Creality**
- [K3 store page](https://store.creality.com/products/k3-multi-material-multicolor-3d-printer), [KliTek FAQ](https://www.creality.com/blog/klitek-nozzle-changer-faq), 2026-06-03
- [K-series store collection](https://store.creality.com/collections/k-series), [K2 Plus extruder kit](https://store.creality.com/products/k2-plus-extruder-kit), [K2 Plus motherboard kit](https://store.creality.com/products/k2-plus-motherboard-kit)
- [Creality AMA](https://www.creality.com/blog/creality-reddit-ama-campaign-2025), 2025-09-27
- Forum: [request for a K2 toolchanger](https://forum.creality.com/t/can-we-please-get/46562), [KliTek thread](https://forum.creality.com/t/meet-klitek-crealitys-next-gen-nozzle-changing/51654), [K2 Pro flushing volumes](https://forum.creality.com/t/k2-pro-flushing-volumes-disappointment/47584), [K2 Plus excessive purging](https://forum.creality.com/t/excessive-purging-in-k2-plus/47435)
- [E3D High Flow ObXidian for K2 Plus](https://e3d-online.com/products/high-flow-obxidian-creality-k2-plus-nozzles)

**Buy-instead**
- Bambu Lab H3C: [3Dnatives](https://www.3dnatives.com/en/bambu-lab-h3c-03112026/), [Bambu forum reveal](https://forum.bambulab.com/t/bambu-lab-h3c-our-full-reveal/261955), 2026-11-03
- [Snapmaker Black Friday guide](https://www.snapmaker.com/blog/3d-printer-shopping-guide-black-friday/)
- [Bambu Black Friday prices via makers101](https://makers101.com/bambu-lab-black-friday-2026/)
- [K3 vs U1 at makers101](https://makers101.com/creality-k3-vs-snapmaker-u1/), 2026-10-22
- [Raspberry Pi 5 4GB at SparkFun](https://www.sparkfun.com/raspberry-pi-5-4gb.html), [BTT Manta M8P V2.0 at 3DJake](https://www.3djake.com/bigtreetech/manta-m8p-v20)
