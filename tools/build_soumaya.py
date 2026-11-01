#!/usr/bin/env python3
"""Génère public/index.html (multilingue FR/EN/ZH/AR) à partir du fichier
SOUMAYA 7 d'origine, sans modifier son design ni ses médias intégrés.

Usage : python3 -I tools/build_soumaya.py source/SOUMAYA_7_Dossier_Confidentiel.html public/index.html
"""
import json
import sys

SRC, DST = sys.argv[1], sys.argv[2]
html = open(SRC, encoding="utf-8").read()

T = {
    "title": ["SOUMAYA 7 | Dossier confidentiel · Lecture automatique", "SOUMAYA 7 | Confidential dossier", "SOUMAYA 7 | 机密投资资料", "SOUMAYA 7 | ملف سري"],
    "nav.dossier": ["Voir le dossier", "View the dossier", "查看资料", "عرض الملف"],
    "nav.pdf": ["Ouvrir le PDF", "Open the PDF", "打开 PDF", "فتح ملف PDF"],
    "kicker": ["Dossier acheteur confidentiel", "Confidential buyer dossier", "买方机密资料", "ملف المشتري السري"],
    "h1sub": ["Foncier commercial d’exception au cœur du quartier diplomatique de Souissi", "Exceptional commercial land in the heart of Souissi’s diplomatic district", "苏伊西外交使馆区核心的稀缺商业用地", "عقار تجاري استثنائي في قلب الحي الدبلوماسي بالسويسي"],
    "lead": ["Parcelle urbaine titrée de 1 515 m² en façade de l’Avenue Mehdi Ben Barka, classée en zone A, secteur A5, face au futur Intercontinental.",
             "A 1,515 m² titled urban plot fronting Avenue Mehdi Ben Barka, zoned A, sector A5, facing the future Intercontinental.",
             "已登记产权的 1,515 平方米城市地块,临 Mehdi Ben Barka 大道,规划为 A 区 A5 分区,正对未来的洲际酒店。",
             "قطعة أرضية حضرية محفّظة مساحتها 1515 م² تطل على شارع المهدي بن بركة، مصنّفة في المنطقة A، القطاع A5، قبالة فندق إنتركونتيننتال المستقبلي."],
    "cta.video": ["Voir la vidéo", "Watch the video", "观看视频", "شاهد الفيديو"],
    "cta.pages": ["Consulter les 10 pages", "View the 10 pages", "查看 10 页资料", "تصفّح الصفحات العشر"],
    "micro.1": ["Lecture hors ligne", "Offline reading", "支持离线阅读", "قراءة دون اتصال"],
    "micro.2": ["Vidéo intégrée", "Built-in video", "内嵌视频", "فيديو مدمج"],
    "micro.3": ["Dossier complet", "Complete dossier", "完整资料", "ملف كامل"],
    "conf": ["STRICTEMENT CONFIDENTIEL", "STRICTLY CONFIDENTIAL", "严格保密", "سري للغاية"],
    "b.auto": ["LECTURE AUTOMATIQUE", "AUTOPLAY", "自动播放", "تشغيل تلقائي"],
    "b.sound": ["VIDÉO AVEC SON", "VIDEO WITH SOUND", "有声播放", "فيديو مع الصوت"],
    "b.playing": ["VIDÉO EN LECTURE", "VIDEO PLAYING", "视频播放中", "الفيديو قيد التشغيل"],
    "b.preview": ["APERÇU EN LECTURE", "PREVIEW PLAYING", "预览播放中", "معاينة قيد التشغيل"],
    "b.loading": ["CHARGEMENT DU SON", "LOADING SOUND", "正在加载声音", "جارٍ تحميل الصوت"],
    "s.on": ["Activer le son", "Turn sound on", "开启声音", "تشغيل الصوت"],
    "s.off": ["Couper le son", "Mute", "静音", "كتم الصوت"],
    "st.1": ["Superficie titrée", "Titled area", "产权面积", "المساحة المحفّظة"],
    "st.2": ["Axe tertiaire", "Business corridor", "商务办公轴线", "محور الأنشطة الثالثية"],
    "st.3": ["Plancher hors œuvre", "Gross floor area", "建筑面积", "المساحة المبنية الإجمالية"],
    "st.4": ["Prix de présentation", "Asking price", "报价", "السعر المعروض"],
    "st.4v": ["24 M MAD", "MAD 24 M", "2,400 万迪拉姆", "24 مليون درهم"],
    "dos.h": ["Dossier acheteur", "Buyer dossier", "买方资料", "ملف المشتري"],
    "dos.p": ["Les dix pages du document sont directement intégrées ci-dessous. Elles restent visibles même lorsque l’ouverture du PDF est limitée par le téléphone.",
              "The ten pages of the document are embedded below (in French). They remain visible even when the phone restricts opening the PDF.",
              "以下直接展示文件的十页内容(法文版)。即使手机限制打开 PDF,也可正常查看。",
              "الصفحات العشر من الوثيقة مدمجة أدناه (باللغة الفرنسية). وتبقى ظاهرة حتى عندما يقيّد الهاتف فتح ملف PDF."],
    "dos.ref": ["Soumaya 7 · Référence SV7-2026", "Soumaya 7 · Reference SV7-2026", "Soumaya 7 · 编号 SV7-2026", "Soumaya 7 · المرجع SV7-2026"],
    "dos.note": ["Document autonome · aucune connexion Internet nécessaire", "Standalone document · no Internet connection required", "独立文件 · 无需联网", "وثيقة مستقلة · لا حاجة للاتصال بالإنترنت"],
    "dos.btn": ["Ouvrir / enregistrer le PDF", "Open / save the PDF", "打开 / 保存 PDF", "فتح / حفظ ملف PDF"],
    "page": ["Page {n} / 10", "Page {n} / 10", "第 {n} / 10 页", "الصفحة {n} / 10"],
    "gal.h": ["La villa en images", "The villa in pictures", "别墅实景", "الفيلا بالصور"],
    "gal.p": ["Photographies actuelles de la propriété : façade, entrée, salons et jardin arboré.", "Current photographs of the property: façade, entrance, reception rooms and landscaped garden.", "物业现状实拍:外立面、入口、客厅及园林花园。", "صور حالية للعقار: الواجهة والمدخل والصالونات والحديقة المشجّرة."],
    "gal.close": ["Fermer", "Close", "关闭", "إغلاق"],
    "g.villa": ["Façade de la villa", "Villa façade", "别墅外观", "واجهة الفيلا"],
    "g.facade": ["Entrée de la propriété", "Property entrance", "物业入口", "مدخل العقار"],
    "g.porche": ["Porche d’entrée", "Entrance porch", "入口门廊", "رواق المدخل"],
    "g.salon1": ["Grand salon", "Main reception room", "主客厅", "الصالون الكبير"],
    "g.salon2": ["Salon, plafonds ouvragés", "Reception room with ornate ceilings", "雕饰天花板客厅", "صالون بأسقف مزخرفة"],
    "g.salon3": ["Salon et baies vitrées", "Reception room and large windows", "客厅与落地窗", "الصالون والنوافذ الكبيرة"],
    "g.jardin": ["Jardin arboré", "Landscaped garden", "园林花园", "الحديقة المشجّرة"],
    "g.haie": ["Jardin et clôture sur rue", "Garden and street-side fence", "花园与临街围墙", "الحديقة والسياج المطل على الشارع"],
    "g.avenue": ["Avenue Mehdi Ben Barka", "Avenue Mehdi Ben Barka", "Mehdi Ben Barka 大道", "شارع المهدي بن بركة"],
    "foot": ["SOUMAYA 7 · Dossier d’investissement strictement confidentiel · Juin 2026", "SOUMAYA 7 · Strictly confidential investment dossier · June 2026", "SOUMAYA 7 · 严格保密投资资料 · 2026 年 6 月", "SOUMAYA 7 · ملف استثماري سري للغاية · يونيو 2026"],
    "pdf.alert": ["Le PDF est déjà visible page par page dans cette présentation.", "The PDF is already shown page by page in this presentation.", "PDF 已在本页面逐页展示。", "ملف PDF معروض بالفعل صفحةً صفحة في هذا العرض."],
    "lang": ["Langue", "Language", "语言", "اللغة"],
}
LANGS = ["fr", "en", "zh", "ar"]
DICT = {l: {k: v[i] for k, v in T.items()} for i, l in enumerate(LANGS)}


