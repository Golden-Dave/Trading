#!/usr/bin/env python3
"""Zkouška oficiálního API Myfxbooku: co vrací pro účty robota a manuálu.
Vypisuje jen počty a názvy polí – žádné zůstatky ani osobní údaje (log je veřejný)."""
import os, sys, json, urllib.request, urllib.parse

BASE = 'https://www.myfxbook.com/api/'
UA = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) trading-panel-updater'}
IDS = ['12034345', '12309673']


def call(path, raw_session=None, **params):
    q = urllib.parse.urlencode(params)
    if raw_session is not None:  # session se předává tak, jak přišla (bez dalšího kódování)
        q = 'session=' + raw_session + ('&' + q if q else '')
    try:
        with urllib.request.urlopen(urllib.request.Request(BASE + path + '?' + q, headers=UA), timeout=60) as r:
            return json.loads(r.read().decode('utf-8', 'replace'))
    except Exception as e:  # nikdy nevypisovat URL (obsahuje přihlašovací údaje)
        return {'error': True, 'message': 'požadavek selhal: ' + type(e).__name__}


def shape(v):
    if isinstance(v, list):
        return f'seznam({len(v)})' + (' prvek: ' + shape(v[0]) if v else '')
    if isinstance(v, dict):
        return 'pole: ' + ', '.join(sorted(v.keys()))
    return type(v).__name__


email, pw = os.environ.get('MYFXBOOK_EMAIL', ''), os.environ.get('MYFXBOOK_PASSWORD', '')
if not email or not pw:
    sys.exit('Chybí MYFXBOOK_EMAIL nebo MYFXBOOK_PASSWORD.')
j = call('login.json', email=email.strip(), password=pw.strip())
if j.get('error'):
    sys.exit('Přihlášení selhalo: ' + str(j.get('message')))
s = j['session']
print('Přihlášení v pořádku.')
try:
    a = call('get-my-accounts.json', s)
    accs = a.get('accounts') or []
    print('Vlastní účty:', len(accs), '| chyba:', a.get('error'), a.get('message'))
    for x in accs:
        print('   id', x.get('id'), '| v seznamu hledaných:', str(x.get('id')) in IDS, '| pole:', ', '.join(sorted(x.keys())))
    w = call('get-watched-accounts.json', s)
    print('Sledované účty:', len(w.get('accounts') or []), '| chyba:', w.get('error'), w.get('message'))
    for i in IDS:
        print('--- účet', i)
        h = call('get-history.json', s, id=i)
        hist = h.get('history') or []
        print('   historie: chyba', h.get('error'), '|', h.get('message'), '| záznamů', len(hist))
        if hist:
            print('   pole záznamu:', ', '.join(sorted(hist[0].keys())))
            ct = sorted(str(x.get('closeTime')) for x in hist)
            print('   closeTime od', ct[0], 'do', ct[-1], '| formát openTime:', hist[0].get('openTime'))
            print('   symboly:', sorted({str(x.get('symbol')) for x in hist})[:8], '| akce:', sorted({str(x.get('action')) for x in hist})[:8])
        for x in sorted(hist, key=lambda x: str(x.get('closeTime'))):
            sz = x.get('sizing') or {}
            print('   T', x.get('openTime'), '|', x.get('closeTime'), '|', x.get('action'), '|', sz.get('type'), sz.get('value'), '|', x.get('pips'), '|', x.get('profit'), '|', x.get('commission'), x.get('interest'))
        g = call('get-daily-gain.json', s, id=i, start='2026-01-01', end='2026-12-31').get('dailyGain') or []
        for row in g:
            for y in row:
                print('   G', y.get('date'), y.get('value'), y.get('profit'))
        dd = call('get-data-daily.json', s, id=i, start='2026-01-01', end='2026-12-31').get('dataDaily') or []
        for row in dd:
            for y in row:
                b, pr = float(y.get('balance') or 0), float(y.get('profit') or 0)
                print('   D', y.get('date'), 'profit', pr, 'pips', y.get('pips'), 'lots', y.get('lots'), 'growthEquity', y.get('growthEquity'), 'profit/(bal-profit)%', round(pr / (b - pr) * 100, 4) if b - pr else None)
        for ep, key in (('get-daily-gain.json', 'dailyGain'), ('get-data-daily.json', 'dataDaily')):
            d = call(ep, s, id=i, start='2026-11-01', end='2026-11-30')
            print('  ', ep, ': chyba', d.get('error'), '|', d.get('message'), '|', shape(d.get(key)))
finally:
    call('logout.json', s)
    print('Odhlášeno.')
