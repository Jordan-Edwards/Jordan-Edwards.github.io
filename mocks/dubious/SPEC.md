# Dubious: build spec

One instrument. A soft struck voice (felt piano / music box) with seven treatments and one ambience bed, shown as a block of world cut into five layers. The mock is `index.html` in this folder. Numbers marked "measured" come from that mock in headless Chromium at 390 x 844. Nothing here has run on a device.

Conventions: 44.1 kHz, 64-sample blocks (689 per second), mono Q1.31, peak at most half scale. `inc` is the per-sample phase increment the host supplies (2^32 = one cycle). A block-rate smoother `y += (target - y) >> n` has a time constant of about 2^n x 1.45 ms (n=6: 93 ms, n=8: 0.37 s, n=10: 1.5 s).

## 1. Knob map

Two pages of four; pressing an encoder switches page. Labels are lowercase and at most 8 characters. Every knob at 0 adds nothing, so later presets stay compatible.

| Slot | Label | Init | Sound, 0 to 100 | Picture, 0 to 100 |
|---|---|---|---|---|
| 1.1 | time | 25 | Bright and quick, to dark, slow attack, pad underneath | Shade crosses the forest left to right; stars, fireflies, eyes, bats |
| 1.2 | dig | 0 | Clean, to coarse steps with a gritty burst | Forest lifts off the dirt (0-7 cells); 0-6 dug pits; crumbs fall on notes |
| 1.3 | glint | 30 | No bells, to clear bell partials and twinkles | Dirt lifts off the ore (0-7 cells); 0-3 steady glints; star flashes on notes |
| 1.4 | deep | 25 | Open (15 kHz), to resonant 310 Hz | Ore lifts off the water (0-7 cells); 0-3 rows of the tank go dark from below |
| 2.1 | tide | 30 | Still, to slow wide sway of the Deep cutoff plus a kick per note | 0-8 chop marks on the waterline; turtles stroke faster while notes sound |
| 2.2 | rift | 0 | Struck, to reversed swells with an octave-down shadow that sink at the end | Water lifts off the underworld (0-12 cells); lava shows; ring grows 1/3, 2/3, full |
| 2.3 | air | 50 | No bed, to wind and drone that duck on a note and bloom as it fades | 0-3 wind streaks at rest; they vanish on a note, then up to 6 return and drift |
| 2.4 | wear | 30 | Steady, to wow, flutter, dust and a duller top | 0-10 dust specks; a scratch above 60 |

No text is drawn on the screen. Two pips at the bottom right show the page (left lit = page 1).

## 2. Picture

Grid: 3 px cells on 480 x 220 (160 x 73 cells). The block is 22 columns of 3 cells (198 px wide). Column j is `h(j) = j+1` cells tall above and below the centre line for j < 11, mirrored after. So every face is a stack of rectangles and every outline turn is 90 degrees. Layer thicknesses: 2, 4, 4, 5, 4 cells. The underworld has ragged hanging columns (0-2 cells).

Exploded view: four gaps, one above each lower layer. `gap = round(knob x max)`, max 7, 7, 7, 12 cells. If the four add up to more than 24 cells they are scaled to fit. Gaps move one whole cell per frame. The forest stays put until the stack needs more than 17 cells of gap, then rises a cell at a time.

| Layer | Shows | Moves with knobs | Answers a note |
|---|---|---|---|
| 1 Forest | 22 ground strips, 37 flecks and flowers, 6 trees, explorer (hat, coat, lantern), wolf | Strips, flecks and trees swap to night colours as the shade line passes; one dusk strip at the edge; lantern and wolf's eye light up inside the shade | Explorer takes one step; wolf's ear flicks; at night a firefly moves and the eyes in two trees blink |
| 2 Grass and dirt | Green rim, soil faces with flecks and pebbles | Pits appear on the top face | Up to 6 crumbs fall 4 cells |
| 3 Ore | Stone faces, 15 ore spots (ice, tan, green) | Steady white glints | Up to 3 star-shaped flashes on random ore, staggered 0.1 s |
| 4 Water | Bright waterline, 4 tank rows, 2 turtles (shell, spot, two limb frames), ripples on top | Rows darken with Deep; chop marks with Tide | Each turtle moves one column and swaps limb frame; a bubble rises. While notes sound, Tide keeps them stroking |
| 5 Underworld | Dark rock, lava top, lava drips, ring (violet disc, dark core, lilac arc) | Ring size follows the gap (4, 7, 11 cells) | Four glisten dots spiral into the ring in 0.5 s and reset; an ember drifts to the ring |
| Sky, overlays | 14 stars, 3 bats, 6 wind streaks, 10 dust specks, scratch, 2 pips | Counts follow Time, Air, Wear | Bats flap and circle only while notes sound; dust jumps |

