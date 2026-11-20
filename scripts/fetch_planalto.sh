#!/bin/bash
UA="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36"
out=${OUT:-../planalto/raw}
tail -n +2 planalto_list.tsv | while IFS=$'\t' read g slug path t; do
  f="$out/$slug.htm"; [ -s "$f" ] && continue
  code=$(curl -sSL -m 90 -A "$UA" -H 'Accept: text/html' -H 'Accept-Language: pt-BR' -o "$f" -w '%{http_code}' "https://www.planalto.gov.br/ccivil_03/$path")
  echo "$code $(stat -c%s "$f") $slug"; sleep 1
done
