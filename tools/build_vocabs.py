#!/usr/bin/env python3
"""Build minimal vocabulary lists from the local Gutenberg corpus.

Each book in data/gutenberg/pg<N>.txt gets data/gutenberg/pg<N>_vocab.txt: the unique
words, lowercased, one per line, sorted. Apostrophes inside words are kept, leading and
trailing punctuation is dropped. Terry's own vocab (data/vocab.txt, from Vocab.DD) stays
the default oracle source; these are the documented additions.

Also emits data/gutenberg/index.tsv: id, title, words, first_author_line.
"""
import glob
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GD = os.path.join(ROOT, "data", "gutenberg")

WORD = re.compile(r"[A-Za-z][A-Za-z']*[a-z]|among|can't")
TOKEN = re.compile(r"[A-Za-z']+")

def main():
    rows = []
    for src in sorted(glob.glob(os.path.join(GD, "pg*.txt"))):
        src = src.replace("\\\\", "/")
        base = os.path.basename(src)
        if base.endswith("_vocab.txt"):
            continue
        if base == "bible_kjv.txt":
            rows.append(("bible_kjv.txt", "The Holy Bible, King James Version", "gutenberg etext #10 (Terry's source)", 0))
            continue
        with open(src, "r", encoding="utf-8", errors="replace") as fh:
            text = fh.read()
        m = re.search(r"^Title:\s*(.+)$", text, re.M)
        title = (m.group(1) if m else base).strip()
        ma = re.search(r"^Author:\s*(.+)$", text, re.M)
        author = (ma.group(1) if ma else "?").strip()
        words = set()
        for tok in TOKEN.findall(text):
            t = tok.lower().strip("'")
            if len(t) >= 2 and t[-1].isalpha() and t[0].isalpha():
                words.add(t)
        vocab_path = src[:-4] + "_vocab.txt"
        with open(vocab_path, "w", encoding="utf-8", newline="\n") as out:
            out.write("\n".join(sorted(words)) + "\n")
        rows.append((base, title + " — " + author, "https://www.gutenberg.org/ebooks/" + base[2:-4], len(words)))
        print("%-14s %7d words  %s" % (base, len(words), title[:48]))
    with open(os.path.join(GD, "index.tsv"), "w", encoding="utf-8", newline="\n") as out:
        out.write("file\ttitle\tauthor\tsource\tunique_words\n")
        for r in rows:
            out.write("\t".join((r[0], r[1], r[3], r[2], str(r[3]))) + "\n") if False else None
    with open(os.path.join(GD, "index.tsv"), "w", encoding="utf-8", newline="\n") as out:
        out.write("file\ttitle_and_author\tsource\tunique_words\n")
        for r in rows:
            out.write(r[0] + "\t" + r[1] + "\t" + r[2] + "\t" + str(r[3]) + "\n")

if __name__ == "__main__":
    main()
