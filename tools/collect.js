// Spouští se v prohlížeči na stránce https://www.myfxbook.com/statements/12034345/statement.html
// Stáhne nejnovější stránky uzavřených obchodů (výchozí 1 stránka = 100 obchodů)
// a vrátí kompaktní text: první řádek "PAGES <n> COUNT <počet> SUM <kontrolní součet>",
// pak jeden obchod na řádek: otevření|zavření (yymmddhhmm)|b/s|loty*100|pipy*10
(async (pages = 1) => {
  const btn = document.querySelector('a.paging-btn');
  if (!btn) return 'ERROR: na stránce není stránkování výpisu';
  const base = btn.getAttribute('params');
  const conv = s => { const m = s.match(/(\d+)\.(\d+)\.(\d+) (\d+):(\d+)/); return m ? m[3].slice(2) + m[1].padStart(2, '0') + m[2].padStart(2, '0') + m[4].padStart(2, '0') + m[5] : null; };
  const out = [];
  for (let n = 1; n <= pages; n++) {
    const r = await fetch('/paging.html' + base.replace(/([?&])p=\d+/, '$1p=' + n) + '&z=' + Math.random(), { credentials: 'include' });
    const d = new DOMParser().parseFromString(await r.text(), 'text/html');
    const t = [...d.querySelectorAll('table')].find(x => /Open Date/.test(x.rows[0]?.innerText || ''));
    if (!t) return 'ERROR: stránka ' + n + ' neobsahuje tabulku obchodů';
    for (const row of [...t.rows].slice(1)) {
      const c = [...row.cells].map(x => x.textContent.trim().replace(/\s+/g, ' '));
      if (c[2] !== 'XAUUSD' || !/^(Buy|Sell)$/.test(c[3])) continue;
      out.push([conv(c[0]), conv(c[1]), c[3][0].toLowerCase(), Math.round(parseFloat(c[4]) * 100), Math.round(parseFloat(c[9]) * 10)].join('|'));
    }
  }
  const body = out.join('\n');
  let h = 0; for (let i = 0; i < body.length; i++) h = (h * 31 + body.charCodeAt(i)) >>> 0;
  return 'PAGES ' + pages + ' COUNT ' + out.length + ' SUM ' + h.toString(36) + '\n' + body;
})()
