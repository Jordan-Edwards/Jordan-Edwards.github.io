# Genre Research for the MIDI Idea Library (J-6 / S-1 / OP-XY)

Researched 2026-09-25.

## 0. How this was researched, and how to read it

**Method limits.** WebFetch was blocked for every site I tried (attackmagazine.com, musicradar.com, splice.com, hooktheory.com, roland.com, teenage.engineering, wikipedia, etc.). So almost every fact below comes from **web-search result excerpts** of the linked page, not from reading the full page. The URL next to each item is the page the excerpt came from.
- One exception: the **J-6 chord-set table** (Section 13). I cloned the public repo `github.com/stonefruit/j6` (commit `d343d58`) and read its `j6-chords.json`, which is a transcription of the Roland J-6 manual's chord-set list. The chord names and voicings there are exact.
- Some excerpts came back from a search that listed several URLs without saying which one said what. Those are marked **(search summary; attribution approximate)**.

**Provenance tags**
- *(no tag)*: the fact is stated at the linked URL.
- **[constructed]**: I wrote the concrete grid or notes by applying a rule that the linked source states. The rule is sourced; this exact grid is not.
- **[unsourced/common practice]**: I could not find a source. It is standard practice as far as I know.

**Notation**
- Step grid: 16 sixteenth-steps in 4 beats, `x` = note on, `.` = rest, `-` = tie/hold. Steps are numbered 1-16. Beat 1 = steps 1-4 (1 = downbeat, 3 = the "and").
- Bass rows:
  - `n:` semitone offset from the chord root for each step (`.` = rest, `12` = octave up, `-12` = octave down).
  - `a:` `A` = accent on that step.
  - `s:` `S` = slide from this step into the next one (TB-303/S-1 convention: slide is set on the step that glides *into* the following step).
- Roman numerals are relative to the tonic. Lowercase = minor. `b` = flat-degree (borrowed/modal). Example chords are in a concrete key.

---

## 1. Synthwave / Retrowave (incl. outrun, darksynth)

**Tempo / key / mode**
- Sweet spot around 100 BPM, usable 80-118. Outrun 100-110 (~105). Darksynth 110-118 (~114). Slower cinematic tracks 80-90. — https://vibesdj.io/dj-tools/what-bpm-is-synthwave , https://vibesdj.io/dj-tools/synthwave-bpm-chart
- Wider claim: 80 to 140 BPM. — https://www.edmprod.com/how-to-make-synthwave/
- Minor keys such as F minor and D minor suit night-drive and dystopian moods. — https://emastered.com/blog/synthwave-chord-progressions
- Phrygian and Mixolydian are common; harmonic minor shows up in darkwave and outrun. — https://emastered.com/blog/synthwave-chord-progressions
- Reference track: Kavinsky "Nightcall" is A minor, 92 BPM, 4/4. — https://www.hooktheory.com/theorytab/view/kavinsky/nightcall

**Progressions**

| # | Numerals | Example | Source |
|---|---|---|---|
| SW1 | i–bVI–bIII–bVII | Am–F–C–G | darkwave usage, https://emastered.com/blog/synthwave-chord-progressions |
| SW2 | i–bIII–bVI–bVII ("Dreamy Dystopia") | Am–C–F–G | https://emastered.com/blog/synthwave-chord-progressions ; used in Timecop1983 "Lovers" per https://unison.audio/synthwave-chord-progressions/ |
| SW3 | I–V–vi–IV ("Neon Nights") | C–G–Am–F | https://emastered.com/blog/synthwave-chord-progressions |
| SW4 | IV–V–vi–I (Timecop1983: "Come Back", "Lovers"; rising bass) | F–G–Am–C | https://www.synthwavedojo.com/blog/timecop1983-chord-progressions-demystified |
| SW5 | i–bVII/2–bVI–iv (Nightcall verse) | Am–G/B–F–Dm | https://www.hooktheory.com/theorytab/view/kavinsky/nightcall |
| SW6 | bVI–bVII–v (Nightcall chorus) | F–G–Em | same |
| SW7 | I–vi–IV–V ("1-6-4-5") | C–Am–F–G | https://www.orpheusaudioacademy.com/synthwave-chords/ |
| SW8 | I–V–vi–IV with triads | D–A–Bm–G | https://www.orpheusaudioacademy.com/synthwave-chords/ |
| SW9 | i–bVII–bVI–V (darkwave, harmonic-minor V) | Am–G–F–E | https://emastered.com/blog/synthwave-chord-progressions |

**Chord quality / voicing**
- Major and minor 7ths, plus sus chords. — https://staytunedguitar.com/synthwave-chord-progressions
- Sus chords and inversions make it "dreamy". — https://www.orpheusaudioacademy.com/synthwave-chords/
- On the J-6, synthwave sets are 34, 39-47 (see Section 13). Set 40 is all add9, set 34 is all sus2. — github.com/stonefruit/j6 `j6-chords.json`

**Basslines**
- SW-B1, octave 8ths (Kavinsky "Nightcall" and Perturbator style). Alternate root low/high (C2-C3) in 8ths. — https://blog.imseankim.com/synthwave-retro-production-techniques-modern-tools/
  ```
  grid: x.x.|x.x.|x.x.|x.x.
  n (per 8th note): 0 12 0 12 | 0 12 0 12   (C2-C3-C2-C3...)
  ```
- SW-B2, root 16th pulse. Root note repeated in 16ths or 8ths. Classic trick: arp set to 1-octave range, hold a single note. — https://www.sweetwater.com/insync/atmospheric-virtual-instruments-catching-the-synthwave/ , https://babyaud.io/blog/how-to-make-synthwave
  ```
  grid: xxxx|xxxx|xxxx|xxxx   n: all 0 (follows chord root each bar)
  ```
- SW-B3, 16th octave arp bass (the 1-octave-range arp on one note, at 16ths). — https://www.attackmagazine.com/technique/tutorials/an-introduction-to-arpeggiators/ **[constructed]**
  ```
  grid: xxxx|xxxx|xxxx|xxxx   n: 0 12 0 12 | 0 12 0 12 | ...
  ```
- SW-B4, darksynth gallop. **[unsourced/common practice]**
  ```
  grid: x.xx|x.xx|x.xx|x.xx   n: 0 . 0 0 | 0 . 0 12 | 0 . 0 0 | 0 . 12 0
  ```

