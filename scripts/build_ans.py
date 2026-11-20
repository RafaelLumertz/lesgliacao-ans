"""Monta a pasta ans/ do repositório a partir dos dados brutos coletados.
Uso: python3 build_ans.py <index_dir> <raw_dir> <out_repo_dir>
"""
import sys, os, re, json, glob, shutil, subprocess, csv, datetime, collections, unicodedata
from bs4 import BeautifulSoup
from markdownify import markdownify as mdify

INDEX, RAW, OUT = sys.argv[1:4]
TODAY = datetime.date.today().isoformat()

CATS = {
    'Resolução Normativa': ('01-resolucoes-normativas', 'Resoluções Normativas (RN)'),
    'Instrução Normativa': ('02-instrucoes-normativas', 'Instruções Normativas (IN)'),
    'Instrução Normativa Conjunta': ('02-instrucoes-normativas', 'Instruções Normativas (IN)'),
    'Resolução de Diretoria Colegiada': ('03-resolucoes-diretoria-colegiada', 'Resoluções de Diretoria Colegiada (RDC)'),
    'Resolução CONSU': ('04-resolucoes-consu', 'Resoluções do Conselho de Saúde Suplementar (CONSU)'),
    'Súmula Normativa': ('05-sumulas-normativas', 'Súmulas Normativas'),
    'Resolução Regimental': ('06-resolucoes-regimentais', 'Resoluções Regimentais (RR)'),
    'Parecer da PROGE': ('07-pareceres-proge', 'Pareceres da Procuradoria Federal junto à ANS (PROGE)'),
    'Entendimento da DIFIS': ('08-entendimentos-difis', 'Entendimentos da Diretoria de Fiscalização (DIFIS)'),
}
MESES = {m: i+1 for i, m in enumerate(['janeiro','fevereiro','março','abril','maio','junho','julho','agosto','setembro','outubro','novembro','dezembro'])}

def load_index():
    recs = {}
    for f in glob.glob(os.path.join(INDEX, '*.jsonl')):
        for l in open(f):
            j = json.loads(l)
            if j.get('id') and j['tipo'] in CATS:
                recs.setdefault(j['id'], j)
    return recs

def parse_title(t):
    # "Resolução Normativa - RN ANS nº 8, de 24 maio 2002"
    rest = t.split(' - ', 1)[1] if ' - ' in t else t
    m = re.match(r'(.*?)\s*n[º°o]\.?\s*([\w\-\.]+),?\s*de\s+(\d{1,2})\s+(\w+)\s+(\d{4})', rest, re.I)
    if not m:
        return None
    sig, num, d, mes, ano = m.groups()
    sig = re.sub(r'\b(ANS|Diretoria Colegiada|Externo à ANS|Externo)\b', '', sig).strip()
    sig = re.sub(r'^[\s\-]+|[\s\-]+$', '', sig)
    toks = []
    for t in re.split(r'\s+', sig):
        if t and (not toks or toks[-1] != t): toks.append(t)
    sig = '-'.join(toks) or 'ATO'
    sig = unicodedata.normalize('NFKD', sig).encode('ascii', 'ignore').decode()
    return dict(sigla=sig, numero=num, dia=int(d), mes=MESES.get(mes.lower(), 0), ano=int(ano))

def slug_for(p):
    num = p['numero']
    n = re.match(r'(\d+)(.*)', num)
    nums = f"{int(n.group(1)):04d}{n.group(2)}" if n else num
    s = f"{p['sigla']}-{nums}-{p['ano']}"
    return re.sub(r'[^A-Za-z0-9\-]', '', s.replace('.', '-'))

