#!/usr/bin/env python3
"""从 apizhongzhuan.github.io 拉取最新的 data.json，覆盖 data/source-data.json。

会先校验返回内容是合法 JSON 且包含足够多的 sites 记录，避免对方站点
临时故障（返回空内容/错误页）时把本地缓存冲成坏数据。校验失败时以
非零退出码退出，供 CI 判断是否继续往下跑。

用法: python3 scripts/fetch_source.py
"""
import json
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_URL = "https://apizhongzhuan.github.io/data.json"
OUT = ROOT / "data" / "source-data.json"
MIN_SITES = 100


def fetch(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; aituijian-directory-bot/1.0)"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="ignore")


def main():
    try:
        raw_text = fetch(SOURCE_URL)
    except Exception as exc:  # noqa: BLE001
        print(f"抓取失败: {exc}")
        sys.exit(1)

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError as exc:
        print(f"返回内容不是合法 JSON: {exc}")
        sys.exit(1)

    sites = data.get("sites")
    if not isinstance(sites, list) or len(sites) < MIN_SITES:
        print(f"数据校验失败：sites 数量为 {len(sites) if isinstance(sites, list) else 'N/A'}，少于阈值 {MIN_SITES}，放弃覆盖本地缓存。")
        sys.exit(1)

    OUT.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"抓取成功，共 {len(sites)} 条记录，更新日期 {data.get('updatedDate')} -> {OUT}")


if __name__ == "__main__":
    main()
