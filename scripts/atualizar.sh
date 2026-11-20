#!/bin/bash
# Atualiza todo o acervo. Requisitos: Node.js 18+ com Playwright (Chromium), Python 3 com
# beautifulsoup4, markdownify e lxml, e poppler-utils (pdftotext).
# Uso: cd scripts && ./atualizar.sh <diretorio-de-trabalho>
set -e
W=${1:-/tmp/legislacao-ans}; R=$(cd .. && pwd)
mkdir -p "$W/index" "$W/raw_ans" "$W/planalto/raw"
cd "$(dirname "$0")"
# 1. Leis do Planalto
OUT="$W/planalto/raw" ./fetch_planalto.sh
python3 conv_planalto.py "$W/planalto/raw" "$R/leis"
# 2. Índice dos atos da ANS (um tipo por vez)
for t in "Resolução Normativa" "Instrução Normativa" "Instrução Normativa Conjunta" "Resolução de Diretoria Colegiada" \
         "Resolução CONSU" "Súmula Normativa" "Resolução Regimental" "Parecer da PROGE" "Entendimento da DIFIS"; do
  node harvest_index.js "$t" "$W/index/$(echo "$t" | tr ' ' '_').jsonl"
done
# 3. Texto integral, anexos e histórico de cada ato
cat "$W"/index/*.jsonl | python3 -c "import sys,json;print(' '.join(sorted({json.loads(l).get('id') for l in sys.stdin}-{None})))" \
  | node fetch_detail.js "$W/raw_ans"
# 4. Montagem
python3 build_ans.py "$W/index" "$W/raw_ans" "$R"
python3 build_docs.py "$R"
