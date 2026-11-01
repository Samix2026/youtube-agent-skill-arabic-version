#!/usr/bin/env python3
"""hookscore.py - قياس افتتاحية فيديو عربية قبل أن تضيع عليها تصويرة.

خمس خصائص، كل واحدة من 0 إلى 100، والحكم النهائي 60% من المتوسط و40% من أضعف خاصية. الوزن
على الأضعف مقصود: افتتاحية فيها أربع خصائص قوية وواحدة ميتة تتسرب من الميتة، والمتوسط يخفي ذلك.

    python3 hookscore.py hooks.txt            # افتتاحية في كل سطر، مرتبة
    python3 hookscore.py --hook "سطر واحد"    # افتتاحية واحدة
    python3 hookscore.py --json hooks.txt     # مخرجات للآلة

ما يستطيع وما لا يستطيع: هذه النسخة العربية استدلالية وغير معايرة على بيانات أداء حقيقية بعد. تفرق
بين افتتاحية ضعيفة بوضوح وأخرى مكتوبة بعناية، ولا تتنبأ بالمشاهدات. الدرجة المنخفضة سبب لإعادة
النظر، والدرجة العالية ليست وعدا.

Arabic port of hookscore.py from Jake Schincariol's youtube-agent-skill (MIT).
"""
import json, os, re, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import arabic as ar  # noqa: E402

FORMULAS = ar.load_json_with_user("hooks.json")["hooks"]
for f in FORMULAS:
    f["_re"] = [re.compile(ar.normalize(p)) for p in f["match"]]

# Spoken Arabic packs more meaning per token than English (clitics glue on), so the 9-24 English
# band becomes 7-20 here. An assumption until calibrated: change it in one place.
BREVITY_LO, BREVITY_HI = 7, 20

LATIN = re.compile(r"^[a-z][a-z0-9]+$")
DIGIT = re.compile(r"\d")
PROHIBITIVE = re.compile(r"(?<!\w)(لا|ما) ت\w{2,}")


def _phr(tn, key):
    return ar.count_phrases(tn, key)


def concrete(toks):
    # a bare time unit is a bound (أقل من سنة), but اليوم/السنة with the article is usually
    # "today"/"the year", so only article-free units count
    units = sum(1 for t in toks if not t.startswith("ال") and ar.in_set(t, "units") and t != "%")
    return (sum(1 for t in toks if DIGIT.search(t)) + ar.count_words(toks, "number_words")
            + min(units, 1))


def specificity(text, toks, tn):
    if not toks:
        return 0
    nums = concrete(toks)
    vague = ar.count_words(toks, "vague") + _phr(tn, "vague")
    filler = ar.count_words(toks, "filler_hook") + _phr(tn, "filler_hook")
    s = 34 + min(nums, 3) * 22 - vague * 16 - filler * 5
    if any(ar.in_set(t, "units") for t in toks) and nums:
        s += 8
    # Arabic has no capital letters, so named things are approximated by Latin-script names
    # (tools, brands, platforms) which Arabic creators write in Latin.
    s += min(18, 6 * sum(1 for t in toks if LATIN.match(t)))
    return max(0, min(100, s))


def _kaf_address(tok):
    """A word ending in the second-person suffix -ك / -كم (مشروعك، فلوسكم)."""
    if ar.in_set(tok, "address_exclude") or ar.in_set(tok, "address_words"):
        return False
    w = tok
    if w.endswith("كم") and len(w) >= 4:
        return True
    if not w.endswith("ك") or len(w) < 4:
        return False
    # verbal nouns that happen to end in kaf: استهلاك، امتلاك، اشتراك، تفكيك، تحريك
    if w.endswith("اك") and len(w) >= 6:
        return False
    if w.startswith("ت") and w.endswith("يك") and len(w) == 5:
        return False
    return True


def _verb(tok):
    """Second-person verb, also with an object suffix: تحتاج -> تحتاجه، تعرف -> تعرفها."""
    if ar.in_set(tok, "address_verbs"):
        return True
    return any(len(v) >= 4 and " " not in v and tok.startswith(v) and len(tok) - len(v) <= 2
               for v in ar.words_of("address_verbs"))


def address_count(toks, tn):
    n = 0
    for t in toks:
        if ar.in_set(t, "address_words") or _verb(t) or _kaf_address(t):
            n += 1
    n += len(PROHIBITIVE.findall(tn))
    n += sum(1 for p in ar.words_of("address_verbs") if " " in p and p in tn)
    return n


def address(text, toks, tn):
    n = address_count(toks, tn)
    first = 30 if address_count(toks[:6], " ".join(toks[:6])) else 0
    return max(0, min(100, 26 + n * 20 + first))


def stakes(text, toks, tn):
    stems = ar.words_of("stakes_stems")
    n = 0
    for t in toks:
        if ar.in_set(t, "stakes_words") or any(s in t for s in stems if " " not in s):
            n += 1
    n += _phr(tn, "stakes_words") + sum(1 for s in stems if " " in s and s in tn)
    return max(0, min(100, 22 + n * 26 + (14 if concrete(toks) else 0)))


