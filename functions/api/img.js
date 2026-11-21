// GET /api/img?u=<encoded url>  -> 服务端抓图并回传（仅允许白名单域名）
const ALLOW = [
  'c0.jdbstatic.com', 'c1.jdbstatic.com', 'c2.jdbstatic.com',
  'c3.jdbstatic.com', 'c4.jdbstatic.com', 'c5.jdbstatic.com',
  'cf.javfree.me', 'javfree.me',
];

export async function onRequestGet({ request }) {
  const url = new URL(request.url);
  const target = url.searchParams.get('u') || '';
  if (!target) return new Response('missing u', { status: 400 });

  let host;
  try {
    host = new URL(target).hostname.toLowerCase();
  } catch {
    return new Response('bad url', { status: 400 });
  }
  if (!ALLOW.includes(host)) return new Response('host not allowed', { status: 403 });

  // 尺寸参数（可选）：w/h/type
  const w = url.searchParams.get('w');
  const q = url.searchParams.get('q') || '80';

  try {
    const upstream = await fetch(target, {
      headers: {
        'User-Agent':
          'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
          '(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36',
        Referer: 'https://javdb.com/',
        Accept: 'image/avif,image/webp,image/apng,image/*,*/*;q=0.8',
      },
      cf: { cacheEverything: true, cacheTtl: 604800 },
    });
    if (!upstream.ok) {
      return new Response('upstream ' + upstream.status, { status: 502 });
    }
    const body = await upstream.arrayBuffer();
    const type = upstream.headers.get('content-type') || 'image/jpeg';
    return new Response(body, {
      status: 200,
      headers: {
        'Content-Type': type,
        'Cache-Control': 'public, max-age=604800, immutable',
        'Access-Control-Allow-Origin': '*',
        'X-Img-Proxy': 'dsh',
        ...(w ? { 'X-Width': w } : {}),
        ...(q ? { 'X-Q': q } : {}),
      },
    });
  } catch (e) {
    return new Response('fetch error: ' + String(e).slice(0, 100), { status: 502 });
  }
}
