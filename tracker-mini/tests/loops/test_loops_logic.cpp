// Host tests for the Loops pure logic. They compile the same loopsLogic.cpp the firmware builds.
// Run with tests/run.sh. No framework: a failed check prints the line and the run exits non-zero.

#include "loopsLogic.h"

#include <cmath>
#include <cstdio>
#include <cstring>
#include <vector>

using namespace loops;

static int g_checks = 0;
static int g_failures = 0;
static const char* g_current = "";

#define CHECK(cond)                                                                                \
    do                                                                                             \
    {                                                                                              \
        g_checks++;                                                                                \
        if (!(cond))                                                                               \
        {                                                                                          \
            g_failures++;                                                                          \
            std::printf("  FAIL %s:%d [%s] %s\n", __FILE__, __LINE__, g_current, #cond);           \
        }                                                                                          \
    } while (0)

#define CHECK_NEAR(a, b, tol) CHECK(std::fabs((double)(a) - (double)(b)) <= (tol))

struct TestCase
{
    const char* name;
    void (*fn)();
};
static std::vector<TestCase>& registry()
{
    static std::vector<TestCase> r;
    return r;
}
struct Registrar
{
    Registrar(const char* name, void (*fn)()) { registry().push_back({ name, fn }); }
};
#define TEST(name)                                                                                 \
    static void name();                                                                            \
    static Registrar reg_##name(#name, name);                                                      \
    static void name()

static bool is(const Step& s, Action a)
{
    return s.action == a;
}

// A 2-bar loop recorded at 125 BPM: 2 bars = 8 beats = 3.84 s = 169344 frames at 44.1 kHz.
static const uint32_t kLoop125 = 169344;

//==================================================================================================
// Fit
//==================================================================================================
TEST(fit_125bpm_two_bars_at_130)
{
    FitResult f = fitToBars(kLoop125, 0, 65535, 130.0f, 8);
    CHECK(f.valid);
    CHECK_NEAR(f.semis, 0.679, 0.005); // +0.68 st
    CHECK(f.semitones == 1);
    CHECK(f.cents < 0 && f.cents >= -40 && f.cents <= -25);
}

TEST(fit_exact_is_zero)
{
    FitResult f = fitToBars(kLoop125, 0, 65535, 125.0f, 8);
    CHECK(f.valid);
    CHECK_NEAR(f.semis, 0.0, 0.001);
    CHECK(f.semitones == 0);
    CHECK(f.cents == 0);
}

TEST(fit_half_and_double_are_octaves)
{
    FitResult up = fitToBars(kLoop125, 0, 65535, 125.0f, 4);    // 1 bar: twice as fast
    FitResult down = fitToBars(kLoop125, 0, 65535, 125.0f, 16); // 4 bars: half speed
    CHECK(up.valid && up.semitones == 12 && up.cents == 0);
    CHECK(down.valid && down.semitones == -12 && down.cents == 0);
}

TEST(fit_out_of_range_is_refused)
{
    // 2 bars squeezed into a quarter bar is three octaves up.
    FitResult f = fitToBars(kLoop125, 0, 65535, 125.0f, 1);
    CHECK(!f.valid);
    CHECK(!fitToBars(0, 0, 65535, 125.0f, 8).valid);
    CHECK(!fitToBars(kLoop125, 0, 65535, 0.0f, 8).valid);
    CHECK(!fitToBars(kLoop125, 30000, 30000, 125.0f, 8).valid);
}

TEST(fit_cents_use_the_players_linear_scale)
{
    // Check the pair (semitones, cents) against the speed the player would really produce.
    const float bpms[] = { 61.0f, 97.5f, 128.0f, 133.3f, 174.0f };
    for (float bpm : bpms)
    {
        for (int i = 0; i < kBarChoices; i++)
        {
            uint16_t qb = quarterBarsAt(i);
            FitResult f = fitToBars(kLoop125, 0, 65535, bpm, qb);
            if (!f.valid)
                continue;
            double base = std::pow(2.0, f.semitones / 12.0);
            double next = std::pow(2.0, (f.semitones + (f.cents >= 0 ? 1 : -1)) / 12.0);
            double speed = base + (next - base) * (std::abs(f.cents) / 100.0);
            double want = (double)kLoop125 / (44100.0 * passSeconds(qb, bpm));
            CHECK_NEAR(speed / want, 1.0, 0.0004); // within the 1-cent step
            CHECK(f.cents >= -51 && f.cents <= 51);
        }
    }
}

TEST(fit_region_scales_frames)
{
    // Half the sample at the same tempo fits half the bars.
    FitResult f = fitToBars(kLoop125, 0, 32768, 125.0f, 4);
    CHECK(f.valid);
    CHECK_NEAR(f.semis, 0.0, 0.01);
    CHECK_NEAR(regionFrames(kLoop125, 0, 65535), (double)kLoop125, 1.0);
    CHECK(regionFrames(kLoop125, 500, 400) == 0.0f);
}

TEST(auto_bars_picks_smallest_shift)
{
    CHECK(quarterBarsAt(autoBarsIndex(kLoop125, 0, 65535, 130.0f)) == 8);  // 2 bars
    CHECK(quarterBarsAt(autoBarsIndex(kLoop125, 0, 65535, 250.0f)) == 16); // 4 bars at double tempo
    CHECK(quarterBarsAt(autoBarsIndex(kLoop125 / 8, 0, 65535, 125.0f)) == 1);
    CHECK(autoBarsIndex(100, 0, 65535, 120.0f) == -1); // a click: nothing within two octaves
    CHECK(quarterBarsAt(-3) == 1);
    CHECK(quarterBarsAt(99) == 64);
}

TEST(cycle_steps)
{
    CHECK(cycleSteps(1, dirForward) == 4);    // 1/4 bar
    CHECK(cycleSteps(4, dirForward) == 16);   // 1 bar
    CHECK(cycleSteps(8, dirReverse) == 32);   // 2 bars
    CHECK(cycleSteps(1, dirPingPong) == 8);   // 1/4 bar there and back
    CHECK(cycleSteps(64, dirPingPong) == 512);  // 16 bars there and back
}

//==================================================================================================
// Slices
//==================================================================================================
TEST(slice_bounds_8_and_16)
{
    for (int n : { 8, 16 })
    {
        const uint16_t a = 1000;
        const uint16_t b = 61003; // not divisible by 8 or 16
        uint16_t prevEnd = a;
        for (int k = 0; k < n; k++)
        {
            Region r = sliceBounds(a, b, (uint8_t)k, (uint8_t)n);
            CHECK(r.start == prevEnd); // no gaps, no overlap
            CHECK(r.end > r.start);
            prevEnd = r.end;
        }
        CHECK(prevEnd == b); // the last slice ends exactly on b
        CHECK(sliceBounds(a, b, 0, (uint8_t)n).start == a);
    }
    Region full = sliceBounds(0, 65535, 15, 16);
    CHECK(full.end == 65535);
    Region clamped = sliceBounds(0, 65535, 99, 8); // k past the end plays the last slice
    CHECK(clamped.end == 65535 && clamped.start == sliceBounds(0, 65535, 7, 8).start);
}

TEST(slice_at_position)
{
    CHECK(sliceAt(0, 0, 65535, 8) == 0);
    CHECK(sliceAt(65535, 0, 65535, 8) == 7);
    CHECK(sliceAt(8192, 0, 65535, 8) == 1);
    CHECK(sliceAt(32768, 0, 65535, 16) == 8);
    CHECK(sliceAt(100, 2000, 4000, 8) == 0);  // before the region
    CHECK(sliceAt(9000, 2000, 4000, 8) == 7); // after it
    for (int k = 0; k < 16; k++)
    {
        Region r = sliceBounds(3000, 50000, (uint8_t)k, 16);
        CHECK(sliceAt((uint16_t)((r.start + r.end) / 2), 3000, 50000, 16) == k);
    }
}

TEST(region_playable)
{
    CHECK(regionPlayable(0, 65535));
    CHECK(regionPlayable(10, 12));
    CHECK(!regionPlayable(10, 11));
    CHECK(!regionPlayable(10, 10));
    CHECK(!regionPlayable(20, 10));
}

//==================================================================================================
// Bars
//==================================================================================================
TEST(reduce_bars)
{
    int8_t upL[600], lowL[600], upR[600], lowR[600];
    std::memset(upL, 0, sizeof(upL));
    std::memset(lowL, 0, sizeof(lowL));
    std::memset(upR, 0, sizeof(upR));
    std::memset(lowR, 0, sizeof(lowR));

    upL[3] = 109;   // bar 1, full scale up
    lowL[5] = -109; // bar 1, full scale down
    upL[7] = 20;    // bar 2: the right channel is louder
    upR[8] = 54;
    lowR[6] = -30;
    upL[599] = 127; // bar 199: past the scale, must clamp

    uint8_t up[kWaveBars], down[kWaveBars];
    reduceBars(upL, lowL, upR, lowR, up, down);

    CHECK(up[0] == 1 && down[0] == 1); // silence still shows as a 1 px dot each way
    CHECK(up[1] == 136 && down[1] == 136);
    CHECK(up[2] == 54 * 136 / 109);
    CHECK(down[2] == 30 * 136 / 109);
    CHECK(up[199] == 136);
    for (int i = 0; i < kWaveBars; i++)
    {
        CHECK(up[i] >= 1 && up[i] <= kBarMaxPx && down[i] >= 1 && down[i] <= kBarMaxPx);
    }

    // Mono: no right channel.
    reduceBars(upL, lowL, nullptr, nullptr, up, down);
    CHECK(up[2] == 20 * 136 / 109);
    CHECK(down[2] == 1);
}

//==================================================================================================
// Step edges
//==================================================================================================
TEST(step_edge_detector)
{
    StepEdge e;
    CHECK(!e.update(false, 0));
    CHECK(e.update(true, 0)); // step 0 of a fresh start is an edge
    CHECK(!e.update(true, 0));
    CHECK(e.update(true, 1));
    CHECK(!e.update(true, 1));
    CHECK(!e.update(false, 1)); // stopped
    CHECK(e.update(true, 0));   // started again
    CHECK(e.update(true, 31));
    CHECK(e.update(true, 0)); // pattern wrap
}

//==================================================================================================
// State machine: every row of the table in docs/PLAN.md section 4
//==================================================================================================
TEST(idle_toggle_pattern_stopped_fires)
{
    Machine m;
    m.reset();
    Step s = m.onCommand(cmdToggle, 0, false);
    CHECK(is(s, actFireFull));
    CHECK(m.getState() == stLoop);
    CHECK(m.isSounding());
}

TEST(idle_toggle_pattern_playing_arms)
{
    Machine m;
    m.reset();
    Step s = m.onCommand(cmdToggle, 0, true);
    CHECK(is(s, actNone));
    CHECK(m.getState() == stArmed);
    CHECK(m.getArmQuant() == 16);
    CHECK(!m.isSounding());
}

TEST(armed_fires_on_the_bar_only)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, true);
    CHECK(is(m.onBlock(true, false, 5, false), actNone)); // no step edge
    CHECK(is(m.onBlock(true, true, 6, false), actNone));  // an edge, not a bar
    CHECK(is(m.onBlock(true, true, 15, false), actNone));
    CHECK(m.getState() == stArmed);
    Step s = m.onBlock(true, true, 16, false);
    CHECK(is(s, actFireFull));
    CHECK(m.getState() == stLoop);
    CHECK(m.getSteps() == 0);
    // step 0 counts as a bar as well
    Machine m2;
    m2.reset();
    m2.onCommand(cmdToggle, 0, true);
    CHECK(is(m2.onBlock(true, true, 0, false), actFireFull));
}