**Leads and arps**
- Arp: 16ths or 8th-triplets. Modes: Up (root, 3rd, 5th, octave) and Up/Down. — https://futureproofmusicschool.com/blog/dive-into-synthwave-create-your-own-sound-today
- Arp: continuous chord-tone arpeggio as the harmonic "engine". — https://staytunedguitar.com/synthwave-chord-progressions
- Lead: build a motif from chord tones, then use repetition and transposition. Double the lead an octave up the second time round. Detuned saw with moderate portamento, or a horn-like voice. — https://synthwavepro.com/how-to-make-synthwave-melodies-in-ableton-tips-and-tutorial/ , https://www.edmprod.com/how-to-make-synthwave/ , https://www.ujam.com/tutorials/create-synthwave-leads-with-usynth-2080/
- Dotted-8th delay on arps (3 sixteenths = 0.75 beat = 45000/BPM ms) makes a "rhythmic waterfall". — https://delay.beatkey.app/dotted-eighth-delay , https://www.cmuse.org/dotted-eighth-delay-calculator/

**Pairings**
- SW-B1 or SW-B2 under sus2/add9 pads on SW1, SW2 or SW4 is the core outrun sound (sources above). Pairing the root-pulse bass with a 1-octave 16th arp comes from https://www.attackmagazine.com/technique/tutorials/an-introduction-to-arpeggiators/ .
- Darksynth: SW9 with harmonic-minor V, SW-B4 and a higher BPM (110-118). **[unsourced/common practice]** for the pairing.

---

## 2. Acid techno / Acid house

**Tempo / key / mode**
- Acid techno: 130-140 BPM. Classic Chicago acid house sits in the 118-125 house range. — https://grokipedia.com/page/Acid_house , https://www.mixgraph.io/bpm-for/acid-techno , https://samplefocus.com/blog/cubase-vs-ableton-classic-chicago-house-tracks/
- Minor scale or modal fragments; Dorian and Phrygian are common. Pick 3-4 notes of the scale. — https://grokipedia.com/page/Acid_house , https://www.theoryhelper.com/genres/techno/scales , https://synths101.com/how-to-make-a-tb-303-acid-sequence-tutorial-clones/

**Harmony**
Acid is mostly a pedal on one root, with chords sparse or absent.
- AC1: i pedal, no chord changes. Phuture "Acid Tracks" loops one 8-note pattern for about 12 minutes. — https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html
- AC2: i–bII–i (Em–F–Em), the Phrygian move. — https://musiversal.com/blog/master-phrygian-mode
- AC3: i–v°–bII–i (Em–B°–F–Em). — https://musiversal.com/blog/master-phrygian-mode
- AC4: Chicago-style chromatically transposed stab: one chord shape moved up and down in semitones rather than diatonically, e.g. Cm7 → Ebm7 → Fm7. — https://www.musicradar.com/how-to/how-to-create-classic-chicago-house-spread-piano-chords
- AC5: i–bVII (Am–G) two-chord vamp. **[unsourced/common practice]**
- On the J-6: set 58 (Techno) and set 57 (House/Techno, includes C5b9, a root+b9 stab).

**Bass (303 / S-1) archetypes**
- Rules from the sources:
  - Base grid is straight 16ths, mostly 1-2 pitches, with an octave jump on a handful of steps.
  - Slide into octave jumps.
  - Accents on offbeats give the "pumping" groove. Accent raises volume, cutoff and resonance.
  - Add accents on both slid and normal notes.
  - Sources: https://www.musicradar.com/news/producers-guide-to-the-roland-tb-303-and-clones , https://www.ultimatepreset.com/roland-tb-303-acid-house-techno-guide/ , https://synths101.com/how-to-make-a-tb-303-acid-sequence-tutorial-clones/ , https://techno-music.com/how-to-create-acid-lines-with-the-roland-tb-303-and-clones/
- AC-B1, Phuture "Acid Tracks" (8 steps, loop ×2 per bar). Transcribed as `B up A+S | B down | C lo A | C hi A | C lo | D# up A | D# | C hi A`. — https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html , https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/1112706-phuture-acid-tracks-303-pattern.html
  ```
  step: 1    2    3   4    5   6     7    8
  note: B+12 B-12 C   C+12 C   D#+12 D#   C+12   (relative to C: 23, -1, 0, 12, 0, 15, 3, 12)
  a:    A    .    A   A    .   A     .    A
  s:    S    .    .   .    .   .     .    .
  ```
  - "up"/"down" are 303 transpose flags; the octave interpretation is mine.
- AC-B2, Josh Wink "Higher State of Consciousness". Two notes, G and B. One G is transposed up. Accents on steps 10 and 13. — https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html , https://www.patreon.com/posts/303-pattern-josh-34699588 (search summary)
  - The exact note order is not in the excerpts. **[constructed]** placeholder:
  ```
  grid: xxxx|xxxx|xxxx|xxxx
  n:    0 0 4 0 | 0 12 0 4 | 0 0 4 0 | 12 0 4 0   (G=0, B=4)
  a:    . . . . | . . . . | . A . . | A . . .
  ```