Rest state is fully still (measured: 0 nodes change).

## 3. Node and colour budget (measured from the mock's own list)

| Group | Nodes | Of which move or recolour on their own | Palette entries used |
|---|---|---|---|
| 1 Forest | 100 | 90 (shade sweep 73, explorer 6, wolf 2, fireflies 5, eyes 4) | grass leaf pine teal night dirt bark stone slate tan ember lilac white |
| 2 Grass and dirt | 40 | 12 | pine dirt bark stone tan leaf |
| 3 Ore | 37 | 6 | stone slate night ice tan leaf white |
| 4 Water | 41 | 30 | water teal ice tan leaf pine |
| 5 Underworld | 40 | 15 | night ember violet lilac slate tan white |
| Sky and overlays | 39 | 39 | white violet slate tan |
| Header mask (device only) | 1 | 0 | static black fill (see risk 6) |
| Total | 297 (+1) | | 16 of 16 |

Largest outline: 44 points (limit 64). Every node is one closed subpath with no holes. Mutable outlines used: 0 of 4. Text slots: 0. Largest hideable node: 30 x 30 px. 190 nodes are single 3 x 3 px squares.

Palette (fixed; nodes switch entry, entries never change): grass 6c9a55, leaf a8c56c, pine 3c6746, teal 1e4a5a, night 1b1e42, dirt 8b6349, bark 54392f, stone 8e9099, slate 5a5d70, water 3e78ae, ice 9edfe4, tan d8b389, ember f08c3c, violet 7a4ec2, lilac c8a4f0, white f2eee1.

Redraw cost, measured changed nodes per frame at 30 fps (mean / peak):

| Case | Mean | Peak |
|---|---|---|
| Rest | 0 | 0 |
| Four notes repeating, init settings | 5.6 | 25 |
| One note, one knob at 100 (worst mean: tide; worst peak: time) | 3.2 | 28 |
| Sweeping time 0 to 100 in 1 s | 2.6 | 10 |
| Sweeping rift 0 to 100 in 1 s | 9.1 | 36 |
| Sweeping dig 0 to 100 in 1 s | 18.5 | 121 |
| All knobs jump to 100 with six notes held | 23.4 | 260 |

Playing stays inside the aim of about 20. Turning a gap knob does not: each cell step moves every layer below the gap in one frame.

## 4. Sound

Voice order: sources -> sum -> Dig -> (+ bed) -> Deep/Tide filter -> out. Cap 6 voices.

**Core.** One 256-point table (harmonics 1-8 at 1, .42, .20, .09, .05, .025, .012, .006). Two readers with linear interpolation at `inc - (inc>>9)` and `inc + (inc>>9)` (about 3.4 cents each way). One-pole low-pass: cutoff starts at f x (2 + 11b) and glides to f x (1.3 + 3b) with n = 8, where b = 1 - 0.8 x time. Coefficient in Q31 is about `3.1416 x ratio x inc`, clamped; no pitch helper needed. Amp: linear attack over 4 ms + 140 ms x time^2 to 0.13, then exponential fall toward 0.014 with a time constant of 1.1 s x 2^((60 - note)/24). Take the decay coefficient from a 16-entry table indexed by the top bits of `inc`. Hammer thump: noise through a one-pole at 600-1000 Hz, level 0.10 x (1 - rift) x (1 - 0.6 x time), 20 ms decay.

**Time.** As above, plus a pad: two naive saws at `inc -/+ (inc>>8)`, one-pole at 2.5 x f (2.6 kHz at most), fade-in n = 8, level 0.11 x time.

**Dig.** On the summed voice. Multiply by drive (3.0 at 0, 0.8 at 100), round to a step of 1/8 full scale (add half a step, mask the low 28 bits), multiply by 1/drive from a small table. Mix dry x (1 - 0.75 x dig) + crushed x 0.9 x dig. Low drive means the note spans fewer steps and gates off as it decays: that is the digging crumble. Also latch the input every 1 + 10 x dig samples (the mock leaves this out). Burst at note start: noise held 14 samples, rounded to 9 levels, level 0.16 x dig, 45 ms decay.