TEST(armed_fires_when_pattern_stops)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, true);
    m.onBlock(true, true, 3, false);
    Step s = m.onBlock(false, false, 0, false);
    CHECK(is(s, actFireFull));
    CHECK(m.getState() == stLoop);
    CHECK(m.getSteps() == 0);
}

TEST(armed_toggle_goes_idle)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, true);
    Step s = m.onCommand(cmdToggle, 0, true);
    CHECK(is(s, actNone)); // nothing was sounding
    CHECK(m.getState() == stIdle);
    CHECK(is(m.onBlock(true, true, 16, false), actNone));
}

TEST(loop_toggle_stops)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, false);
    Step s = m.onCommand(cmdToggle, 0, false);
    CHECK(is(s, actStop));
    CHECK(m.getState() == stIdle);
    CHECK(!m.isSounding());
}

TEST(loop_counts_steps_and_refires_each_cycle_in_fit)
{
    Machine m;
    m.reset();
    m.setCycleSteps(cycleSteps(1, dirForward)); // 1/4 bar = 4 steps
    m.onCommand(cmdToggle, 0, true);
    CHECK(is(m.onBlock(true, true, 0, false), actFireFull));

    int fires = 0;
    for (int pos = 1; pos <= 16; pos++)
    {
        // several audio blocks pass inside a step: only the edge counts
        CHECK(is(m.onBlock(true, false, (uint16_t)(pos - 1), false), actNone));
        Step s = m.onBlock(true, true, (uint16_t)(pos % 32), false);
        if (is(s, actFireFull))
        {
            fires++;
            CHECK(pos % 4 == 0);
            CHECK(m.getSteps() == 0);
        }
    }
    CHECK(fires == 4);
}

