#!/usr/bin/env python3
"""
Situation Report - 全球态势感知工具
数据源: GDELT (新闻), CoinGecko (加密), FRED (美联储), Finnhub (市场)
"""

import argparse
import json
import sys
import os
import time
from datetime import datetime, timedelta
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from urllib.parse import quote_plus


# ================================================================
# 配置
# ================================================================

FINNHUB_KEY = os.environ.get("FINNHUB_API_KEY", "d69euehr01qjmno53050d69euehr01qjmno5305g")
FRED_KEY = os.environ.get("FRED_API_KEY", "")

TIMEOUT = 15  # 秒

# GDELT 新闻分类
NEWS_TOPICS = {
    "world":    "world",
    "china":    "china",
    "us":       "united states",
    "russia":   "russia",
    "ukraine":  "ukraine",
    "ai":       "artificial intelligence",
    "tech":     "technology",
    "finance":  "economy OR markets OR stocks",
    "military": "military OR defense OR troops",
    "trade":    "trade OR tariff OR sanctions",
}

# 加密货币列表
DEFAULT_COINS = "bitcoin,ethereum,solana,cardano,dogecoin"

# FRED 经济指标
FRED_SERIES = {
    "DFF":       "联邦基金利率",
    "T10Y2Y":    "10年-2年国债利差",
    "UNRATE":    "失业率",
    "CPIAUCSL":  "CPI 消费者物价指数",
    "GDP":       "GDP",
    "VIXCLS":    "VIX 恐慌指数",
}


# ================================================================
# 工具函数
# ================================================================

def fetch_json(url, timeout=TIMEOUT):
    """HTTP GET 返回 JSON"""
    try:
        req = Request(url, headers={"User-Agent": "situation-report/1.0"})
        resp = urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode())
    except HTTPError as e:
        return {"error": f"HTTP {e.code}", "url": url}
    except URLError as e:
        return {"error": f"网络错误: {e.reason}", "url": url}
    except Exception as e:
        return {"error": str(e), "url": url}


def fetch_text(url, timeout=TIMEOUT):
    """HTTP GET 返回文本"""
    try:
        req = Request(url, headers={"User-Agent": "situation-report/1.0"})
        resp = urlopen(req, timeout=timeout)
        return resp.read().decode()
    except Exception as e:
        return None


def fmt_time(ts):
    """格式化时间戳"""
    try:
        dt = datetime.strptime(ts[:19], "%Y%m%dT%H%M%S")
        return dt.strftime("%Y-%m-%d %H:%M")
    except:
        return ts[:16] if ts else "unknown"


# ================================================================
# 数据源: GDELT 新闻
# ================================================================

