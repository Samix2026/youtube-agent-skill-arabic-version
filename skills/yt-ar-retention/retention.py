#!/usr/bin/env python3
"""retention.py - قراءة ملف الاحتفاظ بالجمهور من YouTube Studio وتحديد أين يخرج المشاهدون.

    python3 retention.py retention.csv --duration 600
    python3 retention.py retention.csv --duration 600 --transcript transcript.srt
    python3 retention.py retention.csv --axis seconds      # إذا كان العمود الأول ثواني لا نسبة
    python3 retention.py retention.csv --json

تنزيل الملف: Studio ثم الفيديو ثم Analytics ثم Engagement ثم مخطط الاحتفاظ ثم أيقونة التنزيل.
عمودان: الموضع (نسبة أو ثوان) ونسبة من ما زال يشاهد.

ثلاث مشاكل مختلفة بثلاثة حلول مختلفة:
  HOOK LEAK   ما خسرته في أول 30 ثانية
  CLIFFS      سقوط حاد في لحظة محددة
  SLIDE       النزيف التدريجي في المنتصف

مع --transcript يطبع ما كنت تقوله عند كل سقوط، وهذه النسخة الوحيدة من التقرير التي تستطيع العمل
عليها دون أن تعيد مشاهدة الفيديو.

Arabic port of retention.py from Jake Schincariol's youtube-agent-skill (MIT). Changes: an --axis
override (the original guessed percent vs seconds from the largest value, which misreads any video
shorter than 100 seconds exported in seconds) and header-based axis detection.
"""
import csv, json, os, sys


def load_csv(path):
    rows, header = [], ""
    with open(path, newline="", encoding="utf-8-sig", errors="replace") as fh:
        for r in csv.reader(fh):
            nums = []
            for c in r:
                c = c.strip().replace("%", "").replace("٪", "").replace(",", "")
                try:
                    nums.append(float(c))
                except ValueError:
                    nums.append(None)
            vals = [n for n in nums if n is not None]
            if len(vals) >= 2:
                rows.append((vals[0], vals[1]))
            elif not rows:
                header += " ".join(r).lower()
    return rows, header


def detect_axis(xs, header, forced, dur=None):
    """--axis wins; then the header; then the duration (a seconds axis ends near the duration, a
    percent axis ends near 100); then the old max<=100 rule."""
    if forced:
        return forced.startswith("p")
    first = header.split(",")[0]
    if "%" in first or "percent" in header or "نسبة" in header:
        return True
    if "second" in header or "ثاني" in header or "time" in header:
        return False
    top = max(xs)
    if dur and dur < 99 and abs(top - dur) <= max(1.0, 0.03 * dur):
        return False
    return top <= 100.5


def main():
    a = sys.argv[1:]
    as_json = "--json" in a
    a = [x for x in a if x != "--json"]
    opt = lambda k: a[a.index(k) + 1] if k in a else None  # noqa: E731
    tr, dur_s, axis = opt("--transcript"), opt("--duration"), opt("--axis")
    skip = {tr, dur_s, axis}
    files = [x for x in a if not x.startswith("--") and x not in skip]
    if not files or not os.path.exists(files[0]):
        print(__doc__)
        sys.exit(1)
    rows, header = load_csv(files[0])
    if len(rows) < 8:
        print("لم أستطع قراءة 8 نقاط على الأقل من الملف")
        sys.exit(1)
    xs = [r[0] for r in rows]
    ys = [r[1] for r in rows]
    dur = float(dur_s) if dur_s else None
    pct_axis = detect_axis(xs, header, axis, dur)

    def at(x):
        return (x / 100.0 * dur) if (pct_axis and dur) else (x if not pct_axis else None)

    start = ys[0] or 100.0
    cutoff = 30.0 if not pct_axis else (30.0 / dur * 100 if dur else 10.0)
    hook_end = min((y for x, y in rows if x <= cutoff), default=start)
    hook_leak = start - hook_end
    drops = []
    for i in range(1, len(rows)):
        d = ys[i - 1] - ys[i]
        span = xs[i] - xs[i - 1] or 1
        drops.append((d / span, xs[i - 1], xs[i], d))
    by_rate = sorted(drops, reverse=True)
    cliffs = [{"from": round(x0, 2), "to": round(x1, 2), "lost": round(d, 2),
               "at_seconds": round(at(x0), 1) if at(x0) is not None else None}
              for _, x0, x1, d in [r for r in by_rate if r[1] >= cutoff][:5] if d > 0.8]
    # cliffs are counted after the hook window only: the opening is already reported as HOOK
    # LEAK, and letting it into this list (as the original did) crowds out the real mid-video drops
    mid = [rate for rate, x0, _, _ in drops if x0 > cutoff]
    slide = sum(mid) / len(mid) if mid else 0
    said = {}
    if tr and os.path.exists(tr):
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "yt-ar-edit"))
        from deadair import load as load_cues
        cues = load_cues(tr)
        for c in cliffs:
            if c["at_seconds"] is None:
                continue
            t = c["at_seconds"]
            near = [q[2] for q in cues if q[0] <= t + 4 and q[1] >= t - 4]
            said[str(c["from"])] = " ".join(near)[:140]
    verdict = "healthy" if hook_leak < 25 else "leaking" if hook_leak < 40 else "severe"
    out = {"points": len(rows), "axis": "percent" if pct_axis else "seconds", "start": start,
           "hook_leak": round(hook_leak, 2), "hook_verdict": verdict, "end": ys[-1],
           "cliffs": cliffs, "slide_per_unit": round(slide, 3), "said": said}
    if as_json:
        print(json.dumps(out, ensure_ascii=False, indent=1))
        return
    v_ar = {"healthy": "سليم", "leaking": "يتسرب", "severe": "حاد"}[verdict]
    unit = "نقطة مئوية" if pct_axis else "ثانية"
    print(f"\n  {files[0]}   {len(rows)} نقطة   {ys[0]:.1f}% -> {ys[-1]:.1f}%   المحور: {'نسبة' if pct_axis else 'ثواني'}\n")
    print(f"  تسرب الافتتاحية   {hook_leak:.1f}% خسرتها في البداية   [{v_ar}]")
    print("                    أقل من 25 سليم. أصلح السطر الأول قبل أي شيء آخر.\n")
    print("  السقوط الحاد       اللحظات التي خرج فيها الناس فعلا")
    for c in cliffs:
        where = f"{c['at_seconds']:.0f} ث" if c["at_seconds"] is not None else f"عند {c['from']}%"
        line = f"    -{c['lost']:5.1f}%  {where:>10}"
        if said.get(str(c["from"])):
            line += f"   {said[str(c['from'])]}"
        print(line)
    if not cliffs:
        print("    لا يوجد سقوط أحد من 0.8%: الخسارة كلها نزيف تدريجي لا لحظات")
    if any(c["at_seconds"] is None for c in cliffs):
        print("    أضف --duration بطول الفيديو بالثواني لتحويل النسب إلى توقيتات")
    print(f"\n  النزيف التدريجي   {slide:.3f}% لكل {unit} في المنتصف")
    print("                    النزيف المستوي إيقاع لا محتوى. قص من المنتصف، لا تعيد كتابته.\n")


if __name__ == "__main__":
    main()
