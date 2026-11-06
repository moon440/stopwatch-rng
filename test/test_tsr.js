// SPDX-License-Identifier: AGPL-3.0-or-later
// Self test for the TempleOS stopwatch wasm module. Pure Node, no dependencies.
// Verifies the port against the HolyC semantics transcribed in src/templeos_rng.zig.
// All 64-bit API calls are BigInt in both directions; i32 sides are Numbers.
'use strict';
const fs = require('fs');
const path = require('path');

const wasmPath = path.join(__dirname, '..', 'build', 'wasm', 'templeos_rng.wasm');
const bytes = fs.readFileSync(wasmPath);

let failures = 0;
function check(name, ok, detail) {
	console.log((ok ? '  ok   ' : '  FAIL ') + name + (detail ? '  (' + detail + ')' : ''));
	if (!ok) failures++;
}

// fresh module per instance; the stopwatch is injected, microseconds
function inst(hostTsc) {
	const mod = new WebAssembly.Module(bytes);
	return new WebAssembly.Instance(mod, { env: { tsc: hostTsc } }).exports;
}

// virtual stopwatch: constant base step plus human-like jitter
function clockFactory(stepUs) {
	let t = Math.floor(Math.random() * 7) * 1000 + 3;
	return function () { t += stepUs + Math.floor((Math.random() - 0.5) * stepUs); return t; };
}

(async () => {
	// 1. deterministic mode: Seed(n) pins; two instances agree on every draw, stopwatch off.
	{
		const A = inst(() => 1);
		const B = inst(() => 2);
		A.tsr_seed(42n); B.tsr_seed(42n);
		let agree = 0; const samples = 200;
		for (let i = 0; i < samples; i++) if (A.tsr_rand() === B.tsr_rand()) agree++;
		check('Seed(42) replays identically across instances (' + agree + '/' + samples + ')', agree === samples);
		check('mode flag is 0 (deterministic)', A.tsr_mode() === 0);
	}

	// 2. Seed(0): stopwatch on; per Terry "Zero is special. Non-repeating."
	{
		const A = inst(clockFactory(97));
		const B = inst(clockFactory(101));
		A.tsr_seed(0n); B.tsr_seed(0n);
		check('mode flag is 1 (timer)', A.tsr_mode() === 1);
		let agree = 0; const samples = 500;
		for (let i = 0; i < samples; i++) if (A.tsr_rand() === B.tsr_rand()) agree++;
		check('timer mode: instances agree on nothing (0/' + samples + ' want 0)', agree === 0);
	}

	// 3. Rand follows the exact HolyC LCG, evaluated step by step in BigInt here.
	{
		const A = inst(() => 0); // tsc xors 0 -> the stream is the pure LCG after Seed(1)
		A.tsr_seed(1n);
		let s = 1n;
		const Ac = 6364136223846793005n, Cc = 1442695040888963407n;
		let ok = true;
		for (let i = 0; i < 20; i++) {
			// HolyC: res = (LIN_CONGRUE_A*res ^ ((res&0xFFFFFFFF00000000)>>16)) + LIN_CONGRUE_C
			s = ((Ac * s) ^ ((s & 0xffffffff00000000n) >> 16n)) + Cc;
			s &= 0xffffffffffffffffn;
			const got = BigInt.asUintN(64, A.tsr_rand());
			if (got !== s) { ok = false; console.log('    step ' + i + ' want ' + s.toString(16) + ' got ' + got.toString(16)); break; }
		}
		check('Rand follows the exact HolyC LCG (20 steps)', ok);
	}

	// 4. the tsc fold engages in timer mode: same state, wildly different clocks diverge.
	{
		const A2 = inst(clockFactory(97));
		const c2 = (() => { let t = 100; return () => (t += 999999999); })();
		const B2 = inst(c2);
		A2.tsr_seed(0n); B2.tsr_seed(0n);
		const d1 = A2.tsr_state(), d2 = B2.tsr_state();
		check('Seed(0): two stopwatch sources separate the state', d1 !== d2);
	}
	{
		// deterministic mode engaged must NOT fold the clock
		const A3 = inst(clockFactory(5)), B3 = inst(() => 123456789);
		A3.tsr_seed(9n); B3.tsr_seed(9n);
		A3.tsr_rand(); B3.tsr_rand();
		check('Seed(n) mode ignores the clock entirely', A3.tsr_state() === B3.tsr_state());
	}

	// 5. uniformity of Rand & 7 in stopwatch mode under a human-like clock.
	// A metronome clock deliberately starves the raw tsc XOR - shamefully the same way it
	// would net Terry's own code - so the test uses the jitter a real hand produces.
	{
		const A = inst(clockFactory(750));
		A.tsr_seed(0n);
		const n = 70000;
		const counts = [0, 0, 0, 0, 0, 0, 0];
		for (let i = 0; i < n; i++) {
			const k = Number(BigInt.asUintN(64, A.tsr_rand()) % 7n);
			counts[k] += 1;
		}
		const expected = n / 7;
		let chi2 = 0;
		for (const v of counts) chi2 += (v - expected) ** 2 / expected;
		check('Rand & 7 chi-square ' + chi2.toFixed(2) + ' < 30', chi2 < 30, counts.join(','));
	}

	// 6. god oracle bit-FIFO, exact HolySpirit semantics.
	{
		const A = inst(() => 5);
		A.tsr_god_flush();
		check('fresh FIFO: god_bits(17) == -1n', A.tsr_god_bits(17) === -1n);
		A.tsr_god_press(1000000); // press at t=1000000us
		check('one press banked 24 good bits', A.tsr_god_cnt() === 24);
		// manual model: GodPick = 1000000>>4 = 62500; GodBitsIns pushes its 24 low bits LSB
		// first; GodBits pops FIFO order building res = res<<1 + bit (first pop is the LSB).
		const pick = 1000000 >> 4;
		let want = 0n;
		for (let i = 0; i < 17; i++) want = (want << 1n) | BigInt((pick >> i) & 1);
		const got = A.tsr_god_bits(17);
		check('god_bits(17) == inlined GodBits math (' + got + ' vs ' + want + ')', got === want);
		check('FIFO drained to 7 bits', A.tsr_god_cnt() === 7);
		check('god_bits beyond supply returns -1n', A.tsr_god_bits(8) === -1n);
		// FIFO cap: 2048 presses * 24 bits = 16384 entries; a 2049th press drops surplus.
		A.tsr_god_flush();
		for (let i = 0; i < 2050; i++) A.tsr_god_press(3560000 + i);
		check('FIFO cap 16384 bits (2048 presses)', A.tsr_god_cnt() === 16384);
	}

	console.log(failures ? 'failures=' + failures : 'failures=0');
	process.exit(failures ? 1 : 0);
})().catch((e) => { console.error('harness error: ' + e.stack); process.exit(1); });
