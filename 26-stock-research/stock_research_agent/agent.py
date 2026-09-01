"""Stock Research Agent.

A multi-source research agent that combines a price snapshot, recent
news headlines, and a quick fundamental lookup to produce a balanced
"buy / hold / sell" view for a stock ticker.
"""

import json
import re
import statistics
import urllib.error
import urllib.parse
import urllib.request
from typing import Dict, List

try:
    import yfinance as yf  # type: ignore
    _YF_OK = True
except Exception:
    yf = None  # type: ignore
    _YF_OK = False

from google.adk.agents import Agent

_TIMEOUT = 15
_USER_AGENT = "ADK-StockResearchAgent/1.0"


def _http_get(url: str, accept: str = "application/json") -> Dict:
    req = urllib.request.Request(url, headers={
        "User-Agent": _USER_AGENT,
        "Accept": accept,
    })
    with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def get_quote(ticker: str) -> dict:
    """Return a current price snapshot and basic ratios for ``ticker``."""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {"status": "error", "error": "ticker is required."}
    if not _YF_OK:
        return {
            "status": "error",
            "error": "yfinance not installed. Run `pip install yfinance`.",
        }
    try:
        t = yf.Ticker(ticker)
        info = t.info or {}
        hist = t.history(period="6mo", auto_adjust=True)
    except Exception as exc:
        return {"status": "error", "error": f"yfinance failed: {exc}"}

    if not info or hist.empty:
        return {"status": "error", "error": f"No data for {ticker!r}."}

    closes = hist["Close"].tolist()
    high_52w = max(closes[-252:]) if len(closes) >= 1 else None
    low_52w = min(closes[-252:]) if len(closes) >= 1 else None
    avg_30d = statistics.fmean(closes[-30:]) if len(closes) >= 30 else None
    ret_6m = (closes[-1] / closes[0] - 1) * 100 if len(closes) >= 2 else None

    return {
        "status": "ok",
        "ticker": ticker,
        "price": info.get("currentPrice") or info.get("regularMarketPrice"),
        "market_cap": info.get("marketCap"),
        "pe_trailing": info.get("trailingPE"),
        "pe_forward": info.get("forwardPE"),
        "dividend_yield": info.get("dividendYield"),
        "beta": info.get("beta"),
        "sector": info.get("sector"),
        "industry": info.get("industry"),
        "high_52w": high_52w,
        "low_52w": low_52w,
        "avg_30d": avg_30d,
        "return_6m_pct": ret_6m,
    }


def get_news(ticker: str, limit: int = 8) -> dict:
    """Fetch recent news headlines for ``ticker`` (Yahoo Finance RSS)."""
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {"status": "error", "error": "ticker is required."}
    url = (
        f"https://feeds.finance.yahoo.com/rss/2.0/headline?s={ticker}"
        "&region=US&lang=en-US"
    )
    try:
        raw = urllib.request.urlopen(
            urllib.request.Request(url, headers={"User-Agent": _USER_AGENT}),
            timeout=_TIMEOUT,
        ).read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError) as exc:
        return {"status": "error", "error": f"news fetch failed: {exc}"}

    items: List[Dict] = []
    for block in re.findall(r"<item>(.*?)</item>", raw, re.DOTALL):
        title_m = re.search(r"<title>(.*?)</title>", block, re.DOTALL)
        link_m = re.search(r"<link>(.*?)</link>", block, re.DOTALL)
        date_m = re.search(r"<pubDate>(.*?)</pubDate>", block, re.DOTALL)
        if title_m:
            items.append({
                "title": re.sub(r"\s+", " ", title_m.group(1)).strip(),
                "link": (link_m.group(1).strip() if link_m else ""),
                "published": (date_m.group(1).strip() if date_m else ""),
            })
        if len(items) >= limit:
            break
    return {"status": "ok", "ticker": ticker, "headlines": items}


_POS_WORDS = {"beats", "surge", "rally", "growth", "upgrade", "raises",
               "record", "strong", "expansion", "wins", "approval"}
