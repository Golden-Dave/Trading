#!/usr/bin/env python3
"""Zkouška: dá se veřejný výpis Myfxbooku stáhnout přímo z GitHubu (bez prohlížeče)?
Vypisuje jen stavové kódy a počty řádků – žádná data ani přihlašovací údaje."""
import re, sys, subprocess, urllib.request, urllib.error, http.cookiejar

ACC = sys.argv[1] if len(sys.argv) > 1 else '12034345'
UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36'
H = {'User-Agent': UA, 'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
     'Accept-Language': 'en-US,en;q=0.9'}
op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))


def get(url, data=None, extra=None):
    try:
        with op.open(urllib.request.Request(url, data=data, headers=dict(H, **(extra or {}))), timeout=60) as r:
            return r.status, r.read().decode('utf-8', 'replace'), dict(r.headers)
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode('utf-8', 'replace'), dict(e.headers)
    except Exception as e:
        return 0, type(e).__name__ + ': ' + str(e)[:200], {}


def describe(name, st, body, hd):
    rows = len(re.findall(r'XAUUSD', body))
    print(f'{name}: HTTP {st}, {len(body)} znaků, tabulka obchodů: {"ano" if "Open Date" in body else "ne"}, '
          f'řádků XAUUSD: {rows}, server: {hd.get("Server", hd.get("server", "?"))}, '
          f'ochrana: {"ano" if re.search(r"Just a moment|cf-chl|captcha|Access denied|Attention Required", body, re.I) else "ne"}')
    if st != 200 or 'Open Date' not in body:
        print('  začátek odpovědi:', re.sub(r'\s+', ' ', body[:300]))
    return rows


base = f'https://www.myfxbook.com/statements/{ACC}/statement.html'
st, body, hd = get(base)
ok = describe('Výpis (urllib)', st, body, hd) > 0

m = re.search(r'class="[^"]*paging-btn[^"]*"[^>]*params="([^"]+)"|params="([^"]+)"[^>]*class="[^"]*paging-btn', body)
if m:
    params = (m.group(1) or m.group(2)).replace('&amp;', '&')
    print('Stránkování nalezeno: ano')
    for n in (1, 2):
        s2, b2, h2 = get('https://www.myfxbook.com/paging.html' + re.sub(r'([?&])p=\d+', r'\g<1>p=%d' % n, params), extra={'Referer': base, 'X-Requested-With': 'XMLHttpRequest'})
        describe(f'Stránka {n}', s2, b2, h2)
else:
    print('Stránkování nalezeno: ne')

u = ('https://www.myfxbook.com/private/charts.json?startDate=2026-01-01%2000:00&endDate=2099-12-31%2023:59&invitation=&showLots=true'
     '&showPips=false&showChange=false&showSymbolPips=true&showMain=true&magicNumbers=&symbols=&tags=&days=1,5,2,6,3,7,4'
     '&hours=0,4,8,12,16,20,1,5,9,13,17,21,2,6,10,14,18,22,3,7,11,15,19,23&buySell=0,1,6,16&yieldStart=&yieldEnd=&takeProfitStart='
     '&takeProfitEnd=&stopLoss=&stopLossEnd=&sizingStart=&sizingEnd=&selectedTime=1&pipsStart=&pipsEnd=&chartType=1&period=6&l=s&accountOid=' + ACC)
s3, b3, h3 = get(u, data=b'', extra={'Referer': base, 'X-Requested-With': 'XMLHttpRequest'})
print(f'Křivka růstu: HTTP {s3}, {len(b3)} znaků, obsahuje Growth: {"ano" if chr(34) + "Growth" + chr(34) in b3 else "ne"}')
if '"Growth"' not in b3:
    print('  začátek odpovědi:', re.sub(r'\s+', ' ', b3[:300]))

c = subprocess.run(['curl', '-sS', '-o', '/tmp/s.html', '-w', '%{http_code}', '-A', UA, '--compressed', base], capture_output=True, text=True)
try:
    cb = open('/tmp/s.html', encoding='utf-8', errors='replace').read()
except OSError:
    cb = ''
print(f'Výpis (curl): HTTP {c.stdout.strip()}, {len(cb)} znaků, řádků XAUUSD: {len(re.findall("XAUUSD", cb))}')
print('VÝSLEDEK:', 'stažení z GitHubu FUNGUJE' if ok else 'stažení z GitHubu NEFUNGUJE')
