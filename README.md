<div dir="rtl">

# مهارة وكيل يوتيوب: النسخة العربية

مهارات لـ Claude تساعدك تصنع محتوى يوتيوب عربي، مع أدوات تقرأ العربية فعلا. مجانية، ترخيص MIT، بلا
تسجيل، بلا مفتاح API، وبلا أي ربط بحسابك.

هذه نسخة عربية من [youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) للمؤلف
Jake Schincariol. الفكرة والمنهج له، والحقوق محفوظة له حسب الترخيص. ما أضفناه هو أن الأدوات صارت تفهم
العربية.

**لماذا نسخة عربية وليست ترجمة؟** الأدوات الأصلية تقرأ الحروف اللاتينية فقط. أي نص عربي يمر عليها
يقرأ كنص فارغ، فتطلع الدرجات بلا معنى وبدون أي رسالة خطأ. هنا أعيد بناء طبقة اللغة: توحيد الكتابة،
وأل التعريف وحروف العطف والجر، ومعاجم للحشو والمخاطبة والرهان والفضول بالفصحى واللهجات، وإعادة
صياغة الصيغ الإحدى والعشرين لجمهور عربي.

**لا شيء ينشر قبل أن تنشره أنت.** المهارات تكتب، وأنت ترفع.

[English summary](#english)

## التثبيت

الصق هذا في Claude Code:

```
https://github.com/Samix2026/youtube-agent-skill-arabic-version

ثبت هذه المهارة، ثم تأكد أن /yt-ar-script يعمل.
```

أو يدويا:

```bash
git clone https://github.com/Samix2026/youtube-agent-skill-arabic-version.git
cp -r youtube-agent-skill-arabic-version/skills/yt-ar-* ~/.claude/skills/
```

أو كإضافة:

```
/plugin marketplace add Samix2026/youtube-agent-skill-arabic-version
/plugin install youtube-agent-ar
```

الأسماء تبدأ بـ `yt-ar-` حتى تعمل جنبا إلى جنب مع النسخة الإنجليزية بلا تعارض.

بعدها خذ عشر دقائق مع [`templates/voice.md`](templates/voice.md). انسخه إلى
`~/.claude/youtube-ar/voice.md` واملأه، أو أرسل لـ Claude ثلاثة من فيديوهاتك وقل: اكتب ملف
voice.md من هذه. كل المهارات تقرؤه.

## المهارات

| الأمر | ماذا يفعل |
| --- | --- |
| `/yt-ar-script` | فكرة إلى سكربت. خمس افتتاحيات من [21 صيغة](skills/yt-ar-script/hooks.json)، مقاسة، ثم السكربت المنطوق مع ما يظهر على الشاشة. |
| `/yt-ar-package` | العنوان والغلاف كزوج واحد، مفحوص للطول والقص على الجوال والتكرار والإبهام. |
| `/yt-ar-edit` | التفريغ إلى قائمة قص: السكتات، والحشو العربي، والإعادات، بالتوقيت. |
| `/yt-ar-chapters` | فصول من التفريغ، مطابقة لقواعد يوتيوب حتى تظهر. |
| `/yt-ar-retention` | ملف الاحتفاظ مقروء صح: تسرب الافتتاحية، السقوط الحاد، النزيف، وماذا تغير. |
| `/yt-ar-seo` | الوصف، والوسوم التي تستحق، والعبارات الثلاث التي يجب أن يكسبها الفيديو. |

## الأدوات الخمس

كلها تعمل على Python 3 بلا أي مكتبات إضافية. هي سبب أن هذه المهارات ليست مجرد أوامر.

```bash
python3 skills/yt-ar-script/hookscore.py --hook "سطر واحد"          # لوحة قياس الافتتاحية
python3 skills/yt-ar-package/title.py --title "..." --thumb "..."   # فحص العنوان والغلاف
python3 skills/yt-ar-edit/deadair.py transcript.srt                 # قائمة القص
python3 skills/yt-ar-chapters/chapters.py transcript.srt            # فصول صالحة
python3 skills/yt-ar-retention/retention.py retention.csv --duration 600
```

## الاختبارات

```bash
python3 tests/run_tests.py
```

ثمانية وثلاثون فحصا: توحيد الكتابة، وقياس 30 افتتاحية بين مكتوبة بعناية وأخرى تبدأ بالسلام والترحيب،
وكشف التكرار بين العنوان والغلاف عبر أل التعريف، والحشو الممطوط مثل اممممم، والإعادة التي بينها يعني،
وصلاحية الفصول، وسقوط الاحتفاظ في المنتصف، وقراءة ملف شورتس مصدر بالثواني.

## ما الذي تغير عن الأصل، غير اللغة

- **محور ملف الاحتفاظ**: الأصل يعتبر المحور نسبة كلما كانت أكبر قيمة 100 أو أقل، فيخطئ مع أي ملف مصدر
  بالثواني لفيديو أقصر من 100 ثانية، وهذا يعني أغلب الشورتس. هنا يقرأ رأس العمود، ويستدل من
  `--duration`، ويقبل `--axis`.
- **حساب المدة المحذوفة في قائمة القص**: إذا تداخلت توقيتات التفريغ، الأصل يحسب الجزء المتداخل مرتين.
  هنا يحسب مرة واحدة.
- **السقوط الحاد**: الأصل يدخل هبوط الافتتاحية في قائمة السقوط فيزاحم السقوط الحقيقي في المنتصف. هنا
  يحسب بعد نافذة الافتتاحية، لأن الافتتاحية لها بندها.
- **كلمات الغلاف**: الأصل يقول السقف ثلاث كلمات ويفحص أربعا. هنا ثلاث.

## الشروط الصغيرة

**مقياس الافتتاحية العربي استدلالي وغير معاير على أداء حقيقي.** الأصل معاير على 74 افتتاحية
إنجليزية. النسخة العربية مضبوطة على 30 افتتاحية اختبار كتبت لهذا الغرض، والحدود 58 و42 مستنتجة منها.
تفرق جيدا بين افتتاحية مكتوبة بعناية وأخرى تبدأ بحياكم الله في قناتي، ولا تتنبأ بالمشاهدات. الدرجة
المنخفضة سبب لإعادة النظر، والعالية ليست وعدا. إذا جمعت بيانات أداء فعلية، المعايرة أهم مساهمة ممكنة.

**المعاجم بداية لا نهاية.** الفصحى والخليجية أوسع، والمصرية والشامية بداية. اللهجة تؤثر على كشف
الحشو والمخاطبة بالذات.

**حدود الطول تقريبية.** يوتيوب يقص بالبكسل لا بعدد الحروف، والحروف العربية المتصلة تختلف في العرض.

**تصنيف الصيغة حكم على الكلمات، لا على النتيجة.** حين تقول الأداة إن العنوان استخدم صيغة الرقم الصادم،
هذا حكم على النص الظاهر، لا ادعاء عن سبب المشاهدات.

**الوسوم تأثيرها ضعيف** وهذه الحزمة تقول ذلك بدل أن تبيعك مولد وسوم.

**لا شيء يخترع رقما.** إذا احتاجت مهارة رقما ليس عندها، تسألك عنه أو تكتب الجملة بدونه.

## أضف لهجتك أو كلماتك

المعاجم في `skills/yt-ar-script/lexicon/` كملفات JSON، ملف لكل لهجة، تدمج كلها. لتضيف كلماتك
الخاصة بدون تعديل الحزمة، ضع ملف JSON بنفس المفاتيح في `~/.claude/youtube-ar/lexicon/`، وصيغ
افتتاحية إضافية في `~/.claude/youtube-ar/hooks-extra.json`. المساهمات في معاجم اللهجات مرحب بها.

## القادم

المرحلة الثانية: تحليل المنافسين بمقدار تفوق الفيديو على متوسط قناته، وتقطيع الفيديو الطويل إلى
مقاطع لشورتس وتيك توك وريلز، والرد على التعليقات، والخطة الأسبوعية، والتدقيق الشامل للقناة.

## الترخيص

MIT. استخدمه، عدله، انشره. مع الإبقاء على إشعار حقوق المؤلف الأصلي.

</div>

<div dir="ltr">

## English

An Arabic version of [youtube-agent-skill](https://github.com/Jakeschincariol/youtube-agent-skill) by
Jake Schincariol: Claude skills for making YouTube videos, with Python tools that actually read Arabic.

The original tools tokenise with `[a-z]`, so Arabic text comes out as zero words and every score is
meaningless, with no error. This version rebuilds the language layer: normalisation (diacritics,
hamza forms, ta marbuta, Arabic-Indic digits), clitic and article stripping, dialect lexicons (MSA and
Gulf, with Egyptian and Levantine starters) for filler, address, stakes and curiosity, and the 21 hook
formulas rewritten for Arabic audiences.

Six skills (`/yt-ar-script`, `/yt-ar-package`, `/yt-ar-edit`, `/yt-ar-chapters`, `/yt-ar-retention`,
`/yt-ar-seo`), five dependency-free tools, 38 tests (`python3 tests/run_tests.py`). Install:

```bash
git clone https://github.com/Samix2026/youtube-agent-skill-arabic-version.git
cp -r youtube-agent-skill-arabic-version/skills/yt-ar-* ~/.claude/skills/
```

The Arabic hook scorer is a heuristic, tuned on a 30-hook test set, not calibrated against real view
data. MIT, original copyright kept.

</div>
