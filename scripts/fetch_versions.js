// Baixa as versões anteriores dos anexos. Uso: node fetch_versions.js <rawdir> <id> [<id>...]
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [rawdir, ...ids] = process.argv.slice(2);
(async () => {
  const b = await chromium.launch();
  const ctx = await b.newContext({viewport:{width:1400,height:900}, acceptDownloads:true});
  const p = await ctx.newPage();
  for (const id of ids) {
    const dir = path.join(rawdir, id), out = path.join(dir, 'versions');
    if (fs.existsSync(path.join(dir, 'versions.json'))) continue;
    try {
      await p.goto('https://componentes-portal.ans.gov.br/link/legislacao/'+id, { waitUntil: 'networkidle', timeout: 90000 });
      await p.waitForSelector('text=Compartilhe', {timeout: 30000}); await p.waitForTimeout(1500);
      fs.mkdirSync(out, {recursive:true});
      const res = [];
      const gl = p.locator('.widget-datagrid').filter({ has: p.locator('img[src*="download"]') });
      const ng = await gl.count();
      for (let g=0; g<ng; g++) {
        const grid = gl.nth(g);
        for (let pg=0; pg<100; pg++) {
          const rows = grid.locator('[role=row]').filter({ has: p.locator('img[src*="download"]') });
          const nr = await rows.count();
          for (let i=0;i<nr;i++) {
            const row = rows.nth(i);
            const cells = await row.locator('[role=gridcell]').evaluateAll(cs => cs.map(c => c.textContent.replace(/\s+/g,' ').trim()));
            if (cells[1] === 'Versão atual' || /Versão atual$/.test(cells[0])) { res.push({grid:g, arquivo:cells[0].replace(/\s*Versão atual$/,''), norma:'Versão atual', data:cells[2], atual:true}); continue; }
            try {
              const [d] = await Promise.all([p.waitForEvent('download',{timeout:60000}), row.locator('img[src*="download"]').first().evaluate(el => el.click())]);
              const name = `${g+1}-${String(res.length+1).padStart(3,'0')}-` + cells[0].replace(/[\/\\:*?"<>|]/g,'_');
              await d.saveAs(path.join(out, name));
              res.push({grid:g, arquivo:cells[0], norma:cells[1], data:cells[2], file:name});
            } catch(e) { res.push({grid:g, arquivo:cells[0], norma:cells[1], data:cells[2], error:e.message.split('\n')[0]}); }
          }
          const nxt = grid.locator('button[aria-label="Go to next page"]');
          if (!(await nxt.count()) || await nxt.first().isDisabled()) break;
          const st = await grid.locator('.paging-status').first().textContent();
          await nxt.first().evaluate(btn => btn.click());
          for (let k=0;k<50 && (await grid.locator('.paging-status').first().textContent())===st;k++) await p.waitForTimeout(200);
          await p.waitForTimeout(300);
        }
      }
      fs.writeFileSync(path.join(dir,'versions.json'), JSON.stringify(res, null, 1));
      console.log('ok', id, res.length, res.filter(r=>r.file).length, res.filter(r=>r.error).length);
    } catch(e) { console.log('err', id, e.message.split('\n')[0]); }
  }
  await b.close();
})();
