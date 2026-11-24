"""Gera a pasta rol-de-procedimentos/ a partir dos anexos da RN nº 465/2021 e de todas as suas versões.

- Anexo I (lista de procedimentos) é lido como tabela (pdfplumber) -> procedimentos.csv e páginas por capítulo;
- Anexo II (Diretrizes de Utilização - DUT) é dividido em um arquivo por DUT;
- Cada versão anterior dos anexos é comparada com a seguinte, gerando o histórico de inclusões,
  exclusões e alterações, atribuídas à norma que gerou a nova versão.

Os resultados das comparações ficam em historico/cache.json, para que apenas versões novas
precisem ser processadas. Uso: python3 scripts/build_rol.py [repo]
"""
import sys, os, re, json, csv, hashlib, shutil, subprocess, unicodedata, collections, datetime

REPO = os.path.abspath(sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), '..'))
RN_SLUG = 'RN-0465-2021'
RN_MD = f'ans/01-resolucoes-normativas/{RN_SLUG}.md'
ADIR = os.path.join(REPO, f'ans/01-resolucoes-normativas/anexos/{RN_SLUG}')
VDIR = os.path.join(ADIR, 'versoes-anteriores')
OUT = os.path.join(REPO, 'rol-de-procedimentos')
CACHE = os.path.join(OUT, 'historico', 'cache.json')
SEGS = ['OD', 'AMB', 'HCO', 'HSO', 'REF', 'PAC']
NOMES_ANEXOS = {1: 'Anexo I — Lista de procedimentos e eventos', 2: 'Anexo II — Diretrizes de Utilização (DUT)',
                3: 'Anexo III — Diretrizes Clínicas (DC)', 4: 'Anexo IV — Protocolo de Utilização (PROUT)'}
ARQ_ESTAVEL = {1: 'Anexo-I-Lista-de-Procedimentos', 2: 'Anexo-II-Diretrizes-de-Utilizacao',
               3: 'Anexo-III-Diretrizes-Clinicas', 4: 'Anexo-IV-Protocolo-de-Utilizacao'}

def log(*a): print('[rol]', *a, file=sys.stderr, flush=True)
def sha(p): return hashlib.sha1(open(p, 'rb').read()).hexdigest()
def limpa(t): return re.sub(r'\s+', ' ', (t or '').replace('\n', ' ')).strip()
def chave(t): return re.sub(r'[^A-Z0-9]', '', unicodedata.normalize('NFKD', t.upper()).encode('ascii', 'ignore').decode())
def slug(t): return re.sub(r'-+', '-', re.sub(r'[^a-z0-9]+', '-', unicodedata.normalize('NFKD', t.lower()).encode('ascii', 'ignore').decode())).strip('-')[:70]
def esc(t): return (t or '').replace('|', '\\|')

# ------------------------------------------------------------------ leitura dos anexos
COLS = [('PROCEDIMENTO', 'procedimento'), ('SUBGRUPO', 'subgrupo'), ('GRUPO', 'grupo'), ('CAPÍTULO', 'capitulo'),
        ('CAPITULO', 'capitulo'), ('RN', 'rn'), ('VIGÊNCIA', 'vigencia'), ('VIGENCIA', 'vigencia'), ('DUT', 'dut')] + [(s, s.lower()) for s in SEGS]

def mapa_cabecalho(row):
    m = {}
    for i, c in enumerate(row):
        c = limpa(c).upper()
        for k, v in COLS:
            if c == k or c.startswith(k + ' ') or c.startswith(k + '-') or (k == 'RN' and c.startswith('RN')):
                if v not in m.values(): m[i] = v
                break
    # cabeçalho de verdade tem a coluna PROCEDIMENTO e várias outras (evita confundir procedimentos cujo nome começa com 'PROCEDIMENTO')
    return m if 'procedimento' in m.values() and len(m) >= 6 and ({'grupo', 'subgrupo', 'capitulo'} & set(m.values())) else None

