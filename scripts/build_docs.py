"""Gera README.md, leis/README.md, ans/README.md, HISTORICO.md e dados/leis.csv.
Uso: python3 build_docs.py <repo_dir>"""
import sys, os, csv, json, re, collections, datetime
R = sys.argv[1]
TODAY = datetime.date.today().strftime('%d/%m/%Y')
atos = list(csv.DictReader(open(os.path.join(R, 'dados', 'atos-ans.csv'))))
leis = [l.rstrip('\n').split('\t') for l in open(os.path.join(R, 'leis', '_indice.tsv'))]
os.remove(os.path.join(R, 'leis', '_indice.tsv'))

GRUPOS = {
 '01-marco-legal': 'Marco legal da saúde suplementar',
 '02-alteracoes-lei-9656': 'Leis e MPs que alteraram a Lei nº 9.656/1998',
 '03-historico-medidas-provisorias': 'Histórico: reedições de Medidas Provisórias (1998–2003)',
 '04-agencias-reguladoras': 'Agências reguladoras (organização, pessoal, governança)',
 '05-fiscalizacao-regimes-especiais-processo': 'Fiscalização, regimes especiais e processo administrativo',
 '06-legislacao-correlata': 'Legislação correlata (consumidor, idosos, pessoas com deficiência, SUS, dados pessoais, cooperativas)',
 '07-tributacao': 'Tributação das operadoras (PIS/Cofins, ISS, dedução no IRPF)',
 '08-societario-cooperativas-contratos': 'Direito societário, contratos e previdência complementar',
 '09-consumidor': 'Defesa do consumidor: sanções, SAC e crimes',
 '10-assistencia-coberturas-direitos': 'Assistência à saúde: coberturas, direitos dos pacientes, telessaúde e exercício profissional',
}
GRUPOS = {'00-constituicao': 'Constituição Federal', **GRUPOS}
CATN = collections.OrderedDict([
 ('01-resolucoes-normativas', 'Resoluções Normativas (RN)'),
 ('02-instrucoes-normativas', 'Instruções Normativas (IN)'),
 ('03-resolucoes-diretoria-colegiada', 'Resoluções de Diretoria Colegiada (RDC) — 2000 a 2002'),
 ('04-resolucoes-consu', 'Resoluções do CONSU — 1998 a 2000'),
 ('05-sumulas-normativas', 'Súmulas Normativas'),
 ('06-resolucoes-regimentais', 'Resoluções Regimentais (RR)'),
 ('07-pareceres-proge', 'Pareceres da PROGE'),
 ('08-entendimentos-difis', 'Entendimentos da DIFIS'),
 ('09-resolucoes-operacionais', 'Resoluções Operacionais (RO) — operadoras específicas'),
 ('10-comunicados', 'Comunicados'),
 ('11-portarias', 'Portarias'),
 ('12-despachos', 'Despachos'),
 ('13-instrucoes-de-servico', 'Instruções de Serviço'),
 ('14-resolucoes-administrativas', 'Resoluções Administrativas'),
 ('15-resolucoes-especiais', 'Resoluções Especiais'),
])
for a in atos: a['categoria'] = a['categoria'].split('/')[0]

# dados/leis.csv + leis/README.md
with open(os.path.join(R, 'dados', 'leis.csv'), 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['grupo', 'arquivo', 'titulo', 'fonte'])
    for g, slug, t, url in leis: w.writerow([g, f'leis/{g}/{slug}.md', t, url])
L = ['# Leis, decretos e medidas provisórias\n',
     'Textos obtidos no Portal da Legislação do Planalto (www.planalto.gov.br). Cada norma está em Markdown '
     '(com dispositivos revogados ~~tachados~~ e as notas "Redação dada por", "Incluído por", "Revogado por") e no HTML original, '
     'na subpasta `html-original/` de cada grupo.\n']
for g, nome in GRUPOS.items():
    L.append(f'## {nome}\n')
    L += [f'- [{t}]({g}/{slug}.md)' for gg, slug, t, url in leis if gg == g]
    L.append('')
open(os.path.join(R, 'leis', 'README.md'), 'w').write('\n'.join(L))

# ans/README.md
cnt = collections.Counter(a['categoria'] for a in atos)
vig = collections.Counter(a['categoria'] for a in atos if a['status'] == 'Vigente')
anx = sum(int(a['qtd_anexos']) for a in atos)
A = ['# Atos normativos da ANS\n',
     'Coletados do [Portal de Legislação da ANS](https://componentes-portal.ans.gov.br/link/legislacoes). '
     'Cada ato tem um arquivo `.md` com metadados (status, datas de publicação, vigência, alteração e revogação), ementa, texto integral, '
     'anexos (PDF + versão em texto), histórico de versões dos anexos, normas alteradoras e revogadoras, fundamentação legal e participação social.\n',
     '| Categoria | Atos | Vigentes |', '| --- | ---: | ---: |']