def sub(old, new, count=1):
    global html
    n = html.count(old)
    if n != count:
        raise SystemExit(f"Attendu {count} occurrence(s), trouvé {n} : {old[:80]!r}")
    html = html.replace(old, new)


# 1. Fonction de traduction, chargée avant tout autre script (pas de flash de langue)
head_js = """<script>
(function(){
  var D=%s, L=['fr','en','zh','ar'], l='fr';
  try{var q=new URLSearchParams(location.search).get('lang');var s=localStorage.getItem('s7lang');var n=(navigator.language||'fr').slice(0,2).toLowerCase();
    l=L.indexOf(q)>-1?q:(L.indexOf(s)>-1?s:(L.indexOf(n)>-1?n:'fr'));}catch(e){}
  window.S7L=l;
  window.S7T=function(k,n){var v=(D[window.S7L]&&D[window.S7L][k])||D.fr[k]||'';return n!=null?v.replace('{n}',n):v;};
  window.S7D=D;
  var h=document.documentElement;h.lang=l==='zh'?'zh-Hans':l;h.dir=l==='ar'?'rtl':'ltr';
})();
</script>
""" % json.dumps(DICT, ensure_ascii=False)
# Inséré après les balises meta/title/icon d'origine (viewport en premier, comme l'original)
_anchor = "<script>\ntry{if('scrollRestoration' in history)"
sub(_anchor, head_js + _anchor)