**Glint.** Level 0.10 x glint. Sine reader A at `inc<<2` from full level, 0.30 s decay. Sine reader B at 5.404 x inc (`(inc x 5534) >> 10`) from 0.35, 0.12 s decay. Two twinkles at pseudo-random times 120-620 ms after the start (LCG seeded by the note serial): 6 x inc at 0.6, then 8 x inc at 0.3, 4 ms attack, 0.10 s decay. Re-strike reader B for them. Mute any partial above `inc = 2^30` (11 kHz).

**Deep.** Per-voice state-variable low-pass. Cutoff 15 kHz x 2^(-5.6 x deep), from a 33-entry coefficient table with interpolation. Q from 0.75 to 2.1 (damping 1.33 to 0.47).

**Tide.** One LFO phase in `Shared`, 0.10 + 0.45 x tide Hz. Depth D = 0.75 x tide x log2(cutoff / 250 Hz) octaves. The cutoff sways between the Deep value and D octaves below it, so it is audible with Deep at 0 and never closes fully. Second modulation, the turtle stroke: each note start adds 700 cents x tide to the cutoff, decaying in 0.28 s. Both are offsets to the table index (one step = 0.175 octave).

**Rift.** Struck part x (1 - 0.85 x rift). Swell part x 0.4 x rift: a third table reader at `inc` plus a sine at `inc>>1`, one-pole at 4 x f. A clock of 0.62 s (427 blocks) runs from note start for 9 swells. In swell k the gain rises exponentially from 0.003 to 0.5 x 0.82^k over the first 90% (a per-block multiply by one of 9 stored ratios), then drops linearly in the last 10%. In the last 20% of each swell both readers glide down to -260 cents x rift (`inc x (1 - 0.139 x rift x ramp)`), then snap back. This is the "pulled inward" tail. It needs no buffer, no reverb and no note-off.

**Air.** Rendered by one voice only (owner id and live count in `Shared`; the next voice takes over when the owner ends). Wind: noise through one-poles at about 350 Hz high-pass and 1.1 kHz low-pass, centre drifting 260 Hz either way at 0.07 Hz, gain 0.8. Drone: two triangles, one at the last note's pitch class folded into G3-F#4 (shift `inc` until 19,088,743 <= inc < 38,177,486), one a fifth above (`inc + inc>>1`), one-pole at 700 Hz, gain 0.13 each, pitch glide n = 10. Bed gain = 0.7 x air x (1 - 0.85 x s). s is a strike follower in `Shared`: set to 1 at every note start, 0.6 s decay. The bed joins after Dig and before the filter.

**Wear.** Wow 0.43 Hz, 16 cents x wear; flutter 6.1 Hz, 5 cents x wear; both scale every reader's increment once per block. Dust: the stock-cost crackle generator at 0.3 x wear in the bed-owner voice. Dull top: cap the Deep filter's cutoff at 18 kHz x 2^(-2 x wear) instead of adding a filter.

### Cost per voice per block (digest's static figures)

| Part | Static | Runs when |
|---|---|---|
| Core: 2 table readers, one-pole, envelope | 2,288 | always |
| Time pad: 2 saws, one-pole, ramp | 961 | time > 0 |
| Dig: scale, round, hold | 200 | dig > 0 |
| Glint: 2 sine readers, envelope | 1,959 | glint > 0 |
| Deep and Tide: SVF, block-rate cutoff | 1,123 | always |
| Rift: table reader, sine reader, one-pole, envelope | 2,288 | rift > 0 |
| Wear pitch | 120 | wear > 0 |
| Voice total, everything up | 8,939 | |
| Bed owner extra: noise, 3 one-poles, 2 triangles, crackle | 2,444 | one voice only |
| Note start extra for about 0.1 s: thump and burst | 750 | |

The previous synth measured 8,300 static against about 14,100 estimated (x 1.7). On that scale: init preset 6,451 static, about 11,000 (inside the 15,000 aim). Everything up: about 15,200 (just over). Bed owner with everything up: 11,383 static, about 19,400 (over the aim, under the 24,000 drop line). Planned savings, in order: skip any path at zero level; above rift 50 drop the second core reader (-848); read Glint sines without interpolation (about -500); the bed owner drops the second saw and second core reader (-1,114). Host-time the all-up bed-owner case before anything else.

