# Loops: a groove-box looper screen for the Tracker Mini

Design, 2026-11-12. Written from reading the CE source at the commit in `CE_COMMIT` (notes in
`docs/map/`). Nothing here has run on a real Mini. Where this says the firmware "can" do something,
it means the source supports it, not that it was heard or seen.

## 1. What it is

Loops is one new screen. It shows the current instrument's sample as one big waveform across the
whole 800 px screen, loops it forward, reversed or ping-pong in time with the project tempo, and
draws a playhead that sweeps over the wave with a glowing tail. The four screen keys are labelled
soft keys, and the four value keys are pads that stutter slices. It is written new on top of CE,
in the spirit of Retrack; this design was made from the CE source alone.

Stock behaviour is untouched until you open Loops. It is a 12th cell in the Mini's module menu
(hold Menu), in the cell that is empty today. No stock screen or shortcut is removed.

## 2. One correction to the brief: the Mini has no pads

The source is clear (`platforms/imx/source/hardware.cpp`): the Mini build leaves out the pads, the
pad lights, the encoder and the radio. The Mini has 18 keys and the screen: the D-pad (Up, Down,
Left, Right, Middle; only one of the five registers at a time), four screen keys Fn1..Fn4, Menu,
four value keys (+10, +1, -1, -10), and Shift, Play, Rec, Copy, Insert, Delete. So "pads" here are
the four value keys, the way stock Performance mode uses them. All feedback is drawn on the screen.

## 3. Screen layout (800 x 480, absolute pixels)

```
y   0 +------------------------------------------------------------------------------+
      | Loops                                             03 Amen Break     [battery]  |  title bar (stock)
y  30 +--------------------+-------------------+-------------------+-----------------+
      | (o) LOOP           | 130.0 BPM         | 2 BARS  +0.7 st   | TRK 8   o o o o |  info row
y  72 | 1 . . . 2 . . . 3 . . . 4 . . . 5 . . . 6 . . . 7 . . . 8 . . .               |  bar/beat ruler
y  88 |=========== arm countdown (2 px) ==============                               |
y  92 |  | || ||| |||| ||  |  ||| |||| ||||| || | [|] ||| || ||| |||| || |  || |||    |
      |  | || ||| |||| ||  |  ||| |||| ||||| || | [|] ||| || ||| |||| || |  || |||    |  wave, 280 high
y 372 |                                          playhead ^ with glow and tail        |
y 378 | 1  | 2  | 3  | 4  |[+10]|[+1 ]|[-1 ]|[-10]| 9  | 10 | 11 | 12 | 13 | .. | 16  |  slice strip
y 424 +-------------------+-------------------+-------------------+------------------+
      | PING-PONG         | FIT               | 16                | 8                |  soft-key labels
      | Direction         | Sync              | Slices            | Track            |
y 480 +---- Fn1 ----------+---- Fn2 ----------+---- Fn3 ----------+---- Fn4 ---------+
```

| Region | x, y, w, h | Content |
|---|---|---|
| Title bar | 0, 0, 800, 28 | Stock `titleBar`: "Loops" at x 9; instrument number and name right-aligned at x 762; battery 28x13 at x 767, y 13 |
| Info row | 0, 34, 800, 32 | Four 200 px columns, text at x 12 / 212 / 412 / 612: state badge, tempo, length and pitch shift, track. Four beat lamps (10 px dots) at x 724, 742, 760, 778 |
| Ruler | 0, 72, 800, 14 | In Fit: a 12 px tick and a number per bar, a 6 px tick per beat. In Free: ticks at slice edges only |
| Arm countdown | 0, 88, 800, 2 | Fills left to right while waiting for the next bar |
| Wave | 0, 92, 800, 280 | 200 bars, 4 px pitch (3 px bar, 1 px gap), mirrored about y 232, at most 136 px each way, at least 1 px so silence reads as a dotted line. Outside the instrument's start..end the bars are dim |
| Slice strip | 0, 378, 800, 40 | 8 cells of 100 px or 16 of 50 px with the slice number. The four cells the value keys play are filled and carry the key name |
| Soft keys | 0, 424, 800, 56 | Four labels 200 px wide (centres x 100, 300, 500, 700) over the stock grey strip: value on top, name below |

Fonts are the five the firmware has (Roboto Mono Light 14, Light 17, Regular 14, Bold 17, Regular
12): values Bold 17, names Regular 12, info row Light 17. Colours come from the `Theme` struct so
the stock themes still apply. In the Original theme: background black, bars white
(`waveformColors[0]`), playhead glow and tail red 0xCD1818 (`waveformProgressColors[1]`), "LOOP"
green 0x30CB3F, "ARMED" yellow 0xFEF749, label strip 0x323132 with 0x777777 names and white values.

## 4. What moves, and how it stays smooth

The screen chip (FT812) has no framebuffer. The CPU sends it a short list of draw commands and the
chip redraws from that list. So smooth motion means: build the heavy waveform list once, keep it
cached on the chip, and resend only a tiny overlay every frame.