TEST(loop_cycle_is_doubled_for_ping_pong)
{
    Machine m;
    m.reset();
    m.setCycleSteps(cycleSteps(4, dirPingPong)); // 1 bar there, 1 bar back
    m.onCommand(cmdToggle, 0, true);
    m.onBlock(true, true, 0, false);
    int firstFire = -1;
    for (int pos = 1; pos <= 40 && firstFire < 0; pos++)
    {
        if (is(m.onBlock(true, true, (uint16_t)(pos % 64), false), actFireFull))
            firstFire = pos;
    }
    CHECK(firstFire == 32);
}

TEST(loop_free_never_refires)
{
    Machine m;
    m.reset();
    m.setCycleSteps(0);
    m.onCommand(cmdToggle, 0, true);
    m.onBlock(true, true, 0, false);
    for (int pos = 1; pos < 300; pos++)
    {
        CHECK(is(m.onBlock(true, true, (uint16_t)(pos % 32), false), actNone));
    }
    CHECK(m.getState() == stLoop);
}

TEST(loop_rearm_pattern_playing_waits_for_the_bar_and_keeps_sounding)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, true);
    m.onBlock(true, true, 0, false);
    Step s = m.onCommand(cmdRearm, 0, true);
    CHECK(is(s, actNone));
    CHECK(m.getState() == stArmed);
    CHECK(m.isSounding()); // the old loop is still heard
    CHECK(is(m.onBlock(true, true, 7, false), actNone));
    CHECK(is(m.onBlock(true, true, 16, false), actFireFull));
    CHECK(m.getState() == stLoop);
}

