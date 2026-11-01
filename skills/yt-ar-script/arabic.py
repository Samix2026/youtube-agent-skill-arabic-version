#!/usr/bin/env python3
"""arabic.py - shared Arabic text layer for every tool in this pack.

One implementation of normalisation, tokenising and lexicon lookup, so the hook scorer, the title
linter, the edit list and the chapter finder all read Arabic the same way.

Why this exists: the English originals tokenise with [a-z]. Arabic text through that regex comes
out EMPTY, so every score silently becomes meaningless. This module is the fix.

Lexicons live in ./lexicon/*.json (one file per dialect, merged). A user can add words without
touching code by dropping JSON files in ~/.claude/youtube-ar/lexicon/ - same keys, merged on top.
"""
import json, os, re

HERE = os.path.dirname(os.path.abspath(__file__))
USER_DIR = os.path.expanduser(os.environ.get("YOUTUBE_AR_HOME", "~/.claude/youtube-ar"))

TASHKEEL = re.compile(r"[ؐ-ًؚ-ٰٟۖ-ۭ]")
TATWEEL = "ـ"
DIGITS = str.maketrans("٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹", "01234567890123456789")
LETTERS = str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ٱ": "ا", "ى": "ي", "ة": "ه",
                         "ؤ": "و", "ئ": "ي", "٪": "%", "،": ",", "؟": "?", "؛": ";"})
TOKEN = re.compile(r"[ء-يa-z0-9%$]+(?:[.,]\d+)*")
ARABIC_CHAR = re.compile(r"[ء-ي]")

# single-letter clitics that glue onto the front of a word: wa, fa, bi, li, ka
PROCLITICS = ("و", "ف", "ب", "ل", "ك")


def normalize(text):
    """Strip diacritics and tatweel, unify alef/ya/ta-marbuta, convert Arabic-Indic digits."""
    t = TASHKEEL.sub("", text or "").replace(TATWEEL, "")
    return t.translate(LETTERS).translate(DIGITS).lower()


def tokens(text):
    return TOKEN.findall(normalize(text))


def is_arabic(text):
    return bool(ARABIC_CHAR.search(text or ""))


def variants(tok):
    """The token plus its forms with common proclitics and the article removed.

    والمشروع -> {والمشروع, المشروع, مشروع}. Kept deliberately shallow: two clitics and the
    article, never suffixes, because aggressive stemming merges words that mean different things.
    """
    out = {tok}
    stack = [tok]
    while stack:
        w = stack.pop()
        # wa/fa are conjunctions and strip freely; bi/li/ka need a longer remainder because
        # many roots start with those letters (لازم، كبير، بيت)
        if w[0] in ("و", "ف") and len(w) > 3 or w[0] in ("ب", "ل", "ك") and len(w) > 4:
            stack.append(w[1:]); out.add(w[1:])
        if len(w) > 4 and w.startswith("ال"):
            out.add(w[2:])
        if len(w) > 4 and w.startswith("لل"):
            out.add(w[2:])
    return out


def stem(tok):
    """A single key for comparing words (shortest variant that is still 3+ letters)."""
    v = [x for x in variants(tok) if len(x) >= 3]
    return min(v, key=len) if v else tok


def _merge(into, d):
    for k, v in d.items():
        if k.startswith("_"):
            continue
        if isinstance(v, list):
            into.setdefault(k, set()).update(normalize(x) for x in v)


_LEX = None


def lexicon():
    """All lexicon files merged: the pack's dialects first, then the user's own on top."""
    global _LEX
    if _LEX is not None:
        return _LEX
    lex = {}
    dirs = [os.path.join(HERE, "lexicon"), os.path.join(USER_DIR, "lexicon")]
    for d in dirs:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.endswith(".json"):
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    _merge(lex, json.load(fh))
    _LEX = lex
    return lex


def words_of(key):
    return lexicon().get(key, set())


def in_set(tok, key):
    """True when any clitic-stripped form of the token is in the lexicon set."""
    s = words_of(key)
    return any(v in s for v in variants(tok))


def count_words(toks, key):
    return sum(1 for t in toks if in_set(t, key))


def count_phrases(text_norm, key):
    """Multi-word entries (anything containing a space) matched on the normalised string."""
    n = 0
    for p in words_of(key):
        if " " in p:
            n += len(re.findall(r"(?<!\w)" + re.escape(p) + r"(?!\w)", text_norm))
    return n


def count_stems(toks, key):
    s = words_of(key)
    return sum(1 for t in toks if any(st in t for st in s))


def load_json_with_user(name):
    """Load a pack JSON file and merge a same-named list from the user dir (e.g. hooks)."""
    with open(os.path.join(HERE, name), encoding="utf-8") as fh:
        base = json.load(fh)
    extra = os.path.join(USER_DIR, name.replace(".json", "-extra.json"))
    if os.path.exists(extra):
        with open(extra, encoding="utf-8") as fh:
            more = json.load(fh)
        for k, v in more.items():
            if isinstance(v, list) and isinstance(base.get(k), list):
                base[k] = base[k] + v
    return base