Memory: Voice about 160 B, declare 256; cap 6 gives 256 x 7 + 3 KiB + 112 B, about 4.9 KiB. `Shared` about 64 B, declare 128. Tables about 1.3 KiB. No delay line.

## 5. What the device cannot do, and what the mock does instead

- **No sound without a note.** The bed and the dust only exist under notes and their release tails. The mock multiplies both by the same release curve, so they stop when the last tail ends. For the bed to "come up when you let go", the init preset must set a long amp release. The mock uses a 1.1 s time constant (about 5 s to silence). With a short release the bloom is lost.
- **No note-off in the engine.** Nothing in the sound waits for release. Ducking uses the voice's own decay; Rift's sink is clocked from note start.
- **No velocity, tempo or track in the engine.** Not used.
- **Mono.** Mock voices are mono. Only the reverb stand-in is stereo.
- **The page cannot hear the sound.** The picture replays the schedule from held notes, the note serial and the release word (larger = shorter), as before.
- **No blending, gradients, masks, mirror or stretch.** Every shape is solid in one of 16 entries. Night is a recolour sweep. Creatures face one way. The ring grows by uniform scale in three steps.
- **No visibility flag.** Hidden nodes park off-screen; all are under 160 x 100 px.
- **No screen text.** A black block over y 0-20 hides the stock header; the scene draws over it.
- **Stock reverb.** The mock's room (send 0.3) stands in for it. A preset cannot set the send, so the owner turns it up by hand.

Where the mock still differs from the plan: one Deep filter for all notes instead of one per voice; Dig has no sample-hold; twinkles use their own oscillators; the dull top is a separate filter; detunes are within 2 cents of the shift-based ones.

## 6. Compromises the budget forced

- 3 px cells, the smallest proven part. The explorer is 9 x 18 px, the wolf 24 x 15, a turtle 18 x 9.
- A 3:1 block instead of the usual 2:1, so faces are plain rectangles and the ground splits into 22 strips for the shade.
- 16 colours: one green family serves grass, leaves, emerald and shells; tan serves iron, skin and turtle limbs; ember serves lava, coat, fireflies and the wolf's night eye; night navy serves night trees, the ring's core and the underworld rock. No dusk tones (one pine strip marks the edge). The underworld's two faces are the same colour.
- The sky is black by day and by night. Only the block, stars and creatures tell the time.
- Layers move in whole cells with no easing. A full 7-cell move takes 0.23 s.
- With all four gap knobs at 100 the gaps shrink to 73%, and the ring stops at 2/3 size.
- Time does not lift the forest; the shade is its picture. Air and Wear have no layer; they are sky streaks and dust.
- 297 nodes is over 256, so it needs SDK 1.8. To get under 256: drop 16 forest flecks, 10 stars, 6 dust specks, 5 underworld flecks and 4 crumbs.
- Rift is synthesised swells, not a reverb. It cannot smear one note into the next.
- One bed per machine, not per track.
- Mood research by web search was skipped to save credits. The voice was tuned from general knowledge of that style: soft attack, close detune, slow pad, long room, sparse five-note lines.

## 7. Open risks, in order

1. **Redraw bursts.** A gap step redraws up to 121 nodes in a frame (260 when everything moves). Needs a device test. Fallbacks: two-cell steps, one step every second frame, or fewer texture nodes on layers 2-5.
2. **Large fills.** Ten faces are 99 px wide and up to 66 px tall and they move. Repaint cost is unknown.
3. **Touching parts.** Faces are split into halves, rows and 22 strips that only touch. They share one origin and one offset and are never scaled, but hairlines may still show. Fix: 1 px overlap.
4. **CPU.** The all-up bed-owner voice is above the aim on paper. No hardware figure exists.
5. **`Shared` across tracks.** Two tracks of this synth would share the tide phase, the drone pitch and the bed owner.
6. **Header mask colour.** The mask is static art with its own black fill. If static fills also count against the 16 entries, one entry must go (merge lilac into white).
7. **Small sizes.** At 1/3 scale the ring has 1 px cells, under the 3 px minimum. It may need to start at 2/3.
8. **Frame rate.** All timings assume 30 fps.
9. **Draw order.** The scene relies on authored order as depth (lower layers first, upper layers cover them).
10. **Release word.** If the preset release is short, the bed and the picture's tail both shrink. The init preset's amp values need choosing on a device.