def curiosity(text, toks, tn):
    n = ar.count_words(toks, "curiosity_words") + _phr(tn, "curiosity_words")
    q = 18 if tn.strip().endswith("?") else 0
    closed = -18 if (ar.count_words(toks, "closers") or _phr(tn, "closers")) else 0
    return max(0, min(100, 24 + n * 17 + q + closed))


def brevity(text, toks, tn):
    n = len(toks)
    if n == 0:
        return 0
    if BREVITY_LO <= n <= BREVITY_HI:
        return 100
    if n < BREVITY_LO:
        return max(30, 100 - (BREVITY_LO - n) * 12)
    return max(10, 100 - (n - BREVITY_HI) * 8)


PROPS = [("SPECIFICITY", specificity), ("ADDRESS", address), ("STAKES", stakes),
         ("CURIOSITY", curiosity), ("BREVITY", brevity)]

LABEL = {"SPECIFICITY": "التحديد", "ADDRESS": "المخاطبة", "STAKES": "الرهان",
         "CURIOSITY": "الفضول", "BREVITY": "الإيجاز"}

FIX = {
    "SPECIFICITY": "بدل صفة واحدة برقم أو اسم أو تاريخ",
    "ADDRESS": "خاطب المشاهد في أول ست كلمات: انت، مشروعك، لا تفتح",
    "STAKES": "سمِّ وش يكلفه لو استمر على طريقته الحالية",
    "CURIOSITY": "احذف نصف الجملة اللي يجاوب نفسه، أو اختم بسؤال",
    "BREVITY": f"من {BREVITY_LO} إلى {BREVITY_HI} كلمة. اقرأها بصوتك ووقف وين ينقطع نفسك",
}


def classify(tn):
    best, hits = None, 0
    for f in FORMULAS:
        n = sum(1 for p in f["_re"] if p.search(tn))
        if n > hits:
            best, hits = f, n
    return (best["name"] if best else "بدون صيغة"), hits


def strip_intro(tn):
    """Remove greetings and channel-intro phrases. السلام عليكم contains a 'you' (عليكم) that is
    not addressing the viewer about anything, so it must not earn ADDRESS or CURIOSITY points."""
    out = tn
    for p in sorted(ar.words_of("filler_hook"), key=len, reverse=True):
        out = re.sub(r"(?<!\w)" + re.escape(p) + r"(?!\w)", " ", out)
    return out


def score(text):
    tn = ar.normalize(text)
    toks = ar.tokens(text)
    clean = strip_intro(tn)
    ctoks = ar.TOKEN.findall(clean)
    parts = {}
    for k, fn in PROPS:
        if k in ("SPECIFICITY", "BREVITY"):
            parts[k] = fn(text, toks, tn)
        else:
            parts[k] = fn(text, ctoks, clean)
    vals = list(parts.values())
    verdict = round(0.6 * (sum(vals) / len(vals)) + 0.4 * min(vals))
    name, hits = classify(tn)
    return parts, verdict, name, hits


# Provisional Arabic bands. The English original uses 72/55, calibrated on English hooks; Arabic
# scores sit lower because the lexicons are smaller than English's. These thresholds come from the
# 30-hook set in tests/ (every channel-intro opener scores under 42, carefully written hooks mostly
# above 50). They separate written-with-care from not, and say nothing about views.
STRONG_AT, WORKABLE_AT = 58, 42


def band(v):
    return "STRONG" if v >= STRONG_AT else "WORKABLE" if v >= WORKABLE_AT else "WEAK"


BAND_AR = {"STRONG": "قوية", "WORKABLE": "مقبولة", "WEAK": "ضعيفة"}


def report(t, parts, verdict, name, hits):
    print(f"\n  {t.strip()}")
    print("  " + "-" * 40)
    for k, v in parts.items():
        print(f"    {LABEL[k]:<9} {v:3d}  {'#' * (v // 5)}")
    print(f"    {'الحكم':<9} {verdict:3d}  {BAND_AR[band(verdict)]}")
    if hits:
        print(f"    الصيغة    {name}  ({hits} نمط)")
    else:
        print("    الصيغة    لا تطابق أي صيغة، وهذا غالبا ملخص وليس افتتاحية")
    low = min(parts, key=parts.get)
    print(f"    الأضعف    {LABEL[low]}: {FIX[low]}")


def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    if "--hook" in a:
        lines = [a[a.index("--hook") + 1]]
    elif a and os.path.exists(a[0]):
        with open(a[0], encoding="utf-8") as fh:
            lines = [l for l in fh.read().splitlines() if l.strip()]
    else:
        print(__doc__)
        sys.exit(1 if not a else 0)
    out = []
    for t in lines:
        parts, verdict, name, hits = score(t)
        out.append({"hook": t.strip(), "properties": parts, "verdict": verdict,
                    "band": band(verdict), "formula": name, "matched": hits})
    out.sort(key=lambda r: -r["verdict"])
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    for r in out:
        report(r["hook"], r["properties"], r["verdict"], r["formula"], r["matched"])
    if len(out) > 1:
        print(f"\n  الأقوى: {out[0]['hook']}  ({out[0]['verdict']}، {BAND_AR[out[0]['band']]})\n")


if __name__ == "__main__":
    main()