def tabelas_pdf(pdf_path):
    """Linhas brutas das tabelas do PDF. Com ROL_CACHE_DIR definido, guarda o resultado em disco (acelera reprocessamentos)."""
    cdir = os.environ.get('ROL_CACHE_DIR')
    if cdir:
        cf = os.path.join(cdir, sha(pdf_path) + '.json')
        if os.path.exists(cf): return json.load(open(cf))
    import pdfplumber
    rows = []
    with pdfplumber.open(pdf_path) as pdf:
        for pg in pdf.pages:
            for t in pg.extract_tables(): rows += [r for r in t if r]
    if cdir:
        os.makedirs(cdir, exist_ok=True); json.dump(rows, open(cf, 'w'))
    return rows

def ler_anexo1(pdf_path):
    procs, mapa = [], None
    if True:
        if True:
            if True:
                for row in tabelas_pdf(pdf_path):
                    if not row: continue
                    m = mapa_cabecalho(row)
                    if m: mapa = m; continue
                    if not mapa: continue
                    r = {v: limpa(row[i]) if i < len(row) else '' for i, v in mapa.items()}
                    if not r.get('procedimento'):
                        continue
                    procs.append(r)
    out = []
    for r in procs:
        d = {k: r.get(k, '') for k in ['procedimento', 'rn', 'vigencia', 'dut', 'subgrupo', 'grupo', 'capitulo']}
        for s in SEGS: d[s.lower()] = 'X' if r.get(s.lower()) else ''
        m = re.match(r'\D*?(\d{1,3})(?!\d)', d['dut'])  # primeiro número da célula (a célula pode trazer outro texto)
        d['dut'] = str(int(m.group(1))) if m else ''
        out.append(d)
    return out

def texto_pdf(pdf_path):
    return subprocess.run(['pdftotext', '-layout', '-enc', 'UTF-8', pdf_path, '-'], capture_output=True, text=True).stdout

RE_DUT = re.compile(r'^\s{0,1}(\d{1,3})\s*\.\s+(\S.*)$')

def maiusculo(t):
    letras = [c for c in t if c.isalpha()][:10]
    return len(letras) >= 3 and sum(c.isupper() for c in letras) >= 0.75 * len(letras)
LIXO = re.compile(r'^(ROL DE PROCEDIMENTOS|E EVENTOS EM SAÚDE|ANEXO II|DIRETRIZES DE UTILIZAÇÃO|\d{1,3})$'
                  r'|^Publicada em \d{2}/\d{2}/\d{4}|^Diretrizes de Utilização \(anexo II', re.I)  # cabeçalhos e rodapés de página

def ler_anexo2(pdf_path):
    """Divide o Anexo II em DUTs numeradas sequencialmente: {num: {'titulo', 'linhas'}}."""
    linhas = texto_pdf(pdf_path).replace('\f', '\n').split('\n')
    duts, atual, esperado = {}, None, 1
    for ln in linhas:
        if re.search(r'\.{5,}\s*\d*\s*$', ln):  # linha do sumário (pontilhado + página)
            continue
        if atual and re.match(r'^\s*APÊNDICE DE NORMATIVOS', ln): break  # apêndice final não pertence à última DUT
        m = RE_DUT.match(ln)
        if m and int(m.group(1)) == 1 and esperado > 1 and maiusculo(m.group(2)):
            duts, atual, esperado = {}, None, 1  # recomeço da numeração: o corpo vem depois de um sumário
        if m and int(m.group(1)) == esperado and maiusculo(m.group(2)):
            atual = esperado; esperado += 1
            duts[atual] = {'titulo': limpa(m.group(2)), 'linhas': [], 'brutas': [], 'abrindo': True}
            continue
        if atual is None: continue
        d = duts[atual]
        s = limpa(ln)
        if d['abrindo']:  # título que continua na linha seguinte
            if s and ((s == s.upper() and not re.match(r'^\d', s)) or d['titulo'].count('(') > d['titulo'].count(')')):
                d['titulo'] += ' ' + s; continue
            d['abrindo'] = False
        if LIXO.search(s): continue
        d['linhas'].append(s); d['brutas'].append(ln.rstrip())
    for d in duts.values():
        d.pop('abrindo', None)
        while d['linhas'] and not d['linhas'][-1]: d['linhas'].pop()
        while d['linhas'] and not d['linhas'][0]: d['linhas'].pop(0)
    return duts

