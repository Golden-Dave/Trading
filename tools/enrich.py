#!/usr/bin/env python3
"""Uloží křivku růstu účtu a ke každému obchodu dopočítá jeho procentní výnos (sloupec Pct).

Použití:  python3 tools/enrich.py growth.txt data/gold-evolution.csv
          (growth.txt je výstup tools/growth.js; křivka se uloží vedle jako data/gold-evolution-growth.csv)

Proč: zůstatek účtu na Myfxbooku je skrytý, ale veřejná křivka Growth říká, o kolik % účet každý den
vyrostl (bez vlivu vkladů a výběrů). Z denního % a dolarového výsledku obchodů toho dne se odhadne
zůstatek účtu a každý obchod dostane své % = zisk obchodu / zůstatek. Aplikace pak tato % násobí
penězi uživatele, takže výsledek odpovídá výkonu účtu bez ohledu na jeho velikost.
"""
import sys, csv, os

sys.path.insert(0, os.path.dirname(__file__))
from merge_trades import h36  # noqa: E402

TRADE_HEADER = ['Open Date', 'Close Date', 'Symbol', 'Action', 'Lots', 'Pips', 'Profit', 'Pct']


def read_growth(path):
    lines = open(path, encoding='utf-8').read().strip().splitlines()
    head = lines[0].split()
    if head[0] != 'GROWTH':
        sys.exit('Neplatný vstup křivky: ' + lines[0][:200])
    body = '\n'.join(lines[1:])
    if len(lines) - 1 != int(head[1]) or h36(body) != head[3]:
        sys.exit('Kontrolní součet křivky nesouhlasí. Soubory nezměněny.')
    return [(d, float(v)) for d, v in (ln.split('|') for ln in lines[1:])]


def main(gpath, trades_csv):
    growth = read_growth(gpath)
    gfile = trades_csv[:-4] + '-growth.csv'
    with open(gfile, 'w', encoding='utf-8') as f:
        f.write('Date,Growth\n' + ''.join(f'{d},{v}\n' for d, v in growth))

    rows = list(csv.DictReader(open(trades_csv, encoding='utf-8')))
    byday = {}
    for r in rows:
        byday.setdefault(r['Close Date'][:10], []).append(r)

    # denní výnos z kumulativní křivky
    daily, prev = {}, 0.0
    for d, g in growth:
        daily[d] = (1 + g / 100) / (1 + prev / 100) - 1
        prev = g

    # odhad zůstatku: B = dolarový výsledek dne / denní výnos; nespolehlivé dny nahradí průběžný odhad
    est, bal = {}, None
    cands = []
    for d, _ in growth:
        p = sum(float(r['Profit']) for r in byday.get(d, []))
        r = daily[d]
        b = p / r if abs(r) > 0.002 and p * r > 0 else None
        cands.append((d, b, r))
    good = [b for _, b, _ in cands if b]
    if good:
        bal = sorted(good[:5])[len(good[:5]) // 2]
    for d, b, r in cands:
        if b and bal and 0.33 < b / bal < 3:
            bal = b
        elif b and not bal:
            bal = b
        est[d] = bal
        if bal:
            bal = bal * (1 + r)

    missing = 0
    for r in rows:
        d = r['Close Date'][:10]
        b = est.get(d)
        if b is None:  # den bez bodu křivky (např. obchod po posledním bodu) – použij poslední odhad
            later = [est[x] for x in sorted(est) if x <= d and est[x]]
            b = later[-1] if later else None
        if b:
            r['Pct'] = f"{float(r['Profit']) / b * 100:.5f}"
        else:
            r['Pct'] = ''
            missing += 1
    with open(trades_csv, 'w', encoding='utf-8', newline='') as f:
        w = csv.DictWriter(f, fieldnames=TRADE_HEADER, lineterminator='\n', extrasaction='ignore')
        w.writeheader()
        w.writerows(rows)
    print(f'Křivka: {len(growth)} dní, obchodů s % : {len(rows) - missing}, bez % : {missing}.')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
