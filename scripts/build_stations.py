#!/usr/bin/env python3
"""生成 /stations/index.html 和 data/stations.json。

数据来源: data/source-data.json（抓取自 apizhongzhuan.github.io/data.json，
其数据整理自 hvoyai.com 的公开聚合信息）。

用法: python3 scripts/build_stations.py
"""
import datetime
import html
import json
import random
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "source-data.json"
OUT_JSON = ROOT / "data" / "stations.json"
OUT_HTML = ROOT / "stations" / "index.html"
SITE_URL = "https://aituijian.github.io"
TOP_N = 200
CANDIDATE_POOL = 400


def slugify(name: str, rank: int) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", name).strip("-").lower()
    if not s:
        s = "site"
    return f"{rank}-{s}"


def fmt_models(models):
    if not models:
        return "暂未公开具体模型清单"
    sample = models[:3]
    return "、".join(sample)


def fmt_payment(methods):
    if not methods:
        return "暂未公开付款方式"
    return "、".join(methods)


def to_hvoyai(url):
    return url.replace("hvoy.ai", "hvoyai.com")


def summary_for(site, idx):
    name = site["name"]
    models_sample = fmt_models(site.get("models"))
    model_count = site.get("modelCount")
    uptime = site.get("uptime")
    latency = site.get("latencyMs")
    rating = site.get("userRating")
    rating_count = site.get("ratingCount") or 0
    established = site.get("establishedDate")
    payments = fmt_payment(site.get("paymentMethods"))
    refund = site.get("supportsRefund")
    invoice = site.get("supportsInvoice")

    model_clause = f"接入了 {model_count} 种模型" if model_count else "接入模型数量未公开"
    uptime_clause = f"近期在线率 {uptime}%" if uptime is not None else "在线率数据暂缺"
    latency_clause = f"平均响应约 {latency}ms" if latency is not None else "响应速度数据暂缺"
    rating_clause = (
        f"用户评分 {rating} 分（{rating_count} 人评价）"
        if rating is not None and rating_count
        else "尚未积累足够评分"
    )
    extra_bits = []
    if refund:
        extra_bits.append("支持退款")
    if invoice:
        extra_bits.append("可开发票")
    extra_clause = "，".join(extra_bits)

    variant = idx % 3
    if variant == 0:
        text = f"{name} {model_clause}，包含 {models_sample} 等，{uptime_clause}，{latency_clause}。"
    elif variant == 1:
        text = f"{name} 支持 {payments} 付款，{model_clause}，其中含 {models_sample}，{rating_clause}。"
    else:
        est_clause = f"上线于 {established}，" if established else ""
        text = f"{est_clause}{name} 目前 {model_clause}（{models_sample} 等），{uptime_clause}，{rating_clause}。"

    if extra_clause:
        text += f"该站{extra_clause}。"
    return text


def build_dataset():
    raw = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidates = sorted(raw["sites"], key=lambda s: s.get("rank", 999999))[:CANDIDATE_POOL]
    selected = []
    skipped = []
    for site in candidates:
        if len(selected) >= TOP_N:
            break
        if not site.get("modelCount") and not site.get("paymentMethods") and site.get("uptime") is None:
            skipped.append(f"{site['name']}(空数据)")
            continue
        selected.append(site)
    if skipped:
        print(f"跳过 {len(skipped)} 家数据不完整的站点（{'、'.join(skipped)}），已用排名更靠后的站点补足 {TOP_N} 家。")
    if len(selected) < TOP_N:
        print(f"警告：候选池不够，只生成了 {len(selected)} 家，考虑把 CANDIDATE_POOL 调大。")

    random.shuffle(selected)

    out = []
    for idx, site in enumerate(selected):
        visit_url = to_hvoyai(site["url"])
        out.append(
            {
                "slug": slugify(site["name"], idx + 1),
                "rank": idx + 1,
                "sourceRank": site.get("rank"),
                "name": site["name"],
                "url": visit_url,
                "modelCount": site.get("modelCount"),
                "models": site.get("models") or [],
                "uptime": site.get("uptime"),
                "latencyMs": site.get("latencyMs"),
                "userRating": site.get("userRating"),
                "ratingCount": site.get("ratingCount") or 0,
                "paymentMethods": site.get("paymentMethods") or [],
                "supportsRefund": bool(site.get("supportsRefund")),
                "supportsInvoice": bool(site.get("supportsInvoice")),
                "establishedDate": site.get("establishedDate"),
                "summary": summary_for(site, idx),
            }
        )
    return raw, out