def paragrafos(linhas):
    out, buf = [], ''
    for s in linhas + ['']:
        novo = not s or re.match(r'^(\d{1,2}\.|[a-z]\)|[•\-–]|[IVX]+\s*[-–.])\s', s)
        if novo and buf: out.append(buf); buf = ''
        if s: buf = (buf + ' ' + s).strip() if buf and not novo else s
    return out

# ------------------------------------------------------------------ comparações
def cobertura(r): return {s for s in SEGS if r[s.lower()]}

def por_nome(procs):
    d = {}
    for r in procs:
        k = chave(r['procedimento'])
        if k in d:  # mesmo nome em mais de um subgrupo: soma coberturas
            d[k] = dict(d[k]); [d[k].__setitem__(s.lower(), d[k][s.lower()] or r[s.lower()]) for s in SEGS]
        else: d[k] = r
    return d

def diff_anexo1(velho, novo):
    a, b = por_nome(velho), por_nome(novo)
    inc = sorted(b[k]['procedimento'] for k in b.keys() - a.keys())
    exc = sorted(a[k]['procedimento'] for k in a.keys() - b.keys())
    alt = []
    for k in sorted(a.keys() & b.keys(), key=lambda k: b[k]['procedimento']):
        mud = []
        ca, cb = cobertura(a[k]), cobertura(b[k])
        if ca != cb:
            mud.append('cobertura: ' + ', '.join([f'+{s}' for s in sorted(cb - ca)] + [f'−{s}' for s in sorted(ca - cb)]))
        if a[k]['dut'] != b[k]['dut']:
            mud.append(f"DUT: {a[k]['dut'] or '—'} → {b[k]['dut'] or '—'}")
        if mud: alt.append([b[k]['procedimento'], '; '.join(mud)])
    return {'incluidos': inc, 'excluidos': exc, 'alterados': alt}

def norm_dut(d): return chave(d['titulo'] + ' ' + ' '.join(d['linhas']))

def diff_anexo2(velho, novo):
    inc = [[n, novo[n]['titulo']] for n in sorted(novo.keys() - velho.keys())]
    exc = [[n, velho[n]['titulo']] for n in sorted(velho.keys() - novo.keys())]
    alt = [[n, novo[n]['titulo']] for n in sorted(novo.keys() & velho.keys()) if norm_dut(novo[n]) != norm_dut(velho[n])]
    return {'incluidas': inc, 'excluidas': exc, 'alteradas': alt}

