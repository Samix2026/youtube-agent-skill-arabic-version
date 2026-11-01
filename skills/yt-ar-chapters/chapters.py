#!/usr/bin/env python3
"""chapters.py - فصول يوتيوب من تفريغ نصي عربي بتوقيتات.

    python3 chapters.py transcript.srt            # أو .vtt أو whisper .json
    python3 chapters.py transcript.srt --target 8 --json

يطبع كتلة تلصقها في الوصف. قواعد يوتيوب مطبقة هنا لا مفترضة: القائمة تبدأ من 00:00، وفيها ثلاثة
فصول على الأقل، وكل فصل 10 ثوان على الأقل. كتلة تكسر أيا منها لا تتحول إلى فصول، بدون أي رسالة.

الحدود تأتي من السكتات التي أخذتها فعلا بين الأقسام، موزونة بطول السكتة ومدى تغير المفردات قبلها
وبعدها. العناوين كلمات الموضوع، وهي مسودة تعيد كتابتها بصوتك.

Arabic port of chapters.py from Jake Schincariol's youtube-agent-skill (MIT).
"""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "yt-ar-script"))
sys.path.insert(0, os.path.join(HERE, "..", "yt-ar-edit"))
import arabic as ar  # noqa: E402
from deadair import load, filler_only  # noqa: E402  (same parser, one implementation)

MIN = 10.0


def keywords(text):
    """Content stems of 3+ letters: الموقع and موقع count as one word."""
    out = []
    for t in ar.tokens(text):
        if ar.in_set(t, "stop") or ar.in_set(t, "filler_spoken") or t.isdigit():
            continue
        s = ar.stem(t)
        if len(s) >= 3:
            out.append(s)
    return out


def mmss(t):
    t = int(t)
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    target = int(a[a.index("--target") + 1]) if "--target" in a else 7
    a = [x for x in a if not x.startswith("--") and not x.isdigit()]
    if not a or not os.path.exists(a[0]):
        print(__doc__)
        sys.exit(1)
    cues = [c for c in load(a[0]) if not filler_only(c[2])]
    if len(cues) < 6:
        print("مقاطع قليلة جدا لتقسيمها إلى فصول")
        sys.exit(1)
    dur = cues[-1][1]
    cand = []
    for i in range(1, len(cues)):
        gap = cues[i][0] - cues[i - 1][1]
        kb = set(keywords(" ".join(c[2] for c in cues[max(0, i - 12):i])))
        ka = set(keywords(" ".join(c[2] for c in cues[i:i + 12])))
        shift = 1 - (len(kb & ka) / len(kb | ka)) if (kb | ka) else 0
        cand.append((gap * 1.6 + shift * 3.2, cues[i][0], i))
    cand.sort(reverse=True)
    picked = [0.0]
    for _, t, i in cand:
        if len(picked) >= target:
            break
        if all(abs(t - p) >= MIN for p in picked) and dur - t >= MIN:
            picked.append(t)
    picked.sort()
    chapters = []
    for n, t in enumerate(picked):
        end = picked[n + 1] if n + 1 < len(picked) else dur
        kw = keywords(" ".join(c[2] for c in cues if c[0] >= t and c[1] <= end))
        ranked = sorted(set(kw), key=lambda w: (-kw.count(w), kw.index(w)))
        title = " ".join(ranked[:3]) or "قسم"
        chapters.append({"start": round(t, 2), "label": mmss(t), "draft_title": title,
                         "seconds": round(end - t, 2)})
    ok = len(chapters) >= 3 and chapters[0]["start"] == 0 and all(c["seconds"] >= MIN for c in chapters)
    if as_json:
        print(json.dumps({"valid": ok, "chapters": chapters}, ensure_ascii=False, indent=1))
        return
    print()
    for c in chapters:
        print(f"  {c['label']} {c['draft_title']}")
    print(f"\n  {len(chapters)} فصول"
          f"{'' if ok else '  -- غير صالحة: يوتيوب يحتاج 3 فصول أو أكثر، وأول فصل 0:00، وكل فصل 10 ثوان على الأقل'}")
    print("  أعد كتابة كل سطر قبل اللصق. هذه كلمات الموضوع، لا كلماتك.\n")


if __name__ == "__main__":
    main()