def card_html(s):
    e = html.escape
    tags = [f'<span class="tag">{e(str(s["modelCount"]))} 种模型</span>' if s["modelCount"] else ""]
    if s["uptime"] is not None:
        cls = "good" if s["uptime"] >= 99 else ""
        tags.append(f'<span class="tag {cls}">在线率 {e(str(s["uptime"]))}%</span>')
    if s["latencyMs"] is not None:
        tags.append(f'<span class="tag">延迟 {e(str(s["latencyMs"]))}ms</span>')
    if s["userRating"] is not None and s["ratingCount"]:
        tags.append(f'<span class="tag">评分 {e(str(s["userRating"]))}（{s["ratingCount"]}人）</span>')
    if s["supportsRefund"]:
        tags.append('<span class="tag good">支持退款</span>')
    if s["supportsInvoice"]:
        tags.append('<span class="tag good">可开发票</span>')
    tags_html = "".join(t for t in tags if t)

    payments = e(fmt_payment(s["paymentMethods"]))

    return f"""
      <article class="station-card" id="{e(s['slug'])}" data-search="{e(s['name'].lower())} {e(' '.join(s['models']).lower())}">
        <div class="head">
          <h3><a href="{e(s['url'])}" target="_blank" rel="nofollow noopener noreferrer">{e(s['name'])}</a></h3>
          <span class="rank-badge">第 {s['rank']} 名</span>
        </div>
        <p class="summary">{e(s['summary'])}</p>
        <div class="tag-row">{tags_html}</div>
        <div class="stats"><span>付款方式：<strong>{payments}</strong></span></div>
        <a class="visit" href="{e(s['url'])}" target="_blank" rel="nofollow noopener noreferrer">访问站点 →</a>
      </article>"""


def itemlist_jsonld(stations):
    items = [
        {
            "@type": "ListItem",
            "position": s["rank"],
            "url": s["url"],
            "name": s["name"],
        }
        for s in stations
    ]
    data = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": "AI API 中转站推荐榜",
        "numberOfItems": len(items),
        "itemListElement": items,
    }
    return json.dumps(data, ensure_ascii=False)


def breadcrumb_jsonld():
    data = {
        "@context": "https://schema.org",
        "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "首页", "item": SITE_URL + "/"},
            {"@type": "ListItem", "position": 2, "name": "中转站推荐", "item": SITE_URL + "/stations/"},
        ],
    }
    return json.dumps(data, ensure_ascii=False)


PAGE_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI API 中转站推荐榜 Top {count}（{date} 更新）| AI中转站推荐</title>
<meta name="description" content="收录 {count} 家 AI API 中转站，按模型覆盖数、在线率、延迟、用户评分整理，含支付方式与退款/发票信息，方便挑选前先做对比。">
<link rel="canonical" href="{site_url}/stations/">
<meta name="robots" content="index,follow">
<meta property="og:type" content="website">
<meta property="og:title" content="AI API 中转站推荐榜 Top {count}">
<meta property="og:description" content="收录 {count} 家 AI API 中转站，按模型覆盖数、在线率、延迟、用户评分整理，方便对比挑选。">
<meta property="og:url" content="{site_url}/stations/">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="/assets/style.css">
<script type="application/ld+json">{itemlist_ld}</script>
<script type="application/ld+json">{breadcrumb_ld}</script>
<script>
var _hmt = _hmt || [];
(function() {{
  var hm = document.createElement("script");
  hm.src = "https://hm.baidu.com/hm.js?9f8f0ae7252eb5810e75bc1a3bed33d7";
  var s = document.getElementsByTagName("script")[0];
  s.parentNode.insertBefore(hm, s);
}})();
</script>
</head>
<body>
<header class="site-header">
  <div class="container">
    <a class="brand" href="/">
      <svg viewBox="0 0 64 64"><rect width="64" height="64" rx="14" fill="#eef1ec"/><path d="M16 40 L28 22 L36 34 L48 18" stroke="#2f6b3a" stroke-width="5" fill="none" stroke-linecap="round" stroke-linejoin="round"/><circle cx="48" cy="18" r="4" fill="#2f6b3a"/></svg>
      AI中转站推荐
    </a>
    <nav class="main-nav">
      <a href="/">科普与避坑指南</a>
      <a href="/stations/">中转站推荐榜</a>
      <a href="/#faq">常见问题</a>
    </nav>
  </div>
</header>

