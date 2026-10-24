
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

import yfinance as yf

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "latest.json"
JST = ZoneInfo("Asia/Tokyo")

WATCHLIST = {
    "^N225": ("日経平均", "JPY"),
    "^GSPC": ("S&P 500", "USD"),
    "^IXIC": ("NASDAQ総合", "USD"),
    "JPY=X": ("米ドル/円", "JPY"),
    "9984.T": ("ソフトバンクグループ", "JPY"),
    "9434.T": ("ソフトバンク", "JPY"),
    "2914.T": ("JT", "JPY"),
    "8136.T": ("サンリオ", "JPY"),
    "9023.T": ("東京メトロ", "JPY"),
    "2558.T": ("S&P500 ETF参考", "JPY"),
    "1545.T": ("NASDAQ100 ETF参考", "JPY"),
}

def get_quotes():
    quotes = []
    errors = []

    for ticker, (name, currency) in WATCHLIST.items():
        try:
            hist = yf.Ticker(ticker).history(
                period="7d", interval="1d", auto_adjust=False
            )
            hist = hist.dropna(subset=["Close"])

            if hist.empty:
                raise ValueError("終値がありません")

            last = hist.iloc[-1]
            prev = hist.iloc[-2] if len(hist) >= 2 else None
            close = float(last["Close"])
            prev_close = float(prev["Close"]) if prev is not None else None

            change = (
                (close / prev_close - 1) * 100
                if prev_close and prev_close != 0
                else None
            )

            quotes.append({
                "ticker": ticker,
                "name": name,
                "currency": currency,
                "close": round(close, 4),
                "previous_close": (
                    round(prev_close, 4) if prev_close is not None else None
                ),
                "change_pct": round(change, 3) if change is not None else None,
                "price_date": str(hist.index[-1].date()),
                "source": "Yahoo Finance via yfinance",
            })
            time.sleep(0.3)

        except Exception as exc:
            errors.append(f"{ticker}: {type(exc).__name__}: {exc}")
            quotes.append({
                "ticker": ticker,
                "name": name,
                "currency": currency,
                "close": None,
                "previous_close": None,
                "change_pct": None,
                "price_date": None,
                "source": "Yahoo Finance via yfinance",
            })

    return quotes, errors

def get_news():
    queries = [
        "日経平均 日本株 決算",
        "米国株 FRB 金利 インフレ",
        "半導体 AI データセンター 株",
    ]
    items = []
    seen = set()

    for query in queries:
        url = (
            "https://news.google.com/rss/search?q="
            + urllib.parse.quote(query)
            + "&hl=ja&gl=JP&ceid=JP:ja"
        )
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0"}
            )
            with urllib.request.urlopen(req, timeout=15) as response:
                root = ET.fromstring(response.read())

            for item in root.findall("./channel/item"):
                title = item.findtext("title", default="").strip()
                link = item.findtext("link", default="").strip()
                published = item.findtext("pubDate", default="").strip()

                if not title or not link or link in seen:
                    continue

                seen.add(link)
                items.append({
                    "title": title,
                    "link": link,
                    "published": published,
                    "source": "Google News RSS（記事の配信元はリンク先で確認）",
                })

        except Exception:
            continue

    return items[:15]

def main():
    quotes, errors = get_quotes()
    news = get_news()
    now = datetime.now(JST)

    report = {
        "generated_at": now.strftime("%Y-%m-%d %H:%M:%S"),
        "timezone": "Asia/Tokyo",
        "market_as_of": "各銘柄のprice_dateを参照",
        "market_source": "Yahoo Finance via yfinance（非公式・遅延の可能性あり）",
        "news_source": "Google News RSS",
        "quotes": quotes,
        "news": news,
        "warnings": errors,
        "notice": (
            "参考情報のみ。価格はリアルタイムとは限らず、"
            "投資判断や売買を自動実行しない。"
        ),
    }

    OUT.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(f"Generated {OUT}")
    print(f"Quotes: {len(quotes)}, news: {len(news)}, errors: {len(errors)}")

if __name__ == "__main__":
    main()