TEST(loop_rearm_pattern_stopped_fires_now)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, false);
    Step s = m.onCommand(cmdRearm, 0, false);
    CHECK(is(s, actFireFull));
    CHECK(m.getState() == stLoop);
    // Rearm does nothing when no loop runs
    Machine idle;
    idle.reset();
    CHECK(is(idle.onCommand(cmdRearm, 0, false), actNone));
    CHECK(idle.getState() == stIdle);
}

TEST(play_pressed_restarts_a_running_loop_on_the_first_step)
{
    Machine m;
    m.reset();
    m.setCycleSteps(0);
    m.onCommand(cmdToggle, 0, false); // loop runs free, pattern stopped
    CHECK(is(m.onBlock(false, false, 0, false), actNone));
    // Play: the pattern starts. Stock Play cut every voice, so the loop must fire again.
    Step s = m.onBlock(true, true, 0, false);
    CHECK(is(s, actFireFull));
    CHECK(m.getState() == stLoop);
    CHECK(m.getSteps() == 0);
    CHECK(is(m.onBlock(true, false, 0, false), actNone)); // once only
    // Stop: the loop just keeps running
    CHECK(is(m.onBlock(false, false, 0, false), actNone));
    CHECK(m.getState() == stLoop);
    // Play again
    CHECK(is(m.onBlock(true, true, 0, false), actFireFull));
}

TEST(armed_loop_toggled_off_is_cut)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, true);
    m.onBlock(true, true, 0, false);
    m.onCommand(cmdRearm, 0, true); // armed, still sounding
    Step s = m.onCommand(cmdToggle, 0, true);
    CHECK(is(s, actStop));
    CHECK(m.getState() == stIdle);
}

