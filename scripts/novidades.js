// Lê a lista geral do Portal de Legislação da ANS (mais recentes primeiro) e identifica atos novos.
// Uso: node novidades.js <conhecidos.json> <saida.jsonl> <maxPaginas|todas>
//   conhecidos.json: {"<titulo>|<data_dou>": "<id>"} dos atos já existentes no acervo
//   No modo diário, para ao encontrar 2 páginas seguidas sem nenhum ato novo.
//   No modo "todas" (varredura semanal), lê a lista inteira para detectar mudanças de situação.
const { chromium } = require('playwright');
const fs = require('fs');
const [knownFile, out, maxArg] = process.argv.slice(2);
const known = JSON.parse(fs.readFileSync(knownFile, 'utf8'));
const MAX = maxArg === 'todas' ? 100000 : (+maxArg || 5);
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({ viewport: { width: 1400, height: 900 } });
  const p = await ctx.newPage();
  let navs = [];
  await ctx.route('**/*', route => { const r = route.request(); let other = false; if (r.isNavigationRequest()) { try { other = r.frame() !== p.mainFrame(); } catch (e) { other = true; } } if (other) { navs.push(r.url()); return route.abort(); } return route.continue(); });
  await p.goto('https://componentes-portal.ans.gov.br/link/legislacoes', { waitUntil: 'networkidle', timeout: 120000 });
  await p.waitForTimeout(2000);
  const status = async () => (await p.locator('.mx-grid-paging-status').first().innerText()).trim();
  let s0 = await status();
  await p.locator('select[id*=dropDown4]').first().selectOption({ label: '30' });
  for (let k = 0; k < 40 && (await status()) === s0; k++) await p.waitForTimeout(500);
  await p.waitForLoadState('networkidle');
  fs.writeFileSync(out, '');
  let semNovos = 0;
  for (let pg = 0; pg < MAX; pg++) {
    const st = await status(); console.error(st);
    const rows = p.locator('.tr[role=row]').filter({ has: p.locator('.popupmenu-trigger') });
    const n = await rows.count();
    let novos = 0;
    for (let i = 0; i < n; i++) {
      const row = rows.nth(i);
      const cells = await row.locator('[role=gridcell]').allInnerTexts();
      const rec = { tipo: cells[0].split(' - ')[0].trim(), titulo: cells[0].trim(), data_dou: cells[1].trim(), ementa: cells[2].trim(), tema: cells[3].trim(), assunto: cells[4].trim(), status: cells[5].trim() };
      const key = rec.titulo + '|' + rec.data_dou;
      if (known[key]) { rec.id = known[key]; rec.conhecido = true; }
      else if (!/Externo à ANS/.test(rec.titulo)) {
        novos++;
        for (let attempt = 0; attempt < 2 && !rec.id; attempt++) {
          try {
            await row.locator('.popupmenu-trigger').click();
            navs = [];
            await Promise.all([ctx.waitForEvent('page', { timeout: 8000 }), p.locator('.popupmenu-menu:visible').getByText('Acessar legislação').click()]);
            for (let k = 0; k < 40 && !navs.length; k++) await p.waitForTimeout(100);
            const mm = (navs[0] || '').match(/legislacao\/(\d+)/); if (mm) rec.id = mm[1];
            for (const x of ctx.pages().slice(1)) await x.close();
          } catch (e) { await p.keyboard.press('Escape').catch(() => {}); for (const x of ctx.pages().slice(1)) await x.close(); }
        }
      }
      fs.appendFileSync(out, JSON.stringify(rec) + '\n');
    }
    semNovos = novos ? 0 : semNovos + 1;
    if (MAX < 100000 && semNovos >= 2) break;
    const m = st.match(/(\d+) a (\d+) de (\d+)/);
    if (!m || +m[2] >= +m[3]) break;
    // no portal, o botão com a classe "firstPage1" é o que avança uma página
    await p.locator('.mx-name-firstPage1').first().click();
    for (let k = 0; k < 60 && (await status()) === st; k++) await p.waitForTimeout(500);
    await p.waitForLoadState('networkidle'); await p.waitForTimeout(500);
  }
  await b.close();
})();
