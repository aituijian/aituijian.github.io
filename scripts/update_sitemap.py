#!/usr/bin/env python3
"""重新生成 sitemap.xml，把 lastmod 更新为当天日期。

用法: python3 scripts/update_sitemap.py
"""
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "sitemap.xml"
SITE_URL = "https://aituijian.github.io"

TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url>
    <loc>{site_url}/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>1.0</priority>
  </url>
  <url>
    <loc>{site_url}/stations/</loc>
    <lastmod>{today}</lastmod>
    <changefreq>weekly</changefreq>
    <priority>0.9</priority>
  </url>
</urlset>
"""


def main():
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    OUT.write_text(TEMPLATE.format(site_url=SITE_URL, today=today), encoding="utf-8")
    print(f"sitemap.xml 已更新，lastmod = {today}")


if __name__ == "__main__":
    main()