TEST(pad_down_from_idle_stutters_and_pad_up_stops)
{
    Machine m;
    m.reset();
    Step s = m.onCommand(cmdPadDown, 5, false);
    CHECK(is(s, actFireSlice) && s.slice == 5);
    CHECK(m.getState() == stStutter);
    CHECK(m.getSlice() == 5);
    s = m.onCommand(cmdPadDown, 2, false); // another pad while holding
    CHECK(is(s, actFireSlice) && s.slice == 2);
    CHECK(m.getState() == stStutter);
    s = m.onCommand(cmdPadUp, 0, false);
    CHECK(is(s, actStop));
    CHECK(m.getState() == stIdle);
    // the same while the pattern plays: an audition never arms anything
    m.onCommand(cmdPadDown, 1, true);
    s = m.onCommand(cmdPadUp, 0, true);
    CHECK(is(s, actStop));
    CHECK(m.getState() == stIdle);
}

TEST(pad_from_loop_pattern_stopped_returns_at_once)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, false);
    Step s = m.onCommand(cmdPadDown, 3, false);
    CHECK(is(s, actFireSlice) && s.slice == 3);
    CHECK(is(m.onBlock(false, false, 0, false), actNone)); // the stutter holds
    s = m.onCommand(cmdPadUp, 0, false);
    CHECK(is(s, actFireFull));
    CHECK(m.getState() == stLoop);
}

TEST(pad_released_while_pattern_plays_returns_on_the_next_beat)
{
    Machine m;
    m.reset();
    m.setCycleSteps(32);
    m.onCommand(cmdToggle, 0, true);
    m.onBlock(true, true, 0, false);
    for (int pos = 1; pos <= 5; pos++)
        m.onBlock(true, true, (uint16_t)pos, false);

    Step s = m.onCommand(cmdPadDown, 1, true);
    CHECK(is(s, actFireSlice) && s.slice == 1);
    CHECK(is(m.onBlock(true, true, 6, false), actNone)); // no re-fire while a pad is held
    CHECK(is(m.onBlock(true, true, 8, false), actNone)); // not even on a beat
    CHECK(m.getState() == stStutter);

    s = m.onCommand(cmdPadUp, 0, true);
    CHECK(is(s, actNone)); // the slice keeps sounding until the beat
    CHECK(m.isSounding());
    CHECK(m.getArmQuant() == 4);
    CHECK(is(m.onBlock(true, true, 9, false), actNone));
    CHECK(is(m.onBlock(true, true, 10, false), actNone));
    CHECK(is(m.onBlock(true, true, 11, false), actNone));
    s = m.onBlock(true, true, 12, false);
    CHECK(is(s, actFireFull));
    CHECK(m.getState() == stLoop);
    CHECK(m.getSteps() == 0);
}

TEST(pad_pressed_while_armed_comes_back_to_the_loop)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, true); // armed, nothing sounding yet
    Step s = m.onCommand(cmdPadDown, 0, true);
    CHECK(is(s, actFireSlice));
    s = m.onCommand(cmdPadUp, 0, true);
    CHECK(is(s, actNone));
    CHECK(m.getState() == stArmed);
    CHECK(is(m.onBlock(true, true, 4, false), actFireFull));
    CHECK(m.getState() == stLoop);
}

TEST(toggle_while_stuttering_stops_and_late_pad_up_is_ignored)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, false);
    m.onCommand(cmdPadDown, 2, false);
    Step s = m.onCommand(cmdToggle, 0, false);
    CHECK(is(s, actStop));
    CHECK(m.getState() == stIdle);
    s = m.onCommand(cmdPadUp, 0, false);
    CHECK(is(s, actNone));
    CHECK(m.getState() == stIdle);
}

TEST(voice_lost_goes_idle_without_a_stop)
{
    // from LOOP
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, false);
    Step s = m.onBlock(false, false, 0, true);
    CHECK(is(s, actNone)); // the voice belongs to someone else now: do not cut it
    CHECK(m.getState() == stIdle);
    CHECK(!m.isSounding());
    // from STUTTER
    m.onCommand(cmdPadDown, 1, false);
    s = m.onBlock(false, false, 0, true);
    CHECK(is(s, actNone));
    CHECK(m.getState() == stIdle);
    // from ARMED while the old loop still sounds
    m.onCommand(cmdToggle, 0, true);
    m.onBlock(true, true, 0, false);
    m.onCommand(cmdRearm, 0, true);
    s = m.onBlock(true, false, 0, true);
    CHECK(is(s, actNone));
    CHECK(m.getState() == stIdle);
    // armed with nothing sounding: there is no voice to lose
    m.onCommand(cmdToggle, 0, true);
    s = m.onBlock(true, false, 1, true);
    CHECK(m.getState() == stArmed);
}

