// Spouští se v prohlížeči na stránce veřejného výpisu Myfxbook, např.
//   https://www.myfxbook.com/statements/12034345/statement.html  (robot)
//   https://www.myfxbook.com/statements/12309673/statement.html  (manuál)
// Stáhne nejnovější stránky uzavřených obchodů (výchozí 1 stránka = 100 obchodů)
// a vrátí kompaktní text: první řádek "PAGES <n> COUNT <počet> SUM <kontrolní součet>",
// pak jeden obchod na řádek: otevření|zavření (yymmddhhmm)|b/s|loty*100|pipy*10
// Sloupce se hledají podle názvů v hlavičce, takže nezáleží na tom, které sloupce účet zveřejňuje.
(async (pages = 1) => {
  const conv = s => { const m = s.match(/(\d+)\.(\d+)\.(\d+) (\d+):(\d+)/); return m ? m[3].slice(2) + m[1].padStart(2, '0') + m[2].padStart(2, '0') + m[4].padStart(2, '0') + m[5] : null; };
  const findTable = d => [...d.querySelectorAll('table')].find(x => /Open Date/.test(x.rows[0]?.innerText || x.rows[0]?.textContent || ''));
  const out = [];
  const take = t => {
    const head = [...t.rows[0].cells].map(c => c.textContent.trim().toLowerCase());
    const ix = n => head.findIndex(h => n.test(h));
    const io = ix(/^open date/), ic = ix(/^close date/), is = ix(/^symbol/), ia = ix(/^action/), il = ix(/^lots?$/), ip = ix(/^pips$/);
    if ([io, ic, is, ia, il, ip].some(i => i < 0)) throw new Error('výpis nemá potřebné sloupce (chybí Lots nebo Pips?): ' + head.join(', '));
    for (const row of [...t.rows].slice(1)) {
      const c = [...row.cells].map(x => x.textContent.trim().replace(/\s+/g, ' '));
      if (c[is] !== 'XAUUSD' || !/^(Buy|Sell)$/.test(c[ia])) continue;
      out.push([conv(c[io]), conv(c[ic]), c[ia][0].toLowerCase(), Math.round(parseFloat(c[il]) * 100), Math.round(parseFloat(c[ip]) * 10)].join('|'));
    }
  };
  try {
    const btn = document.querySelector('a.paging-btn');
    if (!btn) {
      const t = findTable(document);
      if (!t) return 'ERROR: na stránce není tabulka obchodů';
      take(t); pages = 1;
    } else {
      const base = btn.getAttribute('params');
      for (let n = 1; n <= pages; n++) {
        const r = await fetch('/paging.html' + base.replace(/([?&])p=\d+/, '$1p=' + n) + '&z=' + Math.random(), { credentials: 'include' });
        const t = findTable(new DOMParser().parseFromString(await r.text(), 'text/html'));
        if (!t) { if (n === 1) return 'ERROR: stránka 1 neobsahuje tabulku obchodů'; break; }
        take(t);
      }
    }
  } catch (e) { return 'ERROR: ' + e.message; }
  const body = out.join('\n');
  let h = 0; for (let i = 0; i < body.length; i++) h = (h * 31 + body.charCodeAt(i)) >>> 0;
  return 'PAGES ' + pages + ' COUNT ' + out.length + ' SUM ' + h.toString(36) + '\n' + body;
})()