for c, n in CATN.items():
    if cnt[c]: A.append(f'| [{n}]({c}/README.md) | {cnt[c]} | {vig[c]} |')
A.append(f'| **Total** | **{sum(cnt.values())}** | **{sum(vig.values())}** |\n')
A.append(f'Anexos baixados: **{anx}** arquivos.\n')
A.append('## Atos com mais alterações\n\nNormas que mais receberam alterações ao longo do tempo (bom ponto de partida para entender a evolução da regulação):\n')
A.append('| Ato | Situação | Alterações | Ementa |\n| --- | --- | ---: | --- |')
for a in sorted(atos, key=lambda a: -int(a['qtd_alteradoras']))[:25]:
    if int(a['qtd_alteradoras']) == 0: break
    A.append(f"| [{a['sigla']} {a['numero']}/{a['ano']}]({a['arquivo'][4:]}) | {a['status']} | {a['qtd_alteradoras']} | {a['ementa'][:160].replace('|', '/')}{'…' if len(a['ementa']) > 160 else ''} |")
A.append('\n## Atos por tema\n\nAtos vigentes de caráter geral (as Resoluções Operacionais, que tratam de operadoras específicas, estão na [pasta própria](09-resolucoes-operacionais/README.md)).\n')
temas = collections.defaultdict(list)
for a in atos:
    if a['status'] == 'Vigente' and a['tema'] and a['categoria'] != '09-resolucoes-operacionais': temas[a['tema']].append(a)
for t in sorted(temas):
    A.append(f'<details><summary><b>{t}</b> ({len(temas[t])} atos vigentes)</summary>\n')
    for a in sorted(temas[t], key=lambda a: (a['assunto'], a['sigla'], -int(a['ano']))):
        A.append(f"- [{a['sigla']} {a['numero']}/{a['ano']}]({a['arquivo'][4:]}) — _{a['assunto']}_ — {a['ementa'][:140]}{'…' if len(a['ementa']) > 140 else ''}")
    A.append('\n</details>\n')
open(os.path.join(R, 'ans', 'README.md'), 'w').write('\n'.join(A) + '\n')

# HISTORICO.md
por_ano = collections.defaultdict(collections.Counter)
for a in atos:
    if a['ano'].isdigit(): por_ano[int(a['ano'])][a['sigla'] if a['sigla'] in ('RN', 'RDC', 'CONSU', 'RR', 'RO') else ('IN' if a['sigla'].startswith('IN') else 'Outros')] += 1
H = ['# Histórico da regulação da saúde suplementar\n',
 'Linha do tempo dos principais marcos legais (com links para os textos neste repositório) e produção normativa da ANS por ano.\n',
 '## Marcos legais\n',
 '| Ano | Marco | Texto |', '| --- | --- | --- |']
