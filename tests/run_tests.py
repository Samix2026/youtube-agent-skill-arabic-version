#!/usr/bin/env python3
"""Run every test with: python3 tests/run_tests.py

No dependencies. Each check prints PASS or FAIL; the exit code is the number of failures.
"""
import importlib.util, io, json, os, subprocess, sys, contextlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SK = os.path.join(ROOT, "skills")
FX = os.path.join(ROOT, "tests", "fixtures")
os.environ["YOUTUBE_AR_HOME"] = os.path.join(ROOT, "tests", "no-user-dir")  # isolate from ~/.claude
sys.path.insert(0, os.path.join(SK, "yt-ar-script"))
sys.path.insert(0, os.path.join(SK, "yt-ar-edit"))

import arabic as ar  # noqa: E402
import hookscore  # noqa: E402
import deadair  # noqa: E402

FAILS = []


def check(name, cond, detail=""):
    print(("PASS  " if cond else "FAIL  ") + name + (f"   [{detail}]" if detail and not cond else ""))
    if not cond:
        FAILS.append(name)


def mod(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


def run(script, *args):
    r = subprocess.run([sys.executable, os.path.join(SK, script), *args, "--json"],
                       capture_output=True, text=True, env=os.environ)
    return json.loads(r.stdout)


# ---- arabic.py ------------------------------------------------------------------------------
check("normalize strips tashkeel, unifies alef/ta/ya, converts digits",
      ar.normalize("أَهْلاً بالمدرسةِ إلى ٣٠ يوماً؟") == "اهلا بالمدرسه الي 30 يوما?")
check("tokens returns Arabic words (the English original returned nothing)",
      ar.tokens("خسرت أربعين ألف ريال") == ["خسرت", "اربعين", "الف", "ريال"])
check("clitic stripping: والمشروع -> مشروع", ar.stem("والمشروع") == "مشروع")
check("root letters are not stripped: لازم stays لازم", ar.stem("لازم") == "لازم")
check("kaf suffix counts as address: مشروعك", hookscore._kaf_address("مشروعك"))
check("verbal noun is not address: استهلاك", not hookscore._kaf_address("استهلاك"))
check("excluded word is not address: كذلك", not hookscore._kaf_address(ar.normalize("كذلك")))

# ---- hookscore.py ---------------------------------------------------------------------------
def scores(fname):
    with open(os.path.join(ROOT, "tests", fname), encoding="utf-8") as fh:
        return [hookscore.score(l)[1] for l in fh.read().splitlines() if l.strip()]

strong, weak = scores("hooks_strong.txt"), scores("hooks_weak.txt")
ms, mw = sum(strong) / len(strong), sum(weak) / len(weak)
check(f"strong hooks average well above weak ({ms:.1f} vs {mw:.1f}, gap >= 15)", ms - mw >= 15)
check(f"no weak hook reaches WORKABLE (max {max(weak)})",
      all(hookscore.band(w) == "WEAK" for w in weak))
check("most strong hooks are WORKABLE or better",
      sum(hookscore.band(s) != "WEAK" for s in strong) / len(strong) >= 0.8)
check(f"every weak intro is below 50 (max {max(weak)})", max(weak) < 50)
sep = sum(1 for s in strong if s > max(weak)) / len(strong)
check(f"most strong hooks beat the best weak one ({sep:.0%} >= 70%)", sep >= 0.7)
greet = hookscore.score("السلام عليكم يا جماعة الخير، حياكم الله في قناتي")[0]
check("a greeting does not earn ADDRESS", greet["ADDRESS"] <= 26, greet["ADDRESS"])
check("question hook classified as السؤال",
      hookscore.score("ليش محلك يبيع زين وآخر الشهر ما يبقى شي؟")[2] == "السؤال")
check("warning hook classified as التحذير",
      hookscore.score("لا توقع عقد قبل ما تقرأ هالبند")[2] == "التحذير")
check("summary matches no formula",
      hookscore.score("في هذا الفيديو سنتحدث عن أهمية الموقع")[3] == 0)

# ---- title.py -------------------------------------------------------------------------------
title = mod(os.path.join(SK, "yt-ar-package", "title.py"), "title_ar")
r = title.check("كيف تختار موقع محلك قبل ما تخسر 40 ألف ريال؟", "الموقع يقتلك")
check("duplicate across title and thumb is caught through the article (موقع / الموقع)",
      any(k == "duplicate" for k, _ in r["issues"]))
r = title.check("كيف تختار موقع محلك قبل ما تخسر 40 ألف ريال؟", "لا تستعجل")
check("different thumb words pass", not any(k == "duplicate" for k, _ in r["issues"]))
r = title.check("أفضل طريقة رهيبة لاختيار موقع المحل التجاري الناجح والمثالي للمشروع الصغير")
kinds = {k for k, _ in r["issues"]}
check("long vague title flags length, vague and no-number",
      {"length", "vague", "no-number"} <= kinds, kinds)
r = title.check("5 أخطاء في ٣ أشهر")
check("mixed digit systems flagged", any(k == "digits" for k, _ in r["issues"]))
r = title.check("عنوان", "كلمة كلمتين ثلاث أربع")
check("four thumbnail words flagged", any(k == "thumb-length" for k, _ in r["issues"]))

# ---- deadair.py -----------------------------------------------------------------------------
d = run("yt-ar-edit/deadair.py", os.path.join(FX, "talk.srt"))
kinds = [c["kind"] for c in d["cuts"]]
check("finds 4 filler cues", kinds.count("FILLER") == 4, kinds)
check("finds the retake through an يعني in between", kinds.count("REPEAT") == 1, kinds)
check("finds 4 dead-air gaps", kinds.count("DEAD") == 4, kinds)
check("does not flag real speech as filler", deadair.filler_only("لا توقع عقد إيجار") is False)
check("elongated filler is caught: اممممممم", deadair.filler_only("اممممممم"))
check("multi-word filler is caught: خلني أقول يعني", deadair.filler_only("خلني أقول يعني"))
total = sum(c["end"] - c["start"] for c in d["cuts"])
check("overlapping cuts are not double counted", d["removed"] <= total + 1e-6)

# ---- chapters.py ----------------------------------------------------------------------------
c = run("yt-ar-chapters/chapters.py", os.path.join(FX, "talk.srt"), "--target", "4")
check("chapters valid by YouTube's rules", c["valid"], c)
check("first chapter at 0:00", c["chapters"][0]["label"] == "0:00")
check("every chapter at least 10s", all(x["seconds"] >= 10 for x in c["chapters"]))
check("draft titles are Arabic words, not empty",
      all(ar.is_arabic(x["draft_title"]) for x in c["chapters"]))

# ---- retention.py ---------------------------------------------------------------------------
t = run("yt-ar-retention/retention.py", os.path.join(FX, "retention.csv"), "--duration", "78",
        "--transcript", os.path.join(FX, "talk.srt"))
check("percent axis detected from header", t["axis"] == "percent")
check("hook leak measured as leaking", t["hook_verdict"] == "leaking", t["hook_leak"])
froms = sorted(x["from"] for x in t["cliffs"])
check("both mid-video cliffs found (40% and 75%)", 39 <= froms[0] <= 40 and 74 <= froms[-1] <= 75, froms)
check("cliff names what was said there", all(t["said"].get(str(x["from"])) for x in t["cliffs"]))

import tempfile
with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False) as fh:
    fh.write("\n".join(f"{x},{100 - x * 0.8 - (12 if x >= 30 else 0)}" for x in range(0, 58, 3)))
    short = fh.name
s = run("yt-ar-retention/retention.py", short, "--duration", "57")
check("a 57s Short exported in seconds, no header, is read as seconds", s["axis"] == "seconds", s["axis"])
check("its hook leak covers the first 30 seconds (36, not 7)", abs(s["hook_leak"] - 36) < 0.5, s["hook_leak"])
os.unlink(short)

print(f"\n{len(FAILS)} failed" if FAILS else "\nall passed")
sys.exit(len(FAILS))
