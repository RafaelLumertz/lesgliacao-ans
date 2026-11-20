// Usage: node fetch_detail.js <rawdir> <id> [<id> ...]   (ids lidos de stdin se nenhum for passado)
const { chromium } = require('playwright');
const fs = require('fs'), path = require('path');
const [rawdir, ...argIds] = process.argv.slice(2);
(async () => {
  let ids = argIds.length ? argIds : fs.readFileSync(0,'utf8').split(/\s+/).filter(Boolean);
  const b = await chromium.launch();
  const ctx = await b.newContext({viewport:{width:1400,height:900}, acceptDownloads:true});
  const p = await ctx.newPage();
  for (const id of ids) {
    const dir = path.join(rawdir, id);
    if (fs.existsSync(path.join(dir,'meta.json'))) continue;
    for (let attempt=0; attempt<3; attempt++) {
      try {
        fs.mkdirSync(dir, {recursive:true});
        await p.goto('https://componentes-portal.ans.gov.br/link/legislacao/'+id, { waitUntil: 'networkidle', timeout: 90000 });
        await p.waitForSelector('text=Compartilhe', {timeout: 30000});
        await p.waitForTimeout(1500);
        const text = await p.innerText('body');
        if (/Página não encontrada/.test(text)) { fs.writeFileSync(path.join(dir,'meta.json'), JSON.stringify({id, notfound:true})); break; }
        const ck = await p.$$eval('.wgt-CKEditorViewerForMendixNode', els => els.map(e => e.innerHTML));
        const links = await p.$$eval('a[href]', as => as.map(a => ({text:(a.innerText||'').trim(), href:a.href})).filter(x => !x.href.endsWith('#') && x.text));
        // anexos: cabeçalhos de acordeão com ícone de download
        const heads = p.locator('.widget-accordion-group-header').filter({ has: p.locator('img[src*="download"]') });
        const nh = await heads.count();
        const files = [];
        fs.mkdirSync(path.join(dir,'files'), {recursive:true});
        for (let i=0;i<nh;i++) {
          const h = heads.nth(i);
          const label = (await h.innerText()).trim();
          try {
            const [d] = await Promise.all([p.waitForEvent('download',{timeout:60000}), h.locator('img[src*="download"]').first().click({timeout:15000})]);
            let name = d.suggestedFilename().replace(/[\/\\]/g,'_');
            let k = 1; while (files.some(f=>f.file===name)) name = (k++)+'_'+name;
            await d.saveAs(path.join(dir,'files',name));
            files.push({label, file:name, url:d.url()});
          } catch(e) { files.push({label, error: e.message.split('\n')[0]}); }
        }
        // grades paginadas (legislações alteradoras / revogadoras / alteradas / revogadas)
        const grids = [];
        const gl = p.locator('.widget-datagrid');
        const ng = await gl.count();
        for (let g=0; g<ng; g++) {
          const grid = gl.nth(g);
          const heading = await grid.evaluate(el => { let n=el; while(n){ let s=n.previousElementSibling; while(s){ const lines=(s.innerText||'').split('\n').filter(l=>/Legisla/i.test(l)); if(lines.length) return lines[lines.length-1].trim(); s=s.previousElementSibling;} n=n.parentElement;} return null; });
          const rows = [];
          for (let pg=0; pg<100; pg++) {
            const rt = await grid.locator('[role=row]').evaluateAll(rs => rs.map(r => [...r.querySelectorAll('[role=gridcell]')].map(c => c.textContent.replace(/\s+/g,' ').trim()).filter(Boolean)));
            for (const r of rt) if (r.length) rows.push(r);
            const nxt = grid.locator('button[aria-label="Go to next page"]');
            if (!(await nxt.count()) || await nxt.first().isDisabled()) break;
            const st = await grid.locator('.paging-status').first().textContent();
            try { await nxt.first().evaluate(btn => btn.click()); } catch(e) { console.log('gridclick', id, e.message.split('\n')[0]); break; }
            for (let k=0;k<50 && (await grid.locator('.paging-status').first().textContent())===st;k++) await p.waitForTimeout(200);
            await p.waitForTimeout(300);
          }
          const status = (await grid.locator('.paging-status').count()) ? await grid.locator('.paging-status').first().textContent() : null;
          grids.push({heading, status, rows});
        }
        fs.writeFileSync(path.join(dir,'page.txt'), text);
        fs.writeFileSync(path.join(dir,'ck.json'), JSON.stringify(ck));
        fs.writeFileSync(path.join(dir,'meta.json'), JSON.stringify({id, url:p.url(), fetched: new Date().toISOString(), links, files, grids}, null, 1));
        console.log('ok', id, ck.length, files.length);
        break;
      } catch(e) { console.log('err', id, attempt, e.message.split('\n')[0]); await p.waitForTimeout(3000); }
    }
  }
  await b.close();
})();
