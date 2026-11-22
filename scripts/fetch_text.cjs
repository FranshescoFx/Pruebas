// Vuelca el texto visible de páginas web (JS incluido) a raw/*.txt. Uso: node scripts/fetch_text.cjs URL... (requiere playwright)
const { chromium } = require('playwright');
const fs = require('fs');
(async () => {
  const urls = process.argv.slice(2);
  const b = await chromium.launch();
  const ctx = await b.newContext({ userAgent: 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/124 Safari/537.36', locale: 'es-SV' });
  for (const u of urls) {
    const p = await ctx.newPage();
    try {
      await p.goto(u, { waitUntil: 'domcontentloaded', timeout: 45000 });
      await p.waitForTimeout(3000);
      const t = await p.evaluate(() => document.body.innerText);
      const name = u.replace(/[^a-z0-9]+/gi, '_').slice(0, 100);
      fs.writeFileSync('data/raw/' + name + '.txt', t);
      console.log('OK', u, t.length);
    } catch (e) { console.log('FAIL', u, e.message.split('\n')[0]); }
    await p.close();
  }
  await b.close();
})();
