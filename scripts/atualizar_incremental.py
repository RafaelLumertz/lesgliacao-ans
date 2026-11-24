"""Atualização automática do acervo (executada diariamente pelo GitHub Actions).

1. Procura atos novos no Portal de Legislação da ANS (ou, com --varredura, relê a lista inteira
   para detectar mudanças de situação, como revogações).
2. Baixa texto, anexos e histórico dos atos novos/alterados e das normas que eles alteram ou revogam.
3. Rebaixa as leis do Planalto, regrava as que mudaram e inclui automaticamente leis novas
   que alterem a Lei nº 9.656/1998, a Lei nº 9.961/2000, a Lei nº 10.185/2001 ou a MP nº 2.177-44/2001.
4. Atualiza índices, README e registra o que mudou em NOVIDADES.md.

Uso: python3 scripts/atualizar_incremental.py [--varredura] [--trabalho DIR]
"""
import sys, os, re, json, csv, subprocess, datetime, tempfile, urllib.request, urllib.parse, html as htmlmod

AQUI = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(AQUI)
VARREDURA = '--varredura' in sys.argv
W = sys.argv[sys.argv.index('--trabalho') + 1] if '--trabalho' in sys.argv else tempfile.mkdtemp(prefix='acervo-')
HOJE = datetime.date.today()
UA = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36'
TIPOS = {'Resolução Normativa', 'Instrução Normativa', 'Instrução Normativa Conjunta', 'Resolução de Diretoria Colegiada',
         'Resolução CONSU', 'Súmula Normativa', 'Resolução Regimental', 'Parecer da PROGE', 'Entendimento da DIFIS',
         'Resolução Operacional', 'Comunicado', 'Portaria', 'Despacho', 'Instruções de Serviços',
         'Instrução de serviço Conjunta', 'Resoluções Administrativas', 'Resolução Especial'}

ACOMPANHAR = ['24989']  # RN nº 465/2021 — Rol de Procedimentos

def log(*a): print('[atualizar]', *a, flush=True)

def run(cmd, stdin=None):
    log(' '.join(cmd)[:200])
    return subprocess.run(cmd, input=stdin, text=True, cwd=AQUI, check=False)

def git_mudancas():
    out = subprocess.run(['git', 'status', '--porcelain'], cwd=REPO, capture_output=True, text=True).stdout
    return [l for l in out.splitlines() if not l.endswith('leis/_indice.tsv')]

# ---------------------------------------------------------------- ANS
def atualizar_ans():
    csvp = os.path.join(REPO, 'dados', 'atos-ans.csv')
    linhas = list(csv.DictReader(open(csvp)))
    por_id = {r['id_ans']: r for r in linhas}
    por_titulo = {}
    for r in linhas: por_titulo.setdefault(r['titulo'], []).append(r['id_ans'])
    conhecidos = {r['titulo'] + '|' + r['data_dou']: r['id_ans'] for r in linhas}
    os.makedirs(os.path.join(W, 'index'), exist_ok=True); os.makedirs(os.path.join(W, 'raw'), exist_ok=True)
    kf, nf = os.path.join(W, 'conhecidos.json'), os.path.join(W, 'lista.jsonl')
    json.dump(conhecidos, open(kf, 'w'), ensure_ascii=False)
    run(['node', 'novidades.js', kf, nf, 'todas' if VARREDURA else '5'])
    lista = [json.loads(l) for l in open(nf)] if os.path.exists(nf) else []
    novos = [r for r in lista if r.get('id') and not r.get('conhecido') and r['tipo'] in TIPOS and r['id'] not in por_id]
    mudados = [r for r in lista if r.get('conhecido') and r['id'] in por_id and r['status'] and r['status'] != por_id[r['id']]['status']]
    log(f'{len(lista)} atos lidos; {len(novos)} novos; {len(mudados)} com situação alterada')
    with open(os.path.join(W, 'index', 'atualizacao.jsonl'), 'w') as f:
        for r in novos + mudados: f.write(json.dumps(r, ensure_ascii=False) + '\n')
    baixar = [r['id'] for r in novos + mudados]
    # atos acompanhados diariamente mesmo sem ato novo (ex.: RN 465/2021, o Rol de Procedimentos)
    acompanhar = [i for i in ACOMPANHAR if i in por_id and i not in baixar]
    if baixar or acompanhar:
        run(['node', 'fetch_detail.js', os.path.join(W, 'raw')], stdin=' '.join(baixar + acompanhar))
    # normas alteradas/revogadas pelos atos novos também são atualizadas
    afetados = set()
    for r in novos:
        mp = os.path.join(W, 'raw', r['id'], 'meta.json')
        if not os.path.exists(mp): continue
        for g in json.load(open(mp)).get('grids', []):
            if re.match(r'Legislações (alteradas|revogadas)', g.get('heading') or ''):
                for row in g['rows']:
                    afetados.update(i for i in por_titulo.get(row[0], []) if i not in baixar)
    if afetados:
        log(f'{len(afetados)} normas alteradas/revogadas pelos atos novos serão atualizadas')
        run(['node', 'fetch_detail.js', os.path.join(W, 'raw')], stdin=' '.join(sorted(afetados)))
    # versões anteriores de anexos
    com_versoes = []
    for i in os.listdir(os.path.join(W, 'raw')):
        mp = os.path.join(W, 'raw', i, 'meta.json')
        if os.path.exists(mp) and any(not (g.get('heading') or '').startswith('Legisla') and len(g['rows']) > 1
                                      for g in json.load(open(mp)).get('grids', [])):
            com_versoes.append(i)
    if com_versoes:
        existentes = {}
        for i in com_versoes:
            if i in por_id:
                arq = por_id[i]['arquivo']
                existentes[i] = os.path.join(REPO, os.path.dirname(arq), 'anexos', os.path.basename(arq)[:-3], 'versoes-anteriores')
        os.environ['VERSOES_EXISTENTES'] = json.dumps(existentes)
        run(['node', 'fetch_versions.js', os.path.join(W, 'raw')] + com_versoes)
    if os.listdir(os.path.join(W, 'raw')):
        run(['python3', 'build_ans.py', os.path.join(W, 'index'), os.path.join(W, 'raw'), REPO, '--incremental'])
    novos_csv = {r['id_ans']: r for r in csv.DictReader(open(csvp))}
    def item(i):
        r = novos_csv.get(i)
        if not r: return None
        em = re.sub(r'\s+', ' ', r['ementa'])[:200]
        return f"- [{r['sigla']} {r['numero']}/{r['ano']}]({r['arquivo']}) — {r['status']} — {em}"
    return ([x for x in map(item, [r['id'] for r in novos]) if x],
            [x for x in map(item, [r['id'] for r in mudados] + sorted(afetados)) if x])