def html_to_md(h):
    if not h: return ''
    soup = BeautifulSoup(h, 'lxml')
    for t in soup(['script', 'style']): t.decompose()
    for t in soup.find_all(['s', 'strike']): t.name = 'del'
    for t in soup.find_all(style=re.compile('line-through')): t.name = 'del'
    for dd in soup.find_all('del'):
        if not dd.get_text(strip=True): dd.unwrap()
    for img in soup.find_all('img'):
        src = img.get('src', '')
        img.replace_with('[imagem]' if src.startswith('data:') or not src else f'[imagem: {src}]')
    t = mdify(str(soup.body or soup), heading_style='ATX', escape_underscores=False, escape_asterisks=False, strip=['span', 'font'])
    t = t.replace('\xa0', ' ')
    t = re.sub(r'[ \t]+\n', '\n', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    t = re.sub(r'~~\s*~~', '', t)
    return t.strip()

LABELS = ['Data de vigência', 'Tipo de reunião', 'Número', 'Data da reunião que aprovou o ato',
          'Data da Publicação', 'Data da Alteração', 'Data da Revogação']

def parse_page(txt):
    lines = [l.strip() for l in txt.split('\n')]
    info = {}
    for i, l in enumerate(lines):
        if l in LABELS and l not in info:
            for v in lines[i+1:i+3]:
                if v: info[l] = v; break
        if l.startswith('Esta norma foi revogada por'):
            info['revogada_por'] = next((v for v in lines[i+1:i+3] if v), '')
        m = re.match(r'Publicado em (\S+)\s*\|\s*Atualizado em (\S+)', l)
        if m: info['publicado_em'], info['atualizado_em'] = m.groups()
        if 'Nenhuma informação sobre a Diretoria Colegiada' in l: info['sem_reuniao'] = True
    # participação social
    if 'Participação social' in lines:
        i = lines.index('Participação social')
        seg = []
        for l in lines[i+1:]:
            if l in ('Fundamentação legal',) or l.startswith('Legislaç'): break
            if l: seg.append(l)
        info['participacao_social'] = seg
    return info

def pdf_text(src, dst):
    try:
        subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', src, dst], timeout=300, check=True,
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(dst) and os.path.getsize(dst) < 50:
            os.remove(dst); return False
        return True
    except Exception:
        if os.path.exists(dst): os.remove(dst)
        return False

def esc(s): return (s or '').replace('|', '\\|').replace('\n', ' ')

def main():
    recs = load_index()
    acts = []
    for id_, r in recs.items():
        mp = os.path.join(RAW, id_, 'meta.json')
        if not os.path.exists(mp): continue
        meta = json.load(open(mp))
        if meta.get('notfound'): continue
        p = parse_title(r['titulo']) or dict(sigla='ATO', numero=id_, dia=0, mes=0, ano=0)
        acts.append(dict(id=id_, rec=r, meta=meta, p=p, slug=slug_for(p)))
    # slugs únicos
    seen = {}
    for a in sorted(acts, key=lambda a: int(a['id'])):
        cat = CATS[a['rec']['tipo']][0]
        key = (cat, a['slug'])
        a['base_slug'] = a['slug']
        manx = re.search(r'ANEXO\s+([IVXLC]+)\b', a['rec'].get('ementa', '')[:120])
        if manx and re.match(r'\W*RN\s*N', a['rec'].get('ementa', '')):
            a['slug'] = f"{a['slug']}-anexo-{manx.group(1)}"; a['anexo_de'] = a['base_slug']
            if (cat, a['slug']) in seen: a['slug'] += f"-id{a['id']}"
        elif key in seen:
            a['slug'] = f"{a['slug']}-{a['p']['mes']:02d}{a['p']['dia']:02d}"
            if (cat, a['slug']) in seen: a['slug'] += f"-id{a['id']}"
        seen[(cat, a['slug'])] = a
        a['cat'] = cat
        a['relpath'] = f"ans/{cat}/{a['slug']}.md"
    by_title = {}
    for a in acts: by_title.setdefault(a['rec']['titulo'], a)

    def link_from(a_from, title):
        b = by_title.get(title)
        if not b: return esc(title)
        rel = os.path.relpath(b['relpath'], os.path.dirname(a_from['relpath']))
        return f"[{esc(title)}]({rel.replace(' ', '%20')})"

    rows_csv = []
    for a in acts:
        r, meta, p = a['rec'], a['meta'], a['p']
        raw = os.path.join(RAW, a['id'])
        ck = json.load(open(os.path.join(raw, 'ck.json')))
        txt = open(os.path.join(raw, 'page.txt')).read()
        info = parse_page(txt)
        # ementa/texto/fundamentação
        sizes = [len(c) for c in ck]
        ti = sizes.index(max(sizes)) if ck else None
        ementa_md = html_to_md(ck[0]) if ck and ti != 0 else ''
        texto_md = html_to_md(ck[ti]) if ck else ''
        fund_md = html_to_md(ck[ti+1]) if ck and ti is not None and ti+1 < len(ck) else ''
        extra = [html_to_md(c) for k, c in enumerate(ck) if k not in (0, ti, (ti or 0)+1)]
        # anexos
        cat_dir = os.path.join(OUT, 'ans', a['cat'])
        os.makedirs(cat_dir, exist_ok=True)
        anexos = []
        files = [f for f in meta.get('files', []) if f.get('file')]
        if files:
            adir = os.path.join(cat_dir, 'anexos', a['slug'])
            os.makedirs(adir, exist_ok=True)
            for f in files:
                src = os.path.join(raw, 'files', f['file'])
                if not os.path.exists(src): continue
                if os.path.getsize(src) > 95 * 1024 * 1024:
                    anexos.append(dict(name=f['file'], big=True, size=os.path.getsize(src))); continue
                dst = os.path.join(adir, f['file'])
                shutil.copyfile(src, dst)
                has_txt = False
                if f['file'].lower().endswith('.pdf'):
                    has_txt = pdf_text(dst, dst[:-4] + '.txt')
                anexos.append(dict(name=f['file'], size=os.path.getsize(src), txt=has_txt))
        # grades: histórico de versões de anexos e legislações relacionadas
        versoes, relac = [], []
        for g in meta.get('grids', []):
            h = g.get('heading') or ''
            if h.startswith('Legisla'):
                relac.append((h, g['rows']))
            elif g['rows']:
                vs = []
                for row in g['rows']:
                    c0 = row[0]
                    m = re.match(r'(.+?\.(?:pdf|docx?|xlsx?|xls|zip|rar|odt|ods|csv|txt|ppt|pptx|htm|html))(.*)$', c0, re.I)
                    fname, norma = (m.group(1), m.group(2).strip()) if m else (c0, '')
                    vs.append((fname, norma, row[1] if len(row) > 1 else '', None))
                versoes.append(vs)
        # versões anteriores baixadas (fetch_versions.js)
        vj = os.path.join(raw, 'versions.json')
        if os.path.exists(vj):
            vdata = json.load(open(vj))
            grids_v = collections.OrderedDict()
            for v in vdata: grids_v.setdefault(v['grid'], []).append(v)
            versoes = []
            vdir = os.path.join(cat_dir, 'anexos', a['slug'], 'versoes-anteriores')
            for g, vs in grids_v.items():
                if len(vs) < 2: continue
                lst = []
                for v in vs:
                    href = None
                    if v.get('file') and os.path.exists(os.path.join(raw, 'versions', v['file'])):
                        os.makedirs(vdir, exist_ok=True)
                        src = os.path.join(raw, 'versions', v['file'])
                        if os.path.getsize(src) <= 95 * 1024 * 1024:
                            shutil.copyfile(src, os.path.join(vdir, v['file']))
                            href = f"anexos/{a['slug']}/versoes-anteriores/{v['file']}".replace(' ', '%20')
                    lst.append((v['arquivo'], v['norma'], v['data'], href))
                versoes.append(lst)
        # markdown
        status = r.get('status', '')
        fm = {
            'titulo': r['titulo'], 'tipo': r['tipo'], 'sigla': p['sigla'], 'numero': p['numero'], 'ano': p['ano'],
            'status': status, 'data_dou': r.get('data_dou', ''),
            'data_vigencia': info.get('Data de vigência', ''), 'data_alteracao': info.get('Data da Alteração', ''),
            'data_revogacao': info.get('Data da Revogação', ''), 'revogada_por': info.get('revogada_por', ''),
            'tema': r.get('tema', ''), 'assunto': r.get('assunto', ''),
            'fonte': f"https://componentes-portal.ans.gov.br/link/legislacao/{a['id']}", 'id_ans': a['id'], 'coletado_em': TODAY,
        }
        out = ['---'] + [f"{k}: {json.dumps(v, ensure_ascii=False)}" for k, v in fm.items()] + ['---', '']
        out.append(f"# {r['titulo']}\n")
        if status.lower().startswith('revog'):
            rp = info.get('revogada_por', '')
            out.append(f"> ⚠️ **{status.upper()}**" + (f" por {link_from(a, rp)}" if rp else '') + "\n")
        elif status:
            out.append(f"> Situação: **{status}**\n")
        tab = [('Tipo', r['tipo']), ('Publicação no DOU', r.get('data_dou', '')), ('Data de vigência', info.get('Data de vigência', '')),
               ('Data da última alteração', info.get('Data da Alteração', '')), ('Data da revogação', info.get('Data da Revogação', '')),
               ('Tema', r.get('tema', '')), ('Assunto', r.get('assunto', ''))]
        if info.get('Tipo de reunião'):
            tab.append(('Reunião da Diretoria Colegiada', f"{info.get('Tipo de reunião')} nº {info.get('Número', '')} em {info.get('Data da reunião que aprovou o ato', '')}"))
        tab.append(('Fonte oficial', f"[Portal de Legislação da ANS]({fm['fonte']})"))
        out.append('| Campo | Valor |\n| --- | --- |')
        out += [f"| {k} | {esc(v)} |" for k, v in tab if v]
        out.append('')
        if ementa_md:
            out.append('## Ementa\n\n' + ementa_md + '\n')
        out.append('## Texto\n')
        out.append('> Trechos ~~tachados~~ indicam dispositivos revogados ou com redação alterada, conforme publicado pela ANS. '
                   'Este texto não substitui o publicado no Diário Oficial da União.\n')
        out.append(texto_md or '_Texto não disponível no portal da ANS._')
        out.append('')
        for e in extra:
            if e: out.append(e + '\n')
        if anexos or versoes:
            out.append('## Anexos\n')
            for k, an in enumerate(anexos):
                href = f"anexos/{a['slug']}/{an['name']}".replace(' ', '%20')
                if an.get('big'):
                    out.append(f"- {an['name']} — arquivo com {an['size']//(1024*1024)} MB, acima do limite do GitHub; consulte a [fonte oficial]({fm['fonte']})")
                else:
                    line = f"- [{an['name']}]({href}) ({an['size']//1024} KB)"
                    if an.get('txt'): line += f" · [versão em texto]({href[:-4]}.txt)"
                    out.append(line)
            for vs in versoes:
                if len(vs) > 1:
                    out.append(f"\n<details><summary>Histórico de versões do anexo <b>{esc(re.sub(r'Versão atual$', '', vs[0][0]))}</b> ({len(vs)} versões)</summary>\n")
                    out.append('| Arquivo | Norma que gerou a versão | Data do vínculo |\n| --- | --- | --- |')
                    for fname, norma, dt, href in vs:
                        fcell = f"[{esc(fname)}]({href})" if href else esc(fname)
                        out.append(f"| {fcell} | {link_from(a, norma) if norma and norma != 'Versão atual' else esc(norma)} | {esc(dt)} |")
                    out.append('\n</details>')
            out.append('')
        irmaos = [b for b in acts if b.get('anexo_de') == a['slug'] and b['cat'] == a['cat']]
        if irmaos:
            out.append('## Anexos publicados como registros separados no portal da ANS\n')
            for b in sorted(irmaos, key=lambda b: b['slug']):
                out.append(f"- [{esc(b['rec'].get('ementa', '')[:150])}]({b['slug']}.md)")
            out.append('')
        if a.get('anexo_de'):
            out.insert(out.index(f"# {r['titulo']}\n") + 1, f"> Este registro é um **anexo** da norma [{a['anexo_de']}]({a['anexo_de']}.md), cadastrado separadamente no portal da ANS.\n")
        if relac:
            out.append('## Histórico normativo\n')
            for h, rows in relac:
                h2 = re.sub(r'\s+de\s+' + re.escape(r['titulo']) + r'$', '', h)
                h2 = re.sub(r'\s+por\s+' + re.escape(r['titulo']) + r'$', ' por esta norma', h2)
                out.append(f"### {h2} ({len(rows)})\n")
                srt = sorted(rows, key=lambda x: ((parse_title(x[0]) or {}).get('ano', 0), int(re.match(r'\d*', (parse_title(x[0]) or {}).get('numero', '0')).group() or 0)))
                out += [f"- {link_from(a, row[0])}" + (f" — vínculo registrado em {row[1]}" if len(row) > 1 else '') for row in srt]
                out.append('')
        if fund_md:
            out.append('## Fundamentação legal\n\n' + fund_md + '\n')
        if info.get('participacao_social'):
            out.append('## Participação social\n\n' + '\n'.join(f"- {x}" for x in info['participacao_social']) + '\n')
        open(os.path.join(cat_dir, a['slug'] + '.md'), 'w').write('\n'.join(out).rstrip() + '\n')
        n_alt = sum(len(rows) for h, rows in relac if 'alteradoras' in h)
        rows_csv.append(dict(categoria=a['cat'], arquivo=a['relpath'], id_ans=a['id'], tipo=r['tipo'], sigla=p['sigla'], numero=p['numero'], ano=p['ano'],
                             data_dou=r.get('data_dou', ''), status=status, titulo=r['titulo'], ementa=re.sub(r'\s+', ' ', r.get('ementa', '')),
                             tema=r.get('tema', ''), assunto=r.get('assunto', ''), revogada_por=info.get('revogada_por', ''),
                             qtd_alteradoras=n_alt, qtd_anexos=len(anexos), fonte=fm['fonte']))
    os.makedirs(os.path.join(OUT, 'dados'), exist_ok=True)
    rows_csv.sort(key=lambda x: (x['categoria'], x['sigla'], x['ano'], int(re.match(r'\d+', x['numero']).group()) if re.match(r'\d+', x['numero']) else 0))
    with open(os.path.join(OUT, 'dados', 'atos-ans.csv'), 'w', newline='') as f:
        w = csv.DictWriter(f, fieldnames=list(rows_csv[0].keys())); w.writeheader(); w.writerows(rows_csv)
    json.dump(rows_csv, open(os.path.join(OUT, 'dados', 'atos-ans.json'), 'w'), ensure_ascii=False, indent=1)
    # índice por categoria
    for tipo, (cat, nome) in CATS.items():
        rs = [x for x in rows_csv if x['categoria'] == cat]
        if not rs: continue
        vig = sum(1 for x in rs if x['status'] == 'Vigente')
        lines = [f"# {nome}\n", f"{len(rs)} atos ({vig} vigentes). Ordenados do mais recente para o mais antigo. "
                 "Clique no número para abrir o texto integral, anexos e histórico.\n",
                 '| Ato | DOU | Situação | Ementa |', '| --- | --- | --- | --- |']
        for x in sorted(rs, key=lambda x: (x['ano'], x['data_dou'][6:] + x['data_dou'][3:5] + x['data_dou'][:2], x['numero']), reverse=True):
            em = x['ementa'][:220] + ('…' if len(x['ementa']) > 220 else '')
            lines.append(f"| [{x['sigla']} {x['numero']}/{x['ano']}]({os.path.basename(x['arquivo'])}) | {x['data_dou']} | {x['status']} | {esc(em)} |")
        open(os.path.join(OUT, 'ans', cat, 'README.md'), 'w').write('\n'.join(lines) + '\n')
    print('atos', len(rows_csv))

main()