# 2. Styles additionnels : sélecteur de langue + ajustements RTL / chinois
extra_css = """
/* Sélecteur de langue */
.lang-switch{display:inline-flex;align-items:center;gap:2px;padding:3px;border-radius:999px;background:rgba(255,255,255,.06);border:1px solid rgba(255,255,255,.12)}
.lang-switch button{appearance:none;border:0;background:none;color:#b9c6d0;border-radius:999px;padding:8px 10px;font:700 12px/1 Inter,ui-sans-serif,system-ui,sans-serif;cursor:pointer}
.lang-switch button[aria-pressed=true]{background:linear-gradient(135deg,#e3c681,#c49b4d);color:#091522}
.lang-select{display:none;appearance:none;border:1px solid rgba(255,255,255,.14);background:rgba(255,255,255,.06);color:#fff;border-radius:999px;padding:10px 12px;font:700 13px/1 Inter,ui-sans-serif,system-ui,sans-serif}
.lang-select option{color:#071523}
.top-actions{align-items:center}
.poster-card:after{content:attr(data-conf)}
@media(max-width:760px){.lang-switch{display:none}.lang-select{display:inline-block}}
html[dir=rtl] .micro span:before{margin-right:0;margin-left:8px}
html[dir=rtl] .page-label{right:auto;left:12px}
html[dir=rtl] .autoplay-badge{left:auto;right:26px}
html[dir=rtl] .sound-toggle{right:auto;left:26px}
html[dir=rtl] .stat{border-right:0;border-left:1px solid rgba(255,255,255,.08)}
html[dir=rtl] .stat:last-child{border-left:0}
html[dir=rtl] h1{letter-spacing:0}
html[lang=ar] body{font-family:"Noto Naskh Arabic","Segoe UI",Tahoma,"Geeza Pro",Arial,sans-serif}
html[lang=zh-Hans] body{font-family:Inter,"PingFang SC","Hiragino Sans GB","Microsoft YaHei","Noto Sans SC",sans-serif}
html[lang=ar] .kicker,html[lang=zh-Hans] .kicker,html[lang=ar] .stat span,html[lang=zh-Hans] .stat span{letter-spacing:.04em}
html[lang=ar] h1 span,html[lang=ar] .lead{line-height:1.8}
/* Galerie photos de la villa */
.villa-gallery{padding:70px 0 80px}
.vg-grid{display:grid;grid-template-columns:repeat(4,1fr);grid-auto-rows:210px;gap:12px}
.vg-item{all:unset;position:relative;overflow:hidden;border-radius:16px;cursor:zoom-in;border:1px solid rgba(213,176,103,.24);box-shadow:var(--shadow);display:block}
.vg-item.big{grid-column:span 2;grid-row:span 2}
.vg-item.wide{grid-column:span 2}
.vg-item img{width:100%;height:100%;object-fit:cover;display:block;transition:transform .6s}
.vg-item:hover img{transform:scale(1.04)}
.vg-item span{position:absolute;left:10px;right:10px;bottom:10px;padding:7px 11px;border-radius:999px;background:rgba(5,16,28,.72);backdrop-filter:blur(8px);font-size:11px;font-weight:700;color:#f2d89d;text-align:center;opacity:0;transition:opacity .3s}
.vg-item:hover span,.vg-item:focus-visible span{opacity:1}
.vg-item:focus-visible{outline:2px solid var(--gold);outline-offset:3px}
.vg-box{border:0;padding:0;background:transparent;max-width:94vw;max-height:94vh;color:#fff}
.vg-box::backdrop{background:rgba(3,9,16,.92)}
.vg-box img{display:block;max-width:94vw;max-height:84vh;border-radius:14px}
.vg-box p{text-align:center;color:#d7e0e8;margin:12px 0 0;font-size:14px}
.vg-close{position:fixed;top:16px;right:16px;border:1px solid rgba(255,255,255,.3);background:rgba(5,16,28,.8);color:#fff;border-radius:999px;padding:10px 16px;font:700 13px/1 Inter,system-ui,sans-serif;cursor:pointer}
@media(max-width:900px){.vg-grid{grid-template-columns:repeat(2,1fr);grid-auto-rows:170px}.vg-item.big{grid-column:span 2;grid-row:span 1}}
@media(max-width:600px){.villa-gallery{padding:50px 0 56px}.vg-grid{grid-auto-rows:130px;gap:8px}.vg-item span{opacity:1;font-size:10px;padding:5px 8px}}
/* Héro plus compact : suppression de la hauteur plein écran et des grands vides */
.hero{min-height:0;padding:44px 0 40px;gap:44px}
@media(max-width:900px){.hero{padding-top:32px}}
@media(max-width:600px){.hero{padding:26px 0 32px;gap:24px}.hero-cta{margin-bottom:18px}}
"""
sub("</style>\n\n<script>\ntry { if ('scrollRestoration'", extra_css + "</style>\n\n<script>\ntry { if ('scrollRestoration'")

