import sys, re, os, csv, datetime
from bs4 import BeautifulSoup, NavigableString, Comment
from urllib.parse import urljoin
from markdownify import markdownify as md

RAW, OUT = sys.argv[1], sys.argv[2]
TODAY = datetime.date.today().isoformat()

def decode(b):
    m = re.search(rb'charset=["\']?([\w-]+)', b[:3000], re.I)
    enc = (m.group(1).decode() if m else 'cp1252').lower()
    if enc in ('iso-8859-1', 'latin1', 'windows-1252'): enc = 'cp1252'
    try: return b.decode(enc)
    except Exception: return b.decode('cp1252', 'replace')

def clean_md(t):
    t = t.replace('\xa0', ' ')
    t = re.sub(r'[ \t]+\n', '\n', t)
    t = re.sub(r'\n{3,}', '\n\n', t)
    t = re.sub(r'~~\s*~~', '', t)
    t = re.sub(r'~~ +', '~~', t); t = re.sub(r'(\S) +~~(\s|$)', r'\1~~\2', t)
    return t.strip() + '\n'

rows = list(csv.DictReader(open('planalto_list.tsv'), delimiter='\t'))
index = []
for r in rows:
    src = os.path.join(RAW, r['slug'] + '.htm')
    html = decode(open(src, 'rb').read())
    soup = BeautifulSoup(html, 'lxml')
    for t in soup(['script', 'style', 'img', 'meta', 'link']): t.decompose()
    for t in soup.find_all(style=re.compile(r'line-through', re.I)): t.name = 'del'
    for t in soup.find_all(['strike', 's']): t.name = 'del'
    url = 'https://www.planalto.gov.br/ccivil_03/' + r['path']
    for c in soup.find_all(string=lambda x: isinstance(x, Comment)): c.extract()
    for a in soup.find_all('a', href=True):
        if not a['href'].startswith('#'): a['href'] = urljoin(url, a['href'])
    # tachado que envolve blocos: distribui o <del> para dentro de cada bloco
    BLOCKS = ['p','div','table','tr','td','li','ul','ol','h1','h2','h3','h4','blockquote','center']
    for d in list(soup.find_all('del')):
        if d.find(BLOCKS):
            for blk in d.find_all(['p','li','td','h1','h2','h3','h4']):
                if blk.find(BLOCKS): continue
                inner = soup.new_tag('del')
                for ch in list(blk.contents): inner.append(ch.extract())
                blk.append(inner)
            d.unwrap()
    for sn in list(soup.find_all(string=True)):
        if isinstance(sn, NavigableString) and sn.parent.name not in ('pre',):
            new = re.sub(r'\s+', ' ', str(sn))
            if new != str(sn): sn.replace_with(new)
    for dd in soup.find_all('del'):
        if not dd.get_text(strip=True): dd.unwrap()
    body = soup.body or soup
    text = md(str(body), heading_style='ATX', strip=['img', 'font', 'span'], escape_underscores=False, escape_asterisks=False)
    text = clean_md(text)
    d = os.path.join(OUT, r['grupo']); os.makedirs(os.path.join(d, 'html-original'), exist_ok=True)
    header = (f"---\ntitulo: \"{r['titulo']}\"\nfonte: {url}\norgao: Presidência da República — Portal da Legislação (Planalto)\ncoletado_em: {TODAY}\n---\n\n"
              f"> **{r['titulo']}**  \n> Fonte oficial: <{url}>  \n> Trechos ~~tachados~~ correspondem a dispositivos revogados ou com redação alterada, conforme publicado no Planalto. "
              f"Este arquivo é uma conversão para Markdown; prevalece o texto publicado no Diário Oficial da União.\n\n")
    open(os.path.join(d, r['slug'] + '.md'), 'w').write(header + text)
    open(os.path.join(d, 'html-original', r['slug'] + '.htm'), 'w').write(html)
    index.append((r['grupo'], r['slug'], r['titulo'], url))
with open(os.path.join(OUT, '_indice.tsv'), 'w') as f:
    for x in index: f.write('\t'.join(x) + '\n')
print(len(index))
