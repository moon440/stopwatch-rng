// SPDX-License-Identifier: AGPL-3.0-or-later
// Terry Davis's stopwatch RNG from TempleOS, ported 1:1 to WebAssembly.
//
// Two sources were ported from the TempleOS archive (branch `archive`,
// github.com/cia-foundation/TempleOS). TempleOS is public domain; this port is AGPL.
//
// 1. THE KERNEL GENERATOR (Kernel/KMathB.HC, lines 74-157). Every TempleOS program that
//    calls Rand()/RandI16()/RandU32()/RandU64()/RandF() runs this:
//
//        #define LIN_CONGRUE_A  6364136223846793005
//        #define LIN_CONGRUE_C  1442695040888963407
//        I64 res = Fs->rand_seed;
//        res = LIN_CONGRUE_A * res ^ (res & 0xFFFFFFFF0000) >> 16 + LIN_CONGRUE_C;
//        if (!Bt(&Fs->task_flags, TASKf_NONTIMER_RAND))
//            res ^= GetTSC;                  // the stopwatch, folded in on every draw
//        Fs->rand_seed = res;
//
//    HolyC operator precedence is NOT C precedence (Doc/HolyC.DD, and the table in
//    Compiler/CInit.HC: ` ^= >> << * / % & ^ | + -). Shifts bind tighter than `*`, and
//    `+` is looser than ALL of ^,&,|. So the line parses as:
//
//        res = (LIN_CONGRUE_A * res ^ ((res & 0xFFFFFFFF00000000) >> 16)) + LIN_CONGRUE_C;
//
//    which is xor-then-add, not the PCG32-formulation add-then-verify one might expect
//    from those textbook L'Ecuyer constants.
//
//    Seed(): Seed(n) with n != 0 pins the state and switches the generator to
//    deterministic mode (TASKf_NONTIMER_RAND). Seed(0) returns to stopwatch mode and
//    xors GetTSC into the state. Demo/RandDemo.HC demonstrates both: Seed(1) replays the
//    same sequence every time, Seed(0) never repeats.
//
// 2. THE `god` ORACLE (Adam/God/HolySpirit.HC, Adam/God/GodExt.HC) - AfterEgypt's
//    "high-speed stopwatch". The entropy is the latency of the user's own input:
//
//        GodPick():   return KbdMsEvtTime >> GOD_BAD_BITS   // GOD_BAD_BITS = 4
//        GodBitsIns(N, n): for i in 0..N: FifoU8Ins(god.fifo, n&1); n >>= 1  // LSB first
//        GodBits(N):  res = 0; while (N) { if (!FifoU8Rem()) <prompt user>; res = res<<1+b; }
//        GodWord():   words[GodBits(17) % num_words]
//
//    god.fifo is created with FifoU8New(2048*8): 16,384 one-bit entries, 2048 presses.
//    The generator cannot pop up a dialogue from inside WebAssembly, so tsr_god_bits
//    returns -1 when the FIFO runs dry; the host then asks the player to press OKAY
//    again, which is exactly the information the TempleOS pop-up carried.
//
// The one thing a WASM module cannot reach for itself is a hardware timestamp counter,
// so the stopwatch is imported from the host: env.tsc, microseconds, as f64 like the
// GetTSC of a slow machine. Everything else - the LCG, the Seed modes, the exact
// precedence, the bit FIFO order - is Terry's code, transcribed, not redesigned.

const LinCongrueA: u64 = 6364136223846793005; // LIN_CONGRUE_A
const LinCongrueC: u64 = 1442695040888963407; // LIN_CONGRUE_C
const GodBadBits: u6 = 4; // GOD_BAD_BITS
const GodGoodBits: u16 = 24; // GOD_GOOD_BITS
const FifoCap: usize = 2048 * 8; // FifoU8New(2048*8) bits

extern "env" fn tsc() callconv(.C) f64;

fn nowTsc() u64 {
    const t = tsc();
    if (!(t > 0.0)) return 0;
    return @intFromFloat(t);
}

var state: u64 = 0; // Fs->rand_seed
var timer_mode: bool = true; // TASKf_NONTIMER_RAND not set
var draws: u64 = 0;

var fifo: [FifoCap]u8 = undefined; // god.fifo, one bit per entry
var fifo_head: usize = 0;
var fifo_fill: usize = 0;

// res = LIN_CONGRUE_A * res ^ (res & 0xFFFFFFFF0000) >> 16 + LIN_CONGRUE_C, in HolyC order.
fn lcg() void {
    const mul: u64 = LinCongrueA *% state;
    const shifted: u64 = (state & 0xFFFFFFFF00000000) >> 16;
    state = (mul ^ shifted) +% LinCongrueC;
}

export fn tsr_seed(seed: i64) void {
    if (seed != 0) {
        state = @bitCast(seed); // deterministic stream, TASKf_NONTIMER_RAND set
        timer_mode = false;
    } else {
        timer_mode = true; // Seed(0): stopwatch back on, state ^= GetTSC
        state ^= nowTsc();
    }
}

export fn tsr_rand() i64 {
    lcg();
    if (timer_mode) {
        state ^= nowTsc();
    }
    draws += 1;
    return @bitCast(state);
}

export fn tsr_randf() f64 {
    lcg();
    if (timer_mode) {
        state ^= nowTsc();
    }
    draws += 1;
    const mask: u64 = 0x3FFFFFFFFFFFFFFF;
    return @as(f64, @floatFromInt(state & mask)) / @as(f64, @floatFromInt(@as(u64, 0x4000000000000000)));
}

export fn tsr_state() i64 {
    return @bitCast(state);
}

export fn tsr_mode() i32 {
    return if (timer_mode) 1 else 0;
}

export fn tsr_draws() i64 {
    return @bitCast(draws);
}

// GodBitsIns (LSB first), silent drop when full - Terry ignores FifoU8Ins's return too.
fn bits_ins(n_bits: u16, value: u64) void {
    var v = value;
    var i: u16 = 0;
    while (i < n_bits) {
        if (fifo_fill < FifoCap) {
            fifo[(fifo_head + fifo_fill) % FifoCap] = @intCast(v & 1);
            fifo_fill += 1;
        }
        v >>= 1;
        i += 1;
    }
}

fn bits_rem(out: *u8) bool {
    if (fifo_fill == 0) return false;
    out.* = fifo[fifo_head];
    fifo_head = (fifo_head + 1) % FifoCap;
    fifo_fill -= 1;
    return true;
}

export fn tsr_god_press(t_us: f64) i32 {
    // GodPick: KbdMsEvtTime >> GOD_BAD_BITS, then GodBitsIns(GOD_GOOD_BITS, ...).
    const tt: u64 = if (t_us > 0.0) @intFromFloat(t_us) else 0;
    bits_ins(GodGoodBits, tt >> GodBadBits);
    return 1;
}

export fn tsr_god_cnt() i32 {
    return @intCast(fifo_fill);
}

export fn tsr_god_flush() void {
    fifo_head = 0;
    fifo_fill = 0;
}

// GodBits: pop N bits; when the FIFO runs dry TempleOS blocks on a user prompt, which a
// WASM module cannot do, so this returns -1 (the host's cue to ask for another press).
export fn tsr_god_bits(num_bits: i32) i64 {
    var res: u64 = 0;
    var left = num_bits;
    var b: u8 = 0;
    while (left > 0) {
        if (!bits_rem(&b)) return -1;
        res = (res << 1) +% b;
        left -= 1;
    }
    return @bitCast(res);
}
