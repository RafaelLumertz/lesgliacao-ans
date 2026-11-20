# Scripts de coleta

Programas usados para montar este acervo. Para atualizar tudo: `cd scripts && ./atualizar.sh /caminho/de/trabalho`.

| Script | Função |
| --- | --- |
| `planalto_list.tsv` | Lista curada de leis/decretos/MPs (grupo, nome do arquivo, caminho no Planalto, título). Para incluir uma norma nova, acrescente uma linha. |
| `fetch_planalto.sh` | Baixa o HTML de cada norma da lista no Planalto. |
| `conv_planalto.py` | Converte o HTML do Planalto para Markdown, mantendo dispositivos revogados ~~tachados~~ e links absolutos. |
| `harvest_index.js` | Percorre o [Portal de Legislação da ANS](https://componentes-portal.ans.gov.br/link/legislacoes) (aplicação Mendix) com Playwright, filtrando por tipo de ato, e registra título, data, ementa, tema, assunto, situação e o identificador de cada ato. |
| `fetch_detail.js` | Abre a página de cada ato (`/link/legislacao/<id>`) e salva o texto, os anexos, as grades de histórico (alteradoras, revogadoras, versões de anexos — inclusive páginas além da primeira) e a fundamentação legal. |
| `build_ans.py` | Gera os arquivos Markdown da pasta `ans/`, extrai o texto dos PDFs (pdftotext) e cria `dados/atos-ans.csv/json`. |
| `build_docs.py` | Gera os READMEs, `HISTORICO.md` e `dados/leis.csv`. |

Observações técnicas:

- O portal da ANS exige navegador (JavaScript); por isso a coleta usa Playwright/Chromium.
- No portal da ANS, os botões "próxima página" e "última página" da lista principal estão trocados; `harvest_index.js` já considera isso.
- As grades de histórico na página de cada ato mostram só 20 linhas porque a barra de paginação está oculta pelo CSS do site; `fetch_detail.js` aciona o botão de paginação existente para obter a lista completa.
- O Planalto recusa requisições sem cabeçalho de navegador (User-Agent).
