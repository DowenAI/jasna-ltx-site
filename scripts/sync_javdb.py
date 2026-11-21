#!/usr/bin/env python3
"""
Jasna-LTX 数据自动更新器
从 JavDB 首页「最新上架」抓新作品，按站点数据格式追加到 data/movies.json。

用法:
    python scripts/sync_javdb.py --dry-run
    python scripts/sync_javdb.py --max-add 20
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data", "movies.json")

UA = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/157.0.0.0 Safari/537.36")
BASES = ["https://javdb.com", "https://javdb570.com"]


def log(*a):
    print("[sync]", *a, flush=True)


def curl(url, timeout=45):
    try:
        out = subprocess.run(
            ["curl", "-sL", "--max-time", str(timeout), "-A", UA,
             "-H", "Accept-Language: zh-CN,zh;q=0.9",
             "-H", "Accept: text/html,application/xhtml+xml,*/*;q=0.8", url],
            capture_output=True, timeout=timeout + 15)
        return out.stdout.decode("utf-8", "ignore")
    except Exception as e:
        log("   curl 失败:", str(e)[:60])
        return ""


def fetch(path, timeout=45):
    for b in BASES:
        html = curl(b + path, timeout=timeout)
        if html and len(html) > 20000:
            return html, b
    return "", None


def clean(s):
    s = re.sub(r"<[^>]+>", " ", s or "")
    for a, b in (("&nbsp;", " "), ("&amp;", "&"), ("&quot;", '"'),
                 ("&#39;", "'"), ("&lt;", "<"), ("&gt;", ">")):
        s = s.replace(a, b)
    return re.sub(r"\s+", " ", s).strip()


def field(html, label):
    """取 <strong>标签:</strong> ... </div> 里的值"""
    m = re.search(r"<strong>\s*" + label + r"[:：]?\s*</strong>(.*?)</div>", html, re.S)
    return clean(m.group(1)) if m else ""


def parse_detail(html, url):
    if not html or len(html) < 20000:
        return None

    code, title = "", ""
    m = re.search(r'<h2 class="title is-4">(.*?)</h2>', html, re.S)
    if m:
        block = m.group(1)
        cs = re.search(r"<strong>(.*?)</strong>", block, re.S)
        code = clean(cs.group(1)) if cs else ""
        title = clean(re.sub(r"<strong>.*?</strong>", "", block, flags=re.S))
    if not code:
        m2 = re.search(r'data-clipboard-text="([A-Z][A-Za-z0-9]{0,8}-\d{2,6})"', html)
        code = m2.group(1) if m2 else ""
    if not code:
        return None

    cover = ""
    m = re.search(r'<img[^>]+src="(https://c\d\.jdbstatic\.com/covers/[^"]+)"', html)
    if m:
        cover = m.group(1)

    date = field(html, "日期")
    maker = field(html, "片商") or field(html, "發行商")
    director = field(html, "導演")
    series = field(html, "系列")
    genres_raw = field(html, "類別")
    actors_raw = field(html, "演員")

    actors = []
    for a in re.split(r"[,、/]", actors_raw):
        a = a.strip()
        if a and not a.isdigit() and len(a) <= 24:
            actors.append(a)

    genres = [g.strip() for g in re.split(r"[,、]", genres_raw) if g.strip()][:8]

    score, votes = 0.0, 0
    m = re.search(r"([\d.]+)\s*分[,，]?\s*由\s*([\d,]+)\s*人評價", html)
    if m:
        try:
            score = float(m.group(1))
            votes = int(m.group(2).replace(",", ""))
        except Exception:
            pass
    else:
        m = re.search(r'<span class="score">([\d.]+)</span>', html)
        if m:
            try:
                score = float(m.group(1))
            except Exception:
                pass

    return {
        "actors": actors,
        "added_at": int(time.time() * 1000),
        "code": code,
        "comments": 0,
        "cover": cover,
        "date": date,
        "director": director,
        "genres": genres,
        "likers": 0,
        "link": "",
        "linkPending": True,
        "linkType": "",
        "links": [],
        "lists": 0,
        "maker": maker,
        "missing": False,
        "pending": True,
        "pending_links": [],
        "people": 0,
        "rawScore": score,
        "score": score,
        "series": series,
        "shot": "",
        "size": 0,
        "subtitle": "",
        "title": title,
        "title_zh": title,
        "url": url,
        "votes": votes,
        "waiting": False,
    }


def candidate_ids():
    """首页最新上架 + 分类页"""
    ids = []
    seen = set()
    for path in ("/", "/video_codes/SIRO", "/video_codes/GANA"):
        html, _ = fetch(path)
        if not html:
            continue
        for vid in re.findall(r'href="/v/([A-Za-z0-9]{5,10})"', html):
            if vid not in seen:
                seen.add(vid)
                ids.append(vid)
    return ids


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--max-add", type=int, default=20)
    args = ap.parse_args()

    if not os.path.exists(DATA):
        log("找不到", DATA)
        return 1

    data = json.load(open(DATA, encoding="utf-8"))
    items = data.get("items") or []
    known = {(it.get("code") or "").upper() for it in items}
    log("现有作品:", len(items))

    ids = candidate_ids()
    log("候选视频:", len(ids))

    added = []
    for vid in ids:
        if len(added) >= args.max_add:
            break
        html, base = fetch("/v/" + vid)
        it = parse_detail(html, (base or BASES[0]) + "/v/" + vid)
        if not it:
            continue
        if it["code"].upper() in known:
            continue
        known.add(it["code"].upper())
        added.append(it)
        log("  + %-12s %s  %s" % (it["code"], it["date"], it["title"][:34]))
        time.sleep(0.3)

    log("本次新增:", len(added))
    if args.dry_run:
        if added:
            log("样例:", json.dumps(added[0], ensure_ascii=False)[:400])
        return 0
    if not added:
        return 0

    data["items"] = added + items
    data["updated_at"] = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime())
    n = data.setdefault("nyaa", {})
    n["added"] = (n.get("added") or 0) + len(added)
    n["checked_at"] = int(time.time() * 1000)
    n["ok"] = True
    json.dump(data, open(DATA, "w", encoding="utf-8"),
              ensure_ascii=False, separators=(",", ":"))
    log("已写入，总条数:", len(data["items"]))
    return 0


if __name__ == "__main__":
    sys.exit(main())