# ------------------------------------------------------------------ principal
def main():
    versoes = json.load(open(os.path.join(VDIR, 'versoes.json')))
    cache = json.load(open(CACHE)) if os.path.exists(CACHE) else {}
    cache.setdefault('diffs', {}); cache.setdefault('ndut', {})
    atos = {r['titulo']: r for r in csv.DictReader(open(os.path.join(REPO, 'dados', 'atos-ans.csv')))}
    def link_ato(titulo, base):
        r = atos.get(titulo)
        if not r: return esc(titulo)
        return f"[{r['sigla']} {r['numero']}/{r['ano']}]({os.path.relpath(os.path.join(REPO, r['arquivo']), base)})"

    # cadeias de versões por anexo (mais recente primeiro)
    cadeias = collections.defaultdict(list)
    atuais = sorted(f for f in os.listdir(ADIR) if os.path.isfile(os.path.join(ADIR, f)))
    for v in versoes:
        if v['versao_atual']:
            nome = v['arquivo']
            if not os.path.exists(os.path.join(ADIR, nome)):
                rom = {1: 'I', 2: 'II', 3: 'III', 4: 'IV'}[v['anexo']]
                cand = [f for f in atuais if re.match(rf'ANEXO\s+{rom}\b', f, re.I) and f.lower().endswith('.pdf')]
                nome = cand[0] if cand else nome
            cadeias[v['anexo']].append(dict(v, caminho=os.path.join(ADIR, nome)))
        elif v.get('arquivo_local'):
            cadeias[v['anexo']].append(dict(v, caminho=os.path.join(VDIR, v['arquivo_local'])))
    for n in cadeias: cadeias[n] = [v for v in cadeias[n] if os.path.exists(v['caminho'])]

    os.makedirs(os.path.join(OUT, 'historico'), exist_ok=True)
    # --- Anexo I vigente
    a1 = cadeias[1][0]['caminho']; h1 = sha(a1)
    pcsv = os.path.join(OUT, 'procedimentos.csv')
    campos = ['procedimento', 'od', 'amb', 'hco', 'hso', 'ref', 'pac', 'dut', 'rn', 'vigencia', 'subgrupo', 'grupo', 'capitulo']
    parse_cache = {}
    if cache.get('anexo1_sha') == h1 and os.path.exists(pcsv):
        procs = list(csv.DictReader(open(pcsv)))
    else:
        log('lendo Anexo I vigente'); procs = ler_anexo1(a1)
        with open(pcsv, 'w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=campos); w.writeheader(); w.writerows(procs)
        cache['anexo1_sha'] = h1
    parse_cache[h1] = procs
    # --- histórico do Anexo I
    c1 = cadeias[1]
    for i in range(len(c1) - 1, 0, -1):
        velho, novo = c1[i], c1[i - 1]
        k = f"1|{sha(velho['caminho'])}|{sha(novo['caminho'])}"
        if k in cache['diffs']: continue
        for v in (velho, novo):
            h = sha(v['caminho'])
            if h not in parse_cache: log('lendo', os.path.basename(v['caminho'])); parse_cache[h] = ler_anexo1(v['caminho'])
        cache['diffs'][k] = diff_anexo1(parse_cache[sha(velho['caminho'])], parse_cache[sha(novo['caminho'])])
        json.dump(cache, open(CACHE, 'w'), ensure_ascii=False)
    # --- Anexo II
    c2 = cadeias[2]
    duts = ler_anexo2(c2[0]['caminho'])
    dut_cache = {}
    for i in range(len(c2) - 1, 0, -1):
        velho, novo = c2[i], c2[i - 1]
        k = f"2|{sha(velho['caminho'])}|{sha(novo['caminho'])}"
        if k in cache['diffs']: continue
        for v in (velho, novo):
            h = sha(v['caminho'])
            if h not in dut_cache: dut_cache[h] = ler_anexo2(v['caminho'])
        cache['diffs'][k] = diff_anexo2(dut_cache[sha(velho['caminho'])], dut_cache[sha(novo['caminho'])])
    json.dump(cache, open(CACHE, 'w'), ensure_ascii=False, indent=0, sort_keys=True)

    # --- eventos do histórico, agrupados pela norma que gerou a nova versão
    eventos = collections.OrderedDict()
    for n, cadeia in ((1, c1), (2, c2), (3, cadeias[3]), (4, cadeias[4])):
        for i in range(len(cadeia) - 1, 0, -1):
            velho, novo = cadeia[i], cadeia[i - 1]
            k = f"{n}|{sha(velho['caminho'])}|{sha(novo['caminho'])}"
            norma = velho['substituida_por'] or 'Norma não identificada'
            dt = velho['data_vinculo']
            ev = eventos.setdefault(norma, {'norma': norma, 'data': dt, 'anexos': {}})
            ev['anexos'][n] = {'diff': cache['diffs'].get(k), 'antes': velho, 'depois': novo}
    def data_ord(ev):
        r = atos.get(ev['norma']); d = (r or {}).get('data_dou') or ev['data']
        return d[6:] + d[3:5] + d[:2]
    eventos = sorted(eventos.values(), key=data_ord, reverse=True)

    # ------------------------------------------------------------ saídas
    # anexos vigentes com nomes estáveis
    av = os.path.join(OUT, 'anexos-vigentes'); os.makedirs(av, exist_ok=True)
    vig_lin = []
    for n in sorted(cadeias):
        src = cadeias[n][0]['caminho']; dst = os.path.join(av, ARQ_ESTAVEL[n] + '.pdf')
        if not (os.path.exists(dst) and sha(dst) == sha(src)): shutil.copyfile(src, dst)
        txt = src[:-4] + '.txt'
        if os.path.exists(txt):
            d2 = dst[:-4] + '.txt'
            if not (os.path.exists(d2) and open(d2).read() == open(txt).read()): shutil.copyfile(txt, d2)
        vig_lin.append(f"| {NOMES_ANEXOS[n]} | [PDF]({ARQ_ESTAVEL[n]}.pdf) · [texto]({ARQ_ESTAVEL[n]}.txt) | {esc(os.path.basename(src))} |")
    open(os.path.join(av, 'README.md'), 'w').write(
        '# Anexos vigentes da RN nº 465/2021\n\nCópias da versão em vigor de cada anexo, com nomes fixos (o conteúdo é substituído automaticamente quando a ANS publica uma nova versão).\n\n'
        '| Anexo | Arquivos | Nome do arquivo na ANS |\n| --- | --- | --- |\n' + '\n'.join(vig_lin) + '\n')

    # procedimentos por capítulo
    pdir = os.path.join(OUT, 'procedimentos'); os.makedirs(pdir, exist_ok=True)
    for f in os.listdir(pdir): os.remove(os.path.join(pdir, f))
    caps = collections.OrderedDict()
    for r in procs: caps.setdefault(r['capitulo'] or 'SEM CAPÍTULO', []).append(r)
    idx = ['# Procedimentos do Rol vigente por capítulo\n', f'{len(procs)} itens no Anexo I vigente. Também disponível como planilha: [procedimentos.csv](../procedimentos.csv).\n',
           'Legenda: **OD** odontológico · **AMB** ambulatorial · **HCO** hospitalar com obstetrícia · **HSO** hospitalar sem obstetrícia · **REF** plano-referência · **PAC** procedimento de alta complexidade · **DUT** diretriz de utilização.\n',
           '| Capítulo | Itens |', '| --- | ---: |']
    for i, (cap, rs) in enumerate(caps.items(), 1):
        fn = f'{i:02d}-{slug(cap)}.md'
        idx.append(f'| [{cap.title()}]({fn}) | {len(rs)} |')
        L = [f'# {cap.title()}\n', f'[← Capítulos](README.md) · {len(rs)} itens\n']
        grupo = sub = None
        for r in rs:
            if r['grupo'] != grupo:
                grupo = r['grupo']; sub = None; L.append(f'\n## {grupo.title()}\n')
            if r['subgrupo'] != sub:
                sub = r['subgrupo']; L += [f'\n### {sub.title()}\n', '| Procedimento | OD | AMB | HCO | HSO | REF | PAC | DUT | RN / vigência |', '| --- | :-: | :-: | :-: | :-: | :-: | :-: | :-: | --- |']
            dut = f"[{r['dut']}](../diretrizes-de-utilizacao/DUT-{int(r['dut']):03d}.md)" if r['dut'] else ''
            L.append(f"| {esc(r['procedimento'])} | " + ' | '.join('✔' if r[s.lower()] else '' for s in SEGS) + f" | {dut} | {esc(' '.join(x for x in (r['rn'], r['vigencia']) if x))} |")
        open(os.path.join(pdir, fn), 'w').write('\n'.join(L) + '\n')
    open(os.path.join(pdir, 'README.md'), 'w').write('\n'.join(idx) + '\n')

    # DUTs
    ddir = os.path.join(OUT, 'diretrizes-de-utilizacao'); os.makedirs(ddir, exist_ok=True)
    for f in os.listdir(ddir): os.remove(os.path.join(ddir, f))
    procs_dut = collections.defaultdict(list)
    for r in procs:
        if r['dut']: procs_dut[int(r['dut'])].append(r['procedimento'])
    hist_dut = collections.defaultdict(list)
    for ev in eventos:
        d2 = (ev['anexos'].get(2) or {}).get('diff')
        if not d2: continue
        for tipo, lista in (('incluída', d2['incluidas']), ('alterada', d2['alteradas']), ('excluída', d2['excluidas'])):
            for n, t in lista: hist_dut[int(n)].append((ev, tipo))
    di = ['# Diretrizes de Utilização (DUT)\n', f'{len(duts)} diretrizes no Anexo II vigente. As DUTs definem os critérios para que determinados procedimentos do Anexo I sejam de cobertura obrigatória.\n',
          '| DUT | Título | Alterações desde 2021 |', '| ---: | --- | ---: |']
    for n, d in sorted(duts.items()):
        fn = f'DUT-{n:03d}.md'
        di.append(f"| [{n}]({fn}) | {esc(d['titulo'].title())} | {len(hist_dut[n]) or ''} |")
        L = [f"# DUT {n} — {d['titulo']}\n", f"[← Todas as DUTs](README.md) · Fonte: Anexo II da [RN nº 465/2021](../../{RN_MD}), versão vigente ({esc(os.path.basename(c2[0]['caminho']))})\n"]
        if procs_dut.get(n):
            L.append('**Procedimentos do Anexo I vinculados a esta DUT:**\n'); L += [f'- {p}' for p in procs_dut[n]]; L.append('')
        L.append('## Texto vigente\n')
        cheias = [b for b in d['brutas'] if b.strip()]
        tabular = cheias and sum(1 for b in cheias if re.search(r'\S\s{4,}\S', b.strip()) or len(b) - len(b.lstrip()) >= 20) > 0.3 * len(cheias)
        if tabular:  # DUT em forma de tabela: mantém o alinhamento das colunas do PDF
            recuo = min(len(b) - len(b.lstrip()) for b in cheias)
            L += ['```text'] + [b[recuo:] for b in d['brutas']] + ['```', '']
        else:
            L += [p + '\n' for p in paragrafos(d['linhas'])]
        if hist_dut[n]:
            L.append('## Histórico de alterações desta DUT\n')
            L += [f"- {ev['data']} — {tipo} por {link_ato(ev['norma'], ddir)}" for ev, tipo in hist_dut[n]]
        L.append('\n> Texto extraído automaticamente do PDF oficial; em caso de dúvida, consulte o [Anexo II vigente](../anexos-vigentes/Anexo-II-Diretrizes-de-Utilizacao.pdf).')
        open(os.path.join(ddir, fn), 'w').write('\n'.join(L) + '\n')
    open(os.path.join(ddir, 'README.md'), 'w').write('\n'.join(di) + '\n')

    # histórico
    hdir = os.path.join(OUT, 'historico')
    H = ['# Histórico de alterações do Rol (RN nº 465/2021)\n',
         'Cada bloco corresponde a uma norma que gerou nova versão dos anexos da RN nº 465/2021. As listas são obtidas comparando automaticamente '
         'a versão anterior com a nova versão de cada anexo (mudanças apenas de redação no nome de um procedimento aparecem como exclusão + inclusão). '
         'Quando a ANS publica uma única nova versão de um anexo consolidando mais de uma norma, as mudanças aparecem na norma que a ANS registrou como responsável pela versão.\n',
         'Veja também: [normas anteriores sobre o Rol (1998–2021)](normas-anteriores.md).\n']
    rel_v = lambda v: os.path.relpath(v['caminho'], hdir).replace(' ', '%20')
    resumo_recente = None
    for ev in eventos:
        H.append(f"## {link_ato(ev['norma'], hdir)} — vínculo em {ev['data']}\n")
        r = atos.get(ev['norma'])
        if r and r['ementa']: H.append(f"_{esc(r['ementa'][:400])}_\n")
        partes = []
        for n in sorted(ev['anexos']):
            x = ev['anexos'][n]; d = x['diff']
            H.append(f"**{NOMES_ANEXOS[n]}** — versão anterior: [{esc(x['antes']['arquivo'])}]({rel_v(x['antes'])}) → nova: [{esc(x['depois']['arquivo'])}]({rel_v(x['depois'])})\n")
            if n == 1 and d:
                for rot, k in (('Incluídos', 'incluidos'), ('Excluídos', 'excluidos')):
                    if d[k]: H.append(f'- {rot} ({len(d[k])}): ' + '; '.join(esc(p) for p in d[k]))
                if d['alterados']: H.append(f"- Alterados ({len(d['alterados'])}): " + '; '.join(f'{esc(p)} ({m})' for p, m in d['alterados']))
                if not any(d.values()): H.append('- Sem mudança na lista de procedimentos, coberturas ou DUTs (ajustes de formatação, vigência ou textos).')
                partes.append(f"Anexo I: {len(d['incluidos'])} incluídos, {len(d['excluidos'])} excluídos, {len(d['alterados'])} alterados")
            elif n == 2 and d:
                for rot, k in (('DUTs incluídas', 'incluidas'), ('DUTs alteradas', 'alteradas'), ('DUTs excluídas', 'excluidas')):
                    if d[k]: H.append(f'- {rot} ({len(d[k])}): ' + '; '.join(f"[{nn}](../diretrizes-de-utilizacao/DUT-{int(nn):03d}.md) {esc(t.title())}" if k != 'excluidas' else f"{nn} {esc(t.title())}" for nn, t in d[k]))
                if not any(d.values()): H.append('- Sem mudança no texto das DUTs.')
                partes.append(f"Anexo II: {len(d['incluidas'])} DUTs incluídas, {len(d['alteradas'])} alteradas, {len(d['excluidas'])} excluídas")
            H.append('')
        if resumo_recente is None:
            resumo_recente = f"{(atos.get(ev['norma']) or {}).get('sigla', '')} {(atos.get(ev['norma']) or {}).get('numero', '')}/{(atos.get(ev['norma']) or {}).get('ano', '')}".strip(' /') + ' — ' + '; '.join(partes)
    open(os.path.join(hdir, 'README.md'), 'w').write('\n'.join(H) + '\n')

    # normas anteriores e linha do tempo
    rol = [r for r in atos.values() if ('Rol de Procedimentos' in r['assunto'] or re.search(r'\bRol de Procedimentos\b|\bRol\b.*\bProcedimentos\b', r['ementa'], re.I))
           and r['categoria'].split('/')[0] in ('01-resolucoes-normativas', '03-resolucoes-diretoria-colegiada', '04-resolucoes-consu', '05-sumulas-normativas', '02-instrucoes-normativas')]
    rol.sort(key=lambda r: r['data_dou'][6:] + r['data_dou'][3:5] + r['data_dou'][:2])
    N = ['# Normas sobre o Rol de Procedimentos — linha do tempo completa\n',
         'Todos os atos do acervo que tratam do Rol de Procedimentos e Eventos em Saúde (assunto "Cobertura Assistencial - Rol de Procedimentos" ou ementa que menciona o Rol), do mais antigo ao mais recente. '
         'Inclui os Róis que antecederam a RN nº 465/2021 e todas as normas que a alteraram.\n', '| Data DOU | Norma | Situação | Ementa |', '| --- | --- | --- | --- |']
    for r in rol:
        N.append(f"| {r['data_dou']} | {link_ato(r['titulo'], hdir)} | {r['status']} | {esc(r['ementa'][:260])}{'…' if len(r['ementa']) > 260 else ''} |")
    open(os.path.join(hdir, 'normas-anteriores.md'), 'w').write('\n'.join(N) + '\n')

    # README da pasta
    cont = collections.Counter(s for r in procs for s in SEGS if r[s.lower()])
    ult = eventos[0] if eventos else None
    rn = atos.get('Resolução Normativa - RN ANS nº 465, de 25 fevereiro 2021') or {}
    R = ['# Rol de Procedimentos e Eventos em Saúde\n',
         'O **Rol** é a lista de consultas, exames, cirurgias e tratamentos que os planos de saúde são obrigados a cobrir, conforme a segmentação contratada '
         '(ambulatorial, hospitalar com ou sem obstetrícia, referência ou odontológico). Vale para planos contratados a partir de 2 de janeiro de 1999 e para os adaptados à Lei nº 9.656/1998. '
         f'Atualmente é estabelecido pela [RN nº 465/2021](../{RN_MD}) e suas alterações.\n',
         '> Esta pasta é **atualizada automaticamente** sempre que a ANS publica nova versão dos anexos da RN nº 465/2021. As alterações também são registradas em [NOVIDADES.md](../NOVIDADES.md).\n',
         '## Situação atual\n', '| | |', '| --- | --- |',
         f"| Norma vigente | [RN nº 465/2021](../{RN_MD}) — {rn.get('status', 'Vigente')} |",
         f"| Última alteração dos anexos | {link_ato(ult['norma'], OUT) + ' (vínculo em ' + ult['data'] + ')' if ult else '—'} |",
         f"| Normas que alteraram a RN nº 465/2021 | {rn.get('qtd_alteradoras', '')} |",
         f"| Itens no Anexo I | {len(procs)} |",
         f"| Diretrizes de Utilização (DUT) | {len(duts)} |",
         '| Itens por segmentação | ' + ' · '.join(f'{s}: {cont[s]}' for s in SEGS) + ' |', '',
         '## Conteúdo\n', '| Item | Descrição |', '| --- | --- |',
         '| [Anexos vigentes](anexos-vigentes/README.md) | PDFs oficiais em vigor (Anexos I a IV) e versão em texto |',
         '| [Procedimentos por capítulo](procedimentos/README.md) | Anexo I em tabelas navegáveis, com coberturas por segmentação e link para a DUT |',
         '| [procedimentos.csv](procedimentos.csv) | Anexo I em planilha (abre no Excel) |',
         '| [Diretrizes de Utilização](diretrizes-de-utilizacao/README.md) | Anexo II dividido em um arquivo por DUT, com procedimentos vinculados e histórico |',
         '| [Histórico de alterações](historico/README.md) | O que cada norma incluiu, excluiu ou alterou no Rol desde 2021, com as versões anteriores dos anexos |',
         '| [Linha do tempo das normas sobre o Rol](historico/normas-anteriores.md) | Todos os Róis e alterações desde 1998 |', '']
    if eventos:
        R.append('## Últimas alterações\n')
        for ev in eventos[:8]:
            r = atos.get(ev['norma']) or {}
            R.append(f"- **{link_ato(ev['norma'], OUT)}** ({ev['data']}) — {esc(r.get('ementa', '')[:220])}{'…' if len(r.get('ementa', '')) > 220 else ''}")
        R.append('\n[Ver histórico completo →](historico/README.md)')
    R.append('\n> Tabelas e textos extraídos automaticamente dos PDFs oficiais da ANS. Em caso de divergência, prevalecem os [anexos oficiais](anexos-vigentes/README.md) e a publicação no Diário Oficial da União.')
    open(os.path.join(OUT, 'README.md'), 'w').write('\n'.join(R) + '\n')
    if resumo_recente: open(os.path.join(OUT, 'historico', '.ultima-alteracao'), 'w').write(resumo_recente + '\n')
    log('ok:', len(procs), 'procedimentos,', len(duts), 'DUTs,', len(eventos), 'normas no histórico')

main()