- **Wave** (static): rebuilt only when the instrument, region or slice count changes.
- **Playhead** (every 16 ms while armed or playing): a 3 px white line the full height of the wave,
  a 9 px and a 17 px translucent red line behind it for glow, and a tail of five translucent red
  rectangles on the side it came from. The tail is longer the faster the playhead moves (16 to
  200 px), so a short fast loop reads as a sweep, not a flicker. A small arrow above the wave
  points the way it is travelling.
- **Ping-pong bounce**: when the direction flips, the tail swaps sides, the arrow flips, and the
  loop edge flashes for 180 ms. On a forward or reverse wrap both edges flash.
- **Slices**: the cell under the playhead is lit. A held pad draws a bright frame round its slice.
- **Armed**: the state badge blinks yellow at 4 Hz and the countdown line fills up to the bar.
- **Beat lamps**: four dots step with the beat while the pattern plays.

The position comes from the playing voice itself (`getWavePosition()`), which is accurate to 2.9 ms
and already runs backwards in ping-pong. Nothing is predicted from the tempo, so the line cannot
drift away from the sound. The playhead is placed in 1/16 pixel steps (`VERTEX_FORMAT(4)`) if the
chip accepts that inside a cached list; if not, in whole pixels.

## 5. What every key does on the Loops screen

| Key | Action |
|---|---|
| Middle | Start or stop the loop. While the pattern plays, start waits for the next bar ("ARMED") |
| Fn1 Direction | Forward, Reverse, Ping-pong |
| Fn2 Sync | FREE (original pitch) or FIT (repitched so one pass is a whole number of bars at the project tempo) |
| Fn3 Slices | 8 or 16 equal slices |
| Fn4 Track | Which of the 8 track voices the loop sounds on (default 8) |
| Up / Down | Double / half speed. In FIT this halves or doubles the bar count (1/4 to 16 bars); in FREE it shifts an octave |
| Left / Right | Move the four pads to the previous / next four slices |
| +10, +1, -1, -10 | Pads 1 to 4. Hold: that slice repeats in the current direction (stutter). Release: back to the loop, on the next beat if the pattern plays. With the loop stopped they audition slices |
| Play | Stock: start or stop the pattern (Shift+Play: song). A running loop restarts with the pattern, on its first step |
| Menu (hold) | Stock module menu. Leaving Loops stops the loop |
| Shift + Fn1..4 | Stock: your Shift-layer module shortcuts |
| Shift + value keys | Stock: master volume |
| Rec, Copy, Insert, Delete | Nothing in slice 1 (reserved: capture, copy lane, keep to instrument, clear) |

Inside Loops the plain Fn keys are soft keys instead of module shortcuts. They go back to their
stock job the moment you leave the screen.

## 6. How sound flows

Loops adds no new audio processing. It plays the instrument through the stock voice chain:

```
Loops key -> request -> audio callback (one hook after sequencer.tick) -> instrumentPlayer[track].noteOn
  -> AudioPlayMemory (stock loop / ping-pong code) -> bitcrush -> filter -> amp -> pan
  -> track mixer + delay/reverb sends -> limiter -> master -> headphones / USB
```

- **Your instrument is not changed.** The engine reads play mode, points and tune from the
  instrument at note-on. Loops swaps in its own values for that one call and puts yours back
  straight away, inside the audio callback, where the sequencer cannot run in between.
- **Direction.** Forward and Ping-pong use the stock loop modes. Reverse uses the stock loop with
  the stock "reverse playback" step effect.
- **Tempo.** There is no time-stretch in this firmware. FIT changes the pitch so the loop lasts
  exactly N bars (a 2-bar break recorded at 125 BPM in a 130 BPM project goes up 0.68 of a
  semitone). The finest pitch step is 1 cent, so a fitted loop can be up to 0.03 % off. While the
  pattern plays, Loops re-fires the loop at every cycle boundary, so that error never adds up.
  With the pattern stopped the loop runs free.
- **Timing.** Starts and re-fires happen on the sequencer's own step edges, seen from inside the
  audio callback, so they land within one audio block (2.9 ms) of the grid.
- The loop passes through the instrument's envelope, filter and sends, so the stock instrument
  screens shape it.

## 7. Memory and CPU budget

| Resource | Slice 1 use | Limit |
|---|---|---|
| Audio CPU | One of the 8 existing voices; the hook is a few comparisons per block | 2.9 ms per block |
| Voices | 1 of 8 | 8, shared with the pattern |
| Sample memory | 0 (plays what is already loaded) | about 60 MB pool |
| Fast RAM (SRAM_DTC) | under 4 KB: 200 bars, two 600-column scratch arrays, state | about 21 KB free |
| Flash | a few KB | about 14.5 MB free |
| Display list | about 3.8 KB (estimate) | 8172 bytes for the whole screen |
| Display controls | about 12 | 65 |

