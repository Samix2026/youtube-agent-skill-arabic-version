#!/usr/bin/env python3
"""deadair.py - قائمة قص (EDL) من تفريغ نصي بتوقيتات، لتسجيل عربي.

    python3 deadair.py transcript.srt            # أو .vtt أو whisper .json
    python3 deadair.py transcript.srt --floor 0.35 --json

يجد ثلاثة أشياء ويطبعها كقائمة قص:
  DEAD    سكتات بين المقاطع أطول من الحد
  FILLER  مقاطع كلها حشو: يعني، اممم، طيب، خلني أقول، وش اسمه
  REPEAT  جملة أعيدت: التصويرة الثانية لنفس البداية

ما لا يفعله: لا يقص الملف. يطبع القائمة والمدة المحذوفة والمدة النهائية، وتطبقها أنت في برنامج
المونتاج. لا يلمس أي ملف فيديو أو صوت.

Arabic port of deadair.py from Jake Schincariol's youtube-agent-skill (MIT).
"""
import json, os, re, sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yt-ar-script"))
import arabic as ar  # noqa: E402

ELONGATED = re.compile(r"(.)\1{2,}")


def parse_ts(s):
    s = s.strip().replace(",", ".")
    p = s.split(":")
    return int(p[0]) * 3600 + int(p[1]) * 60 + float(p[2]) if len(p) == 3 else int(p[0]) * 60 + float(p[1])


def load(path):
    with open(path, encoding="utf-8-sig", errors="replace") as fh:
        raw = fh.read()
    if path.endswith(".json"):
        d = json.loads(raw)
        segs = d.get("segments", []) if isinstance(d, dict) else d
        return [(float(s["start"]), float(s["end"]), (s.get("text") or "").strip()) for s in segs]
    cues, cur = [], None
    for line in raw.splitlines():
        m = re.match(r"\s*(\d[\d:.,]+)\s*-->\s*(\d[\d:.,]+)", line)
        if m:
            cur = [parse_ts(m.group(1)), parse_ts(m.group(2)), []]
            cues.append(cur)
        elif cur is not None and line.strip() and not line.strip().isdigit() \
                and not line.startswith("WEBVTT"):
            cur[2].append(line.strip())
    return [(a, b, " ".join(t)) for a, b, t in cues if t]


def _clean(t):
    return ELONGATED.sub(r"\1\1", ar.normalize(t))


_FILLERS = None


def _filler_re():
    global _FILLERS
    if _FILLERS is None:
        items = sorted({_clean(x) for x in ar.words_of("filler_spoken")}, key=len, reverse=True)
        _FILLERS = re.compile(r"(?<!\w)(" + "|".join(re.escape(x) for x in items) + r")(?!\w)")
    return _FILLERS


def filler_only(t):
    c = _clean(t)
    if not ar.TOKEN.findall(c):
        return False
    rest = _filler_re().sub(" ", c)
    return not ar.TOKEN.findall(rest)


def norm(t):
    """First words of a cue, fillers removed and clitics stripped, for retake comparison."""
    c = _filler_re().sub(" ", _clean(t))
    return [ar.stem(w) for w in ar.TOKEN.findall(c)]


def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    floor = float(a[a.index("--floor") + 1]) if "--floor" in a else 0.45
    a = [x for x in a if not x.startswith("--") and not re.match(r"^[\d.]+$", x)]
    if not a or not os.path.exists(a[0]):
        print(__doc__)
        sys.exit(1)
    cues = load(a[0])
    if not cues:
        print("لم أجد مقاطع. هل الملف srt أو vtt أو whisper json؟")
        sys.exit(1)
    dur = cues[-1][1]
    cuts = []
    for i, (s, e, t) in enumerate(cues):
        is_filler = filler_only(t)
        if is_filler:
            cuts.append({"kind": "FILLER", "start": s, "end": e, "why": t.strip()[:48]})
        if i:
            gap = s - cues[i - 1][1]
            if gap > floor:
                keep = floor / 2
                cuts.append({"kind": "DEAD", "start": round(cues[i - 1][1] + keep, 3),
                             "end": round(s - keep, 3), "why": f"سكتة {gap:.2f} ث"})
        # A restart is compared against the last cue that was actually SPEECH, so a retake with
        # "يعني" between the two attempts is still caught.
        if t.strip() and not is_filler:
            j = i - 1
            while j >= 0 and (filler_only(cues[j][2]) or not cues[j][2].strip()):
                j -= 1
            if j >= 0:
                a1, b1 = norm(cues[j][2])[:4], norm(t)[:4]
                if len(a1) >= 3 and a1 == b1:
                    cuts.append({"kind": "REPEAT", "start": cues[j][0], "end": cues[j][1],
                                 "why": "إعادة لـ: " + cues[j][2].strip()[:40]})
    cuts = [c for c in cuts if c["end"] > c["start"]]
    cuts.sort(key=lambda c: c["start"])
    # overlapping cuts (a FILLER cue next to a DEAD gap) must not be counted twice
    removed, last = 0.0, -1.0
    for c in cuts:
        st = max(c["start"], last)
        if c["end"] > st:
            removed += c["end"] - st
            last = c["end"]
    if as_json:
        print(json.dumps({"source": a[0], "duration": dur, "cuts": cuts,
                          "removed": round(removed, 3), "out": round(dur - removed, 3)},
                         ensure_ascii=False, indent=1))
        return
    print(f"\n  {a[0]}   المدة {dur:.2f} ث، {len(cues)} مقطع، حد السكتة {floor} ث\n")
    for c in cuts:
        print(f"    {c['kind']:<7} {c['start']:8.2f} -> {c['end']:8.2f}   {c['end']-c['start']:5.2f} ث   {c['why']}")
    print(f"\n  {len(cuts)} قص، يحذف {removed:.2f} ث، الناتج {dur - removed:.2f} ث "
          f"(أقصر بـ {removed / dur * 100:.1f}%)\n")
    print("  النسبة من الكلام فقط. إذا فيه عرض صامت طويل في الفيديو، راجعها على اللقطات قبل أن تثق بها.\n")


if __name__ == "__main__":
    main()
