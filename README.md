# Legislação da Saúde Suplementar — Planos de Saúde e ANS

Acervo organizado da legislação brasileira sobre **regulação, fiscalização e supervisão das operadoras de planos privados de assistência à saúde**: as leis federais (com o histórico de alterações) e os atos normativos da **Agência Nacional de Saúde Suplementar (ANS)** — todas as Resoluções Normativas, Instruções Normativas, RDCs, Resoluções CONSU, Súmulas, Resoluções Regimentais, pareceres e entendimentos — com textos integrais, anexos e histórico normativo.

> Atualizado em 20/11/2026. Os textos são reproduções de fontes oficiais e **não substituem a publicação no Diário Oficial da União**.

## Conteúdo

| Pasta | O que tem | Qtde |
| --- | --- | ---: |
| [`leis/`](leis/README.md) | Leis, decretos e MPs (Planalto), incluindo a Lei nº 9.656/1998 com histórico de redações e todas as normas que a alteraram | 56 |
| [`ans/`](ans/README.md) | Atos normativos da ANS com texto integral, anexos e histórico | 1196 |
| [`ans/01-resolucoes-normativas/`](ans/01-resolucoes-normativas/README.md) | Todas as Resoluções Normativas (RN) disponíveis no portal da ANS | 700 |
| [`HISTORICO.md`](HISTORICO.md) | Linha do tempo dos marcos legais e produção normativa por ano | |
| [`dados/`](dados/) | Índices em CSV/JSON (para planilhas, buscas e uso em IA/RAG) | |
| [`scripts/`](scripts/README.md) | Programas usados na coleta, para atualizar o acervo | |

### Atos da ANS por categoria

| Categoria | Atos | Vigentes |
| --- | ---: | ---: |
| [Resoluções Normativas (RN)](ans/01-resolucoes-normativas/README.md) | 700 | 265 |
| [Instruções Normativas (IN)](ans/02-instrucoes-normativas/README.md) | 272 | 42 |
| [Resoluções de Diretoria Colegiada (RDC) — 2000 a 2002](ans/03-resolucoes-diretoria-colegiada/README.md) | 95 | 38 |
| [Resoluções do CONSU — 1998 a 1999](ans/04-resolucoes-consu/README.md) | 26 | 8 |
| [Súmulas Normativas](ans/05-sumulas-normativas/README.md) | 32 | 19 |
| [Resoluções Regimentais (RR)](ans/06-resolucoes-regimentais/README.md) | 39 | 19 |
| [Pareceres da PROGE](ans/07-pareceres-proge/README.md) | 19 | 19 |
| [Entendimentos da DIFIS](ans/08-entendimentos-difis/README.md) | 13 | 12 |

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

- As Resoluções Operacionais (RO, ~3.200 atos sobre operadoras específicas, como regimes de direção fiscal/técnica, alienação de carteira e portabilidade especial), portarias, comunicados, despachos, instruções de serviço e resoluções administrativas internas **não** foram incluídos, por não serem normas gerais de regulação do setor. Os scripts em `scripts/` permitem incluí-los.
- As RNs nº 552, 554, 556 e 608 não constam do portal de legislação da ANS.
- Os vínculos de histórico ("data do vínculo") refletem a data em que a ANS cadastrou a relação no portal, não a data da norma.
- Atos oficiais não são protegidos por direito autoral (Lei nº 9.610/1998, art. 8º, IV).