<main>
  <div class="container">
    <h1 style="margin-top:32px;">AI API 中转站推荐榜（Top {count}）</h1>
    <p style="color:var(--text-muted);max-width:720px;">按模型覆盖、在线率、延迟和用户评分整理的中转站列表，数据每次更新时间见下方说明。点进任何一家之前，建议先看首页的<a href="/#checklist">《怎么判断一个中转站靠不靠谱》</a>，再小额测试。</p>

    <div class="disclaimer">
      数据整理自公开聚合信息，更新于 {source_updated}，仅供横向对比参考，不构成推荐或担保。请在正式使用前自行核实价格、模型真实性与售后条款，建议先小额充值测试再决定是否长期使用。
    </div>

    <div class="stations-toolbar">
      <input type="search" id="station-search" placeholder="按名称或模型搜索，例如 Claude、GPT、DeepSeek" aria-label="搜索中转站">
      <span class="stations-count" id="station-count">共 {count} 家</span>
    </div>

    <div class="station-grid" id="station-grid">
{cards}
    </div>
    <p class="no-result" id="no-result">没有找到匹配的中转站，换个关键词试试。</p>
  </div>
</main>

<footer class="site-footer">
  <div class="container">
    <span>&copy; {year} AI中转站推荐</span>
    <span><a href="/">返回首页</a></span>
  </div>
</footer>

<script>
(function () {{
  var input = document.getElementById('station-search');
  var cards = Array.prototype.slice.call(document.querySelectorAll('.station-card'));
  var countEl = document.getElementById('station-count');
  var noResult = document.getElementById('no-result');
  input.addEventListener('input', function () {{
    var q = input.value.trim().toLowerCase();
    var visible = 0;
    cards.forEach(function (card) {{
      var match = !q || card.getAttribute('data-search').indexOf(q) !== -1;
      card.style.display = match ? '' : 'none';
      if (match) visible++;
    }});
    countEl.textContent = '共 ' + visible + ' 家';
    noResult.style.display = visible === 0 ? 'block' : 'none';
  }});
}})();
</script>
</body>
</html>
"""


def pick_card_html(s):
    e = html.escape
    return f"""
          <div class="pick-card">
            <div class="rank">第 {s['rank']} 名</div>
            <div class="name"><a href="{e(s['url'])}" target="_blank" rel="nofollow noopener noreferrer">{e(s['name'])}</a></div>
            <div class="meta">{e(fmt_models(s['models']))}</div>
          </div>"""


def inject_picks(stations, n=12):
    index_path = ROOT / "index.html"
    if not index_path.exists():
        return
    content = index_path.read_text(encoding="utf-8")
    start_marker = "<!-- PICKS_START -->"
    end_marker = "<!-- PICKS_END -->"
    if start_marker not in content or end_marker not in content:
        return
    picks_html = "\n".join(pick_card_html(s) for s in stations[:n])
    pre, _, rest = content.partition(start_marker)
    _, _, post = rest.partition(end_marker)
    new_content = f"{pre}{start_marker}\n{picks_html}\n          {end_marker}{post}"
    index_path.write_text(new_content, encoding="utf-8")


def inject_date(today):
    index_path = ROOT / "index.html"
    if not index_path.exists():
        return
    content = index_path.read_text(encoding="utf-8")
    pattern = re.compile(r"<!-- DATE_START -->.*?<!-- DATE_END -->", re.S)
    if not pattern.search(content):
        return
    new_content = pattern.sub(f"<!-- DATE_START -->{today}<!-- DATE_END -->", content)
    index_path.write_text(new_content, encoding="utf-8")


def main():
    raw, stations = build_dataset()
    today = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
    OUT_JSON.write_text(
        json.dumps(
            {
                "sourceUpdatedDate": today,
                "generatedAt": datetime.datetime.now(datetime.timezone.utc).isoformat(),
                "count": len(stations),
                "stations": stations,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    cards = "\n".join(card_html(s) for s in stations)
    html_out = PAGE_TEMPLATE.format(
        count=len(stations),
        date=today,
        source_updated=today,
        site_url=SITE_URL,
        cards=cards,
        itemlist_ld=itemlist_jsonld(stations),
        breadcrumb_ld=breadcrumb_jsonld(),
        year=datetime.date.today().year,
    )
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html_out, encoding="utf-8")
    inject_picks(stations)
    inject_date(today)
    print(f"生成 {len(stations)} 条记录 -> {OUT_JSON} / {OUT_HTML}，并更新首页精选卡片")


if __name__ == "__main__":
    main()
