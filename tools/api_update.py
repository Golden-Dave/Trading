#!/usr/bin/env python3
"""Hodinová aktualizace manuálního obchodování přes oficiální API Myfxbooku (běží na GitHubu).

Použití:  MYFXBOOK_EMAIL=... MYFXBOOK_PASSWORD=... python3 tools/api_update.py [id účtu] [cílový.csv]
          (výchozí: účet 12309673 -> data/manual.csv)

API vrací jen posledních cca 40 obchodů účtu, proto se nové obchody přidávají k těm uloženým
(stejně jako u tools/collect.js) a nic se nemaže. Křivka růstu se bere z denních výnosů účtu
a tools/enrich.py z ní dopočítá sloupec Pct. API funguje jen pro vlastní účty přihlášeného
uživatele – cizí účet (robot 12034345) přes něj číst nejde.
Do logu se nevypisují zůstatky ani přihlašovací údaje (log je veřejný).
"""
import os, sys, json, csv, tempfile, urllib.request, urllib.parse
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import merge_trades, enrich  # noqa: E402

BASE = 'https://www.myfxbook.com/api/'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) trading-panel-updater'}


def call(path, raw_session=None, **params):
    q = urllib.parse.urlencode(params)
    if raw_session is not None:  # session se předává tak, jak přišla (bez dalšího kódování)
        q = 'session=' + raw_session + ('&' + q if q else '')
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path + '?' + q, headers=UA), timeout=60) as r:
            j = json.loads(r.read().decode('utf-8', 'replace'))
    except Exception as e:  # URL se nikdy nevypisuje – obsahuje přihlašovací údaje
        sys.exit(f'Požadavek {path} selhal: {type(e).__name__}')
    if j.get('error'):
        sys.exit(f'{path}: {j.get("message")}')
    return j


def stamp(s):  # "11/13/2026 11:38" -> "2611131138"
    d, t = s.strip().split(' ')
    m, dd, y = d.split('/')
    hh, mi = t.split(':')[:2]
    return y[2:] + m.zfill(2) + dd.zfill(2) + hh.zfill(2) + mi.zfill(2)


def main(acc='12309673', target=None):
    target = target or os.path.join(HERE, '..', 'data', 'manual.csv')
    email, pw = os.environ.get('MYFXBOOK_EMAIL', '').strip(), os.environ.get('MYFXBOOK_PASSWORD', '').strip()
    if not email or not pw:
        sys.exit('Chybí MYFXBOOK_EMAIL nebo MYFXBOOK_PASSWORD (Settings → Secrets and variables → Actions).')
    s = call('login.json', email=email, password=pw)['session']
    try:
        hist = call('get-history.json', s, id=acc).get('history') or []
        gain = call('get-daily-gain.json', s, id=acc, start='2000-01-01', end='2099-12-31').get('dailyGain') or []
        daily = call('get-data-daily.json', s, id=acc, start='2000-01-01', end='2099-12-31').get('dataDaily') or []
    finally:
        try:
            call('logout.json', s)
        except SystemExit:
            pass

    lines = []
    for x in hist:
        sz = x.get('sizing') or {}
        if x.get('symbol') != 'XAUUSD' or x.get('action') not in ('Buy', 'Sell') or sz.get('type') != 'lots':
            continue
        lines.append('|'.join([stamp(x['openTime']), stamp(x['closeTime']), x['action'][0].lower(),
                               str(round(float(sz['value']) * 100)), str(round(float(x['pips']) * 10))]))
    tmp = tempfile.mkdtemp()
    if lines:
        body = '\n'.join(lines)
        tf = os.path.join(tmp, 'trades.txt')
        with open(tf, 'w', encoding='utf-8') as f:
            f.write(f'PAGES 1 COUNT {len(lines)} SUM {merge_trades.h36(body)}\n{body}')
        merge_trades.main(tf, target)
    else:
        print('API nevrátilo žádné obchody XAUUSD.')

    pts = []
    for row in gain:
        for y in (row if isinstance(row, list) else [row]):
            m, dd, yy = y['date'].split('/')
            pts.append(f'{yy}-{m.zfill(2)}-{dd.zfill(2)}|{y["value"]}')
    pts.sort()
    if pts and os.path.exists(target):
        body = '\n'.join(pts)
        gf = os.path.join(tmp, 'growth.txt')
        with open(gf, 'w', encoding='utf-8') as f:
            f.write(f'GROWTH {len(pts)} SUM {merge_trades.h36(body)}\n{body}')
        enrich.main(gf, target)

    # kontrola úplnosti: součet lotů za den v souboru proti dennímu přehledu účtu
    have = defaultdict(float)
    if os.path.exists(target):
        for r in csv.DictReader(open(target, encoding='utf-8')):
            have[r['Close Date'][:10]] += float(r['Lots'])
    gaps = []
    for row in daily:
        for y in (row if isinstance(row, list) else [row]):
            m, dd, yy = y['date'].split('/')
            d = f'{yy}-{m.zfill(2)}-{dd.zfill(2)}'
            if abs(have.get(d, 0) - float(y.get('lots') or 0)) > 0.005:
                gaps.append(f'{d} (v souboru {have.get(d, 0):.2f} lotu, na účtu {float(y.get("lots") or 0):.2f})')
    if gaps:
        print('::warning::V souboru chybí obchody za dny: ' + '; '.join(gaps) + '. Doplní je aktualizace přes výpis v prohlížeči.')
    else:
        print('Kontrola úplnosti v pořádku – denní součty lotů souhlasí s účtem.')


if __name__ == '__main__':
    main(*sys.argv[1:3])