# ---------------------------------------------------------------- Planalto
LEIS_BASE = {'lei-9656-1998': '02-alteracoes-lei-9656', 'lei-9961-2000': '04-agencias-reguladoras',
             'lei-10185-2001': '01-marco-legal', 'mp-2177-44-2001': '02-alteracoes-lei-9656'}
LINK_ALT = re.compile(r'<a[^>]+href="([^"#]+)[^"]*"[^>]*>\s*\((?:Redação dada|Incluíd[oa]|Revogad[oa]|Vide|Acrescid[oa]|Renumerad[oa])[^<]*?'
                      r'((Lei Complementar|Lei|Medida Provisória|Decreto)\s+n[ºo°]\s*([\d\.\-]+),\s*de\s*(\d{4}))', re.I | re.S)

def baixar_planalto(caminho, destino):
    url = 'https://www.planalto.gov.br/ccivil_03/' + caminho
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html', 'Accept-Language': 'pt-BR'})
    for tentativa in range(3):
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                dados = resp.read()
            if len(dados) > 1000:
                open(destino, 'wb').write(dados); return True
        except Exception as e:
            log('falha ao baixar', url, e)
    return False

def atualizar_leis():
    lista_p = os.path.join(AQUI, 'planalto_list.tsv')
    linhas = list(csv.DictReader(open(lista_p), delimiter='\t'))
    caminhos = {l['path'].lower() for l in linhas}
    raw = os.path.join(W, 'planalto'); os.makedirs(raw, exist_ok=True)
    falhas = [l['slug'] for l in linhas if not baixar_planalto(l['path'], os.path.join(raw, l['slug'] + '.htm'))]
    if len(falhas) > len(linhas) / 2:
        log('Planalto indisponível; leis não atualizadas'); return [], []
    # leis novas que alteram as leis-base
    incluidas = []
    for slug, grupo in LEIS_BASE.items():
        f = os.path.join(raw, slug + '.htm')
        if not os.path.exists(f): continue
        h = open(f, 'rb').read().decode('cp1252', 'replace')
        for href, texto, tipo, num, ano in LINK_ALT.findall(h):
            if int(ano) < 2024: continue
            caminho = urllib.parse.urljoin('https://www.planalto.gov.br/ccivil_03/' + [l['path'] for l in linhas if l['slug'] == slug][0], href)
            caminho = caminho.split('/ccivil_03/', 1)[-1]
            if caminho.lower() in caminhos: continue
            sig = {'lei complementar': 'lc', 'lei': 'lei', 'medida provisória': 'mp', 'decreto': 'decreto'}[tipo.lower()]
            novo_slug = f"{sig}-{num.replace('.', '')}-{ano}"
            titulo = f"{htmlmod.unescape(re.sub(r'\s+', ' ', texto))} — altera a norma {slug}"
            if baixar_planalto(caminho, os.path.join(raw, novo_slug + '.htm')):
                linhas.append({'grupo': grupo, 'slug': novo_slug, 'path': caminho, 'titulo': titulo})
                caminhos.add(caminho.lower()); incluidas.append(titulo)
                log('lei nova incluída:', titulo)
    if incluidas:
        with open(lista_p, 'w', newline='') as fo:
            w = csv.DictWriter(fo, fieldnames=['grupo', 'slug', 'path', 'titulo'], delimiter='\t', lineterminator='\n')
            w.writeheader(); w.writerows(linhas)
    for l in linhas:  # mantém o HTML anterior quando o download falhou
        f = os.path.join(raw, l['slug'] + '.htm')
        if not os.path.exists(f):
            antigo = os.path.join(REPO, 'leis', l['grupo'], 'html-original', l['slug'] + '.htm')
            if os.path.exists(antigo): open(f, 'w').write(open(antigo).read())
    p = subprocess.run(['python3', 'conv_planalto.py', raw, os.path.join(REPO, 'leis')], cwd=AQUI, capture_output=True, text=True)
    alteradas = [l.split(':', 1)[1].strip() for l in p.stderr.splitlines() if l.startswith('alterada:')]
    titulos = {l['slug']: (l['titulo'], l['grupo']) for l in linhas}
    alt = [f"- [{titulos[s][0]}](leis/{titulos[s][1]}/{s}.md)" for s in alteradas if s in titulos and titulos[s][0] not in incluidas]
    inc = [f"- [{titulos[s][0]}](leis/{titulos[s][1]}/{s}.md)" for s in titulos if titulos[s][0] in incluidas]
    return inc, alt