MARCOS = [
 ('1966', 'Decreto-Lei nº 73 institui o Sistema Nacional de Seguros Privados (base para o seguro-saúde antes da Lei nº 9.656)', 'leis/05-fiscalizacao-regimes-especiais-processo/decreto-lei-73-1966.md'),
 ('1974', 'Lei nº 6.024 — intervenção e liquidação extrajudicial; aplicada às operadoras de planos de saúde', 'leis/05-fiscalizacao-regimes-especiais-processo/lei-6024-1974.md'),
 ('1990', 'Código de Defesa do Consumidor (Lei nº 8.078), aplicável aos contratos de planos de saúde', 'leis/06-legislacao-correlata/lei-8078-1990.md'),
 ('1998', 'Lei nº 9.656 — marco regulatório dos planos e seguros privados de assistência à saúde', 'leis/01-marco-legal/lei-9656-1998.md'),
 ('1998', 'Resoluções do CONSU (Conselho de Saúde Suplementar) regulamentam a Lei nº 9.656', 'ans/04-resolucoes-consu/README.md'),
 ('1998–2001', 'Sucessivas Medidas Provisórias alteram a Lei nº 9.656 (MP nº 1.665 e reedições)', 'leis/README.md#histórico-reedições-de-medidas-provisórias-19982003'),
 ('2000', 'Lei nº 9.961 cria a Agência Nacional de Saúde Suplementar (ANS); Decreto nº 3.327 aprova seu regulamento', 'leis/01-marco-legal/lei-9961-2000.md'),
 ('2000–2002', 'Resoluções de Diretoria Colegiada (RDC) da ANS', 'ans/03-resolucoes-diretoria-colegiada/README.md'),
 ('2001', 'Lei nº 10.185 — seguradoras especializadas em saúde', 'leis/01-marco-legal/lei-10185-2001.md'),
 ('2001', 'MP nº 2.177-44 — última reedição; permanece em vigor por força da EC nº 32/2001', 'leis/01-marco-legal/mp-2177-44-2001.md'),
 ('2002', 'Início da série de Resoluções Normativas (RN nº 1/2002)', 'ans/01-resolucoes-normativas/README.md'),
 ('2003', 'Estatuto da Pessoa Idosa (Lei nº 10.741) — vedação de discriminação por idade nos planos', 'leis/06-legislacao-correlata/lei-10741-2003.md'),
 ('2004', 'Lei nº 10.850 — programas de incentivo à adaptação de contratos antigos', 'leis/01-marco-legal/lei-10850-2004.md'),
 ('2009', 'Lei nº 11.935 — cobertura de urgência, emergência e planejamento familiar', 'leis/02-alteracoes-lei-9656/lei-11935-2009.md'),
 ('2013', 'Lei nº 12.880 — antineoplásicos orais', 'leis/02-alteracoes-lei-9656/lei-12880-2013.md'),
 ('2014', 'Lei nº 13.003 — contratualização entre operadoras e prestadores', 'leis/02-alteracoes-lei-9656/lei-13003-2014.md'),
 ('2019', 'Lei nº 13.848 — Lei Geral das Agências Reguladoras', 'leis/04-agencias-reguladoras/lei-13848-2019.md'),
 ('2021', 'MP nº 1.067 — novo rito de incorporação de tecnologias ao Rol', 'leis/02-alteracoes-lei-9656/mp-1067-2021.md'),
 ('2022', 'Lei nº 14.307 — processo de atualização do Rol de Procedimentos', 'leis/02-alteracoes-lei-9656/lei-14307-2022.md'),
 ('2022', 'Lei nº 14.454 — critérios para cobertura de tratamentos fora do Rol', 'leis/02-alteracoes-lei-9656/lei-14454-2022.md'),
]
for ano, m, link in MARCOS:
    ok = os.path.exists(os.path.join(R, link.split('#')[0]))
    H.append(f'| {ano} | {m} | ' + (f'[abrir]({link})' if ok else '') + ' |')
H.append('\nA evolução detalhada de cada artigo da Lei nº 9.656/1998 pode ser vista em [leis/01-marco-legal/lei-9656-1998.md](leis/01-marco-legal/lei-9656-1998.md), '
         'que mantém os textos revogados tachados com a indicação da norma que os alterou.\n')
H.append('## Produção normativa da ANS por ano\n')
cols = ['CONSU', 'RDC', 'RN', 'IN', 'RR', 'RO', 'Outros']
H.append('| Ano | ' + ' | '.join(cols) + ' | Total |'); H.append('| --- |' + ' ---: |' * (len(cols) + 1))
for ano in sorted(por_ano):
    c = por_ano[ano]; H.append(f'| {ano} | ' + ' | '.join(str(c[k] or '') for k in cols) + f' | {sum(c.values())} |')
open(os.path.join(R, 'HISTORICO.md'), 'w').write('\n'.join(H) + '\n')

