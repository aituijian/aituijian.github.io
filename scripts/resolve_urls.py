#!/usr/bin/env python3
"""把 data/source-data.json 里 hvoy.ai 的档案页链接，解析成中转站自己的真实官网域名。

每条记录的 "url" 字段实际是 https://www.hvoy.ai/sites/xxx/ 这样的第三方
档案页，不是站点本身。档案页的 JSON-LD 里有 "sameAs": "https://真实域名"，
这里把它抓出来，写入 data/url-cache.json 做缓存，供 build_stations.py 使用。

用法: python3 scripts/resolve_urls.py [--limit N]
"""
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "source-data.json"
CACHE = ROOT / "data" / "url-cache.json"
TOP_N = 200

SAME_AS_RE = re.compile(r'"sameAs"\s*:\s*"([^"]+)"')


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; aituijian-directory-bot/1.0)"
        },
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def main():
    limit = TOP_N
    if "--limit" in sys.argv:
        limit = int(sys.argv[sys.argv.index("--limit") + 1])

    raw = json.loads(SOURCE.read_text(encoding="utf-8"))
    sites = sorted(raw["sites"], key=lambda s: s.get("rank", 999999))[:limit]

    cache = {}
    if CACHE.exists():
        cache = json.loads(CACHE.read_text(encoding="utf-8"))

    resolved = 0
    failed = []
    for site in sites:
        url = site["url"]
        if url in cache:
            continue
        html = None
        for attempt in range(5):
            try:
                html = fetch(url)
                break
            except urllib.error.HTTPError as exc:
                if exc.code == 429:
                    time.sleep(3 * (attempt + 1))
                    continue
                html = None
                break
            except Exception:  # noqa: BLE001
                time.sleep(1.5 * (attempt + 1))
                continue
        if html is None:
            failed.append((site["name"], url))
            time.sleep(1.5)
            continue
        m = SAME_AS_RE.search(html)
        if m:
            cache[url] = m.group(1)
            resolved += 1
        else:
            failed.append((site["name"], url))
        time.sleep(1.5)
        if resolved % 10 == 0 and resolved:
            CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")

    CACHE.write_text(json.dumps(cache, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"解析成功 {resolved} 条，缓存共 {len(cache)} 条，失败 {len(failed)} 条")
    for name, url in failed:
        print("  失败:", name, url)


if __name__ == "__main__":
    main()
