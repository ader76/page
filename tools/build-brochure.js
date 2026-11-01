// Génère les brochures PDF (fr, en, zh, ar) à partir de public/assets/i18n.js
// Usage: NODE_PATH=$(npm root -g) node tools/build-brochure.js
const { chromium } = require('playwright');
const path = require('path'), fs = require('fs');
global.window = {};
const root = path.resolve(__dirname, '..', 'public');
require(path.join(root, 'assets/i18n.js'));
const I = window.I18N;
// Images allégées (JPEG 1500px) pour limiter le poids du PDF
const { execFileSync } = require('child_process');
const tmp = '/tmp/pdfimg';
if (!fs.existsSync(tmp)) { fs.mkdirSync(tmp); }
for (const f of fs.readdirSync(path.join(root, 'assets/img')).filter(x => x.endsWith('.webp'))) {
  execFileSync('python3', ['-I', '-c', "import sys;from PIL import Image;im=Image.open(sys.argv[1]).convert('RGB');im.thumbnail((1500,1500));im.save(sys.argv[2],'JPEG',quality=72,optimize=True)", path.join(root, 'assets/img', f), path.join(tmp, f)]);
}
const img = n => 'file://' + path.join(tmp, n);

const page = (l) => {
  const t = k => I[l][k] || I.fr[k];
  const dir = l === 'ar' ? 'rtl' : 'ltr';
  const font = l === 'zh' ? '"WenQuanYi Zen Hei","Noto Sans SC",sans-serif'
    : l === 'ar' ? '"Noto Naskh Arabic","DejaVu Sans",sans-serif' : '"DejaVu Serif",Georgia,serif';
  const ls = (l === 'ar' || l === 'zh') ? '0' : '.18em';
  const ul = ks => '<ul>' + ks.map(k => `<li>${t(k)}</li>`).join('') + '</ul>';
  const gal = ['villa', 'facade-entree', 'salon-1', 'salon-2', 'porche'];
  const galImg = { 'villa': 'villa.webp', 'facade-entree': 'facade-entree.webp', 'salon-1': 'salon-1.webp', 'salon-2': 'salon-2.webp', 'jardin': 'jardin.webp', 'porche': 'porche.webp' };
  return `<!doctype html><html lang="${l === 'zh' ? 'zh-Hans' : l}" dir="${dir}"><head><meta charset="utf-8"><style>
@page{size:A4;margin:0}
*{box-sizing:border-box}
body{margin:0;font-family:${font};color:#f3efe7;background:#06201a;font-size:10.5pt;line-height:1.65}
.pg{width:210mm;height:297mm;padding:16mm 16mm 14mm;page-break-after:always;position:relative;overflow:hidden;background:#06201a}
.pg:last-child{page-break-after:auto}
h1,h2,h3{font-weight:500;margin:0;line-height:1.25}
.eb{color:#c8a96a;font-size:8pt;letter-spacing:${ls};text-transform:uppercase;margin-bottom:6px}
h2{font-size:20pt;margin-bottom:10px}
h3{font-size:12pt;color:#e0c78f;margin-bottom:6px}
p{margin:0 0 8px;color:#cfd6d0}
ul{list-style:none;padding:0;margin:0}
li{position:relative;padding-inline-start:14px;margin-bottom:5px;color:#dedbd2;font-size:9.5pt}
li:before{content:"";position:absolute;inset-inline-start:0;top:.7em;width:7px;height:1px;background:#c8a96a}
.cover{padding:0}
.cover .im{height:176mm;background:url(${img('villa.webp')}) center/cover;position:relative}
.cover .im:after{content:"";position:absolute;inset:0;background:linear-gradient(180deg,rgba(6,32,26,.15),rgba(6,32,26,.55) 70%,#06201a)}
.cover .tx{position:absolute;inset-inline:16mm;top:104mm;z-index:2}
.cover .tx h1{font-size:30pt;margin:8px 0 12px}
.cover .tx p{font-size:12pt;max-width:150mm}
.brand{position:absolute;top:14mm;inset-inline-start:16mm;z-index:2;display:flex;align-items:center;gap:10px;color:#e0c78f;letter-spacing:.3em;font-size:10pt}
.brand i{display:grid;place-items:center;width:28px;height:28px;border:1px solid #c8a96a;font-style:normal;letter-spacing:0}
.facts{display:grid;grid-template-columns:repeat(5,1fr);margin:6mm 16mm 0;border:1px solid rgba(200,169,106,.35);background:#0a2b22}
.facts div{padding:11px 6px;text-align:center;border-inline-start:1px solid rgba(200,169,106,.3)}
.facts div:first-child{border:0}
.facts b{display:block;font-size:14pt;color:#e0c78f;font-weight:500}
.facts span{font-size:7pt;color:#a9bdb3;letter-spacing:${l==='ar'||l==='zh'?'0':'.08em'}}
.cols{display:grid;grid-template-columns:1fr 1fr;gap:10mm;margin-top:8px}
.box{background:#0d3328;border:1px solid rgba(200,169,106,.3);padding:10px 12px;margin-bottom:8px}
.map{width:100%;border:1px solid rgba(200,169,106,.3);margin-top:6px;display:block}
.g{display:grid;grid-template-columns:1fr 1fr;gap:6px;margin-top:8px}
.g img{width:100%;height:36mm;object-fit:cover;border:1px solid rgba(200,169,106,.3);display:block}
.g .w{grid-column:span 2}.g .w img{height:62mm}
.pj{display:grid;grid-template-columns:repeat(4,1fr);gap:6px;margin-top:6px}
.pj img{width:100%;height:24mm;object-fit:cover;display:block;border:1px solid rgba(200,169,106,.3)}
.pj h3{font-size:9pt;margin:5px 0 2px}.pj p{font-size:7.5pt;margin:0;line-height:1.45}
.ct{margin-top:8px;background:#0d3328;border:1px solid #c8a96a;padding:12px 16px;display:flex;justify-content:space-between;gap:12px;align-items:center}
.ct b{display:block;color:#e0c78f;font-size:13pt;font-weight:500;direction:ltr;unicode-bidi:embed}
.ct span{font-size:7.5pt;color:#a9bdb3}
.ft{position:absolute;bottom:8mm;inset-inline:16mm;display:flex;justify-content:space-between;font-size:7pt;color:#7f9a8e}
.wide{margin-bottom:6px}
</style></head><body>
<div class="pg cover"><div class="im"></div>
<div class="brand"><i>S</i>SOUISSI</div>
<div class="tx"><div class="eb">${t('hero.kicker')} · ${t('pdf.title')}</div><h1>${t('hero.title')}</h1><p>${t('hero.lead')}</p></div>
<div class="facts" style="margin-top:6mm">
<div><b dir="ltr">1 515 m²</b><span>${t('facts.area')}</span></div>
<div><b dir="ltr">70 %</b><span>${t('facts.cos')}</span></div>
<div><b dir="ltr">40 %</b><span>${t('facts.cus')}</span></div>
<div><b dir="ltr">2</b><span>${t('facts.basement')}</span></div>
<div><b>${t('facts.heightv')}</b><span>${t('facts.height')}</span></div></div>
<div style="padding:8mm 16mm"><p>${t('prop.intro')}</p></div>
<div class="ft"><span>Souissi · Rabat</span><span>1</span></div></div>

<div class="pg"><div class="eb">${t('prop.eyebrow')}</div><h2>${t('prop.title')}</h2>
<div class="cols"><div><div class="box"><h3>${t('prop.c1.t')}</h3>${ul(['prop.c1.1','prop.c1.2','prop.c1.3','prop.c1.4'])}</div>
<div class="box"><h3>${t('prop.c2.t')}</h3>${ul(['prop.c2.1','prop.c2.2','prop.c2.3','prop.c2.4'])}</div></div>
<div><div class="box"><h3>${t('prop.c3.t')}</h3>${ul(['prop.c3.1','prop.c3.2','prop.c3.3','prop.c3.4'])}</div>
<div class="box"><h3>${t('loc.title')}</h3><p style="font-size:9pt">${t('loc.intro')}</p>${ul(['loc.1','loc.2','loc.3','loc.4','loc.5'])}</div></div></div>
<img class="map" src="${img('carte.webp')}" style="height:78mm;object-fit:cover">
<div class="ft"><span>Souissi · Rabat</span><span>2</span></div></div>

<div class="pg"><div class="eb">${t('gal.eyebrow')}</div><h2>${t('gal.title')}</h2>
<div class="g">${gal.map((k,i)=>`<div class="${i===0?'w':''}"><img src="${img(galImg[k])}"></div>`).join('')}</div>
<div class="eb" style="margin-top:9mm">${t('proj.eyebrow')}</div>
<div class="pj">${[['bureaux','1'],['hotel','2'],['clinique','3'],['restaurant','4']].map(([f,n])=>`<div><img src="${img(f+'.webp')}"><h3>${t('proj.'+n+'.t')}</h3><p>${t('proj.'+n+'.d')}</p></div>`).join('')}</div>
<p style="font-size:7pt;color:#7f9a8e;margin-top:4px">${t('proj.note')}</p>
<div class="ct"><div><div class="eb" style="margin:0">${t('con.title')}</div><span>${t('con.intro')}</span></div>
<div><span>${t('con.phone')}</span><b>+212 661 247 505</b><span>${t('con.mail')}</span><b style="font-size:10pt">reda.bouaamri@gmail.com</b></div></div>
<div class="ft"><span>© ${new Date().getFullYear()} Souissi · ${t('foot.rights')}</span><span>3</span></div></div>
</body></html>`;
};

(async () => {
  const b = await chromium.launch(); fs.mkdirSync(path.join(root, 'assets/docs'), { recursive: true });
  for (const l of ['fr', 'en', 'zh', 'ar']) {
    const p = await b.newPage(); const f = `/tmp/brochure-${l}.html`;
    fs.writeFileSync(f, page(l)); await p.goto('file://' + f); await p.waitForTimeout(500);
    await p.pdf({ path: path.join(root, `assets/docs/brochure-${l}.pdf`), format: 'A4', printBackground: true, preferCSSPageSize: true });
    console.log('ok', l);
  }
  await b.close();
})();
