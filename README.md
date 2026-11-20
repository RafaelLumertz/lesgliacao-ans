# Legislação da Saúde Suplementar — Planos de Saúde e ANS

Acervo organizado da legislação brasileira que afeta as **operadoras de planos privados de assistência à saúde (OPS)** — regulação, fiscalização, supervisão, tributação, relações de consumo e coberturas: a legislação federal (com o histórico de alterações) e **todos** os atos normativos da **Agência Nacional de Saúde Suplementar (ANS)** — Resoluções Normativas, Instruções Normativas, RDCs, Resoluções CONSU, Súmulas, Resoluções Regimentais, Resoluções Operacionais, pareceres, entendimentos, comunicados, portarias e demais atos — com textos integrais, anexos e histórico normativo.

> Atualizado em 20/11/2026. Os textos são reproduções de fontes oficiais e **não substituem a publicação no Diário Oficial da União**.

## Conteúdo

| Pasta | O que tem | Qtde |
| --- | --- | ---: |
| [`leis/`](leis/README.md) | Constituição, leis, decretos e MPs (Planalto) que afetam as operadoras: marco legal (Lei nº 9.656/1998 com histórico de redações e todas as normas que a alteraram), agências reguladoras, fiscalização e regimes especiais, tributação, direito societário, consumidor, coberturas assistenciais e direitos dos pacientes | 89 |
| [`ans/`](ans/README.md) | Atos normativos da ANS com texto integral, anexos e histórico | 4702 |
| [`ans/01-resolucoes-normativas/`](ans/01-resolucoes-normativas/README.md) | Todas as Resoluções Normativas (RN) disponíveis no portal da ANS | 700 |
| [`NOVIDADES.md`](NOVIDADES.md) | Registro das atualizações automáticas: atos novos, normas alteradas e leis novas | |
| [`HISTORICO.md`](HISTORICO.md) | Linha do tempo dos marcos legais e produção normativa por ano | |
| [`dados/`](dados/) | Índices em CSV/JSON (para planilhas, buscas e uso em IA/RAG) | |
| [`scripts/`](scripts/README.md) | Programas usados na coleta, para atualizar o acervo | |

### Atos da ANS por categoria

| Categoria | Atos | Vigentes |
| --- | ---: | ---: |
| [Resoluções Normativas (RN)](ans/01-resolucoes-normativas/README.md) | 700 | 265 |
| [Instruções Normativas (IN)](ans/02-instrucoes-normativas/README.md) | 272 | 42 |
| [Resoluções de Diretoria Colegiada (RDC) — 2000 a 2002](ans/03-resolucoes-diretoria-colegiada/README.md) | 95 | 38 |
| [Resoluções do CONSU — 1998 a 2000](ans/04-resolucoes-consu/README.md) | 26 | 8 |
| [Súmulas Normativas](ans/05-sumulas-normativas/README.md) | 32 | 19 |
| [Resoluções Regimentais (RR)](ans/06-resolucoes-regimentais/README.md) | 39 | 19 |
| [Pareceres da PROGE](ans/07-pareceres-proge/README.md) | 19 | 19 |
| [Entendimentos da DIFIS](ans/08-entendimentos-difis/README.md) | 13 | 12 |
| [Resoluções Operacionais (RO) — operadoras específicas](ans/09-resolucoes-operacionais/README.md) | 3176 | 3147 |
| [Comunicados](ans/10-comunicados/README.md) | 101 | 101 |
| [Portarias](ans/11-portarias/README.md) | 47 | 46 |
| [Despachos](ans/12-despachos/README.md) | 5 | 5 |
| [Instruções de Serviço](ans/13-instrucoes-de-servico/README.md) | 66 | 3 |
| [Resoluções Administrativas](ans/14-resolucoes-administrativas/README.md) | 89 | 33 |
| [Resoluções Especiais](ans/15-resolucoes-especiais/README.md) | 22 | 1 |

## Atualização automática

O acervo se atualiza sozinho todos os dias (por volta das 6h40, horário de Brasília) por meio do GitHub Actions ([`.github/workflows/atualizar-acervo.yml`](.github/workflows/atualizar-acervo.yml)):

- **Atos novos da ANS** são baixados com texto, anexos e histórico, e as normas que eles alteram ou revogam são atualizadas;
- **Leis do Planalto** são conferidas; se o texto de alguma mudou, o arquivo é atualizado, e **leis novas que alterem a Lei nº 9.656/1998, a Lei nº 9.961/2000, a Lei nº 10.185/2001 ou a MP nº 2.177-44/2001 são incluídas automaticamente**;
- Aos domingos, uma varredura completa da lista da ANS detecta mudanças de situação (por exemplo, revogações) em atos antigos;
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