def fetch_news(topic="world", limit=15):
    """从 GDELT 获取新闻"""
    query = NEWS_TOPICS.get(topic, topic)
    if " OR " in query:
        query = f"({query})"
    encoded_query = quote_plus(query)
    url = (
        f"https://api.gdeltproject.org/api/v2/doc/doc"
        f"?query={encoded_query}&mode=ArtList&maxrecords={limit}"
        f"&format=json&sort=DateDesc"
    )
    data = fetch_json(url)

    if "error" in data:
        return data

    articles = data.get("articles", [])
    results = []
    seen_titles = set()

    for a in articles:
        title = a.get("title", "").strip()
        # 去重
        if title.lower() in seen_titles:
            continue
        seen_titles.add(title.lower())

        results.append({
            "title":    title,
            "source":   a.get("domain", "unknown"),
            "url":      a.get("url", ""),
            "time":     fmt_time(a.get("seendate", "")),
            "language": a.get("language", ""),
        })

    return {
        "topic":     topic,
        "query":     query,
        "count":     len(results),
        "articles":  results,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ================================================================
# 数据源: CoinGecko 加密货币
# ================================================================

def fetch_crypto(coins=DEFAULT_COINS):
    """从 CoinGecko 获取加密货币价格"""
    url = (
        f"https://api.coingecko.com/api/v3/simple/price"
        f"?ids={coins}"
        f"&vs_currencies=usd"
        f"&include_24hr_change=true"
        f"&include_market_cap=true"
        f"&include_24hr_vol=true"
    )
    data = fetch_json(url)

    if "error" in data:
        return data

    results = []
    for coin_id, info in data.items():
        results.append({
            "coin":       coin_id,
            "price_usd":  info.get("usd", 0),
            "change_24h": round(info.get("usd_24h_change", 0), 2),
            "market_cap": info.get("usd_market_cap", 0),
            "volume_24h": info.get("usd_24h_vol", 0),
        })

    results.sort(key=lambda x: x["market_cap"], reverse=True)

    return {
        "count":     len(results),
        "coins":     results,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ================================================================
# 数据源: Yahoo Finance 经济/市场指标
# ================================================================

def fetch_fed():
    """从 Yahoo Finance 获取经济相关指标"""
    symbols = {
        "^VIX":   "VIX 恐慌指数",
        "^TNX":   "10年期美债收益率",
        "^FVX":   "5年期美债收益率",
        "^TYX":   "30年期美债收益率",
        "GC=F":   "黄金期货",
        "CL=F":   "原油期货 (WTI)",
        "DX-Y.NYB": "美元指数",
    }

    results = []
    for symbol, name in symbols.items():
        url = (
            f"https://query1.finance.yahoo.com/v8/finance/chart/"
            f"{symbol}?interval=1d&range=5d"
        )
        data = fetch_json(url)

        if "error" in data and isinstance(data["error"], str):
            results.append({"symbol": symbol, "name": name, "error": data["error"]})
            continue

        try:
            chart = data.get("chart", {}).get("result", [{}])[0]
            meta = chart.get("meta", {})
            price = meta.get("regularMarketPrice", 0)
            prev = meta.get("chartPreviousClose", 0)
            change = round(price - prev, 4) if prev else 0
            change_pct = round(change / prev * 100, 2) if prev else 0

            results.append({
                "symbol":     symbol,
                "name":       name,
                "price":      price,
                "prev_close": prev,
                "change":     change,
                "change_pct": change_pct,
            })
        except (KeyError, IndexError, TypeError) as e:
            results.append({"symbol": symbol, "name": name, "error": str(e)})

    return {
        "count":      len(results),
        "indicators": results,
        "source":     "Yahoo Finance",
        "timestamp":  datetime.utcnow().isoformat() + "Z",
    }


# ================================================================
# 数据源: Finnhub 市场数据
# ================================================================

def fetch_markets():
    """从 Finnhub 获取市场数据"""
    if not FINNHUB_KEY:
        return {"error": "FINNHUB_API_KEY 未设置。获取免费 Key: https://finnhub.io/"}

    symbols = {
        "AAPL":  "苹果",
        "MSFT":  "微软",
        "GOOGL": "谷歌",
        "AMZN":  "亚马逊",
        "NVDA":  "英伟达",
        "TSLA":  "特斯拉",
        "SPY":   "标普500 ETF",
        "QQQ":   "纳斯达克100 ETF",
        "DIA":   "道琼斯 ETF",
        "GLD":   "黄金 ETF",
    }

    results = []
    for symbol, name in symbols.items():
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
        data = fetch_json(url)

        if "error" in data:
            results.append({"symbol": symbol, "name": name, "error": data["error"]})
            continue

        c = data.get("c", 0)   # current
        pc = data.get("pc", 0) # previous close
        change_pct = round((c - pc) / pc * 100, 2) if pc else 0

        results.append({
            "symbol":     symbol,
            "name":       name,
            "price":      c,
            "prev_close": pc,
            "change_pct": change_pct,
            "high":       data.get("h", 0),
            "low":        data.get("l", 0),
        })

        time.sleep(0.1)  # 限速

    return {
        "count":     len(results),
        "stocks":    results,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


# ================================================================
# 自定义关键词监控
# ================================================================

def fetch_watch(keywords):
    """监控自定义关键词"""
    kw_list = [k.strip() for k in keywords.split(",")]
    query = " OR ".join(kw_list)
    return fetch_news(topic=query, limit=20)


# ================================================================
# 完整报告
# ================================================================

def full_report():
    """生成完整态势报告"""
    report = {
        "report_type": "SITUATION REPORT",
        "generated":   datetime.utcnow().isoformat() + "Z",
        "sections":    {}
    }

    print("正在获取全球新闻...", file=sys.stderr)
    report["sections"]["news_world"] = fetch_news("world", 10)

    print("正在获取中国相关新闻...", file=sys.stderr)
    report["sections"]["news_china"] = fetch_news("china", 8)

    print("正在获取科技新闻...", file=sys.stderr)
    report["sections"]["news_tech"] = fetch_news("ai", 8)

    print("正在获取加密货币数据...", file=sys.stderr)
    report["sections"]["crypto"] = fetch_crypto()

    print("正在获取美联储数据...", file=sys.stderr)
    report["sections"]["fed"] = fetch_fed()

    if FINNHUB_KEY:
        print("正在获取市场数据...", file=sys.stderr)
        report["sections"]["markets"] = fetch_markets()
    else:
        report["sections"]["markets"] = {
            "note": "Finnhub API Key 未配置，跳过市场数据。设置 FINNHUB_API_KEY 环境变量即可启用。"
        }

    return report


# ================================================================
# CLI
# ================================================================

def main():
    parser = argparse.ArgumentParser(
        description="Situation Report - 全球态势感知工具"
    )
    sub = parser.add_subparsers(dest="command", help="子命令")

    # full
    sub.add_parser("full", help="完整态势报告")

    # news
    p_news = sub.add_parser("news", help="新闻")
    p_news.add_argument("--topic", default="world",
                        help="主题: world/china/us/russia/ukraine/ai/tech/finance/military/trade 或自定义关键词")
    p_news.add_argument("--limit", type=int, default=15, help="数量")

    # crypto
    p_crypto = sub.add_parser("crypto", help="加密货币")
    p_crypto.add_argument("--coins", default=DEFAULT_COINS, help="币种列表,逗号分隔")

    # fed
    sub.add_parser("fed", help="美联储经济数据")

    # markets
    sub.add_parser("markets", help="股票市场")

    # watch
    p_watch = sub.add_parser("watch", help="关键词监控")
    p_watch.add_argument("--keywords", required=True, help="关键词,逗号分隔")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    if args.command == "full":
        result = full_report()
    elif args.command == "news":
        result = fetch_news(args.topic, args.limit)
    elif args.command == "crypto":
        result = fetch_crypto(args.coins)
    elif args.command == "fed":
        result = fetch_fed()
    elif args.command == "markets":
        result = fetch_markets()
    elif args.command == "watch":
        result = fetch_watch(args.keywords)
    else:
        parser.print_help()
        sys.exit(1)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