# 3. Textes marqués pour traduction
sub('onclick="document.getElementById(\'dossier\').scrollIntoView()">Voir le dossier</button>\n      <button class="btn btn-gold" type="button" onclick="openPdf()">Ouvrir le PDF</button>',
    'onclick="document.getElementById(\'dossier\').scrollIntoView()" data-i18n="nav.dossier">Voir le dossier</button>\n'
    '      <div class="lang-switch" role="group" data-i18n-aria="lang" aria-label="Langue">'
    '<button type="button" data-lang="fr" lang="fr">FR</button><button type="button" data-lang="en" lang="en">EN</button>'
    '<button type="button" data-lang="zh" lang="zh-Hans">中文</button><button type="button" data-lang="ar" lang="ar">عربي</button></div>\n'
    '      <select class="lang-select" data-i18n-aria="lang" aria-label="Langue"><option value="fr">FR</option><option value="en">EN</option><option value="zh">中文</option><option value="ar">عربي</option></select>\n'
    '      <button class="btn btn-gold" type="button" onclick="openPdf()" data-i18n="nav.pdf">Ouvrir le PDF</button>')
sub('<div class="kicker">Dossier acheteur confidentiel</div>', '<div class="kicker" data-i18n="kicker">Dossier acheteur confidentiel</div>')
sub('<h1>Soumaya 7<span>Foncier', '<h1>Soumaya 7<span data-i18n="h1sub">Foncier')
sub('<p class="lead">Parcelle', '<p class="lead" data-i18n="lead">Parcelle')
sub("block:'center'})\">Voir la vidéo</button>", "block:'center'})\" data-i18n=\"cta.video\">Voir la vidéo</button>")
sub('scrollIntoView()">Consulter les 12 pages</button>', 'scrollIntoView()" data-i18n="cta.pages">Consulter les 12 pages</button>')
sub('<div class="micro"><span>Lecture hors ligne</span><span>Vidéo intégrée</span><span>Dossier complet</span></div>',
    '<div class="micro"><span data-i18n="micro.1">Lecture hors ligne</span><span data-i18n="micro.2">Vidéo intégrée</span><span data-i18n="micro.3">Dossier complet</span></div>')
