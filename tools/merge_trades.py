#!/usr/bin/env python3
"""Doplní nové obchody z výstupu tools/collect.js do data/gold-evolution.csv.

Použití:  python3 tools/merge_trades.py vystup.txt [cílový.csv]
          (bez cílového souboru se použije data/gold-evolution.csv – robotické obchodování;
           pro manuální obchodování: data/manual.csv)
Ověří kontrolní součet, sloučí bez duplicit a seřadí podle času zavření.
Vypíše počet přidaných obchodů; při chybě skončí s nenulovým kódem a soubor nezmění.
"""
import sys, csv, os

CSV = os.path.join(os.path.dirname(__file__), '..', 'data', 'gold-evolution.csv')
HEADER = ['Open Date', 'Close Date', 'Symbol', 'Action', 'Lots', 'Pips', 'Profit', 'Pct']  # Pct doplní tools/enrich.py


def h36(s):
    x = 0
    for ch in s:
        x = (x * 31 + ord(ch)) & 0xffffffff
    d = '0123456789abcdefghijklmnopqrstuvwxyz'
    out = ''
    while True:
        x, r = divmod(x, 36)
        out = d[r] + out
        if not x:
            return out


def fmt(t):  # yymmddhhmm -> YYYY-MM-DD HH:MM
    return f"20{t[0:2]}-{t[2:4]}-{t[4:6]} {t[6:8]}:{t[8:10]}"


def main(path, target=None):
    global CSV
    if target:
        CSV = target
    if not os.path.exists(CSV):
        with open(CSV, 'w', encoding='utf-8') as f:
            f.write(','.join(HEADER) + '\n')
    lines = open(path, encoding='utf-8').read().strip().splitlines()
    head = lines[0].split()
    if head[0] != 'PAGES':
        sys.exit('Neplatný vstup: ' + lines[0][:200])
    count, chk = int(head[3]), head[5]
    body = '\n'.join(lines[1:])
    if len(lines) - 1 != count or h36(body) != chk:
        sys.exit(f'Kontrolní součet nesouhlasí (řádků {len(lines)-1}, čekáno {count}). Soubor nezměněn.')
    from collections import Counter
    with open(CSV, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))
    key = lambda r: (r['Open Date'], r['Close Date'], r['Action'], r['Lots'], r['Pips'])
    have = Counter(key(r) for r in rows)
    new = []
    for ln in lines[1:]:
        o, c, s, l, p = ln.split('|')
        lots, pips = int(l) / 100, int(p) / 10
        new.append({'Open Date': fmt(o), 'Close Date': fmt(c), 'Symbol': 'XAUUSD', 'Action': 'Buy' if s == 'b' else 'Sell',
                    'Lots': f'{lots:.2f}', 'Pips': f'{pips:.1f}', 'Profit': f'{pips * lots:.2f}'})
    # stejné obchody se mohou opakovat (stejný čas, směr, loty i pipy) – přidáme jen chybějící počet kusů
    want = Counter(key(r) for r in new)
    added = 0
    for k, n in want.items():
        extra = n - have.get(k, 0)
        if extra > 0:
            sample = next(r for r in new if key(r) == k)
            rows.extend([dict(sample) for _ in range(extra)])
            added += extra
    out = sorted(rows, key=lambda r: (r['Close Date'], r['Open Date']))
    with open(CSV, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=HEADER, lineterminator='\n', restval='', extrasaction='ignore')
        w.writeheader()
        w.writerows(out)
    print(f'Přidáno {added} obchodů, celkem {len(rows)}.')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
