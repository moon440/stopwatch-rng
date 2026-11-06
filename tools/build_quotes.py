#!/usr/bin/env python3
"""Extract quotable quotation lines from the Gutenberg corpus.

For every data/gutenberg/pg<N>.txt book: collect lines that look like prose sentences,
drop Project-Gutenberg header/footer boilerplate, keep them with their original line
numbers so every quote is verifiable against the reference file in this repository.

Writes data/gutenberg/pg<N>_quotes.json: {"title": ..., "source": ..., "quotes":
[{"l": <1-based line>, "t": <text>}]}. Capped; evenly spread through the book.

usage: python tools/build_quotes.py
"""
import glob
import hashlib
import json
import os
import re

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GD = os.path.join(ROOT, "data", "gutenberg")
CAP = 800
MIN_LEN, MAX_LEN = 42, 120

def main():
    for src in sorted(glob.glob(os.path.join(GD, "pg*.txt"))):
        base = os.path.basename(src)
        if base.endswith(("_vocab.txt", "_quotes.json")):
            continue
        if base == "bible_kjv.txt":
            print("skip bible (its own verse mode handles it)")
            continue
        text = open(src, "r", encoding="utf-8", errors="replace").read()
        m = re.search(r"^Title:\s*(.+)$", text, re.M)
        title = (m.group(1) if m else base).strip()
        # body between the Gutenberg markers
        start = text.find("*** START OF THE PROJECT GUTENBERG")
        end = text.find("*** END OF THE PROJECT GUTENBERG")
        body_raw = text[start:end if end != -1 else len(text)]
        lines = body_raw.splitlines()
        # line numbers are relative to the body; keep an offset for the reference file
        offset = text[:start].count("\n") if start != -1 else 0
        cand = []
        for j, line in enumerate(lines):
            t = re.sub(r"\s+", " ", line).rstrip()
            if not (MIN_LEN <= len(t) <= MAX_LEN):
                continue
            # mostly letters/spaces, low punctuation density, no markup/headers
            alpha = sum(c.isalpha() for c in t)
            if alpha < len(t) * 0.55:
                continue
            if any(bad in t for bad in ("***", "PROJECT GUTENBERG", "_gutenberg", "Illustration", "CONTENTS", "http", "GUTENBERG EBOOK")):
                continue
            if t.count('_') >= 2 or t.count("[") >= 2:
                continue
            cand.append({"l": offset + j + 1, "t": t})
        step = max(1, (len(cand) + CAP - 1) // CAP) if cand else 1
        picked = cand[::step][:CAP]
        out = src[:-4] + "_quotes.json"
        with open(out, "w", encoding="utf-8", newline="\n") as fh:
            json.dump({"title": title, "source": base, "quotes": picked}, fh, ensure_ascii=False, indent=0)
        print("%-12s %6d candidates -> %4d quoted  %s" % (base, len(cand), len(picked), title[:40]))

if __name__ == "__main__":
    main()