sub('<div class="poster-card autoplay-card" id="autoplayCard">', '<div class="poster-card autoplay-card" id="autoplayCard" data-conf="STRICTEMENT CONFIDENTIEL">')
sub('id="autoplayBadge">LECTURE AUTOMATIQUE</div>', 'id="autoplayBadge" data-i18n="b.auto">LECTURE AUTOMATIQUE</div>')
sub('aria-label="Activer le son">Activer le son</button>', 'data-i18n="s.on" data-i18n-aria="s.on" aria-label="Activer le son">Activer le son</button>')

# Textes posés par le script vidéo
sub("badge.textContent = 'APERÇU EN LECTURE';", "badge.textContent = S7T('b.preview');", 2)
sub("badge.textContent = v.dataset.audioLoaded === '1' ? 'VIDÉO AVEC SON' : 'VIDÉO EN LECTURE';",
    "badge.textContent = v.dataset.audioLoaded === '1' ? S7T('b.sound') : S7T('b.playing');")
sub("sound.textContent = 'Couper le son';", "sound.textContent = S7T('s.off');")
sub("badge.textContent = 'CHARGEMENT DU SON';", "badge.textContent = S7T('b.loading');")
sub("sound.textContent = v.muted ? 'Activer le son' : 'Couper le son';", "sound.textContent = v.muted ? S7T('s.on') : S7T('s.off');")
sub("alert('Le PDF est déjà visible page par page dans cette présentation.')", "alert(S7T('pdf.alert'))")

sub('<span>Superficie titrée</span>', '<span data-i18n="st.1">Superficie titrée</span>')
sub('<span>Axe tertiaire</span>', '<span data-i18n="st.2">Axe tertiaire</span>')
sub('<span>Plancher hors œuvre</span>', '<span data-i18n="st.3">Plancher hors œuvre</span>')
sub('<b>24 M MAD</b><span>Prix de présentation</span>', '<b data-i18n="st.4v">24 M MAD</b><span data-i18n="st.4">Prix de présentation</span>')
sub('<h2>Dossier acheteur</h2><p>Les douze', '<h2 data-i18n="dos.h">Dossier acheteur</h2><p data-i18n="dos.p">Les douze')
sub('<strong>Soumaya 7 · Référence SV7-2026</strong><div class="loading-note">',
    '<strong data-i18n="dos.ref">Soumaya 7 · Référence SV7-2026</strong><div class="loading-note" data-i18n="dos.note">')
sub('onclick="openPdf()">Ouvrir / enregistrer le PDF</button>', 'onclick="openPdf()" data-i18n="dos.btn">Ouvrir / enregistrer le PDF</button>')
for n in range(1, 13):
    sub(f'<div class="page-label">Page {n} / 12</div>', f'<div class="page-label" data-i18n-page="{n}">Page {n} / 12</div>')
sub('<h2>Visite et échange confidentiel</h2><p>', '<h2 data-i18n="con.h">Visite et échange confidentiel</h2><p data-i18n="con.p">')
sub('<footer><div class="shell">SOUMAYA 7', '<footer><div class="shell" data-i18n="foot">SOUMAYA 7')