# README.md principal
tot_rn = cnt['01-resolucoes-normativas']
README = f"""# Legislação da Saúde Suplementar — Planos de Saúde e ANS

Acervo organizado da legislação brasileira que afeta as **operadoras de planos privados de assistência à saúde (OPS)** — regulação, fiscalização, supervisão, tributação, relações de consumo e coberturas: a legislação federal (com o histórico de alterações) e **todos** os atos normativos da **Agência Nacional de Saúde Suplementar (ANS)** — Resoluções Normativas, Instruções Normativas, RDCs, Resoluções CONSU, Súmulas, Resoluções Regimentais, Resoluções Operacionais, pareceres, entendimentos, comunicados, portarias e demais atos — com textos integrais, anexos e histórico normativo.

> Atualizado em {TODAY}. Os textos são reproduções de fontes oficiais e **não substituem a publicação no Diário Oficial da União**.

## Conteúdo

| Pasta | O que tem | Qtde |
| --- | --- | ---: |
| [`leis/`](leis/README.md) | Constituição, leis, decretos e MPs (Planalto) que afetam as operadoras: marco legal (Lei nº 9.656/1998 com histórico de redações e todas as normas que a alteraram), agências reguladoras, fiscalização e regimes especiais, tributação, direito societário, consumidor, coberturas assistenciais e direitos dos pacientes | {len(leis)} |
| [`ans/`](ans/README.md) | Atos normativos da ANS com texto integral, anexos e histórico | {sum(cnt.values())} |
| [`ans/01-resolucoes-normativas/`](ans/01-resolucoes-normativas/README.md) | Todas as Resoluções Normativas (RN) disponíveis no portal da ANS | {tot_rn} |
| [`rol-de-procedimentos/`](rol-de-procedimentos/README.md) | **Rol de Procedimentos e Eventos em Saúde**: anexos vigentes, lista de procedimentos (tabelas e planilha), Diretrizes de Utilização separadas por DUT e histórico de tudo o que cada norma incluiu, excluiu ou alterou — atualizado automaticamente | |
| [`NOVIDADES.md`](NOVIDADES.md) | Registro das atualizações automáticas: atos novos, normas alteradas e leis novas | |
| [`HISTORICO.md`](HISTORICO.md) | Linha do tempo dos marcos legais e produção normativa por ano | |
| [`dados/`](dados/) | Índices em CSV/JSON (para planilhas, buscas e uso em IA/RAG) | |
| [`scripts/`](scripts/README.md) | Programas usados na coleta, para atualizar o acervo | |

### Atos da ANS por categoria

| Categoria | Atos | Vigentes |
| --- | ---: | ---: |
""" + '\n'.join(f'| [{n}](ans/{c}/README.md) | {cnt[c]} | {vig[c]} |' for c, n in CATN.items() if cnt[c]) + f"""

## Atualização automática

O acervo se atualiza sozinho todos os dias (por volta das 6h40, horário de Brasília) por meio do GitHub Actions ([`.github/workflows/atualizar-acervo.yml`](.github/workflows/atualizar-acervo.yml)):

- **Atos novos da ANS** são baixados com texto, anexos e histórico, e as normas que eles alteram ou revogam são atualizadas;
- **Leis do Planalto** são conferidas; se o texto de alguma mudou, o arquivo é atualizado, e **leis novas que alterem a Lei nº 9.656/1998, a Lei nº 9.961/2000, a Lei nº 10.185/2001 ou a MP nº 2.177-44/2001 são incluídas automaticamente**;
- Aos domingos, uma varredura completa da lista da ANS detecta mudanças de situação (por exemplo, revogações) em atos antigos;
- O **Rol de Procedimentos** (RN nº 465/2021) é conferido todos os dias; quando a ANS publica nova versão dos anexos, a pasta [`rol-de-procedimentos/`](rol-de-procedimentos/README.md) é regenerada, com o registro do que mudou;
- Cada atualização fica registrada em [`NOVIDADES.md`](NOVIDADES.md). Se não houver novidade, nada é alterado.

Para rodar na hora: aba **Actions** → **Atualizar acervo** → **Run workflow**. Leis novas que afetem as operadoras sem alterar as leis acima (ex.: uma nova lei tributária) precisam ser acrescentadas em [`scripts/planalto_list.tsv`](scripts/planalto_list.tsv).

## Como cada ato está organizado

Cada ato da ANS é um arquivo Markdown (ex.: [`ans/01-resolucoes-normativas/RN-0465-2021.md`](ans/01-resolucoes-normativas/RN-0465-2021.md)) com:

1. **Metadados** (cabeçalho YAML): tipo, número, ano, situação (vigente/revogada), datas de publicação no DOU, vigência, última alteração e revogação, norma revogadora, tema, assunto e link oficial;
2. **Ementa** e **texto integral** — dispositivos revogados ou alterados aparecem ~~tachados~~, como no portal da ANS;
3. **Anexos** — arquivo original (PDF etc.) em `anexos/<ato>/` e, para PDFs, uma versão `.txt` pesquisável; quando o anexo foi alterado ao longo do tempo, há uma tabela com **todas as versões** e a norma que gerou cada uma;
4. **Histórico normativo** — listas completas de normas **alteradoras**, **revogadoras** e de normas **alteradas/revogadas** pelo ato, com links entre os arquivos;
5. **Fundamentação legal** e **participação social** (consultas e audiências públicas).

## Fontes

- **Planalto** — Portal da Legislação da Presidência da República: <https://www.planalto.gov.br/ccivil_03/>
- **ANS** — Portal de Legislação da ANS: <https://componentes-portal.ans.gov.br/link/legislacoes>

### Observações

- O acervo inclui **todos os tipos de ato** do portal de legislação da ANS, inclusive as Resoluções Operacionais (RO), que tratam de operadoras específicas: instauração e encerramento de regimes de direção fiscal e técnica, liquidação extrajudicial, alienação compulsória de carteira, portabilidade especial e extraordinária, suspensão de comercialização etc. Elas estão organizadas por ano.
- Não estão incluídas normas de outros órgãos que também incidem sobre as operadoras (ex.: instruções normativas da Receita Federal, resoluções do CFM, normas da Anvisa e da SUSEP/CNSP) — apenas as leis e decretos federais correspondentes.
- As RNs nº 552, 554, 556 e 608 não constam do portal de legislação da ANS.
- Os vínculos de histórico ("data do vínculo") refletem a data em que a ANS cadastrou a relação no portal, não a data da norma.
- Atos oficiais não são protegidos por direito autoral (Lei nº 9.610/1998, art. 8º, IV).
"""
open(os.path.join(R, 'README.md'), 'w').write(README)
print('docs ok')