_NEG_WORDS = {"miss", "falls", "drop", "lawsuit", "downgrade", "cuts",
               "weak", "recall", "investigation", "probe", "loss", "delay"}


def sentiment_score(headlines_json: str) -> dict:
    """Score the sentiment of a JSON list of news headlines.

    A simple lexicon-based scorer. Returns the proportion of
    positive vs. negative headlines and an aggregate label.
    """
    try:
        headlines = json.loads(headlines_json)
    except ValueError as exc:
        return {"status": "error", "error": f"invalid JSON: {exc}"}
    if not isinstance(headlines, list):
        return {"status": "error", "error": "expected a JSON list."}

    pos = neg = 0
    breakdown = []
    for item in headlines:
        text = (item.get("title") if isinstance(item, dict) else str(item)).lower()
        p = sum(1 for w in _POS_WORDS if w in text)
        n = sum(1 for w in _NEG_WORDS if w in text)
        breakdown.append({"title": text, "pos": p, "neg": n})
        pos += p
        neg += n
    total = pos + neg
    if total == 0:
        label = "neutral"
    elif pos > neg * 1.25:
        label = "positive"
    elif neg > pos * 1.25:
        label = "negative"
    else:
        label = "mixed"
    return {
        "status": "ok",
        "positive_hits": pos,
        "negative_hits": neg,
        "label": label,
        "score": round((pos - neg) / max(total, 1), 3),
    }


def peer_comparison(ticker: str, peers: str = "") -> dict:
    """Return a quick peer-set comparison for a ticker.

    If ``peers`` is empty, falls back to a few well-known
    sector-anchor tickers.
    """
    if not _YF_OK:
        return {
            "status": "error",
            "error": "yfinance not installed. Run `pip install yfinance`.",
        }
    ticker = (ticker or "").strip().upper()
    if not ticker:
        return {"status": "error", "error": "ticker is required."}
    peer_list = [p.strip().upper() for p in peers.split(",") if p.strip()]
    if not peer_list:
        peer_list = ["SPY", "QQQ", "DIA"]
    tickers = [ticker] + [p for p in peer_list if p != ticker]

    rows = []
    for sym in tickers:
        try:
            t = yf.Ticker(sym)
            info = t.info or {}
            rows.append({
                "ticker": sym,
                "price": info.get("currentPrice") or info.get("regularMarketPrice"),
                "pe": info.get("trailingPE"),
                "market_cap": info.get("marketCap"),
                "ytd_return_pct": info.get("52WeekChange"),
            })
        except Exception:
            rows.append({"ticker": sym, "error": "lookup failed"})
    return {"status": "ok", "rows": rows}


root_agent = Agent(
    name="stock_research_agent",
    model="gemini-2.0-flash",
    description=(
        "Builds a balanced buy/hold/sell view for a stock ticker "
        "by combining a price snapshot, recent news, and peer data."
    ),
    instruction="""
    You are a disciplined equity-research assistant.

    WORKFLOW for every ticker:
    1. Call `get_quote` for price, valuation ratios, and 6m
       momentum.
    2. Call `get_news` for the latest headlines. Pipe the result
       through `sentiment_score` to quantify tone.
    3. Call `peer_comparison` to place the stock against the broad
       market or named peers.
    4. Synthesise the data into a structured report with these
       sections:
         * Snapshot (price, market cap, P/E, sector, beta, 52w range)
         * Momentum (6m return, 30d avg, distance from 52w highs)
         * Sentiment (label + key supporting headlines)
         * Peer context (how it compares on P/E and YTD)
         * Verdict (one of: Buy / Hold / Sell, plus a 2-3 sentence
           rationale grounded ONLY in the numbers above)

    RULES:
    - Never give personalised financial advice; you may surface
       analysis but the final decision is the user's.
    - If a tool errors out, say so explicitly and continue with the
       remaining sources.
    - Round percentages to 2 decimals; large numbers to 2 sig figs.
    """,
    tools=[get_quote, get_news, sentiment_score, peer_comparison],
)