# 4. Application de la langue + changement de langue
tail_js = """<script>
(function(){
  function apply(l){
    window.S7L=l;try{localStorage.setItem('s7lang',l)}catch(e){}
    var h=document.documentElement;h.lang=l==='zh'?'zh-Hans':l;h.dir=l==='ar'?'rtl':'ltr';
    document.title=S7T('title');
    document.querySelectorAll('[data-i18n]').forEach(function(el){el.textContent=S7T(el.getAttribute('data-i18n'));});
    document.querySelectorAll('[data-i18n-aria]').forEach(function(el){el.setAttribute('aria-label',S7T(el.getAttribute('data-i18n-aria')));});
    document.querySelectorAll('[data-i18n-page]').forEach(function(el){el.textContent=S7T('page',el.getAttribute('data-i18n-page'));});
    var card=document.getElementById('autoplayCard');if(card)card.setAttribute('data-conf',S7T('conf'));
    var v=document.getElementById('heroVideo'),b=document.getElementById('autoplayBadge'),s=document.getElementById('soundToggle');
    if(v&&b&&!v.paused&&card.classList.contains('video-ready'))b.textContent=v.dataset.audioLoaded==='1'?S7T('b.sound'):S7T('b.playing');
    if(v&&s&&v.dataset.audioLoaded==='1')s.textContent=v.muted?S7T('s.on'):S7T('s.off');
    document.querySelectorAll('.lang-switch button').forEach(function(x){x.setAttribute('aria-pressed',x.getAttribute('data-lang')===l);});
    var sel=document.querySelector('.lang-select');if(sel)sel.value=l;
  }
  document.querySelectorAll('.lang-switch button').forEach(function(x){x.addEventListener('click',function(){apply(x.getAttribute('data-lang'));});});
  var sel=document.querySelector('.lang-select');if(sel)sel.addEventListener('change',function(){apply(sel.value);});
  apply(window.S7L||'fr');
})();
</script>
"""
sub("</body>", tail_js + "</body>")

# --- Galerie photos de la villa (avant le dossier) ---
PHOTOS = [("villa", "villa.webp", "big"), ("facade", "facade-entree.webp", ""), ("porche", "porche.webp", ""),
          ("salon1", "salon-1.webp", ""), ("salon2", "salon-2.webp", ""), ("jardin", "jardin.webp", "wide"),
          ("salon3", "salon-3.webp", ""), ("haie", "jardin-haie.webp", "")]
items = "".join(
    f'<button type="button" class="vg-item {c}" data-k="g.{k}"><img src="assets/img/{f}" alt="" loading="lazy" decoding="async"><span data-i18n="g.{k}"></span></button>'
    for k, f, c in PHOTOS)
gallery = f"""<section class="villa-gallery" id="photos">
    <div class="shell">
      <div class="section-head"><h2 data-i18n="gal.h">La villa en images</h2><p data-i18n="gal.p"></p></div>
      <div class="vg-grid">{items}</div>
    </div>
  </section>
  <dialog class="vg-box" id="vgBox"><button type="button" class="vg-close" id="vgClose" data-i18n="gal.close">Fermer</button><img id="vgImg" alt=""><p id="vgCap"></p></dialog>

  """
sub('<section class="dossier" id="dossier">', gallery + '<section class="dossier" id="dossier">')
sub("</body>", """<script>
(function(){
  var box=document.getElementById('vgBox'),img=document.getElementById('vgImg'),cap=document.getElementById('vgCap');
  document.querySelectorAll('.vg-item').forEach(function(b){b.addEventListener('click',function(){
    img.src=b.querySelector('img').src;var t=S7T(b.getAttribute('data-k'));img.alt=t;cap.textContent=t;
    if(box.showModal)box.showModal();else box.setAttribute('open','');});});
  document.getElementById('vgClose').addEventListener('click',function(){box.close();});
  box.addEventListener('click',function(e){if(e.target===box)box.close();});
  document.querySelectorAll('.vg-item img').forEach(function(i){i.alt=S7T(i.parentNode.getAttribute('data-k'));});
})();
</script>
</body>""")

# --- Pages du dossier : retouches à partir des images d'origine ---
#  * coordonnées personnelles retirées (page 1 : ligne « Contact direct » ; page 9 : ligne « Contact »)
#  * page 6 (une seule ligne) fusionnée en bas de la page 5
#  * page 10 (titre seul) fusionnée avec le plan de la page 11
#  * pieds de page « Page N » effacés (la numérotation change)
#  * le PDF est reconstruit à partir de ces pages (aucun texte caché ne subsiste)
import base64, io, re
from PIL import Image