TEST(close_stops_from_any_state)
{
    Machine m;
    m.reset();
    CHECK(is(m.onCommand(cmdClose, 0, false), actNone)); // idle: nothing to stop
    m.onCommand(cmdToggle, 0, false);
    CHECK(is(m.onCommand(cmdClose, 0, false), actStop));
    CHECK(m.getState() == stIdle);
    m.onCommand(cmdPadDown, 0, false);
    CHECK(is(m.onCommand(cmdClose, 0, false), actStop));
    CHECK(m.getState() == stIdle);
    m.onCommand(cmdToggle, 0, true); // armed, silent
    CHECK(is(m.onCommand(cmdClose, 0, true), actNone));
    CHECK(m.getState() == stIdle);
}

TEST(clear_sounding_after_engine_cut)
{
    Machine m;
    m.reset();
    m.onCommand(cmdToggle, 0, true);
    m.onBlock(true, true, 0, false);
    m.clearSounding(); // track change: the engine cut the old voice itself
    m.onCommand(cmdRearm, 0, true);
    CHECK(m.getState() == stArmed);
    // the new track's voice holds another instrument: that is not a lost voice
    CHECK(is(m.onBlock(true, false, 1, true), actNone));
    CHECK(m.getState() == stArmed);
    CHECK(is(m.onBlock(true, true, 16, false), actFireFull));
}

//==================================================================================================
// Playhead
//==================================================================================================
TEST(head_x_is_in_sixteenths_of_a_pixel)
{
    CHECK(headX16(0) == 0);
    CHECK(headX16(32768) == 6400); // the middle of the screen
    CHECK(headX16(65535) == 12799);
    CHECK(headX16(82) == 16); // one pixel is about 82 position units
}

TEST(head_forward_then_wrap_flashes_both_edges)
{
    HeadModel h;
    h.reset(0, 65535, 8, 1);
    uint16_t pos = 0;
    for (int i = 0; i < 40; i++)
    {
        h.advance(pos, 16);
        pos = (uint16_t)(pos + 1500);
    }
    CHECK(h.view().dir == 1);
    CHECK(h.view().flashStartMs == 0 && h.view().flashEndMs == 0);
    CHECK(h.view().slice == sliceAt((uint16_t)(pos - 1500), 0, 65535, 8));

    h.advance(64000, 16);
    h.advance(300, 16); // wrapped to the start
    CHECK(h.view().dir == 1); // a wrap is not a change of direction
    CHECK(h.view().flashStartMs == kFlashMs && h.view().flashEndMs == kFlashMs);
    CHECK(h.view().slice == 0);

    for (int i = 0; i < 12; i++) // 192 ms later the flash is gone
        h.advance((uint16_t)(1800 + i * 1500), 16);
    CHECK(h.view().flashStartMs == 0 && h.view().flashEndMs == 0);
    CHECK(h.view().dir == 1);
}

TEST(head_reverse_runs_left_and_wraps)
{
    HeadModel h;
    h.reset(0, 65535, 16, -1);
    h.advance(65000, 16);
    h.advance(63000, 16);
    h.advance(61000, 16);
    CHECK(h.view().dir == -1);
    CHECK(h.view().flashStartMs == 0);
    h.advance(900, 16);
    h.advance(64800, 16); // wrapped back to the end
    CHECK(h.view().dir == -1);
    CHECK(h.view().flashEndMs == kFlashMs);
    CHECK(h.view().slice == 15);
}

