// Spouští se v prohlížeči na libovolné stránce www.myfxbook.com.
// Stáhne veřejnou křivku růstu (Growth, kumulativní % po dnech, bez vlivu vkladů a výběrů)
// pro účet ACCOUNT_ID a vrátí text: "GROWTH <počet> SUM <kontrolní součet>" a pak řádky "YYYY-MM-DD|growth%".
// ACCOUNT_ID nahraďte číslem účtu (12034345 robot, 12309673 manuál).
(async (id = ACCOUNT_ID) => {
  const u = '/private/charts.json?startDate=2026-01-01%2000:00&endDate=2099-12-31%2023:59&invitation=&showLots=true&showPips=false&showChange=false&showSymbolPips=true&showMain=true&magicNumbers=&symbols=&tags=&days=1,5,2,6,3,7,4&hours=0,4,8,12,16,20,1,5,9,13,17,21,2,6,10,14,18,22,3,7,11,15,19,23&buySell=0,1,6,16&yieldStart=&yieldEnd=&takeProfitStart=&takeProfitEnd=&stopLoss=&stopLossEnd=&sizingStart=&sizingEnd=&selectedTime=1&pipsStart=&pipsEnd=&chartType=1&period=6&l=s&accountOid=' + id + '&rand=' + Math.random();
  let j;
  try { j = await (await fetch(u, { method: 'POST', credentials: 'include' })).json(); } catch (e) { return 'ERROR: ' + e.message; }
  const g = (j.series || []).find(s => s.name === 'Growth');
  if (!g) return 'ERROR: odpověď neobsahuje křivku Growth';
  const M = { Jan: 1, Feb: 2, Mar: 3, Apr: 4, May: 5, Jun: 6, Jul: 7, Aug: 8, Sep: 9, Oct: 10, Nov: 11, Dec: 12 };
  const body = g.data.map(([i, v]) => { const m = j.categories[i].match(/(\w+) (\d+), '(\d+)/); return '20' + m[3] + '-' + String(M[m[1]]).padStart(2, '0') + '-' + m[2].padStart(2, '0') + '|' + v; }).join('\n');
  let h = 0; for (let i = 0; i < body.length; i++) h = (h * 31 + body.charCodeAt(i)) >>> 0;
  return 'GROWTH ' + g.data.length + ' SUM ' + h.toString(36) + '\n' + body;
})()
