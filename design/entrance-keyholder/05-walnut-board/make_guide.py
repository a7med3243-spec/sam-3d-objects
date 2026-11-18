"""
Arabic print & assembly guide (PDF) and the single-file ZIP kit for the 30 cm walnut board.

Run after print_kit.py. Needs node + playwright (Chromium) for the PDF.
Output: 30cm/walnut_board_30cm_print_kit.zip  (plates, STLs, guide PDF, pictures)
"""

import base64
import json
import os
import subprocess
import sys
import tempfile
import zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
KIT = os.path.join(HERE, "30cm", "print_kit")
sys.path.insert(0, ROOT)
from common import kh  # noqa: E402

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("walnut", os.path.join(HERE, "build.py"))
_w = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_w)
CFG = _w.SIZES["30cm"]
CHANGE_Z = CFG["PANEL_BASE"] + CFG["REED_H"]                  # filament change height (mm)
HANG_MM = CFG["KEYHOLES"][1][0] - CFG["KEYHOLES"][0][0]        # distance between wall screws
N_SCREWS = len(CFG["SHELF_SCREWS_X"])
N_PINS = len(CFG["SEAM_DOWELS_Y"]) + 2


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def img(path, mime="image/jpeg"):
    return f"data:{mime};base64,{b64(path)}"


PLATE_AR = {
    "1_board_left": ("اللوح — النصف الأيسر", "بني / خشبي", ""),
    "2_board_right": ("اللوح — النصف الأيمن", "بني / خشبي", ""),
    "3_shelf": ("الرف — النصفان معاً", "بني / خشبي", ""),
    "4_panel_with_verse": ("اللوح الأبيض مع الآية — النصفان معاً", "أبيض + غامق",
                           f"بدون طابعة ألوان: اطبعه أبيض وغيّر إلى الخيط الغامق عند <b>{CHANGE_Z:.1f} مم</b>"),
    "5_knobs": ("المقابض × 6", "نحاسي / ذهبي", ""),
}


