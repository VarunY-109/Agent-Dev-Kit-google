# A/B Test Analyzer Agent

A pure-Python ADK agent that runs a **two-proportion z-test** on
A/B test data, reports 95% CI on the lift, computes a Bayesian
`P(B > A)`, and estimates required sample size for a desired MDE.

## Tools

| Tool | Purpose |
| --- | --- |
| `two_proportion_test(success_a, trials_a, success_b, trials_b)` | Frequentist z-test + 95% CI. |
| `bayesian_prob_b_better(...)` | Monte Carlo Beta-binomial estimate. |
| `sample_size(baseline, mde, alpha, power)` | Required N per group. |

## Project Structure

```
41-a-b-test-analyzer/
└── ab_test_analyzer_agent/
    ├── __init__.py
    ├── agent.py
    └── .env.example
```

## Getting Started

```bash
source ../.venv/bin/activate
cp .env.example .env
adk web
```

## Example Prompts

- "A: 240/5000, B: 290/5000 - is B winning?"
- "I have a 5% baseline and want to detect a 0.5pp lift at 80% power. How many samples per group?"
- "What's P(B>A) for 1200/10000 vs 1350/10000?"
