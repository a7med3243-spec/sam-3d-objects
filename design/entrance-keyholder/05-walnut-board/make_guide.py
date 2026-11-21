"""
Arabic print & assembly guide (PDF) and the single-file ZIP kit for the walnut board, either size
(Bambu Lab A2L: board + shelf + knobs in one strong piece, verse panel on its own).

Run after print_kit.py. Needs node + playwright (Chromium) for the PDF.
Usage:  python3 make_guide.py [30cm|small]
Output: <size>/walnut_board_<size>_print_kit.zip  (plates, STLs, guide PDF, pictures)
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
SIZE = sys.argv[1] if len(sys.argv) > 1 else "30cm"      # "30cm" or "small"
KIT = os.path.join(HERE, SIZE, "print_kit")
LABEL = {"30cm": "مقاس 30 سم", "small": "المقاس الصغير (21 سم)"}[SIZE]
HERO = f"05-walnut-board-{SIZE}-hero.jpg"
EXPLODED = f"05-walnut-board-{SIZE}-exploded.jpg"
DETAIL = {"30cm": "05-walnut-board-verse-detail.jpg", "small": "05-walnut-board-small-verse-detail.jpg"}[SIZE]
sys.path.insert(0, ROOT)
from common import kh  # noqa: E402

import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("walnut", os.path.join(HERE, "build.py"))
_w = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_w)
CFG = _w.SIZES[SIZE]
CHANGE_Z = CFG["PANEL_BASE"] + CFG["REED_H"]                  # filament change height (mm)
HANG_MM = CFG["KEYHOLES"][1][0] - CFG["KEYHOLES"][0][0]        # distance between wall screws
N_SCREWS = len(CFG["SHELF_SCREWS_X"])
PHONE_W = CFG["SHELF_D"] - CFG["COVE"] - CFG["LIP"] - 2.5          # flat depth behind the lip
_g = 9.81
# bending stress at the shelf root (MPa): 5 kg at mid-depth over the full width; 10 kg pressed on the
# front edge over ~150 mm of width; 2 kg hanging near the end of a knob neck (solid round section)
S_SHELF = 6 * (5 * _g * CFG["SHELF_D"] / 2) / (CFG["W"] * CFG["SHELF_T"] ** 2)
S_EDGE = 1.2 * 6 * (10 * _g * (CFG["SHELF_D"] - 3)) / (min(150.0, CFG["W"]) * CFG["SHELF_T"] ** 2)
S_KNOB = 1.2 * (2 * _g * (CFG["NECK_L"] - 1)) / (3.14159 * CFG["NECK_D"] ** 3 / 32)


def b64(path):
    with open(path, "rb") as f:
        return base64.b64encode(f.read()).decode()


def img(path, mime="image/jpeg"):
    return f"data:{mime};base64,{b64(path)}"


PLATE_AR = {
    "1_brown_main_board_shelf_knobs": ("اللوح + الرف + المقابض — قطعة واحدة", "بني",
                                       "خيط واحد · 4 جدران · حشو 15%"),
    "2_white_panel_dark_verse": ("قاعدة الآية (اللوح الأبيض مع الآية)", "أبيض ثم غامق",
                                 f"تبديل واحد فقط إلى الغامق عند <b>{CHANGE_Z:.1f} مم</b> · 2 جدار · حشو 10%"),
}


def html(data):
    fonts = os.path.join(ROOT, "fonts")
    rows = ""
    for p in data["plates"]:
        name, colour, note = PLATE_AR[p["plate"]]
        rows += (f"<tr><td class='n'>{p['plate'][0]}</td><td><code>{p['file']}</code></td><td>{name}</td>"
                 f"<td>{colour}</td><td class='n'>{p['grams']:.0f} غ</td><td class='n'><span class='ltr'>{p['time']}</span></td>"
                 f"<td>{note}</td></tr>")
    hero = img(os.path.join(ROOT, "renders", HERO))
    verse = img(os.path.join(ROOT, "renders", DETAIL))
    expl = img(os.path.join(ROOT, "renders", EXPLODED))
    plates = img(os.path.join(KIT, "plates_layout.png"), "image/png")
    section = img(os.path.join(KIT, "section.png"), "image/png")
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
.plates {{ height: 56mm; object-fit: contain; }}
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

<h1>حاملة المفاتيح الخشبية — {LABEL}</h1>
<p class="sub">{CFG["W"]:.0f} × {CFG["H"]:.0f} مم · لطابعة Bambu Lab A2L (سرير 330 × 320 مم) · كل قطعة كاملة بدون تقطيع · ملف لكل لون</p>
<img class="hero" src="{hero}">

<h2>الآية</h2>
<div class="verse">﴿{kh.VERSE_MUSHAF}﴾</div>
<p style="text-align:center;margin:0">سورة الضحى — الآية 5 · بخط النسخ القرآني (أميري قرآن) بلون غامق مع كامل التشكيل</p>
<div class="box">النص مطابق لرسم مصحف المدينة (رواية حفص). قورن حرفاً بحرف مع نصّين منشورين مستقلين للقرآن
(Tanzil و quran-json)، ويتطابقان في كل حرف وحركة. وراجعتُ كل النقاط والحركات في الرسم.
يُستحسن مطابقة القطعة المطبوعة بالمصحف قبل التعليق.</div>
<img class="detail" src="{verse}" style="margin-top:2mm">

<h2 class="page">ملفات الطباعة — ملف لكل لون (طبعتان)</h2>
<img class="plates" src="{plates}">
<table><tr><th>#</th><th>الملف</th><th>المحتوى</th><th>اللون</th><th>الوزن</th><th>الوقت*</th><th>ملاحظة</th></tr>{rows}
<tr><th></th><th colspan="3">المجموع</th><th class="n">{data['total_grams']:.0f} غ</th><th class="n">≈ {data['total_hours']:.0f} ساعة</th><th></th></tr></table>
<p class="small">* الوزن من PrusaSlicer (طبقة 0.2 مم، PLA، حشو Gyroid) بالإعدادات المكتوبة في الجدول. الوقت تقدير بسرعات قريبة من Bambu
وقد يختلف قليلاً في Bambu Studio. وزن القطعة على الجدار ≈ <b>{data['total_grams'] / 1000:.2f} كغ</b>.</p>
<div class="box">اللوح والرف والمقابض <b>قطعة واحدة جاهزة</b> — بدون براغي ولا تركيب، وقاعدة الآية فقط تُطبع لحالها وتُلصق.
كل طبعة بخيط واحد؛ التبديل الوحيد في الطبعة 2 عند {CHANGE_Z:.1f} مم (كل ما فوقه هو الآية) — أقل هدر ممكن.</div>

<h2>إعدادات الطباعة للقوة</h2>
<ul>
<li><b>الطبعة 1 (القطعة البنية):</b> 4 جدران، 4 طبقات علوية و4 سفلية، حشو 15% Gyroid، طبقة 0.2 مم، بدون دعامات — تُطبع على ظهرها والرف والمقابض للأعلى.
القوة تأتي من الجدران عند جذر الرف والمقابض، فالحشو القليل يوفّر الخيط بدون ما يضعفها.</li>
<li><b>الطبعة 2 (قاعدة الآية):</b> 2 جدار وحشو 10% تكفي لأنها لا تحمل وزناً.</li>
<li><b>للقوة:</b> PLA أو PLA+ بني عادي أقوى من الخيط الخشبي، وحرارة الفوهة حوالي 220° مع تبريد أقل يقوّي التصاق الطبقات عند جذر الرف والمقابض.</li>
<li><b>الطبعة 2 في Bambu Studio:</b> مع AMS lite اجعل الجزء الأبيض على خانة الأبيض والآية على خانة الغامق.
بدون AMS: في المعاينة (<span class='ltr'>Preview</span>) اذهب إلى الطبقة عند {CHANGE_Z:.1f} مم واضغط «+» واختر <span class='ltr'>Change filament</span> ثم الغامق.</li>
</ul>

<h2 class="page">القوة والتحمّل</h2>
<img src="{section}" style="height:62mm;object-fit:contain">
<ul>
<li><b>بدون براغي:</b> القوة من الشكل نفسه. الرف سماكته {CFG["SHELF_T"]:.0f} مم وعمقه {CFG["SHELF_D"]:.0f} مم، وجذره مدوّر بنصف قطر {CFG["COVE"]:.0f} مم فوقه حتى لا يتركّز الضغط في زاوية حادة،
وحافته الأمامية {CFG["LIP"]:.0f} مم تمسك الجوال (تتسع لجوال عرضه حتى {PHONE_W:.0f} مم وهو مسطّح).</li>
<li><b>المقابض:</b> رقبة سماكتها {CFG["NECK_D"]:.0f} مم وقاعدة مخروطية عريضة مطبوعة مع اللوح، ورأس {CFG["CAP_D"]:.0f} مم يمسك حلقة المفاتيح.</li>
<li><b>الحساب النظري:</b> 5 كغ على الرف ≈ {S_SHELF:.1f} ميجاباسكال عند الجذر · ضغط 10 كغ على الحافة الأمامية ≈ {S_EDGE:.0f} ميجاباسكال ·
2 كغ على مقبض ≈ {S_KNOB:.0f} ميجاباسكال — وقوة التصاق طبقات PLA الجيدة 15–25 ميجاباسكال، أي أمان 4–5 مرات أو أكثر.</li>
<li><b>الاستخدام المقترح:</b> الرف حتى 5 كغ (جوال، محفظة، نبتة صغيرة)، وكل مقبض حتى 2 كغ (مفاتيح وحقيبة صغيرة).
للتعليق استخدم فيشر مناسبة للجدار لا تقل عن 10 كغ لكل برغي.</li>
</ul>

<h2 class="page">التركيب</h2>
<img src="{expl}" style="height:100mm;object-fit:contain;background:#ece8e1">
<p><b>تحتاج فقط:</b> غراء سيانو أو إيبوكسي لقاعدة الآية · برغيين 4 مم مع فيشر للتعليق على الجدار (رأس البرغي حتى 9 مم).</p>
<ol>
<li><b>قاعدة الآية:</b> ضع الغراء في التجويف واضغط اللوح الأبيض فيه حتى يستوي تحت الرف.</li>
<li><b>التعليق:</b> برغيان في الجدار على نفس الارتفاع والمسافة بينهما <b>{HANG_MM:.0f} مم</b>. اترك 2.5 مم تحت رأس البرغي، علّق القطعة وأنزلها 10 مم. شريط لاصق مزدوج صغير في الأسفل يمنع ارتفاعها عند سحب المفاتيح.</li>
</ol>
<div class="box">ملفات 3MF جرّبتها في PrusaSlicer. لو ما ظهرت الأجزاء بألوانها في Bambu Studio، استخدم ملفات <code>stl</code>:
<code>main_brown_board_shelf_knobs.stl</code> للبني، و<code>panel_white_with_verse.stl</code> مع تغيير الخيط عند {CHANGE_Z:.1f} مم.</div>
<p class="small">المقاسات والأوزان من ملفات التصميم والسلايسر؛ التحمّل محسوب نظرياً ولم يُختبر على قطعة مطبوعة.</p>
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


STLS = ["main_brown_board_shelf_knobs.stl", "panel_white_with_verse.stl",
        "mmu_panel_white.stl", "mmu_verse_dark.stl"]


if __name__ == "__main__":
    data = json.load(open(os.path.join(KIT, "plates.json")))
    pdf = os.path.join(KIT, "guide-ar.pdf")
    make_pdf(html(data), pdf)
    zpath = os.path.join(HERE, SIZE, f"walnut_board_{SIZE}_print_kit.zip")
    top = f"walnut_board_{SIZE}"
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED) as z:
        z.write(pdf, f"{top}/guide-ar.pdf")
        for p in data["plates"]:
            z.write(os.path.join(KIT, p["file"]), f"{top}/{p['file']}")
        for s in STLS:
            z.write(os.path.join(HERE, SIZE, "stl", s), f"{top}/stl/{s}")
        z.write(os.path.join(KIT, "plates_layout.png"), f"{top}/plates_layout.png")
        z.write(os.path.join(KIT, "section.png"), f"{top}/pictures/section.png")
        for r in (HERO, EXPLODED, DETAIL):
            z.write(os.path.join(ROOT, "renders", r), f"{top}/pictures/{r}")
        z.write(os.path.join(HERE, SIZE, "weight.json"), f"{top}/weight.json")
    print(zpath, os.path.getsize(zpath) // 1024, "KB")
    print(pdf, os.path.getsize(pdf) // 1024, "KB")