# ---------------------------------------------------------------- principal
def main():
    log('diretório de trabalho:', W, '| varredura completa' if VARREDURA else '| modo diário')
    novos, atualizados = atualizar_ans()
    leis_novas, leis_alteradas = atualizar_leis()
    # Rol de Procedimentos: regenera a pasta a partir dos anexos da RN 465/2021
    rol_alterado = None
    p = subprocess.run(['python3', 'build_rol.py', REPO], cwd=AQUI)
    if p.returncode != 0:
        log('falha ao gerar a pasta do Rol (a pasta anterior foi mantida)')
        subprocess.run(['git', 'checkout', '--', 'rol-de-procedimentos'], cwd=REPO)
    elif any('rol-de-procedimentos/' in l for l in git_mudancas()):
        ua = os.path.join(REPO, 'rol-de-procedimentos', 'historico', '.ultima-alteracao')
        rol_alterado = open(ua).read().strip() if os.path.exists(ua) else 'anexos atualizados'
    if not git_mudancas():
        idx = os.path.join(REPO, 'leis', '_indice.tsv')
        if os.path.exists(idx): os.remove(idx)
        log('nenhuma alteração'); return
    subprocess.run(['python3', 'build_docs.py', REPO], cwd=AQUI, check=True)
    blocos = []
    if novos: blocos.append(f'### Novos atos da ANS ({len(novos)})\n\n' + '\n'.join(novos))
    if atualizados: blocos.append(f'### Atos da ANS atualizados ({len(atualizados)})\n\nSituação alterada ou novas alterações/revogações registradas.\n\n' + '\n'.join(atualizados))
    if rol_alterado: blocos.append(f'### Rol de Procedimentos atualizado\n\n- {rol_alterado}\n- Detalhes: [histórico do Rol](rol-de-procedimentos/historico/README.md)')
    if leis_novas: blocos.append(f'### Leis novas incluídas ({len(leis_novas)})\n\n' + '\n'.join(leis_novas))
    if leis_alteradas: blocos.append(f'### Leis com texto atualizado no Planalto ({len(leis_alteradas)})\n\n' + '\n'.join(leis_alteradas))
    if not blocos: blocos.append('Ajustes nos índices.')
    nov = os.path.join(REPO, 'NOVIDADES.md')
    cab = '# Novidades\n\nRegistro automático das atualizações do acervo (mais recentes primeiro).\n'
    antigo = open(nov).read()[len(cab):] if os.path.exists(nov) else ''
    open(nov, 'w').write(cab + f"\n## {HOJE.strftime('%d/%m/%Y')}\n\n" + '\n\n'.join(blocos) + '\n' + antigo)
    resumo = f"{len(novos)} atos novos, {len(atualizados)} atualizados, {len(leis_novas)} leis novas, {len(leis_alteradas)} leis alteradas" + (', Rol atualizado' if rol_alterado else '')
    open(os.path.join(W, 'resumo.txt'), 'w').write(resumo)
    log('concluído:', resumo)

main()