def html(data):
    fonts = os.path.join(ROOT, "fonts")
    rows = ""
    for p in data["plates"]:
        name, colour, note = PLATE_AR[p["plate"]]
        rows += (f"<tr><td class='n'>{p['plate'][0]}</td><td><code>{p['file']}</code></td><td>{name}</td>"
                 f"<td>{colour}</td><td class='n'>{p['grams']:.0f} غ</td><td class='n'><span class='ltr'>{p['time']}</span></td>"
                 f"<td>{note}</td></tr>")
    hero = img(os.path.join(ROOT, "renders", "05-walnut-board-30cm-hero.jpg"))
    verse = img(os.path.join(ROOT, "renders", "05-walnut-board-verse-detail.jpg"))
    expl = img(os.path.join(ROOT, "renders", "05-walnut-board-30cm-exploded.jpg"))
    plates = img(os.path.join(KIT, "plates_layout.png"), "image/png")
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8">
<style>
@font-face {{ font-family: Naskh; src: url(data:font/ttf;base64,{b64(os.path.join(fonts, 'NotoNaskhArabic-Regular-arabic.ttf'))}); }}
@font-face {{ font-family: Naskh; font-weight: bold; src: url(data:font/ttf;base64,{b64(os.path.join(fonts, 'NotoNaskhArabic-Bold-arabic.ttf'))}); }}
@font-face {{ font-family: Quran; src: url(data:font/ttf;base64,{b64(os.path.join(fonts, 'AmiriQuran-Regular-arabic.ttf'))}); }}
@page {{ size: A4; margin: 13mm 14mm; }}
* {{ box-sizing: border-box; }}
body {{ font-family: Naskh, sans-serif; color: #2b2420; font-size: 11.5pt; line-height: 1.75; margin: 0; }}
h1 {{ font-size: 21pt; margin: 0 0 2mm; color: #4a3424; }}
h2 {{ font-size: 14pt; margin: 6mm 0 2mm; color: #4a3424; border-bottom: 1.5px solid #c8a25a; padding-bottom: 1mm; }}
.sub {{ color: #7a6a5c; margin: 0 0 4mm; }}
img {{ width: 100%; border-radius: 6px; display: block; }}
.hero {{ height: 92mm; object-fit: cover; }}
.detail {{ height: 52mm; object-fit: cover; }}
.expl {{ height: 95mm; object-fit: cover; }}
.verse {{ font-family: Quran; font-size: 25pt; text-align: center; color: #2a1d16; margin: 2mm 0 1mm; line-height: 2.2; }}
.box {{ background: #f6f2ea; border-right: 4px solid #c8a25a; padding: 3mm 4mm; border-radius: 4px; margin: 3mm 0; }}
table {{ width: 100%; border-collapse: collapse; font-size: 10pt; margin: 2mm 0; }}
th, td {{ border: 1px solid #dcd3c6; padding: 1.4mm 2mm; vertical-align: top; text-align: right; }}
th {{ background: #efe8dc; }}
td.n {{ white-space: nowrap; text-align: center; }}
.ltr {{ direction: ltr; unicode-bidi: isolate; display: inline-block; }}
code {{ direction: ltr; unicode-bidi: embed; font-size: 8.5pt; }}
ol li {{ margin-bottom: 1.5mm; }}
.two {{ display: flex; gap: 4mm; }} .two > div {{ flex: 1; }}
.page {{ page-break-before: always; }}
.small {{ font-size: 9.5pt; color: #6b5d50; }}
</style></head><body>

<h1>حاملة المفاتيح الخشبية — مقاس 30 سم</h1>
<p class="sub">{CFG["W"]:.0f} × {CFG["H"]:.0f} مم · دليل الطباعة قطعة قطعة والتركيب · كل قطعة تدخل سرير 220 × 220 مم</p>
<img class="hero" src="{hero}">

<h2>الآية</h2>
<div class="verse">﴿{kh.VERSE_MUSHAF}﴾</div>
<p style="text-align:center;margin:0">سورة الضحى — الآية 5 · بخط النسخ القرآني (أميري قرآن) بلون غامق مع كامل التشكيل</p>
<div class="box">النص مطابق لرسم مصحف المدينة (رواية حفص). قورن حرفاً بحرف مع نصّين منشورين مستقلين للقرآن
(Tanzil و quran-json)، ويتطابقان في كل حرف وحركة. وراجعتُ كل النقاط والحركات في الرسم.
يُستحسن مطابقة القطعة المطبوعة بالمصحف قبل التعليق.</div>
<img class="detail" src="{verse}" style="margin-top:2mm">

<h2 class="page">ألواح الطباعة (5 طبعات)</h2>
<img src="{plates}">
<table><tr><th>#</th><th>الملف</th><th>المحتوى</th><th>اللون</th><th>الوزن</th><th>الوقت*</th><th>ملاحظة</th></tr>{rows}
<tr><th></th><th colspan="3">المجموع</th><th class="n">{data['total_grams']:.0f} غ</th><th class="n">≈ {data['total_hours']:.0f} ساعة</th><th></th></tr></table>
<p class="small">* الوزن والوقت من PrusaSlicer: طبقة 0.2 مم، 3 جدران، حشو 15% Gyroid، PLA. الوقت بسرعات الطابعات العادية؛
الطابعات السريعة (مثل Bambu) تحتاج تقريباً ثلثه. الوزن على الجدار بعد التركيب ≈ <b>{(data['total_grams'] + 10) / 1000:.2f} كغ</b> (مع البراغي).</p>

<h2>إعدادات الطباعة</h2>
<ul>
<li>PLA، فتحة 0.4 مم، طبقة 0.2 مم (وأول طبقة 0.2 مم حتى يقع تغيير اللون على حد طبقة).</li>
<li>3 جدران، 5 طبقات علوية و4 سفلية، حشو 15%. <b>بدون دعامات</b> لكل القطع.</li>
<li>كل قطعة محفوظة في وضعيتها الصحيحة: اللوح والرف واللوح الأبيض مستلقية، والمقابض واقفة على وجهها المسطّح.</li>
<li>لو تستخدم خيطاً خشبياً (Wood PLA) للّوح والرف: فتحة 0.6 مم أفضل لتجنّب الانسداد. اللوح الأبيض يبقى بفتحة 0.4 مم.</li>
<li>في ملفات 3MF الأجزاء مربوطة بخانات الخيوط (اللوح الأبيض: خانة 1 أبيض، خانة 2 الآية الغامقة). وملفات STL المنفصلة موجودة أيضاً في مجلد <code>stl</code>.</li>
</ul>

<h2 class="page">التركيب</h2>
<img class="expl" src="{expl}">
<div class="two"><div>
<p><b>تحتاج:</b> {N_PINS} قطع من خيط الطباعة 1.75 مم بطول 20 مم · {N_SCREWS} براغي M3 × 16 · برغيين 4 مم مع فيشر للجدار
(رأس البرغي حتى 9 مم) · غراء سيانو أو إيبوكسي · ورق صنفرة ناعم.</p>
</div></div>
<ol>
<li><b>اللوح:</b> أدخل 4 قطع خيط في الفتحات على حافة النصفين، ضع الغراء على الحافتين، واضغطهما معاً على سطح مستوٍ حتى يجف.</li>
<li><b>اللوح الأبيض والآية:</b> الصق النصفين في التجويف: «وَلَسَوۡفَ يُعۡطِيكَ» على اليمين و«رَبُّكَ فَتَرۡضَىٰٓ» على اليسار. خط الالتقاء يقع بين الكلمتين ولا يمر بأي حرف.</li>
<li><b>الرف:</b> اجمع نصفيه بقطعتي خيط وغراء، ثم ضعه فوق اللوح الأبيض وثبّته بـ {N_SCREWS} براغي M3 × 16 من خلف اللوح.</li>
<li><b>المقابض:</b> ضع نقطة غراء في كل فتحة (قطرها 8.4 مم) واضغط المقبض حتى يلمس اللوح.</li>
<li><b>التعليق:</b> برغيان في الجدار على نفس الارتفاع والمسافة بينهما <b>{HANG_MM:.0f} مم</b>. اترك 2.5 مم تحت رأس البرغي، علّق اللوح وأنزله 10 مم. شريط لاصق مزدوج صغير في الأسفل يمنع ارتفاعه عند سحب المفاتيح.</li>
</ol>
<div class="box">القطع الثلاث مقسومة في أماكن مختلفة (اللوح عند المنتصف، الرف 20 مم يمين المنتصف، اللوح الأبيض بين الكلمتين)،
فكل قطعة تغطي خط التقاء الأخرى وتشدّها. يمكن تعبئة خط الالتقاء في اللوح والرف بمعجون ثم صنفرته.</div>
<p class="small">المقاسات والأوزان من ملفات التصميم والسلايسر؛ التحمّل (الرف 2 كغ، المقبض 1 كغ) محسوب نظرياً ولم يُختبر على قطعة مطبوعة.</p>
</body></html>"""


PDF_JS = r"""
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const [src, out] = process.argv.slice(2);
  const browser = await chromium.launch();
  const page = await browser.newPage();
  await page.setContent(fs.readFileSync(src, 'utf8'), { waitUntil: 'load' });
  await page.evaluate(() => document.fonts.ready);
  await page.pdf({ path: out, format: 'A4', printBackground: true, preferCSSPageSize: true });
  await browser.close();
})();
"""


def make_pdf(html_text, out_pdf):
    with tempfile.TemporaryDirectory() as wd:
        src = os.path.join(wd, "guide.html")
        js = os.path.join(wd, "pdf.js")
        with open(src, "w", encoding="utf-8") as f:
            f.write(html_text)
        with open(js, "w") as f:
            f.write(PDF_JS)
        subprocess.run(["node", js, src, out_pdf], check=True, timeout=300)


STLS = ["board_left.stl", "board_right.stl", "shelf_left.stl", "shelf_right.stl",
        "panel_left_white_with_verse.stl", "panel_right_white_with_verse.stl",
        "mmu_panel_left_white.stl", "mmu_verse_left_dark.stl",
        "mmu_panel_right_white.stl", "mmu_verse_right_dark.stl", "knob.stl"]


if __name__ == "__main__":
    data = json.load(open(os.path.join(KIT, "plates.json")))
    pdf = os.path.join(KIT, "guide-ar.pdf")
    make_pdf(html(data), pdf)
    zpath = os.path.join(HERE, "30cm", "walnut_board_30cm_print_kit.zip")
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf, "walnut_board_30cm/guide-ar.pdf")
        for p in data["plates"]:
            z.write(os.path.join(KIT, p["file"]), f"walnut_board_30cm/{p['file']}")
        for s in STLS:
            z.write(os.path.join(HERE, "30cm", "stl", s), f"walnut_board_30cm/stl/{s}")
        z.write(os.path.join(KIT, "plates_layout.png"), "walnut_board_30cm/plates_layout.png")
        for r in ("05-walnut-board-30cm-hero.jpg", "05-walnut-board-30cm-exploded.jpg",
                  "05-walnut-board-verse-detail.jpg"):
            z.write(os.path.join(ROOT, "renders", r), f"walnut_board_30cm/pictures/{r}")
        z.write(os.path.join(HERE, "30cm", "weight.json"), "walnut_board_30cm/weight.json")
    print(zpath, os.path.getsize(zpath) // 1024, "KB")
    print(pdf, os.path.getsize(pdf) // 1024, "KB")
