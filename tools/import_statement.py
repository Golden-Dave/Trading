#!/usr/bin/env python3
"""Doplní obchody z výpisu Myfxbooku (CSV export „Statement“) do souboru obchodů.

Použití:  python3 tools/import_statement.py vypis.csv [další.csv …] [--target data/manual.csv]
Výpis se nahraje do složky imports/ v repozitáři (na GitHubu: Add file → Upload files). Workflow
„Aktualizace obchodů – manuál“ ho při nahrání sám zpracuje, chybějící obchody přidá (existující nezdvojí)
a soubor z imports/ smaže. Procenta obchodů pak dopočítá tools/enrich.py při stažení z API.
Vklady, výběry a jiné řádky než Buy/Sell se přeskočí.
"""
import sys, os, csv, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import merge_trades  # noqa: E402


def stamp(s):  # "11/23/2026 17:08" -> "2611231708"
    d, t = s.strip().split(' ')
    m, dd, y = d.split('/')
    hh, mi = t.split(':')[:2]
    return y[2:] + m.zfill(2) + dd.zfill(2) + hh.zfill(2) + mi.zfill(2)


def lines_from(path):
    out = []
    with open(path, encoding='utf-8-sig', newline='') as f:
        for r in csv.DictReader(f):
            act = (r.get('Action') or '').strip()
            if act not in ('Buy', 'Sell') or not (r.get('Close Date') or '').strip():
                continue
            sym = ''.join(ch for ch in (r.get('Symbol') or '').upper() if ch.isalnum() or ch in '._-')
            try:
                lots = round(float(r.get('Units/Lots') or r.get('Lots') or 0) * 100)
                pips = round(float(r.get('Pips') or 0) * 10)
            except ValueError:
                continue
            out.append('|'.join([stamp(r['Open Date']), stamp(r['Close Date']), act[0].lower(), str(lots), str(pips)]
                                + ([sym] if sym and sym != 'XAUUSD' else [])))
    return out


def main(argv):
    target = os.path.join(HERE, '..', 'data', 'manual.csv')
    files = []
    it = iter(argv)
    for a in it:
        if a == '--target':
            target = next(it)
        else:
            files.append(a)
    lines = []
    for p in files:
        got = lines_from(p)
        print(f'{os.path.basename(p)}: {len(got)} obchodů ve výpisu.')
        lines += got
    if not lines:
        sys.exit('Ve výpisu nejsou žádné obchody (čeká se CSV export výpisu z Myfxbooku).')
    body = '\n'.join(lines)
    tf = os.path.join(tempfile.mkdtemp(), 'stmt.txt')
    with open(tf, 'w', encoding='utf-8') as f:
        f.write(f'PAGES 1 COUNT {len(lines)} SUM {merge_trades.h36(body)}\n{body}')
    merge_trades.main(tf, target)


if __name__ == '__main__':
    main(sys.argv[1:])
