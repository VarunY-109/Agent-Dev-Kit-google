# Investment Allocator Agent

A pure-Python ADK agent that takes a current portfolio (ticker,
shares, price) and a target risk profile, then produces a
**scored, prioritised rebalance plan** with buy/sell trades.

## Tools

| Tool | Purpose |
| --- | --- |
| `profile_targets(profile)` | Canonical weights for `conservative / balanced / aggressive / all_weather`. |
| `classify_holding(ticker)` | Map a ticker to an asset class. |
| `portfolio_value(holdings_json)` | Total value + per-class split. |
| `drift(holdings, target_profile)` | Per-class weight drift. |
| `rebalance_plan(holdings, target_profile, new_capital=0)` | Trade list. |
| `risk_score(holdings)` | 0-100 risk label. |

The agent is configured with `output_schema=RebalancePlan`.

## Built-in Asset-Class Map

| Asset class | Sample tickers |
| --- | --- |
| stocks | VTI, VOO, SPY, QQQ |
| bonds | AGG, BND, TLT |
| gold | GLD, IAU |
| cash | (none) |

Unknown tickers default to `stocks`. Extend `_ASSET_CLASS_OF_TICKER`
to fit your universe.

## Project Structure

```
32-investment-allocator/
└── investment_allocator_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Disclaimer

Educational only. Not investment advice. Always consult a licensed
adviser and consider tax/fee impact before trading.

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env
adk web
```
