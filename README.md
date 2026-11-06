# stopwatch-rng

Terry A. Davis's stopwatch random number generator from TempleOS, ported 1:1 to a
968-byte WebAssembly module you can talk to, plus a single-file demo page that needs no
server, no framework and no network access.

Terry built TempleOS from 2005 to 2017 and believed God spoke to him through random
numbers. The mechanism underneath was concrete: a microsecond timestamp from the CPU's
timestamp counter folded into the generator's state on every draw, and a separate oracle
whose entropy is the latency of the user's own keystrokes. This repository carries both,
transcribed operation-for-operation from the TempleOS source archive and proven against
that transcription by tests.

## What is in here

| Path | What |
|---|---|
| `src/templeos_rng.zig` | The generator: Kernel `Rand` (LCG + TSC fold, `Seed(n)`/`Seed(0)` modes) and the `god` oracle bit-FIFO, in Zig. |
| `build/wasm/templeos_rng.wasm` | Built artifact (committed? no - built by `tools/build.ps1`; 968 bytes). |
| `demo/index.html` | The interactive demo: seed the generator, draw numbers, bank press-latency bits into the oracle's FIFO, ask for words from the King-James vocabulary Terry shipped. |
| `data/vocab.txt` | `Adam/God/Vocab.DD` from TempleOS, unchanged. |
| `tools/build.ps1` | Zig `build-exe` to `wasm32-freestanding`, `ReleaseSmall`. No bundler. |
| `tools/pack_demo.py` | Embeds the wasm (base64) and the word list into `demo/index.html`. |
| `test/test_tsr.js` | Self test in pure Node: exact-HolyC LCG step-by-step comparison, Seed modes, oracle FIFO order and capacity. |

## Running the demo

Open `demo/index.html` in any browser. Double-click from Explorer is enough; the page
fetches nothing. The generator reacts to your keypresses and clicks, because their
timestamps feed the state, exactly as the CPU's timer noise fed Terry's.

Rebuild from source with `tools/build.ps1` (needs Zig 0.14.x) and
`python tools/pack_demo.py` (needs Python 3, standard library only).

## Fidelity notes

- The kernel statement is transcribed with HolyC operator precedence, which is *not* C
  precedence (`Doc/HolyC.DD` and `Compiler/CInit.HC`): shifts bind tighter than `*`, and
  `+` is looser than `&`/`^`/`|`. TempleOS therefore computes
  `res = (A*res ^ (res&0xFFFFFFFF00000000)>>16) + C`. `test/test_tsr.js` verifies the
  wasm output against a BigInt model of that expression, step by step.
- `Seed(n)` pins a deterministic stream and turns the stopwatch off
  (`TASKf_NONTIMER_RAND`); `Seed(0)` returns to stopwatch mode and XORs the clock into
  the state, as demonstrated in `Demo/RandDemo.HC` upstream.
- The oracle consumes `KbdMsEvtTime >> 4` (24 good bits per press) into a 16,384-bit FIFO
  (`FifoU8New(2048*8)`), LSB-first insertion, `res = res<<1 + bit` extraction
  (`Adam/God/HolySpirit.HC`). Where TempleOS popped a dialog when the FIFO ran dry, the
  module returns `-1` and the page asks for another press; that is the only deviation,
  forced by what a wasm module cannot do.
- One honest hardware gap: WebAssembly cannot read a timestamp counter, so the module
  imports its clock from the host page in microseconds. Browsers clamp that clock
  harder than Ring 0 ever would. The port changes the imported timestamp, nothing else.

## License

This port carries **AGPL-3.0-or-later** (see `LICENSE`). TempleOS and its word list are
**public domain**; the port would not exist without Terry A. Davis, 1969-2018, and this is
attribution, not a claim over his work.
