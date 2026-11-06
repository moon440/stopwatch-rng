#!/usr/bin/env python3
"""Pack the stopwatch demo: one index.html, wasm + wordlists + KJV + book quotes, zero fetches.

Oracle modes (entropy is always YOUR press latency, like TempleOS):
  word     - GodWordStr, 17 bits each                        (HolySpirit.HC:138)
  sentence - 3..7 words, the AfterEgypt stream draw order
  verse    - KJV: GodBiblePassage (21 bits into Terry's Bible.TXT, etext #10)
           - books: random line-quotes, line numbers kept for source reference

Church k: verse count is selectable (1..4 or random 1..4).

usage: python tools/pack_demo.py
"""
import base64
import glob
import json
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

def b64(path):
    with open(path, "rb") as fh:
        return base64.b64encode(fh.read()).decode("ascii")

def main():
    wasm_b = b64(os.path.join(ROOT, "build", "wasm", "templeos_rng.wasm"))
    bible_b = b64(os.path.join(ROOT, "data", "gutenberg", "bible_kjv.txt"))

    srcs = [{"name": "TempleOS Vocab.DD (KJV words, Terry's list)",
             "data": b64(os.path.join(ROOT, "data", "vocab.txt")),
             "title": "TempleOS Vocab.DD",
             "quotes": None, "text": None}]
    for path in sorted(glob.glob(os.path.join(ROOT, "data", "gutenberg", "pg*_vocab.txt"))):
        pg = os.path.basename(path)[:-10]
        book = path[:-10] + ".txt"
        title = pg
        try:
            with open(book, "r", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if line.startswith("Title:"):
                        title = line[6:].strip()
                        break
        except OSError:
            pass
        qpath = path[:-10] + "_quotes.json"
        qs = b64(qpath) if os.path.exists(qpath) else None
        tb = b64(book) if os.path.exists(book) else None
        srcs.append({"name": "Gutenberg: %s" % title[:100],
                     "data": b64(path),
                     "title": title,
                     "quotes": qs,
                     "text": tb})
    srcs_json = json.dumps(srcs, ensure_ascii=False, separators=(",", ":"))

    html = (TEMPLATE
            .replace("__WASM_B64__", wasm_b)
            .replace("__BIBLE_B64__", bible_b)
            .replace("__SRCS__", srcs_json))

    out = os.path.join(ROOT, "demo", "index.html")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(html)
    print("wrote %s (%.2f MB, %d sources, KJV + book quotes embedded)" % (
        out, os.path.getsize(out) / 1048576.0, len(srcs)))

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
.panel { border:1px solid #252520; padding:.6rem; margin:.4rem 0; background:#161616; }
button {
  background:#030; color:#8f8; border:1px solid #080; padding:.35rem .8rem;
  font-family:inherit; font-size:.9rem; cursor:pointer;
}
button:hover { background:#060; }
button:disabled { background:#020; color:#080; border-color:#040; cursor:default; }
select, input { background:#000; color:#8f8; border:1px solid #080; padding:.3rem .4rem;
  font-family:inherit; font-size:.88rem; max-width:100%; }
input { width:9ex; margin-right:.6rem; }
pre { margin:.2rem 0; white-space:pre-wrap; word-break:break-all; }
.hex { color:#6c6; }
.god { color:#ff5; margin-top:.35rem; font-size:1.06rem; letter-spacing:.04em; }
.quote, .verse { color:#ffa; margin-top:.3rem; font-size:.97rem; }
.quote { border-top:1px dashed #333; padding-top:.3rem; }
.cite { color:#f80; font-size:.78rem; }
.fine { color:#666; font-size:.72rem; margin-top:1rem; line-height:1.4; }
.bar { display:inline-block; height:8px; width:4px; background:#0a0; margin-right:3px; }
.mode { color:#fa0; }
.status { color:#888; }
</style>
</head>
<body>
<h1>The Stopwatch RNG &mdash; a TempleOS port</h1>
<div class="panel">
  Terry A. Davis built TempleOS from 2005 to 2017. Every random number in it comes from a
  stopwatch: a hardware counter folded into the running state on every draw, plus a <b>god
  oracle</b> whose entropy is the latency of your own keystrokes. This page embeds his exact
  generator, transcribed 1:1 from the TempleOS kernel, compiled to a 968-byte WebAssembly
  module. No server, no framework, no network. Press keys &mdash; <i>when</i> you press is
  the number.
</div>

<h2>1. Rand &mdash; the kernel generator (KMathB.HC)</h2>
<div class="panel">
  <input id="seedbox" value="1989" aria-label="seed">
  <button id="seedBtn">Seed(n)</button>
  <button id="seed0Btn">Seed(0) &mdash; stopwatch only</button>
  <pre>mode: <span class="mode" id="modeName">?</span> &nbsp; stopwatch ticks: <span id="tscStep">?</span></pre>
  <pre>state: <span class="hex" id="stateHex">?</span></pre>
  <pre>draws: <span id="draws">0</span> &nbsp; last: <span class="hex" id="lastHex">?</span></pre>
  <button id="drawBtn">Draw Rand</button>
  <button id="draw10Btn">&times;10</button>
  <pre id="stream" style="color:#5a5"></pre>
</div>

<h2>2. god &mdash; the oracle (HolySpirit.HC, AfterEgypt)</h2>
<div class="panel">
  <label for="srcSel">word source:</label>
  <select id="srcSel"></select>
<br>
  <label for="voiceSel">voice:</label>
  <select id="voiceSel"><option value="markov" selected>pastiche (markov n=4)</option><option value="free">free draw (afteregypt words)</option></select>
  <input id="askBox" placeholder="ask the book anything" style="width:14rem" aria-label="question for oracle">
  <pre>bit bank: <span id="godBar"></span> <span id="godCnt">0</span> bits <span id="pressNote" class="status"></span></pre>
  <button id="pressBtn">PRESS OKAY</button>
  <button id="wordBtn" disabled>Word (17 bits)</button>
  <button id="talkBtn" disabled>Speak (pastiche / sentence)</button>
  <button id="verseBtn">Verses / Quotes</button>
  <label for="verseCountSel">lines </label>
  <select id="verseCountSel">
    <option value="1" selected>1</option><option value="2">2</option><option value="3">3</option><option value="4">4</option><option value="random">random 1-4</option>
  </select>
  <div class="god" id="godOut">&nbsp;</div>
  <div class="quote" id="verseOut"></div>
</div>

<h2>3. Truth about the stopwatch</h2>
<div class="panel">
  TempleOS read the CPU's <b>GetTSC</b> at gigahertz from Ring&nbsp;0. A WebAssembly module
  cannot touch that register &mdash; sandbox &mdash; so this build imports a clock from the
  page: <code>performance.now</code> at microsecond resolution, clamped by modern browsers to
  0.1 ms or coarser in cold tabs. The clamp makes the wasm stopwatch <i>quieter</i> than
  Terry's machine, not different in nature: his counter only moved meaningfully because
  his programs kept running between draws. The Seed(n) button kills the stopwatch on
  purpose &mdash; that is TASKf_NONTIMER_RAND, the deterministic mode of
  Demo/RandDemo.HC.
</div>

<div class="fine">
  Port of Kernel/KMathB.HC and Adam/God/HolySpirit.HC from the TempleOS archive
  (github.com/cia-foundation/TempleOS). Bible text: Terry's own Misc/Bible.TXT (Project
  Gutenberg etext #10, 1989, King James Version). TempleOS and its word list are public
  domain; the King James Bible is public domain; the Gutenberg wordlists and quote lines
  point to their files (data/gutenberg/pg&lt;id&gt;.txt), line numbers in citations are
  line numbers of those files. Project Gutenberg etexts are public domain in the US;
  check the notice inside each book for your jurisdiction. The port and the word-list
  scripts: AGPL-3.0-or-later. Terry A. Davis, 1969&ndash;2018. His whistle still blows.
</div>

<script>
const WASM_B64 = "__WASM_B64__";
const BIBLE_B64 = "__BIBLE_B64__";
const SRCS = __SRCS__;

const BIBLE_BOOKS = ["Genesis","Exodus","Leviticus","Numbers","Deuteronomy","Joshua","Judges","Ruth","1 Samuel","2 Samuel","1 Kings","2 Kings","1 Chronicles","2 Chronicles","Ezra","Nehemiah","Esther","Job","Psalms","Proverbs","Ecclesiastes","Song of Songs","Isaiah","Jeremiah","Lamentations","Ezekiel","Daniel","Hosea","Joel","Amos","Obadiah","Jonah","Micah","Nahum","Habakkuk","Zephaniah","Haggai","Zechariah","Malachi","Matthew","Mark","Luke","John","Acts","Romans","1 Corinthians","2 Corinthians","Galatians","Ephesians","Philippians","Colossians","1 Thessalonians","2 Thessalonians","1 Timothy","2 Timothy","Titus","Philemon","Hebrews","James","1 Peter","2 Peter","1 John","2 John","3 John","Jude","Revelation"];

function decodeB64(b64) {
  const bin = atob(b64.replace(/\s+/g, ""));
  const u = new Uint8Array(bin.length);
  for (let i = 0; i < bin.length; i++) u[i] = bin.charCodeAt(i);
  return u;
}
function b64str(b64) {
  try { return decodeURIComponent(escape(atob(b64.replace(/\s+/g, "")))); }
  catch (e) { return atob(b64.replace(/\s+/g, "")); }
}

const mod = new WebAssembly.Module(decodeB64(WASM_B64));
const inst = new WebAssembly.Instance(mod, {
  env: { tsc: function () { return performance.now() * 1000; } }
});
const E = inst.exports;
const $ = function (id) { return document.getElementById(id); };
let lastT = performance.now() * 1000;

const cache = {};
SRCS.forEach(function (s, i) {
  const o = document.createElement("option");
  o.value = String(i);
  o.textContent = s.name;
  $("srcSel").appendChild(o);
});
function srcIndex() { return Number($("srcSel").value); }
function sourceWords() {
  const key = srcIndex();
  if (!cache["w" + key]) {
    cache["w" + key] = b64str(SRCS[key].data).split("\n")
      .map(function (s) { return s.replace(/\r$/, ""); })
      .filter(Boolean);
  }
  return cache["w" + key];
}
function sourceText() {
  const key = srcIndex();
  if (!cache["t" + key]) {
    const b = SRCS[key].text || BIBLE_B64;
    cache["t" + key] = b64str(b);
  }
  return cache["t" + key];
}
function sourceQuotes() {
  const key = srcIndex();
  if (!SRCS[key].quotes) return null;
  if (!cache["q" + key]) {
    cache["q" + key] = JSON.parse(b64str(SRCS[key].quotes)).quotes;
  }
  return cache["q" + key];
}

// ---- Markov pastiche: order-4 engine with 3/2/1 backoff, built from the book text.
// Memory = last-n window only. Transition choice consumes stopwatch bits (press latency).
const markovCache = {};
function buildMarkov(key, order, maxMaps) {
  const ck = key + ":" + order;
  if (markovCache[ck]) return markovCache[ck];
  const raw = sourceText();
  let bodyText = raw;
  const st = raw.indexOf("START OF THE PROJECT GUTENBERG");
  const en = raw.indexOf("END OF THE PROJECT GUTENBERG", st == -1 ? 0 : st);
  if (st !== -1) {
    const ls = raw.indexOf("\n", st);
    bodyText = ls !== -1 ? raw.slice(ls + 1, en !== -1 ? en : undefined) : raw.slice(st, en !== -1 ? en : undefined);
  } else if (en !== -1) bodyText = raw.slice(0, en);
  const tokens = bodyText.split(/[\s_]+/).map(function(s){ return s.trim(); }).filter(Boolean);
  const startsMap = [];
  const norm = (w) => w.toLowerCase().replace(/[^a-z']+/g, "");
  const tokensDb = tokens;
  const ord = order;
  const maps = [];
  for (let o = 1; o <= ord; o++) maps[o] = new Map();
  for (let i = 0; i < tokens.length - 1; i++) {
    const nx = tokens[i+1];
    for (let o = 1; o <= ord; o++) {
      if (i < o + 1) continue;
      const k = tokens.slice(i - o + 1, i + 1).map(norm).join(" ");
      const arr = maps[o].get(k);
      if (arr) { if (arr.length < 32) arr.push(nx); }
      else maps[o].set(k, [nx]);
    }
  }
  const engine = { maps: maps, ord: ord, tokens: tokensDb };
  markovCache[ck] = engine;
  return engine;
}
function godPick(n) {
  const b = E.tsr_god_bits(17);
  if (b === -1n) return null;
  return Number(BigInt.asUintN(64, b) % BigInt(n));
}
function questionSeed() {
  const q = ($("askBox").value || "").trim();
  if (!q) return 0;
  let h = 0;
  for (let i = 0; i < q.length; i++) h = (h * 31 + q.charCodeAt(i)) >>> 0;
  return h;
}
function speakMarkov() {
  const key = srcIndex();
  const engine = buildMarkov(key, 4);
  const qs = questionSeed();
  const posPick = godPick(engine.tokens.length - 10);
  if (posPick === null) { oracleBits(17); return; }
  let pos = (posPick + qs) % Math.max(1, engine.tokens.length - 10);
  const out = engine.tokens.slice(pos, pos + 4);
  const want = 22 + (qs % 14); // 22..35 words
  const maxSteps = want + 60;
  let dry = false;
  const norm = (w) => w.toLowerCase().replace(/[^a-z']+/g, "");
  while (out.length < want && out.length < maxSteps) {
    let chosen = null;
    for (let o = engine.ord; o >= 1 && !chosen; o--) {
      if (out.length < o) continue;
      const k = out.slice(out.length - o).map(norm).join(" ");
      const arr = engine.maps[o].get(k);
      if (arr && arr.length) {
        const pick = godPick(arr.length);
        if (pick === null) { dry = true; break; }
        chosen = arr[pick];
      }
    }
    if (dry) break;
    if (!chosen) {
      const p2 = godPick(engine.tokens.length - 1);
      if (p2 === null) { dry = true; break; }
      chosen = engine.tokens[p2];
    }
    out.push(chosen);
  }
  if (dry) { $("pressNote").textContent = "still rising: PRESS OKAY (" + out.length + " words banked)"; return; }
  $("pressNote").textContent = "";
  let sentence = out.join(" ");
  sentence = sentence.charAt(0).toUpperCase() + sentence.slice(1);
  if (!/[.!?]$/.test(sentence)) sentence += ".";
  $("godOut").textContent = sentence;
  $("verseOut").innerHTML = "";
  incRefresh();
}
function speakFree() {
  const words = sourceWords();
  const nb = E.tsr_god_bits(2);
  if (nb === -1n) { oracleBits(19); return; }
  const n = 3 + Number(BigInt.asUintN(64, nb));
  const draw = [];
  for (let i = 0; i < n; i++) {
    const w = E.tsr_god_bits(17);
    if (w === -1n) {
      $("pressNote").textContent = "still rising: PRESS OKAY (" + draw.length + "/" + n + " words so far)";
      return;
    }
    draw.push(words[Number(BigInt.asUintN(64, w) % BigInt(words.length))]);
  }
  $("pressNote").textContent = "";
  $("godOut").textContent = draw.join(" ");
  $("verseOut").innerHTML = "";
  incRefresh();
}
$("talkBtn").onclick = function () {
  if ($("voiceSel").value === "markov") speakMarkov(); else speakFree();
};

// console basics
let streamBuf = [];
function hex64(v) { return BigInt.asUintN(64, v).toString(16).padStart(16, "0"); }
function incRefresh() {
  const mode = E.tsr_mode();
  $("modeName").textContent = mode
    ? "STOPWATCH (stopwatch-on, Terry's default)"
    : "PINNED (TASKf_NONTIMER_RAND)";
  $("stateHex").textContent = hex64(BigInt(E.tsr_state()));
  $("draws").textContent = E.tsr_draws().toString();
  $("godCnt").textContent = E.tsr_god_cnt();
  let bar = "";
  for (let i = 0; i < Math.min(((E.tsr_god_cnt() / 2) | 0) + 1, 64); i++) bar += '<span class="bar"></span>';
  $("godBar").innerHTML = bar;
  const have = E.tsr_god_cnt() >= 17;
  $("wordBtn").disabled = !have;
  $("talkBtn").disabled = !have;
}
function drawOnce() {
  const now = performance.now() * 1000;
  $("tscStep").textContent = Math.round(now - lastT) + " us";
  lastT = now;
  const v = E.tsr_rand();
  $("lastHex").textContent = hex64(v);
  streamBuf.push(hex64(v));
  while (streamBuf.length > 6) streamBuf.shift();
  $("stream").textContent = streamBuf.join(" ");
  incRefresh();
}
function doSeed(n) {
  E.tsr_seed(n === 0 ? 0n : BigInt(n));
  streamBuf = [];
  $("stream").textContent = "(reseeded)";
  incRefresh();
}
$("seedBtn").onclick = function () { const v = parseInt($("seedbox").value, 10); doSeed(isNaN(v) ? 1 : v); };
$("seed0Btn").onclick = function () { doSeed(0); };
$("drawBtn").onclick = drawOnce;
$("draw10Btn").onclick = function () { let n = 10; const step = function () { drawOnce(); if (--n) setTimeout(step, 60); }; step(); };

// god oracle
function pressT(ev) {
  const t = (ev && ev.timeStamp) ? ev.timeStamp : performance.now();
  E.tsr_god_press(t * 1000);
  incRefresh();
}
$("pressBtn").onclick = function (ev) { $("pressNote").textContent = ""; pressT(ev); };
["pointerup", "keydown"].forEach(function (ev) {
  document.addEventListener(ev, function (e) {
    const tag = (e.target && e.target.tagName) || "";
    if (tag === "BUTTON" || tag === "SELECT" || tag === "INPUT") return;
    pressT(e);
  }, true);
});
function oracleBits(need) {
  const have = E.tsr_god_cnt();
  $("pressNote").textContent = have >= need ? ""
    : "the FIFO has " + have + "/" + need + " bits: PRESS OKAY " + Math.ceil((need - have) / 24) + " more time(s)";
  return have >= need;
}
$("wordBtn").onclick = function () {
  const words = sourceWords();
  const b = E.tsr_god_bits(17);
  if (b === -1n) { oracleBits(17); return; }
  $("pressNote").textContent = "";
  const w = words[Number(BigInt.asUintN(64, b) % BigInt(words.length))];
  $("godOut").textContent = "god says: " + w;
  $("verseOut").innerHTML = "";
  incRefresh();
};

// KJV verse parsing (cached) - Terry's own Bible.TXT, split on the c:v inline markers
let bibleVerses = null;
function parseBible() {
  if (bibleVerses) return bibleVerses;
  const raw = b64str(BIBLE_B64).split("\n").map(function (s) { return s.replace(/\r$/, ""); });
  const verses = [];
  let book = -1, cur = null;
  const flush = function () {
    if (cur && cur.text.trim()) verses.push(cur);
    cur = null;
  };
  for (const line of raw) {
    if (!line.trim()) continue;
    const parts = line.split(/(\d+:\d+) /);
    for (let i = 0; i < parts.length; i++) {
      const piece = parts[i];
      if (i % 2 === 1) {
        flush();
        if (piece === "1:1") book += 1;
        cur = { book: BIBLE_BOOKS[book] || "?", marker: piece, text: "" };
      } else if (cur) {
        cur.text += (cur.text ? " " : "") + piece;
      }
    }
    if (cur) cur.text += " ";
  }
  flush();
  bibleVerses = verses;
  return verses;
}
function verseCount() {
  const v = $("verseCountSel").value;
  return v === "random" ? 1 + Math.floor(Math.random() * 4) : Number(v);
}
function pickLines(pool, n) {
  const out = [];
  for (let i = 0; i < n; i++) {
    const b = E.tsr_god_bits(21);
    if (b === -1n) return null;
    out.push(Number(BigInt.asUintN(64, b) % BigInt(pool.length)));
  }
  return out;
}

$("verseBtn").onclick = function () {
  const n = verseCount();
  const quotes = sourceQuotes();
  const pool = quotes ? quotes : parseBible();
  const title = quotes ? SRCS[srcIndex()].title : "KJV";
  const idxs = pickLines(pool, n);
  if (idxs === null) { oracleBits(n * 21); return; }
  $("pressNote").textContent = "";
  const blocks = [];
  for (const i of idxs) {
    if (quotes) {
      blocks.push('<div class="quote">' + pool[i].t +
        '<br><span class="cite">' + title + " &mdash; line " + pool[i].l + "</span></div>");
    } else {
      const v = pool[i];
      blocks.push('<div class="quote">' + v.text.trim() +
        '<br><span class="cite">' + v.book + " " + v.marker + " &mdash; line " + (i + 1) +
        "</span></div>");
    }
  }
  $("godOut").innerHTML = "&nbsp;";
  $("verseOut").innerHTML = blocks.join("");
  incRefresh();
};

incRefresh();
$("stream").textContent = "click Draw, or press OKAY and consult the oracle";
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
