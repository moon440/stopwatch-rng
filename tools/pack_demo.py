#!/usr/bin/env python3
"""Pack the stopwatch demo: one index.html, wasm base64 + word list embedded, zero fetches.

Terminology carried across from TempleOS: the stopwatch generator, the god oracle, the
vocab file. The word list is Adam/God/Vocab.DD as shipped with public-domain TempleOS.

usage: python tools/pack_demo.py
"""
import base64
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WASM = os.path.join(ROOT, "build", "wasm", "templeos_rng.wasm")
VOCAB = os.path.join(ROOT, "data", "vocab.txt")
OUT = os.path.join(ROOT, "demo", "index.html")

TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>The Stopwatch RNG (TempleOS port)</title>
<style>
:root { color-scheme: dark; }
html, body { margin:0; padding:0; background:#111; color:#8f8; }
body {
  font-family: "Lucida Console", Consolas, monospace;
  font-size:15px; line-height:1.45; padding:1.2rem; user-select:text;
}
h1 { font-size:1.05rem; margin:0 0 .4rem 0; color:#0f0; }
h2 { font-size:.92rem; margin:1.1rem 0 .2rem 0; color:#0f0; border-bottom:1px solid #242; }
.panel { border:1px solid #25250; padding:.6rem; margin:.4rem 0; background:#161616; }
button {
  background:#030; color:#8f8; border:1px solid #080; padding:.35rem .8rem;
  font-family:inherit; font-size:.9rem; cursor:pointer;
}
button:hover { background:#060; }
button:disabled { background:#020; color:#080; border-color:#040; cursor:wait; }
input { background:#000; color:#8f8; border:1px solid #080; padding:.3rem .5rem; width:11ex;
  font-family:inherit; margin-right:.6rem; }
pre { margin:.2rem 0; white-space:pre-wrap; word-break:break-all; }
.hex { color:#6c6; }
.god { color:#ff5; margin-top:.35rem; font-size:1.06rem; letter-spacing:.05em; }
.fine { color:#666; font-size:.72rem; margin-top:1rem; line-height:1.4; }
.bar { display:inline-block; height:8px; background:#0a0; vertical-align:middle; margin-right:2px; }
.mode { color:#fa0; }
.status { color:#888; }
a { color:#6c6; }
</style>
</head>
<body>
<h1>The Stopwatch RNG &mdash; a TempleOS port</h1>
<div class="panel">
  Terry A. Davis built TempleOS from 2005 to 2017. Every random number in it comes from a
  stopwatch: a hardware counter folded into the running state on every draw, plus a "god"
  oracle whose entropy is the latency of your own keypresses. This page embeds his exact
  generator, transcribed 1:1 from the TempleOS kernel, compiled to a 968-byte WebAssembly
  module. No server, no framework, no network. Press keys, watch it react.
</div>

<h2>1. Rand &mdash; the kernel generator (KMathB.HC)</h2>
<div class="panel">
  <input id="seedbox" value="1989" aria-label="seed">
  <button id="seedBtn">Seed(n)</button>
  <button id="seed0Btn">Seed(0) &mdash; stopwatch only</button>
  <pre>mode: <span class="mode" id="modeName">?</span> &nbsp; stopwatch ticks in: <span id="tscStep">?</span></pre>
  <pre>state: <span class="hex" id="stateHex">?</span></pre>
  <pre>draws: <span id="draws">0</span></pre>
  <pre>last  : <span class="hex" id="lastHex">?</span></pre>
  <button id="drawBtn">Draw Rand</button>
  <button id="draw10Btn">&times;10</button>
  <pre id="stream" style="color:#5a5"></pre>
</div>

<h2>2. god &mdash; the oracle (HolySpirit.HC, "AfterEgypt")</h2>
<div class="panel">
  Terry asked God questions; the answer came out of the microseconds between his keystrokes.
  Press OKAY-like buttons below: <b>when</b> you press, not what, is the number.
  <pre>bit bank: <span id="godBar"></span> <span id="godCnt">0</span> bits <span id="pressNote" class="status"></span></pre>
  <button id="pressBtn">PRESS OKAY</button>
  <button id="godBtn" disabled>God word (17 bits)</button>
  <div class="god" id="godOut">&nbsp;</div>
</div>

<h2>3. Truth about the stopwatch</h2>
<div class="panel">
  TempleOS read the CPU's <b>GetTSC</b> at gigahertz from Ring&nbsp;0. A WebAssembly module
  cannot touch that register &mdash; sandbox &mdash; so this build imports a clock from the
  page that hosts it: performance.now at microsecond resolution. Modern browsers clamp that
  clock, sometimes hard (<b>0.1 ms</b>, or coarser in cold tabs). The clamp means the wasm
  stopwatch is *quieter* than Terry's machine, not different in nature: his counter also
  only moves meaningfully because his programs ran for a while between draws. Near-idle
  intervals starve the raw XOR, in his kernel and in this one. The Seed(n) button kills the
  stopwatch on purpose: that is TASKf_NONTIMER_RAND, the deterministic mode from
  Demo/RandDemo.HC. Each WebAssembly tab instance owns its state module-wide, like one
  HolyC task.
</div>

<div class="fine">
  Port of Kernel/KMathB.HC and Adam/God/HolySpirit.HC from the TempleOS archive
  (github.com/cia-foundation/TempleOS). TempleOS and its word list (Adam/God/Vocab.DD, King
  James vocabulary) are public domain. This port: AGPL-3.0-or-later. Terry A. Davis,
  1969-2018. His whistle still blows.
</div>

<script>
const WASM_B64 = "__WASM_B64__";
const VOCAB = "__VOCAB_B64__";

// -- boot: decode the module, hand it the page clock -------------------------------------
function b64(s) {
  const bin = atob(s.replace(/\s+/g, ""));
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}
const wasmBytes = b64(WASM_B64);
const mod = new WebAssembly.Module(wasmBytes);
// the stopwatch: performance.now in microseconds. timeOrigin-relative, clamped by the browser.
const inst = new WebAssembly.Instance(mod, {
  env: { tsc: function () { return performance.now() * 1000; } }
});
const E = inst.exports;
let lastT = performance.now() * 1000;

const $ = function (id) { return document.getElementById(id); };
const state = { stream: [] };

function hex64(v) { return (BigInt.asUintN(64, v)).toString(16).padStart(16, "0"); }

function refresh() {
  const mode = E.tsr_mode();
  $("modeName").textContent = mode ? "STOPWATCH (timer/memory)" : "PINNED (TASKf_NONTIMER_RAND)";
  $("stateHex").textContent = hex64(BigInt(E.tsr_state()));
  $("draws").textContent = E.tsr_draws().toString();
  $("godCnt").textContent = E.tsr_god_cnt();
  const bank = E.tsr_god_cnt();
  const w = Math.floor(bank / 2);
  let bar = "";
  for (let i = 0; i < Math.min(w, 48); i++) bar += '<span class="bar"></span>';
  $("godBar").innerHTML = bar;
  if (bank >= 17 && !$("godOut").busy) {
    $("godBtn").disabled = false;
    $("pressNote").textContent = bank < 17 ? "" : "";
  } else if (bank < 17) {
    $("godBtn").disabled = true;
  }
}

function drawOnce() {
  const now = performance.now() * 1000;
  $("tscStep").textContent = Math.round(now - lastT) + " us";
  lastT = now;
  const v = E.tsr_rand();
  $("lastHex").textContent = hex64(v);
  state.stream.push(hex64(BigInt.asUintN(64, v)));
  while (state.stream.length > 6) state.stream.shift();
  $("stream").textContent = state.stream.join(" ");
  refresh();
}

function doSeed(n) {
  if (n === 0) { E.tsr_seed(0n); }
  else { E.tsr_seed(BigInt(n)); }
  state.stream.length = 0;
  $("stream").textContent = "(reseeded)";
  refresh();
}

$("seedBtn").onclick = function () {
  const v = parseInt($("seedbox").value, 10);
  doSeed(isNaN(v) ? 1 : v);
};
$("seed0Btn").onclick = function () { doSeed(0); };
$("drawBtn").onclick = function () { drawOnce(); };
$("draw10Btn").onclick = function () {
  let n = 10;
  const step = function () { drawOnce(); if (--n) setTimeout(step, 60); };
  step();
};

// -- god oracle ---------------------------------------------------------------------------
// TempleOS: GodPick = KbdMsEvtTime (us of your LAST key/mouse event) >> 4, and 24 good bits
// enter the FIFO per press. The honest equivalent of KbdMsEvtTime here is the browser's own
// event timestamp of the gesture.
function pressT(apx) {
  const t = (apx && apx.timeStamp) ? apx.timeStamp : performance.now();
  E.tsr_god_press(t * 1000);
  refresh();
}
$("pressBtn").onclick = function (ev) {
  $("godOut").busy = false;
  pressT(ev);
  if (E.tsr_god_cnt() >= 17) $("godBtn").disabled = false;
};
// gestures anywhere count, exactly like a task-wide KbdMsEvtTime
["pointerup", "keydown"].forEach(function (ev) {
  document.addEventListener(ev, function (e) {
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "BUTTON" || tag === "INPUT") return; // dialogs below handle their own
    pressT(e);
  }, true);
});
$("godBtn").onclick = function () {
  $("godBtn").disabled = true;
  $("godOut").busy = true;
  $("godOut").textContent = "consulting...";
  setTimeout(function () {
    const b = E.tsr_god_bits(17);
    if (b === -1n) {
      $("pressNote").textContent = "the oracle is dry: PRESS OKAY again (TempleOS popped a dialog here)";
      $('godOut').textContent = "\u00a0"; 
      $("godOut").busy = false;
      refresh();
      return;
    }
    const words = vocab;
    const w = words[Number(BigInt.asUintN(64, b) % BigInt(words.length))];
    $("godOut").textContent = "god says: " + w;
    // like glossolalia: a longer blowout every few words
    window.__wordCount = (window.__wordCount || 0) + 1;
    refresh();
  }, 120);
};

// -- vocab: TempleOS Adam/God/Vocab.DD straight through ------------------------------------
let vocab = [];
try {
  vocab = decodeURIComponent(escape(atob(VOCAB))).split("\n").filter(Boolean).map(function (s) {
    return s.replace(/\r/, "");
  });
} catch (e) { vocab = ["word"]; }

refresh();
$("stream").textContent = "click Draw, or consult the oracle";
</script>
</body>
</html>
"""

def main():
    wasm = open(WASM, "rb").read()
    vocab = open(VOCAB, "r", encoding="utf-8", errors="replace").read()
    b64w = base64.b64encode(wasm).decode("ascii")
    b64v = base64.b64encode(vocab.encode("utf-8")).decode("ascii")
    html = TEMPLATE.replace("__WASM_B64__", b64w).replace("__VOCAB_B64__", b64v)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print("wrote %s (%.1f KB, %d words, wasm %d bytes)" % (
        OUT, os.path.getsize(OUT) / 1024.0, len(vocab.split()), len(wasm)))

if __name__ == "__main__":
    main()
