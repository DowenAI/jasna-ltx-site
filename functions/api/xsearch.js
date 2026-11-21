// GET /api/xsearch?q=关键词&n=20  -> 搜索 X 上的视频推文，返回 ID 列表
export async function onRequestGet({ request }) {
  const u = new URL(request.url);
  const q = (u.searchParams.get('q') || '').trim();
  const n = Math.min(40, parseInt(u.searchParams.get('n') || '20', 10));
  if (!q) return json({ ok: false, error: 'missing q' }, 400);

  const ids = [];
  const seen = new Set();
  const UA =
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
    '(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36';

  const queries = ['site:x.com ' + q, 'site:twitter.com ' + q];

  for (const query of queries) {
    try {
      const body = new URLSearchParams({ q: query }).toString();
      const r = await fetch('https://html.duckduckgo.com/html/', {
        method: 'POST',
        headers: {
          'User-Agent': UA,
          'Content-Type': 'application/x-www-form-urlencoded',
          Accept: 'text/html,application/xhtml+xml,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
          Referer: 'https://duckduckgo.com/',
        },
        body,
      });
      const html = await r.text();
      const re1 = /(?:x|twitter)\.com\/([A-Za-z0-9_]+)\/status\/(\d{8,25})/g;
      let m;
      while ((m = re1.exec(html))) {
        if (!seen.has(m[2])) {
          seen.add(m[2]);
          ids.push(m[2]);
        }
      }
      // uddg 跳转链接
      const re2 = /uddg=([^&"]+)/g;
      while ((m = re2.exec(html))) {
        try {
          const real = decodeURIComponent(m[1]);
          const mm = real.match(/(?:x|twitter)\.com\/[A-Za-z0-9_]+\/status\/(\d{8,25})/);
          if (mm && !seen.has(mm[1])) {
            seen.add(mm[1]);
            ids.push(mm[1]);
          }
        } catch (e) {}
      }
    } catch (e) {
      // try next
    }
    if (ids.length >= n) break;
  }

  return json({ ok: true, q, count: ids.length, ids: ids.slice(0, n) });
}

function json(obj, status = 200) {
  return new Response(JSON.stringify(obj), {
    status,
    headers: {
      'Content-Type': 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'Access-Control-Allow-Origin': '*',
    },
  });
}