- AC-B3, New Order "Confusion" style two-note line (G and A#, i.e. 0 and 3). — https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html
- AC-B4, generic offbeat-accent acid. **[constructed]** from the rules above.
  ```
  grid: xxxx|xxxx|xxxx|xxxx
  n:    0 0 12 0 | 0 3 0 12 | 0 0 7 0 | 12 0 3 0
  a:    . . A  . | . . A .  | . . A . | A  . . .
  s:    . S .  . | . . S .  | . . .  S| .  . S .
  ```
- AC-B5, odd length. Shorten the pattern to 15 or 13 steps so it drifts against the bar ("woozy"). — https://www.musicradar.com/news/producers-guide-to-the-roland-tb-303-and-clones , https://musictech.com/guides/essential-guide/how-to-create-a-chicago-style-acid-house-bassline/ (search summaries)
- AC-B6, polymetric lanes. Make the accent or slide lanes a different length from the note lane. — https://www.mind-flux.com/news-1/2025/5/26/acid-v-by-arturia-a-walkthrough-for-crafting-authentic-acid-lines

**Pairings**
- 303 + 909/707 drums, with no chords or a single stab (AC1 with AC-B1..B5). — https://www.attackmagazine.com/technique/beat-dissected/armando-acid-house/
- Acid techno at 130-140 with AC2 (Phrygian bII) under AC-B4. **[unsourced/common practice]** for the pairing.

---

## 3. Deep house

**Tempo / key / mode**
- 118-124 BPM. Classic Larry Heard / Kerri Chandler: 118-122. — https://note.com/soundwitches/n/n2238b015d600?hl=en , https://beatkey.app/how-to-make-deep-house-music
- Common keys Am, Dm, Fm, Gm. Dorian (im7–IV7 vamp) and Mixolydian modal loops. — https://beatkey.app/how-to-make-deep-house-music
- Usually a minor key. — https://emastered.com/blog/house-chord-progressions

**Progressions**

| # | Numerals | Example | Source |
|---|---|---|---|
| DH1 | im7 (2 bars) – ivm7 (2 bars) | Am7–Dm7 | https://beatkey.app/how-to-make-deep-house-music |
| DH2 | ii7–V7–Imaj7 at ~120 | Dm7–G7–Cmaj7 | https://beatkey.app/how-to-make-deep-house-music |
| DH3 | Dorian vamp im7–IV7 | Am7–D7 | https://beatkey.app/how-to-make-deep-house-music |
| DH4 | III–vi–ii–V | E7–Am7–Dm7–G7 (in C) | https://unison.audio/house-chord-progressions/ |
| DH5 | Kerri Chandler one-bar loop | D#m7(11) → Bm(13) | https://www.attackmagazine.com/technique/passing-notes/kerri-chandler-chords/ |
| DH6 | Kerri Chandler "Bar a Thym", parallel m7s | G#m7–A#m7–Dm7–F#m7 | same |
| DH7 | Mr Fingers "Can You Feel It" | G#m–E7–F#–G#7 (i–bVI7–bVII–I7) | https://www.hooktheory.com/theorytab/view/mr-fingers/can-you-feel-it (chords via https://chordify.net/chords/mr-fingers-songs/can-you-feel-it-4-chords ) |
| DH8 | Parallel shapes: one m7/m9 voicing slid by a step or semitone | Am9–Bbm9–Am9 | https://beatkey.app/how-to-make-deep-house-music , https://www.attackmagazine.com/technique/passing-notes/parallel-chords/ |
| DH9 | iv–i–v–VI | Dm7–Am7–Em7–Fmaj7 | https://m.youtube.com/shorts/GJVyZVPhhRI (weak source) |

**Voicing**
- m7 and m9; add the 9th and/or the 11th above the 7th. Moving the 7th down an octave keeps voicings close and makes the top line descend. — https://www.attackmagazine.com/technique/passing-notes/passing-notes-deep-house-chords/ , https://www.attackmagazine.com/technique/passing-notes/further-deep-house-techno-chords/
- "Can You Feel It" uses an organ played like strings: long held chords, not stabs. — https://gearspace.com/threads/mr-fingers-can-you-feel-it-bass-synth.448172/page-5 (search summary)
- Kerri Chandler lays chords over a looping pedal bass. — https://www.attackmagazine.com/technique/passing-notes/kerri-chandler-chords-part2/

**Bass**
- The rule: start with the root on each beat, move some notes to offbeats, add octave leaps. Sound is sine or a heavily filtered saw. — https://www.edmprod.com/how-to-make-classic-deep-house/ , https://modeaudio.com/magazine/deep-house-5-production-essentials
- DH-B1, offbeat 8th ("and" of each beat), ducked by the kick. — https://www.myloops.net/how-to-make-a-melodic-techno-bassline
  ```
  grid: ..x.|..x.|..x.|..x.   n: 0 on all
  ```
- DH-B2, syncopated with octave. **[constructed]** from the edmprod rule.
  ```
  grid: x..x|..x.|x..x|..x.
  n:    0..12|..0.|0..12|..7.
  ```
- DH-B3, tresillo 3-3-2 (hits on beat 1, the "and" of 2, beat 4), i.e. steps 1, 7, 13. — https://www.myloops.net/how-to-make-a-melodic-techno-bassline
  ```
  grid: x...|..x.|....|x...   n: 0, 0, 12 (or 7)
  ```
- DH-B4, pedal bass under changing chords (Kerri Chandler): the bass holds the tonic while chords move. — https://www.attackmagazine.com/technique/passing-notes/kerri-chandler-chords-part2/
- Named patterns ("Classic Deep House Pattern", "2-notes Deep Tribal", "Double On Beat", "Ten Walls Bassline") exist in a tutorial, but I could not read the grids. — https://gearspace.com/board/electronic-music-instruments-and-electronic-music-production/991498-7-deep-house-bassline-patterns-tutorial-beginners-only.html

**Pairings**
- DH1 or DH3 (static m7/m9) with DH-B1 or DH-B3.
- DH5 or DH6 (moving parallel chords) with DH-B4 pedal. — Attack Kerri Chandler part 2 (URL above)

---

## 4. Classic / Chicago house

**Tempo**
- 118-125 BPM, four-on-the-floor. Open hats on offbeats, claps on 2 and 4. — https://samplefocus.com/blog/cubase-vs-ableton-classic-chicago-house-tracks/ (search summary; attribution approximate)

**Progressions**
- CH1: I–IV–V–vi family, which is the most common set of chords. Example C–F–G–Am. — https://mixedinkey.com/captain-plugins/wiki/house-music-chords/
- CH2: I–VI–IV–V (progressive / anthem house). — https://unison.audio/house-chord-progressions/
- CH3: chromatic parallel stab. Transpose one chord shape chromatically rather than diatonically, so it sounds like a sampled chord being pitched. — https://www.musicradar.com/how-to/how-to-create-classic-chicago-house-spread-piano-chords
- CH4: "Can You Feel It" (G#m–E7–F#–G#7), see DH7. It sits between deep and Chicago house.
- CH5: minor key with major chords borrowed in, e.g. i–bVI–bVII (Am–F–G). — https://mixedinkey.com/captain-plugins/wiki/house-music-chords/ (general statement; example chords are mine)
- CH6: old-school organ/M1-type m7/m9 stabs. — https://www.attackmagazine.com/technique/synth-secrets/old-school-house-chords/
- On the J-6: sets 49-54 (House).

**Stab rhythm**
- Short stabs on the "and" of each beat, mirroring the offbeat hat. — https://www.drumloopai.com/blog/house-chord-progressions/ (search summary)
  ```
  grid: ..x.|..x.|..x.|..x.
  ```
- Syncopated 16th stab that skips the main drum hits (downbeats 1 and 4) and favours offbeat 16ths. — https://www.attackmagazine.com/technique/passing-notes/levelling-up-your-chord-stabs/ **[constructed]** grid:
  ```
  grid: ...x|..x.|.x..|..x.
  ```
- Spread piano: copy each chord's lowest note into a left-hand bassline and add new bass notes under the right-hand triads. — https://www.musicradar.com/how-to/how-to-create-classic-chicago-house-spread-piano-chords

**Bass**
- The rule: repetitive, hooky, often octave-jumping, syncopated, locked to the kick. — https://samplefocus.com/blog/cubase-vs-ableton-classic-chicago-house-tracks/ (search summary; attribution approximate)
- CH-B1. **[constructed]**
  ```
  grid: x.xx|..x.|x.xx|..x.
  n:    0.12 0|..0.|0.12 0|..12.
  ```
- CH-B2, jack-style 303 line (see AC-B1..B4).
- CH-B3, offbeat bass (DH-B1).

---

## 5. Lo-fi hip hop / Chillhop

**Tempo**
- 70-90 BPM, most tracks around 80-85. 70-75 for sleepy late-night beats, 88-90 for more bounce. Drums slightly off-grid. — https://blog.flat.io/lofi-chord-progressions/ , https://chordprogressionmaker.com/blog/lofi-chord-progressions/

**Progressions**

| # | Numerals | Example | Source |
|---|---|---|---|
| LF1 | ii7–V7–Imaj7 | Dm7–G7–Cmaj7 | https://blog.flat.io/lofi-chord-progressions/ |
| LF2 | Imaj7–vi7–ii7–V7 ("circling") | Cmaj7–Am7–Dm7–G7 | same |
| LF3 | vi7–ii7–V7–Imaj7 | Am7–Dm7–G7–Cmaj7 | https://chordprogressionmaker.com/blog/lofi-chord-progressions/ |
| LF4 | IVmaj7–iii7–ii7–Imaj7 (descending) | Fmaj7–Em7–Dm7–Cmaj7 | https://www.chordoo.com/blog/lofi-chord-progressions-for-chill-beats (search summary) |
| LF5 | Imaj7–vi7–IVmaj7–V7 (C–Am–F–G with 7ths added) | Cmaj7–Am7–Fmaj7–G7 | https://blog.flat.io/lofi-chord-progressions/ |
| LF6 | Imaj9–IVmaj13, all-maj9 color | Ebmaj9–Abmaj13 | https://blog.landr.com/lofi-chord-progressions/ |
| LF7 | add m7b5 (half-diminished) for darker chill | e.g. Bm7b5–E7–Am7 (iiø–V–i) | https://blog.landr.com/lofi-chord-progressions/ (m7b5 color); example **[unsourced/common practice]** |

**Voicing**
- maj7 = dreamy/warm, m7 = mellow, dominant 7 = bluesy. Hold each chord a bar or more. — https://blog.flat.io/lofi-chord-progressions/
- Open voicings in 4ths/5ths rather than stacked 3rds. — https://mysticalankar.com/blogs/blog/crafting-lofi-melodies-a-step-by-step-guide (search summary)
- On the J-6: sets 68-69 (Lofi R&B), 72-81 (Neo Soul), 19-20 (maj7/m7 utility).

**Bass**
- The rule: root on beat 1, mostly root and 5th, octave jumps or slides, swing or ghost notes on offbeats. — https://www.lofimusicacademy.com/crafting-warm-basslines-for-lofi-music-production , https://www.transmissionsamples.com/how-to-make-lofi-bass
- LF-B1, root-5th. **[constructed]**
  ```
  grid: x..-|..x.|x...|....
  n:    0   |..0.|7   |      (swing 55-60%)
  ```
- LF-B2, root with a ghost offbeat and an octave. **[constructed]**
  ```
  grid: x...|..x.|..x.|x...
  n:    0...|..12.|..0.|7...
  ```
- LF-B3, a walking line that moves to the next chord's root by step. — https://www.learnjazzstandards.com/blog/learning-jazz/bass/write-walking-bass-line/ (jazz source)

**Melody**
- Sparse, pentatonic or modal, with lots of rests. Example 4-note motif: C–B–A–G on Rhodes, repeated with rhythmic variation. — https://mysticalankar.com/blogs/blog/crafting-lofi-melodies-a-step-by-step-guide , https://producersociety.com/how-to-make-a-lo-fi-piano-melody/

---

## 6. Dark / Berlin techno (incl. dub/hypnotic)

**Tempo / mode**
- Techno 125-150 BPM, mostly 130-140. Berlin peak-time from 132. Berlin minimal 124-130. — https://bpmcalc.com/genres/techno/ , https://noctava.com/guides/techno-clubs-berlin , https://www.melodigging.com/genre/berlin-minimal-techno
- Phrygian (1 b2 b3 4 5 b6 b7) for dark and hard techno; Dorian for "moody but not overly dark". — https://www.theoryhelper.com/genres/techno/scales

**Harmony**
Mostly stabs and pedals.
- DT1: i–bII–i (Em–F–Em). — https://musiversal.com/blog/master-phrygian-mode
- DT2: i–v°–bII–i (Em–B°–F–Em). — same
- DT3: two-note root+b2 stab (E+F) hitting offbeats. — https://splice.com/blog/how-to-make-basslines/ or https://www.mind-flux.com/news-1/2025/9/3/how-to-make-a-rhythmic-bass-for-melodic-techno-with-jun-6v (search summary; attribution approximate)
- DT4: parallel m7/m9 stab. Keep the voicing shape and transpose it, e.g. Em7 root position (E G B D) moved to Gm7 or Am7. — https://www.attackmagazine.com/technique/tutorials/the-theory-of-techno-parallel-chord-stabs/ , https://www.electronicproduction.co.uk/post/parallel-harmony-vs-diatonic-harmony-the-secret-behind-rave-stab-chords
- DT5: dub-techno m7 stab (Am7 = A C E G) through a dotted-division delay. — https://www.transmissionsamples.com/tutorials/sound-design/dub-chords-sound-design , https://www.studiobrootle.com/dub-techno-tutorial-ableton/
- DT6: chromatic descending bass under a minor chord (i–i/maj7–i7–i6), the dark-cliché line. — https://motifkit.com/dark-chord-progressions/ (search summary)
- On the J-6: set 58 (Techno), set 57 (C5b9 = root+b9 stab), set 20 (m7 utility, ideal for parallel stabs).

**Bass**
- TB-1, rolling 16ths with the first 16th of each beat left empty for the kick. — https://www.attackmagazine.com/technique/tutorials/warehouse-rolling-techno-bass/ (search summary)
  ```
  grid: .xxx|.xxx|.xxx|.xxx   n: 0 0 0 (or 0 12 0 / 0 0 1 for Phrygian b2)
  ```
- TB-2, offbeat 8th (see DH-B1). The source says the offbeat notes ("slots 5, 7, 13, 15" in its own numbering, which I could not check) should be the longest, 90-100% of a 16th. — https://theproducerschool.com/blogs/featured-blogs/master-modern-tech-house-bass-lines-complete-tutorial-guide
- TB-3, EBM: all 16 steps on, heavy distortion, SH-101 + DX7 layering (Nitzer Ebb). — https://www.studiobrootle.com/ebm-bassline-tutorial-ableton/
  ```
  grid: xxxx|xxxx|xxxx|xxxx   n: 0 0 12 0 | 0 0 12 0 ... [constructed octave accent]
  ```
- TB-4, kick-derived rolling sub. Kick copy with delay and filter at 138 BPM, all notes C3, MPC swing 20%. — https://www.studiobrootle.com/rolling-techno-bassline-ableton/
- TB-5, 3-note rolling 16ths (tech-house style, Chris Stussy): near-continuous 16ths using 3 notes, with swing and velocity humanization. — https://theproducerschool.com/blogs/featured-blogs/building-a-rolling-bassline-like-chris-stussy-the-3-note-pattern-that-defines-modern-tech-house
  - Example **[constructed]**: `n: 0 7 0 3 | 0 7 0 3 | ...`

**Hypnotic devices**
- Odd step lengths on some tracks against a 16-step kick and snare. Example: a 6-step loop against 16. — https://keithmcmillen.com/blog/analog-rytm-programming-with-polymeter/ , https://www.studiobrootle.com/how-to-make-hypnotic-techno/

---

## 7. Melodic techno / Progressive

**Tempo / key**
- 120-124 BPM (myloops); 122-130 with 125 standard (edmprod). Minor keys only; Am, Fm, Dm and Cm are the workhorses. Chords change every 2 or 4 bars, almost never every bar. — https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies , https://www.edmprod.com/how-to-make-melodic-techno/ , https://presetground.com/blogs/news/melodic-techno-chord-progressions

**Progressions**
- MT1: i–bVI–bIII–bVII (Am–F–C–G), "the sound of Tale Of Us, Anyma, Afterlife". — https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies
- MT2: i–bVI (Am–F). — same
- MT3: i–bVII–bVI (Am–G–F). — same
- MT4: i–iv–bVII (Am–Dm–G). — same
- MT5: in Dorian, i–IV (Am–D), which uses the raised 6th. — same (Dorian mention); example **[constructed]**
- MT6: Phrygian i–bII (see DT1). — https://www.chordoo.com/blog/melodic-techno-chord-progressions-for-dark-atmosphere

**Voicing**
- Low voicing (root around C2-E2), three notes, with inversions carrying the movement. — https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies

**Bass**
- Offbeat 8th (DH-B1), ducked by the kick; sidechain release 80-150 ms at 122-124. — https://www.myloops.net/how-to-make-a-melodic-techno-bassline
- Add a ghost 16th just before the next kick at velocity 60-70. — same
  ```
  grid: ..x.|..xx|..x.|..xx   (ghost on steps 8 and 16, vel 60-70)
  ```
- 16-slot pattern with 9-10 slots filled; tresillo backbone. — same **[constructed]**
  ```
  grid: x.xx|.xx.|xx.x|.xx.   (10 hits)
  ```
- Stay on chord roots with 1/8 and 1/16 pulsing. — https://www.edmprod.com/how-to-make-melodic-techno/

**Lead / arp**
- Plucked 16th arp cycling chord tones: quick attack, 100-200 ms decay, low sustain. — https://www.myloops.net/how-to-create-melodic-techno-chords-and-melodies
- Motif from chord tones A C E G. Example: A–C–E–D, then sequence it up a 4th (D–F–A–G), then back. — same
- Hypnotic polymetric lead. — https://www.productionmusiclive.com/blogs/news/hypnotic-polymetric-lead-in-analog-melodic-techno-ableton-tutorial

---

## 8. UK garage / 2-step

**Tempo / swing**
- About 130 BPM (2-step), range 130-140. Heavy swing: e.g. SP1200 16 Swing-71 at 60%. — https://www.musicradar.com/how-to/uk-garage-tutorial , https://www.studiobrootle.com/uk-garage-drum-pattern-with-presets-and-bassline/ , https://bpmcalc.com/genres/garage/

**Kick**
- 2-step kick on beat 1 and on the 8th between beats 3 and 4, i.e. steps 1 and 11. — https://theproducerschool.com/blogs/featured-blogs/how-to-program-uk-garage-drums-complete-guide-for-producers (search summary; attribution approximate)
  ```
  kick: x...|....|..x.|....   snare: ....|x...|....|x...
  ```

**Harmony**
- m7 and m9 chords in Am, Cm or Dm, voiced tight for punch or wide for warmth. — https://vixsound.com/ai-music/garage/chord-progressions
- UK1: MJ Cole "Crazy Love" centres on Dm–Am–Dm (i–v), 134 BPM. — https://chordu.com/chords-tabs-uk-garage-mj-cole-crazy-love-id_4QMA2WGvtmQ
- UK2: im9–ivm9 (Cm9–Fm9). **[unsourced/common practice]**
- UK3: im7–bVIImaj7–bVImaj7 (Am7–Gmaj7–Fmaj7). **[unsourced/common practice]**
- UK4: parallel m9 stabs (see DH8), shared with house. — https://www.attackmagazine.com/technique/passing-notes/passing-notes-deep-house-chords/
- UK5: organ stab on one chord, transposed. — https://samplefocus.com/samples/garage-house-chord , https://www.attackmagazine.com/technique/synth-secrets/old-school-house-chords/
- On the J-6: sets 22, 24 (m9, m9/11), 49-52.
- Stabs use the same MIDI rhythm as the bassline, with notes shortened. — https://theproducerschool.com/blogs/featured-blogs/master-uk-garage-production-complete-guide-to-filthy-basslines-and-swing-drums

**Bass**
- Sounds: FM "wub", detuned 3-oscillator reese sub, and Korg M1 organ bass. MIDI swung like the drums. — https://www.studiobrootle.com/uk-garage-drum-pattern-with-presets-and-bassline/ , https://www.attackmagazine.com/technique/synth-secrets/garage-bass/ , https://samplefocus.com/samples/standard-uk-garage-bass-line
- UK-B1, follows the 2-step kick. **[constructed]**
  ```
  grid: x..x|..x.|..x.|.x..
  n:    0..0|..12.|..0.|.10..   (b7 pickup)
  ```
- UK-B2, long sub notes with a slow-attack "wub". — https://www.studiobrootle.com/uk-garage-drum-pattern-with-presets-and-bassline/
  ```
  grid: x---|--x-|--x-|----
  ```
- UK-B3, organ-bass bounce. **[unsourced/common practice]**
  ```
  grid: x.x.|.x.x|x.x.|.x..   n: 0 12 0 12...
  ```

---

## 9. Drum & bass / Liquid

**Tempo**
- 170-180 BPM, mostly 174-175. Liquid 165-175. — https://www.edmprod.com/how-to-make-drum-and-bass/ , https://www.edmprod.com/how-to-make-liquid-drum-and-bass/
- Sub sweet spot: D#1 to G#1. — https://www.edmprod.com/how-to-make-liquid-drum-and-bass/

**Drums**
- Two-step: snare on 2 and 4, kick on the 1st and 6th eighth notes (steps 1 and 11). — https://www.loopcloud.com/cloud/blog/4978-Tricks-of-the-Trade-Drum-Bass or https://blog.native-instruments.com/drum-patterns/ (search summary; attribution approximate)
  ```
  kick: x...|....|..x.|....   snare: ....|x...|....|x...
  ```

**Progressions**
- DB1: i9–iv7–bVImaj9–bVIImaj7 (Dm9–Gm7–Bbmaj9–Cmaj7). — https://beatkey.app/how-to-make-liquid-dnb-music (search summary)
- DB2: Am9–Cmaj7–Em7–Am9–Cmaj7sus4/F–E, with one new bass note every three 8ths (A C E A F E). This is a built-in 3-against-4 feel. — https://www.musicradar.com/how-to/how-to-create-uplifting-liquid-dnb-chords
- DB3: i–iv–bVI. — https://www.youtube.com/watch?v=TmAVC96Zg4w
- DB4: Am9 and Cmaj7 share notes C E G B. Switching only the bass (A vs C) swaps the chord. — https://www.musicradar.com/how-to/how-to-create-uplifting-liquid-dnb-chords
- DB5: ivm9–bVIImaj7–IIImaj7–vim9 in minor (ii–V–I in the relative major). **[unsourced/common practice]**

**Bass**
- The rule: the bass follows the kick, either landing with it note for note or weaving around it. — https://www.musicradar.com/how-to/beat-programming-drums-bass-rhythm-section
- DB-B1, sub on every kick. — same
  ```
  grid: x...|....|..x.|....   (long notes, root of chord)
  ```
- DB-B2, reese: two detuned saws in the same octave with an LFO on the filter. — https://bassgorilla.com/what-is-reese-how-make-one/ , https://noisemasters.eu/blogs/dnb-guides/how-to-make-reese-basses-for-drum-and-bass-a-step-by-step-guide
  ```
  grid: x---|----|--x-|----   (legato, glide)
  ```
- DB-B3: 10 classic DnB bass rhythms exist in a tutorial, but I could not read the grids. — https://www.transmissionsamples.com/tutorials/drum-and-bass-production/dnb-bass-tutorial
- DB-B4, rolling offbeat. **[constructed]**
  ```
  grid: x..x|..x.|..xx|.x..
  ```

---

## 10. Trap / Dark pop

**Tempo / scale**
- 130-170 BPM, typically 140-160, feeling like 70-80 in half-time. Natural minor, harmonic minor and Phrygian dominate. — https://chordmap.io/trap-chord-progressions , https://www.drumloopai.com/blog/trap-chord-progressions/

**Progressions**
- TR1: i–bVI–bVII (Cm–Ab–Bb). — https://unison.audio/trap-chord-progressions/
- TR2: i–bVII–bVI (drill; chords as staccato hits). — https://www.drumloopai.com/blog/trap-chord-progressions/ (search summary)
- TR3: i–v–bVI–bVII (Cm–Gm–Ab–Bb), emotional trap. — same
- TR4: i–v–bVI–iv (Cm–Gm–Ab–Fm), described as harmonic-minor mood. — https://medium.com/@emmiemmi755/20-trap-chord-progressions-for-killer-beats-bc0eb228cffd
- TR5: a two-chord minor loop leaving space for the 808. — https://emastered.com/blog/trap-chord-progressions
- TR6: Billie Eilish "Bad Guy": Gm–Cm–D7 (i–iv–V7), 135 BPM. — https://emastered.com/blog/dark-chord-progressions (search summary)
- TR7: i–i°–ii passing diminished (eerie descending bass). — https://emastered.com/blog/dark-chord-progressions
- TR8: one-chord drill loop. — https://songen.app/blog/how-to-make-trap-melodies/

**808**
- Follows the kick. Slides of an octave (C2→C3), a minor 3rd or a 4th. — https://songen.app/blog/808-bass-guide/ , https://www.productionmusiclive.com/blogs/news/trap-beat-guide-bass-essential-tips-for-making-808-patterns
- 808-1. **[constructed]**
  ```
  grid (half-time bar): x..x|....|..x.|....
  n:    0..0|....|..12.|....
  s:    ...S|....|.....|....   (slide into the octave)
  ```
- 808-2: glide to b3 or 4 then back to root. **[constructed]**

**Melody**
- Layers: lead, a counter melody answering in the gaps, texture, accents. Call-and-response gives bounce. Bells in a high octave. Hats in 16th triplets. — https://songen.app/blog/how-to-make-trap-melodies/ , https://mixedinkey.com/captain-plugins/wiki/trap-beat/

---

## 11. Ambient / Cinematic

**Harmony**
- CI1: i–bVI–bIII–bVII (Zimmer "Inception" shorthand), e.g. Am–F–C–G. — https://www.chordgen.org/chords/cinematic
- CI2: i–IV–v–i–bVI–bIII–i (Pirates of the Caribbean; drifts from minor toward major). — https://blog.landr.com/cinematic-chord-progressions/
- CI3: Lydian I–II (raised 4th = wonder), e.g. C–D/C. — https://www.chordgen.org/chords/cinematic
- CI4: Phrygian i–bII (dread). — https://www.chordgen.org/chords/cinematic
- CI5: modal vamp with sus chords and open 5ths; chords change every 4-32 bars. — https://www.chordgen.org/chords/ambient
- CI6: pedal tone held under changing chords. — https://www.chordgen.org/chords/ambient
- Voicings: maj7, sus2, sus4, add9; open voicings. — https://www.chordgen.org/chords/cinematic
- On the J-6: sets 33-38 (Cinematic), 23 (M9#11, Lydian), 34/36 (sus2).

**Tempo**
- Free, or 60-90. **[unsourced/common practice]**

**Bass**
- AM-B1: drone or pedal root, whole notes tied across bars. — https://www.chordgen.org/chords/ambient , https://en.wikipedia.org/wiki/Drone_music
- AM-B2: octave + 5th sustained. — https://www.chordgen.org/chords/ambient

**Generative device**
- 2-3 unsynchronized loops of different lengths (Eno approach). Pad attack 1-5 s. — https://www.musicradar.com/tuition/tech/how-to-create-a-generative-evolving-ambient-drone-sound-in-ableton-live-590880 , https://beatkey.app/how-to-make-ambient-music

---

## 12. Future garage / Chillwave

**Future garage**
- 130-140 BPM. Sparse, thinned 2-step drums with 55-65% swing. — https://en.wikipedia.org/wiki/Future_garage , https://note.com/soundwitches/n/ndfbc63653c59?hl=en
- Minor keys, sus2/sus4 and m7, slow-moving pads. — same
- Warm filtered reese or sine sub; pitched vocal chops. — same
- FG1: im7–bVImaj7 over 4 bars each (Am7–Fmaj7). **[unsourced/common practice]**
- FG2: isus2–bVIsus2–bVIIsus2 (Asus2–Fsus2–Gsus2); J-6 set 34 provides all of these. **[unsourced]** progression; chords from j6-chords.json
- FG3: im9–ivm9 (Burial-style dark minor). Dark progressions in this style are covered in a video I could not read. — https://www.youtube.com/watch?v=nkacAA_WpDI
- FG4: i–bVI–iv–v. **[unsourced/common practice]**
- FG5: parallel m9 (DH8). **[unsourced]** for this genre
- FG-B1: long sine sub on the kick positions of 2-step (steps 1 and 11), tied. — derived from https://en.wikipedia.org/wiki/Future_garage **[constructed]**

**Chillwave**
- 80-110 BPM. — https://vibesdj.io/dj-tools/synthwave-bpm-chart
- Major and minor scales; the character comes from tempo, sound and tape warble rather than special harmony. — https://www.kvraudio.com/forum/viewtopic.php?t=359227 , https://www.musicradar.com/news/beginners-guide-chillwave
- CW1: Imaj7–IVmaj7 loop. **[unsourced/common practice]**
- CW2: use LF1-LF5 at 90-100 BPM with synthwave sounds. **[unsourced]**

---

## 13. Hardware-specific notes

### Roland J-6
- It has 100 chord sets ("GENRES"). Each set maps 12 keys (C..B) to 12 chords. Select with SHIFT+CHORD and the VALUE knob. — https://www.sweetwater.com/sweetcare/articles/how-to-use-the-roland-aira-compact-j-6/
- STYLE banks: 9 styles × 12 variations of arps and chord rhythms. Styles 1-2 are up/down arps at various speeds. — https://articles.roland.com/getting-to-know-aira-compact-j-6-chord-synth/
- Sequencer: 64 patterns × up to 64 steps. Each step holds a chord, style variation, single note or tempo change. — same
- 64 Juno-60-derived presets. — https://www.roland.com/us/products/j-6/
- Full chord-set list: J-6 manual p.25, https://static.roland.com/manuals/J-6_manual_v102/eng/28645807.html , transcribed in https://github.com/stonefruit/j6 (`j6-chords.json`).

**Genre → chord set (exact data from j6-chords.json)**

| Target genre | Sets | Notes |
|---|---|---|
| Synthwave | 39-47 (Synthwave), 34 (Cinematic/Synthwave, all sus2), 27 (Pop/Synth: C Em G Am Bm...) | 40 = all add9; 45 = plain triads Ab Fm Gm Bb Cm (C-minor palette); 46 = C D Em G Am Bm (G-major palette) |
| Deep/Chicago house | 49-54 (House), 55-56 (Jazz House), 47 (Synthwave/House, all m7/M7) | 52 = alternating m7/M7 a major 3rd apart |
| Techno | 58 (Techno), 57 (House/Techno: C5b9, M7#11), 20 (all m7), 22 (all m9), 24 (all m9/11) | Utility sets 20/22/24 are ideal for parallel-stab techno and garage (same shape on every key) |
| Lo-fi | 68-69 (Lofi R&B), 72-81 (Neo Soul), 19 (all M7), 21 (all M9) | |
| Cinematic/ambient | 33, 35-38 (Cinematic), 23 (all M9#11 = Lydian), 36 (sus2 slash) | |
| Trance/melodic techno | 48 (Trance: Cm Ab/C Bb/D Eb C/E Fm F Gm Ab F7/A Bb G7/B) | Minor-key palette with slash-chord bass walking up |
| Pop / generic | 1-2, 7-11 (Trad Maj/Min, Pop Min), 28-32 | 7 = C-major diatonic; 8 = C-minor diatonic |

- Key→chord for set 20 (all m7): C=Cm7, C#=C#m7, ... B=Bm7. Voicings are close position around octave 3-4.
- Key→chord for set 47: C=Cm7, C#=D#M7, D=Dm7, D#=Fm7, E=D#M7, F=Gm7, F#=Fm7, G=G#M7, G#=Gm7, A=A#7, A#=G#M7, B=C#/C.
- Encoding tip: a progression on the J-6 is a sequence of **key presses**, not chord names. For utility sets (17-24), the key pressed equals the chord root, so e.g. DH1 in set 20 is keys A → D. For themed sets you must look up which key holds the chord you want. The JSON has this mapping.

### Roland S-1
- 64-step sequencer, 64 patterns. Per-step data: pitch, velocity, gate time (note length), probability, sub-steps (ratchets), and up to 8 motion parameters. — https://static.roland.com/manuals/s-1_manual_v102/eng/87295006.html , https://www.engadget.com/roland-s-1-tweak-synth-is-the-most-compelling-member-of-the-aira-compact-family-070014423.html
- Last step: SHIFT + pad 4 (LAST), then the VALUE knob. Any length 1-64, so odd lengths such as 13, 15, 5 or 7 are possible for acid drift and polymeter. — https://support.roland.com/hc/en-us/articles/15032698015899-S-1-How-to-Input-a-Sequence-in-3-4-Time
- 3/4 time: set last step = 12. — same
- Triplets: separate Roland support article. — https://support.roland.com/hc/en-us/articles/15032742562587-S-1-How-do-you-input-a-sequence-in-triplets
- Step Loop for live fills. Probability for variation. Sub-steps for ratchets. — https://synthanatomy.com/2023/05/roland-s-1-tweak-synth-the-iconic-sh-101-joins-the-aira-compact-family.html
- Sub-oscillator level via SHIFT+SUB knob. SH-101-style sub can be −1 or −2 octaves. Motion can change sub-osc tuning per step. — https://static.roland.com/assets/media/pdf/S-1_eng02_W.pdf , https://en.wikipedia.org/wiki/Roland_SH-101 , https://www.engadget.com/roland-s-1-tweak-synth-is-the-most-compelling-member-of-the-aira-compact-family-070014423.html
- Arpeggiator can be recorded straight into the sequencer. Chord mode (voices tuned per voice) and 4-voice poly. — https://www.musicradar.com/reviews/roland-s-1-tweak-synthesizer-review , https://brian-candler.medium.com/roland-s-1-tweak-synthesizer-816e0c2b9660
- Accent and slide in the sense of TB-303 flags. The S-1 is SH-101-derived and exposes velocity and portamento. — https://www.engadget.com/roland-s-1-tweak-synth-is-the-most-compelling-member-of-the-aira-compact-family-070014423.html
  - Mapping acid `A` to high velocity and `S` to a legato/overlapping gate with portamento is **[unsourced/common practice]**. Verify in the manual.
- Encoding suggestions:
  - Acid lines: use `a:` → velocity 127 vs 90.
  - `s:` → gate 100%+ (tie) with portamento on.
  - Probability 50-75% on ghost notes (DH-B2, MT ghost 16th).
  - Sub-steps (x2/x3) on the last step of the bar for fills. **[constructed]**

### OP-XY
- 14 step components, e.g.:
  - Multiply (ratchet), Hold, Velocity, Ramp up/down (in scale), Random (in scale)
  - Portamento, Bend, Tonality (transpose), Jump, Skip-param-lock, Skip-component, Pulse
  - — https://teenage.engineering/guides/op-xy/step-components (search summary), https://op-forums.com/t/op-xy-step-components/28550
- "Brain" handles key/scale and transposition across tracks. Holding a chord forces progressions outside the scale. Slow down the Brain track to sketch song sections. — https://www.soundonsound.com/reviews/teenage-engineering-op-xy
- 16 tracks, up to 64 bars. — same
- Encoding: Ramp and Random components give the "drifting" melodic variation of acid and techno without writing it. The Jump component can create odd loop lengths (polymeter). **[constructed]** from the component descriptions.

---

## 14. Polyrhythm / polymeter catalogue (cross-genre)

| ID | Device | Encode as | Source |
|---|---|---|---|
| P1 | 3-against-4: part repeats every 3 sixteenths over a 16-step bar | pattern length 3 (or notes on steps 1,4,7,10,13,16) | https://www.pointblankmusicschool.com/blog/exploring-polyrhythms-in-modern-music-production/ ; hi-hat every 3 16ths: https://hackmusictheory.com/blogs/theory/posts/6985143/polymeter-hack-for-better-beats |
| P2 | 3-3-2 / 3-3-3-3-4: cross-rhythm cut short to realign with the bar | `x..x..x.` per half bar, or `x..x..x..x..x...` per bar | https://www.8notes.com/school/lessons/piano/trance_pattern1.asp , https://www.myloops.net/programming-trance-arpeggios-and-rhythmic-sequences |
| P3 | Dotted-8th delay on a 16th arp (echo = 3 sixteenths) | delay = 45000/BPM ms | https://delay.beatkey.app/dotted-eighth-delay |
| P4 | Odd-length acid loop (13 or 15 steps) over 4/4 | S-1 last step = 13/15 | https://www.musicradar.com/news/producers-guide-to-the-roland-tb-303-and-clones |
| P5 | Accent/slide lanes of a different length from the note lane | e.g. notes 16, accents 7, slides 5 | https://www.mind-flux.com/news-1/2025/5/26/acid-v-by-arturia-a-walkthrough-for-crafting-authentic-acid-lines |
| P6 | Techno polymeter: 16-step kick/snare, other parts at 6, 5 or 7 steps | per-track length | https://keithmcmillen.com/blog/analog-rytm-programming-with-polymeter/ , https://modwiggler.com/forum/viewtopic.php?t=205603 |
| P7 | Liquid DnB chord/bass change every 3 eighths | chord change at 8th positions 0,3,6,9,12,15 | https://www.musicradar.com/how-to/how-to-create-uplifting-liquid-dnb-chords |
| P8 | Ambient: 2-3 unsynchronized loops of different lengths | lengths e.g. 17/23/29 beats | https://www.musicradar.com/tuition/tech/how-to-create-a-generative-evolving-ambient-drone-sound-in-ableton-live-590880 |
| P9 | Tresillo 3-3-2 bass (melodic house/progressive) | steps 1,7,13 (x...|..x.|....|x...) | https://www.myloops.net/how-to-make-a-melodic-techno-bassline |
| P10 | Trap 16th-triplet hats against a straight grid | 24-per-bar triplet grid | https://mixedinkey.com/captain-plugins/wiki/trap-beat/ |
| P11 | 3/4 bar (12 steps) on S-1 against 4/4 on other gear | S-1 last=12 | https://support.roland.com/hc/en-us/articles/15032698015899-S-1-How-to-Input-a-Sequence-in-3-4-Time |

---

## 15. Pairing matrix (bass style ↔ chord style)

| Genre | Chord style | Bass | Source for pairing |
|---|---|---|---|
| Synthwave | sus2/add9 pads, SW1/SW2/SW4 | SW-B1 octave 8ths or SW-B2 root 16ths; 16th arp on top | imseankim, sweetwater, orpheus (above) |
| Darksynth | SW9 / harmonic minor, power chords | SW-B4 gallop | [unsourced/common practice] |
| Acid | none or AC4 chromatic stab | AC-B1..B6 303 | https://www.attackmagazine.com/technique/beat-dissected/armando-acid-house/ |
| Deep house | DH1/DH3 static m7/m9 pads | DH-B1 offbeat or DH-B3 tresillo | beatkey, myloops |
| Deep house (Kerri) | DH5/DH6 moving parallel chords | DH-B4 pedal | https://www.attackmagazine.com/technique/passing-notes/kerri-chandler-chords-part2/ |
| Chicago house | offbeat organ/piano stabs CH3/CH6 | CH-B1 octave-jump, or 303 | musicradar spread piano; samplefocus |
| Lo-fi | LF1-LF7 maj7/m7/9 held 1+ bars | LF-B1/LF-B2 root-5th with swing | flat.io, lofimusicacademy |
| Berlin techno | DT3/DT4/DT5 stabs, one chord | TB-1 rolling 16ths or TB-4 kick-derived sub | Attack warehouse bass, studio brootle |
| Melodic techno | MT1-MT4, 3-note low voicings, 2-4 bars each | offbeat 8th + ghost 16th, 16th pluck arp | myloops |
| UKG | m7/m9 stabs with the same rhythm as the bass | UK-B1 skippy / UK-B2 wub, swung | TPS UKG guide, studio brootle |
| Liquid DnB | DB1/DB2 extended chords | DB-B1 sub on kick, DB-B2 reese | musicradar kick-bass, edmprod |
| Trap | TR1-TR5 sparse minor, bells | 808 following kick with slides | songen, chordmap |
| Ambient | CI1-CI6 sus/maj7, 4-32 bars | AM-B1 drone/pedal | chordgen ambient |
| Future garage | sus2/m7 slow pads | long sine sub / filtered reese on 2-step kicks | wikipedia future garage |

---

## 16. Gaps / what to verify
- Exact 16-step grids for the Josh Wink, Hardfloor and Fast Eddie 303 patterns are on https://djjondent.blogspot.com/2020/04/famous-303-bassline-patterns-page-1.html , which I could not fetch.
- Could not read these tutorials that have concrete MIDI:
  - The 7 deep-house bassline grids (gearspace / pro music producers).
  - Transmission Samples' 10 DnB bass rhythms.
  - The Presetground "5 melodic techno progressions".
  - The emastered 7 synthwave progressions (only 4 surfaced in excerpts).
- S-1 accent/slide: confirm in the S-1 manual whether there is a dedicated per-step slide/portamento flag or whether it is done via gate overlap plus the portamento setting.
- Reddit r/edmproduction and r/synthesizers threads did not surface in search results.
