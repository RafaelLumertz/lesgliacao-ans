// Usage: node harvest_index.js "<Tipo label>" out.jsonl
const { chromium } = require('playwright');
const fs = require('fs');
const [tipo, out] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({viewport:{width:1400,height:900}});
  const p = await ctx.newPage();
  let navs = [];
  await ctx.route('**/*', route => { const r = route.request(); let other=false; if (r.isNavigationRequest()) { try { other = r.frame() !== p.mainFrame(); } catch(e){ other = true; } } if (other) { navs.push(r.url()); return route.abort(); } return route.continue(); });
  ctx.on('request', r => { try { if (r.isNavigationRequest() && r.frame().page() !== p) navs.push(r.url()); } catch(e){} });
  await p.goto('https://componentes-portal.ans.gov.br/link/legislacoes', { waitUntil: 'networkidle', timeout: 120000 });
  await p.waitForTimeout(1500);
  const T0=Date.now(); const dbg=(...a)=>console.error(((Date.now()-T0)/1000).toFixed(1), ...a);
  const status = async () => (await p.locator('.mx-grid-paging-status').first().innerText()).trim();
  const sel = p.locator('select').filter({hasText:'Resolução Normativa'}).first();
  let s0 = await status();
  dbg('start', s0); const [lab, nth] = tipo.split('#'); const vals = await sel.evaluate((s,l) => [...s.options].filter(o=>o.textContent.trim()===l).map(o=>o.value), lab); await sel.selectOption(vals[(+nth||1)-1]); dbg('selected');
  for (let k=0;k<40 && (await status())===s0;k++) await p.waitForTimeout(500);
  s0 = await status(); dbg('after tipo', s0);
  await p.locator('select[id*=dropDown4]').first().selectOption({label:'30'});
  for (let k=0;k<40 && (await status())===s0;k++) await p.waitForTimeout(500);
  await p.waitForLoadState('networkidle');
  const seen = new Set();
  if (fs.existsSync(out)) fs.readFileSync(out,'utf8').split('\n').filter(Boolean).forEach(l=>seen.add(JSON.parse(l).titulo));
  while (true) {
    const st = await status(); console.error(tipo, st);
    const rows = p.locator('.tr[role=row]').filter({has: p.locator('.popupmenu-trigger')});
    const n = await rows.count();
    for (let i=0;i<n;i++) {
      const row = rows.nth(i);
      const cells = await row.locator('[role=gridcell]').allInnerTexts();
      const rec = {tipo: tipo.split('#')[0], titulo: cells[0].trim(), data_dou: cells[1].trim(), ementa: cells[2].trim(), tema: cells[3].trim(), assunto: cells[4].trim(), status: cells[5].trim()};
      if (seen.has(rec.titulo)) continue; dbg('row', i, rec.titulo);
      for (let attempt=0; attempt<2; attempt++) {
        try {
          await row.locator('.popupmenu-trigger').click();
          navs = []; const [np] = await Promise.all([ctx.waitForEvent('page',{timeout:8000}), p.locator('.popupmenu-menu:visible').getByText('Acessar legislação').click()]);
          for (let k=0;k<40 && !navs.length;k++) await p.waitForTimeout(100);
          rec.url = navs[0] || np.url(); navs = []; const mm = rec.url.match(/legislacao\/(\d+)/); if (mm) rec.id = mm[1];
          await np.close();
          break;
        } catch(e) { console.error('retry', rec.titulo, e.message.split('\n')[0]); await p.keyboard.press('Escape').catch(()=>{}); await p.waitForTimeout(1000); for (const x of ctx.pages().slice(1)) await x.close(); if (e.message.includes('waiting for event')) break; }
      }
      fs.appendFileSync(out, JSON.stringify(rec)+'\n'); seen.add(rec.titulo);
    }
    const m = st.match(/(\d+) a (\d+) de (\d+)/);
    if (!m || +m[2] >= +m[3]) break;
    await p.locator('.mx-name-firstPage1').first().click();
    for (let k=0;k<60 && (await status())===st;k++) await p.waitForTimeout(500);
    await p.waitForLoadState('networkidle'); await p.waitForTimeout(500);
  }
  await b.close();
})();
