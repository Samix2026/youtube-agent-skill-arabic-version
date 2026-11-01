#!/usr/bin/env python3
"""title.py - فحص العنوان والغلاف كزوج واحد قبل النشر.

    python3 title.py --title "..." --thumb "الموقع يقتلك"
    python3 title.py titles.txt            # عنوان في كل سطر، مرتبة
    python3 title.py --title "..." --json

الوحدة هي الزوج وليس العنوان. غلاف يكرر كلمات العنوان يضيع نصف مساحة النقرة، وهذا أكثر خطأ يفحصه
هذا الملف.

الطول: يوتيوب يقص قرابة 60 حرفا في بحث سطح المكتب وقرابة 40 في الصفحة الرئيسية على الجوال، والحد
الأقصى 100. القص الفعلي بالبكسل وليس بعدد الحروف، والحروف العربية المتصلة أضيق غالبا من اللاتينية،
فاعتبر الرقمين تقريبيين.

Arabic port of title.py from Jake Schincariol's youtube-agent-skill (MIT).
"""
import json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yt-ar-script"))
import arabic as ar  # noqa: E402

DESKTOP, MOBILE, HARD = 60, 40, 100
THUMB_MAX = 3
EASTERN = re.compile(r"[٠-٩۰-۹]")
WESTERN = re.compile(r"[0-9]")
EMOJI = re.compile("[\U0001F300-\U0001FAFF☀-➿]")


def content(toks):
    stop = ar.words_of("stop")
    return {ar.stem(t) for t in toks if not ar.in_set(t, "stop") and t not in stop and len(t) > 1}


def check(title, thumb=None):
    t = title.strip()
    n = len(t)
    issues, good, notes = [], [], []
    toks = ar.tokens(t)
    tn = ar.normalize(t)
    if n > HARD:
        issues.append(("length", f"{n} حرف، والحد الأقصى في يوتيوب {HARD}"))
    elif n > DESKTOP:
        issues.append(("length", f"{n} حرف، وبحث سطح المكتب يقص قرابة {DESKTOP}"))
    else:
        good.append(f"{n} حرف، داخل حد سطح المكتب")
    if n > MOBILE:
        head = t[:MOBILE].rsplit(" ", 1)[0]
        issues.append(("mobile", f"الجوال يعرض تقريبا: {head}... تأكد أن الموضوع ما زال ظاهرا"))
    if ar.TASHKEEL.search(t):
        issues.append(("tashkeel", "فيه تشكيل: يزيد عدد الحروف ولا يضيف وضوحا في العنوان"))
    caps = [w for w in t.split() if len(w) > 2 and w.isupper() and w.isascii()]
    if len(caps) > 2:
        issues.append(("shouting", f"{len(caps)} كلمات لاتينية بحروف كبيرة، اثنتان هي السقف"))
    if len(EMOJI.findall(t)) > 1:
        issues.append(("emoji", "أكثر من رمز تعبيري واحد يجعل العنوان يبدو إعلانا"))
    v = sorted({x for x in toks if ar.in_set(x, "vague")} |
               {p for p in ar.words_of("vague") if " " in p and p in tn})
    if v:
        issues.append(("vague", f"{'، '.join(v)}: بدلها برقم أو اسم أو تاريخ"))
    nums = re.findall(r"[\d٠-٩۰-۹][\d٠-٩۰-۹,.٬]*%?٪?", t)
    words_num = [x for x in toks if ar.in_set(x, "number_words")]
    if nums or words_num:
        good.append(f"فيه رقم محدد ({'، '.join((nums + words_num)[:3])})")
    else:
        issues.append(("no-number", "لا رقم ولا تاريخ ولا اسم: هذا أكثر إصلاح موثوق"))
    if EASTERN.search(t) and WESTERN.search(t):
        issues.append(("digits", "يخلط الأرقام الهندية واللاتينية، اختر نوعا واحدا"))
    if t and (t[0].isascii() and t[0].isalnum()):
        notes.append("يبدأ برقم أو كلمة لاتينية: صيغة مقبولة، لكن راجع ترتيب العرض على الجوال لأن اتجاه النص قد ينقلب")
    if tn.rstrip().endswith("?"):
        good.append("سؤال مفتوح في العنوان")
    front = [w for w in toks[:3] if not ar.in_set(w, "stop") and not ar.in_set(w, "filler_hook")]
    if toks and not front:
        issues.append(("front-load", "أول ثلاث كلمات كلها حشو، قدّم الموضوع"))
    if thumb:
        shared = content(toks) & content(ar.tokens(thumb))
        if shared:
            issues.append(("duplicate", f"الغلاف يكرر العنوان في: {'، '.join(sorted(shared))}. "
                                        "الغلاف يقول ما لا يقوله العنوان"))
        else:
            good.append("الغلاف والعنوان بكلمات مختلفة")
        tw = len(ar.tokens(thumb))
        if tw > THUMB_MAX:
            issues.append(("thumb-length", f"{tw} كلمات على الغلاف، والسقف {THUMB_MAX} بحجم الجوال"))
    score = max(0, min(100, 100 - 14 * len(issues) + 4 * len(good)))
    return {"title": t, "chars": n, "score": score, "issues": issues, "good": good, "notes": notes}


def show(r):
    print(f"\n  {r['title']}")
    print(f"  {r['chars']} حرف   الدرجة {r['score']}/100")
    for k, m in r["issues"]:
        print(f"    x   {k:<12} {m}")
    for m in r["good"]:
        print(f"    ok               {m}")
    for m in r.get("notes", []):
        print(f"    ملاحظة           {m}")


def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    thumb = a[a.index("--thumb") + 1] if "--thumb" in a else None
    if "--title" in a:
        rows = [check(a[a.index("--title") + 1], thumb)]
    elif a and os.path.exists(a[0]):
        with open(a[0], encoding="utf-8") as fh:
            rows = [check(l, thumb) for l in fh.read().splitlines() if l.strip()]
    else:
        print(__doc__)
        sys.exit(1)
    rows.sort(key=lambda r: -r["score"])
    if as_json:
        print(json.dumps(rows, ensure_ascii=False, indent=1))
        return
    for r in rows:
        show(r)
    print()


if __name__ == "__main__":
    main()
