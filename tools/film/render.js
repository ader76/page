// Rend le film SOUMAYA 7 en MP4 (1920×1080, 25 i/s) pour une ou plusieurs langues.
//
// Préparation (une fois) — images de la vidéo source, ralenties par interpolation :
//   ffmpeg -i transformation_9x16.mp4 -vf "crop=720:320:0:480,minterpolate=fps=75:mi_mode=mci:mc_mode=aobmc:me_mode=bidir:vsbmc=1,scale=1170:520:flags=lanczos" -q:v 3 /tmp/film/frames/f%04d.jpg
// Utilisation :
//   NODE_PATH=$(npm root -g) node tools/film/render.js --frames /tmp/film/frames --audio src.mp4 --out public/assets/video fr en zh ar
//   --test 2,8,20 : n'écrit que des captures PNG aux instants donnés (contrôle visuel)
const { chromium } = require('playwright');
const { execFileSync } = require('child_process');
const fs = require('fs'), path = require('path');

const args = process.argv.slice(2);
const opt = (k, d) => { const i = args.indexOf(k); if (i < 0) return d; const v = args[i + 1]; args.splice(i, 2); return v; };
const FRAMES = opt('--frames', '/tmp/film/frames');
const AUDIO = opt('--audio', null);
const OUT = opt('--out', 'public/assets/video');
const TEST = opt('--test', null);
const FRESH = args.includes('--fresh') && args.splice(args.indexOf('--fresh'), 1);
const FPS = 25;
const langs = args.length ? args : ['fr', 'en', 'zh', 'ar'];
const page = 'file://' + path.resolve(__dirname, 'film.html');

async function renderLang(browser, lang) {
  const p = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  await p.goto(`${page}?lang=${lang}&frames=${encodeURIComponent(FRAMES)}`);
  await p.evaluate(() => document.fonts.ready);
  const total = await p.evaluate(() => window.FILM_TOTAL);
  if (TEST) {
    for (const t of TEST.split(',').map(Number)) {
      await p.evaluate(t => window.render(t), t);
      await p.screenshot({ path: `/tmp/film/test-${lang}-${t}.png` });
    }
    await p.close(); return;
  }
  // Les images déjà rendues sont réutilisées (reprise après interruption) ; --fresh pour tout refaire
  const dir = `/tmp/film/out-${lang}`;
  if (FRESH) fs.rmSync(dir, { recursive: true, force: true });
  fs.mkdirSync(dir, { recursive: true });
  const n = Math.round(total * FPS);
  for (let i = 0; i < n; i++) {
    const file = `${dir}/${String(i).padStart(5, '0')}.jpg`;
    if (fs.existsSync(file)) continue;
    for (let attempt = 1; ; attempt++) {
      try {
        await p.evaluate(t => window.render(t), i / FPS);
        await p.screenshot({ path: file, type: 'jpeg', quality: 92, timeout: 120000 });
        break;
      } catch (e) {
        if (attempt >= 3) throw e;
        console.log(lang, 'nouvel essai image', i);
      }
    }
    if (i % 250 === 0) console.log(lang, i, '/', n);
  }
  await p.close();
  fs.mkdirSync(OUT, { recursive: true });
  const out = path.join(OUT, `presentation-soumaya7-${lang}.mp4`);
  const a = ['-v', 'error', '-y', '-framerate', String(FPS), '-i', `${dir}/%05d.jpg`];
  if (AUDIO) {
    // musique d'origine bouclée en fondu, fondus d'entrée et de sortie
    a.push('-stream_loop', '4', '-i', AUDIO, '-filter_complex',
      `[1:a]atrim=0:${total},afade=t=in:d=1.2,afade=t=out:st=${(total - 2.5).toFixed(2)}:d=2.5,volume=0.85[a]`, '-map', '0:v', '-map', '[a]', '-c:a', 'aac', '-b:a', '128k');
  }
  a.push('-c:v', 'libx264', '-preset', 'slow', '-crf', '21', '-pix_fmt', 'yuv420p', '-movflags', '+faststart', '-t', String(total), out);
  execFileSync('ffmpeg', a);
  console.log('OK', out);
}

(async () => {
  const browser = await chromium.launch();
  for (const l of langs) await renderLang(browser, l);   // une langue à la fois (plus fiable)
  await browser.close();
})();