pages = {}
for m in re.finditer(r'<article class="pdf-page" id="page-(\d+)">\s*<div class="page-label"[^>]*>[^<]*</div>\s*<img src="data:image/webp;base64,([^"]+)"', html):
    pages[int(m.group(1))] = Image.open(io.BytesIO(base64.b64decode(m.group(2)))).convert("RGB")
assert sorted(pages) == list(range(1, 13))
W, H = pages[1].size
FOOT = (1675, 1715)   # bande du pied de page


def blank():
    return Image.new("RGB", (W, H), "white")


def clear_footer(im):
    im.paste((255, 255, 255), (0, FOOT[0], W, FOOT[1]))
    return im


def remove_band(im, y0, y1):
    """Supprime les lignes y0..y1 et remonte le contenu situé dessous."""
    out = blank()
    out.paste(im.crop((0, 0, W, y0)), (0, 0))
    out.paste(im.crop((0, y1, W, FOOT[0])), (0, y0))
    return out


def stack(parts, top, bottom, gap):
    """Empile des bandes d'images (réduites si besoin) sur une page blanche."""
    total = sum(p.height for p in parts) + gap * (len(parts) - 1)
    sc = min(1, (bottom - top) / total)
    out = blank()
    y = top
    for part in parts:
        if sc < 1:
            part = part.resize((int(W * sc), int(part.height * sc)), Image.LANCZOS)
        out.paste(part, ((W - part.width) // 2, y))
        y += part.height + int(gap * sc)
    return out


p1 = remove_band(pages[1], 1108, 1167)   # ligne de contact + site web
p9 = remove_band(pages[9], 609, 686)     # ligne « Contact » du tableau
p5 = stack([pages[5].crop((0, 120, W, 1640)), pages[6].crop((0, 122, W, 210))], top=120, bottom=1665, gap=10)
p10 = stack([pages[10].crop((0, 160, W, 275)), pages[11].crop((0, 120, W, 1615))], top=160, bottom=1665, gap=28)

final = [p1, pages[2], pages[3], pages[4], p5, pages[7], pages[8], p9, p10, pages[12]]
final = [clear_footer(im.copy()) for im in final]
N = len(final)


def enc(im):
    b = io.BytesIO()
    im.save(b, "WEBP", quality=88, method=6)
    return base64.b64encode(b.getvalue()).decode()


arts = []
for i, im in enumerate(final, 1):
    load = "eager" if i <= 2 else "lazy"
    arts.append(
        '<article class="pdf-page" id="page-%d">\n'
        '      <div class="page-label" data-i18n-page="%d">Page %d / %d</div>\n'
        '      <img src="data:image/webp;base64,%s" alt="Dossier acheteur Soumaya 7, page %d" loading="%s" decoding="async">\n'
        '    </article>' % (i, i, i, N, enc(im), i, load))
html, n = re.subn(r'<div class="pages">.*?</article></div>', lambda _: '<div class="pages">' + "\n".join(arts) + '</div>', html, count=1, flags=re.S)
assert n == 1

# PDF reconstruit à partir des pages retouchées
buf = io.BytesIO()
final[0].save(buf, "PDF", save_all=True, append_images=final[1:], resolution=150.0, quality=85)
m = re.search(r'<script id="pdf-b64" type="text/plain">([^<]+)</script>', html)
html = html.replace(m.group(1), base64.b64encode(buf.getvalue()).decode(), 1)

# --- Aucune coordonnée personnelle sur la page : section contact supprimée ---
html, n = re.subn(r'\s*<section class="contact" id="contact">.*?</section>', '', html, count=1, flags=re.S)
assert n == 1
for bad in ("reda.bouaamri", "661 247", "661247", "souissivilla.pro", "mailto:", "tel:"):
    assert bad not in html, bad

open(DST, "w", encoding="utf-8").write(html)
print("OK", DST, len(html))