TEST(head_ping_pong_bounce_flips_and_flashes_the_near_edge)
{
    HeadModel h;
    h.reset(0, 65535, 8, 1);
    // recorded shape: up to the end, then back down
    const uint16_t up[] = { 58000, 60000, 62000, 64000, 65400 };
    for (uint16_t p : up)
        h.advance(p, 16);
    CHECK(h.view().dir == 1);

    h.advance(64100, 16); // first read going back: not trusted yet
    CHECK(h.view().dir == 1);
    CHECK(h.view().flashEndMs == 0);
    h.advance(62100, 16); // second read in a row: it turned
    CHECK(h.view().dir == -1);
    CHECK(h.view().flashEndMs == kFlashMs);
    CHECK(h.view().flashStartMs == 0);

    // down to the start and bounce again
    for (int p = 60000; p > 1000; p -= 2000)
        h.advance((uint16_t)p, 16);
    CHECK(h.view().dir == -1);
    CHECK(h.view().flashEndMs == 0);
    h.advance(600, 16);
    h.advance(2600, 16);
    h.advance(4600, 16);
    CHECK(h.view().dir == 1);
    CHECK(h.view().flashStartMs == kFlashMs);
}

TEST(head_small_jitter_does_not_flip)
{
    HeadModel h;
    h.reset(0, 65535, 8, 1);
    h.advance(30000, 16);
    h.advance(32000, 16);
    h.advance(34000, 16);
    h.advance(33997, 16); // less than 8 units back: ignored
    h.advance(33995, 16);
    CHECK(h.view().dir == 1);
    CHECK(h.view().flashStartMs == 0 && h.view().flashEndMs == 0);
}

TEST(head_tail_grows_with_speed_and_stays_in_range)
{
    HeadModel slow;
    slow.reset(0, 65535, 8, 1);
    for (int i = 0; i < 100; i++)
        slow.advance((uint16_t)(i * 40), 16); // about 30 px/s
    CHECK(slow.view().tailPx == kTailMinPx);

    HeadModel fast;
    fast.reset(0, 65535, 8, 1);
    for (int i = 0; i < 100; i++)
        fast.advance((uint16_t)((i * 1300) % 65536), 16); // about 990 px/s
    CHECK(fast.view().tailPx > 80 && fast.view().tailPx <= kTailMaxPx);

    HeadModel stutter;
    stutter.reset(0, 4096, 16, 1); // a 1/16 slice hammered very fast
    for (int i = 0; i < 400; i++)
        stutter.advance((uint16_t)((i * 1999) % 4096), 16);
    CHECK(stutter.view().tailPx >= kTailMinPx && stutter.view().tailPx <= kTailMaxPx);
}

TEST(head_slice_follows_the_region_of_a_stutter)
{
    HeadModel h;
    Region r = sliceBounds(0, 65535, 5, 8);
    h.reset(r.start, r.end, 8, 1);
    h.advance((uint16_t)(r.start + 10), 16);
    // inside a stuttered slice the wrap is judged against the slice, not the whole sample
    h.advance((uint16_t)(r.end - 10), 16);
    CHECK(h.view().flashStartMs == kFlashMs);
    CHECK(h.view().x16 == headX16((uint16_t)(r.end - 10)));
}

TEST(head_fade_only)
{
    HeadModel h;
    h.reset(0, 65535, 8, 1);
    h.advance(65000, 16);
    h.advance(100, 16);
    CHECK(h.view().flashEndMs == kFlashMs);
    h.fade(100);
    CHECK(h.view().flashEndMs == kFlashMs - 100);
    h.fade(500);
    CHECK(h.view().flashEndMs == 0 && h.view().flashStartMs == 0);
}

TEST(countdown_line)
{
    CHECK(countdownPx(0, 1, 16) == 0);
    CHECK(countdownPx(8, 1, 16) == 400);  // half a bar in
    CHECK(countdownPx(24, 1, 16) == 400); // the same in the next bar
    CHECK(countdownPx(15, 48, 16) > 790 && countdownPx(15, 48, 16) < 800);
    CHECK(countdownPx(2, 1, 4) == 400); // waiting for a beat
    CHECK(countdownPx(5, 0, 16) == countdownPx(5, 1, 16));
    CHECK(countdownPx(5, 1, 0) == 0);
}

//==================================================================================================
int main()
{
    int failedTests = 0;
    for (const TestCase& t : registry())
    {
        int before = g_failures;
        g_current = t.name;
        t.fn();
        if (g_failures != before)
        {
            failedTests++;
            std::printf("not ok  %s\n", t.name);
        }
        else
        {
            std::printf("ok      %s\n", t.name);
        }
    }
    std::printf("\n%d tests, %d checks, %d failed tests\n",
                (int)registry().size(),
                g_checks,
                failedTests);
    return failedTests == 0 ? 0 : 1;
}