Display list estimate: title bar 300, info row 400, ruler and countdown 300, wave 1650 (200 bars
x 8 bytes), slice strip 450, playhead overlay 220, soft keys 500. Past 8172 bytes the firmware
silently drops controls, so the development build logs the real number.

## 8. Slice 1, and what comes after

**Slice 1 (today): "see it and play it".** The Loops screen in the Mini menu; the full-width
waveform of the current instrument; loop Forward, Reverse, Ping-pong on a chosen track; the sweeping
playhead with glow, tail and bounce; FREE and FIT to bars; start on the bar when the pattern plays;
8 or 16 slices stuttered from the four value keys; labelled soft keys. Limits of slice 1: ordinary
samples held in RAM only (not wavetable, granular or streamed instruments); the loop stops when you
leave the screen; nothing is saved.

Later, in this order:

1. **Keep and stay.** Insert writes the loop setup into the instrument so patterns play it; the
   loop keeps running while you visit other screens; zoom the wave to the loop region and trim it;
   drop back into the loop in phase after a stutter.
2. **Capture.** Record line-in, the mic or USB into a buffer that belongs to Loops, with the length
   snapped to bars, then save it as a WAV and an instrument in a free slot.
3. **Resample.** Record the Tracker's own output. This needs a new tap on the master mix.
4. **Lanes.** Up to four loops stacked on the screen, each on its own track, with mute and
   retrigger per lane on the value keys.
5. **Overdub.** Layer new audio onto a captured loop, with one level of undo.
6. **Keep the pitch.** Fit to tempo by re-firing slices on the step grid instead of repitching;
   play the 16 slices from a USB MIDI pad controller; a per-project Loops file.

## 9. What the hardware allows and where it stops

**Allows**

- A big, sharp 800 x 480 colour screen driven by a graphics chip. Lines, bars, translucent glow and
  text are cheap, so a full-width waveform with a moving, glowing playhead fits with room to spare.
- Stock loop, reverse and ping-pong playback (stereo, 16-bit, 44.1 kHz) with a readable play position,
  and a tempo clock we can follow to within 2.9 ms. The playhead and the sync need no new audio code.
- About 60 MB of sample memory (about 45 MB outside the editor's scratch area, roughly four and a half
  minutes of stereo), card streaming, three synth engines, USB audio and MIDI: the Tracker+ engine.
- Line-in, the built-in mic and USB as record sources; 14.5 MB of flash free; a free menu cell.

**Stops**

- No pads, no lights, no encoder on the Mini. Those are the Plus's extras. The Mini's four value
  keys are the pads, and all feedback is on the screen.
- The D-pad and Middle register one at a time, so no chords on those five keys.
- No time-stretch. Matching tempo changes pitch. The engine's finest pitch step is 1 cent.
- 8 voices in total. Each running loop takes one from the pattern.
- The screen is drawn from an 8 KB command list. One 200-bar waveform is fine; four lanes fit only
  at about 100 bars each; there are no per-pixel effects such as blur.
- The screen scans at about 54 Hz (worked out from the panel timings). How often the firmware
  really redraws depends on its main loop and was not measured.
- Almost no spare memory outside the sample pool (about 8 KB of the 64 MB). Capture has to borrow
  from the pool or from the editor's scratch area.
- The stock recorder overwrites the whole sample pool and stops the pattern, and there is no
  "record the master" source. Capture, resampling and overdub are new code, not reuse.
- No simulator or test rig exists. Logic is tested on a computer; sound and motion can only be
  judged on the device.

## 10. Risks

1. **Borrowing the instrument's settings.** Read from source, not proven: nothing re-reads the
   instrument's points while the voice plays. Fallback: a small "forced play mode" flag in the player.
2. **The pattern can take the voice.** A pattern note on the Loops track replaces the loop. Use an empty track.
3. **Smoothness is unmeasured.** Redraw rate and 1/16 pixel placement are untested. Fallback: whole pixels.
4. **Display list overflow** drops controls without an error. The estimate leaves 4 KB spare.
5. **Zero-crossing snap** may move loop points by a few samples; the per-cycle re-fire hides it.
6. **Fn and value keys** are taken over inside Loops and must be handed back on exit. The manual test checks it.
7. **Going back to stock firmware.** Loops is kept out of Config's Fn-shortcut list; stock firmware could not read that entry.
8. **Quiet loops.** An instrument whose envelope has no sustain fades out while looping.
9. **Key layout guesses.** Labels assume the screen keys sit in a row under the screen; pad order is +10 first.

## 11. Open questions for Jordan

1. How are the four value keys laid out on your Mini, and should the leftmost slice be +10 or -10?
2. Are you happy that Fn1..4 are soft keys inside Loops (Shift+Fn keeps the shortcuts)?
3. Hold-to-stutter on the pads, or would you rather a pad jumps the loop to that slice?
4. Should a loop keep running when you leave the screen (planned next)?
5. For capture: is it acceptable to set aside part of the 60 MB sample pool for loops?
