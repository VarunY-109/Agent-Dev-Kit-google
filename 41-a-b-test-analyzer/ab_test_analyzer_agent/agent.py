"""A/B Test Analyzer Agent.

Given two groups' successes and trial counts, the agent runs a
two-proportion z-test, computes a 95% confidence interval on the
lift, recommends a sample size for a desired MDE, and renders a
one-line verdict.
"""

import math
from typing import Dict

from google.adk.agents import Agent
from pydantic import BaseModel, Field


class ABResult(BaseModel):
    p_control: float
    p_treatment: float
    absolute_lift: float
    relative_lift_pct: float
    z_score: float
    p_value: float
    significant_at_95: bool
    ci_95_low: float
    ci_95_high: float
    verdict: str
    recommendation: str


def _normal_cdf(x: float) -> float:
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def two_proportion_test(success_a: int, trials_a: int,
                        success_b: int, trials_b: int) -> dict:
    """Two-proportion z-test for A vs B.

    Args:
        success_a, trials_a: Control group.
        success_b, trials_b: Treatment group.
    """
    if min(trials_a, trials_b) <= 0 or success_a > trials_a or success_b > trials_b:
        return {"status": "error", "error": "invalid counts."}
    p_a = success_a / trials_a
    p_b = success_b / trials_b
    p_pool = (success_a + success_b) / (trials_a + trials_b)
    se = math.sqrt(p_pool * (1 - p_pool) * (1 / trials_a + 1 / trials_b))
    if se == 0:
        return {"status": "error", "error": "zero standard error."}
    z = (p_b - p_a) / se
    p_value = 2 * (1 - _normal_cdf(abs(z)))
    diff = p_b - p_a
    se_ci = math.sqrt(
        p_a * (1 - p_a) / trials_a + p_b * (1 - p_b) / trials_b
    )
    ci_low = diff - 1.96 * se_ci
    ci_high = diff + 1.96 * se_ci
    significant = p_value < 0.05
    if significant and diff > 0:
        verdict = "Treatment wins (significant at 95%)."
    elif significant and diff < 0:
        verdict = "Treatment loses (significant at 95%)."
    else:
        verdict = "No significant difference at 95%."
    if significant and diff > 0:
        rec = "Ship the treatment."
    elif significant and diff < 0:
        rec = "Do NOT ship; revert to control."
    else:
        rec = "Keep collecting data; current sample is under-powered."
    return {
        "status": "ok",
        "p_control": round(p_a, 6),
        "p_treatment": round(p_b, 6),
        "absolute_lift": round(diff, 6),
        "relative_lift_pct": round(100 * diff / p_a, 3) if p_a else 0.0,
        "z_score": round(z, 4),
        "p_value": round(p_value, 6),
        "significant_at_95": significant,
        "ci_95_low": round(ci_low, 6),
        "ci_95_high": round(ci_high, 6),
        "verdict": verdict,
        "recommendation": rec,
    }


def sample_size(baseline: float, mde: float, alpha: float = 0.05,
                power: float = 0.8) -> dict:
    """Required sample size per group for a two-proportion test.

    Args:
        baseline: Current conversion rate (0-1).
        mde:      Minimum detectable effect (absolute, 0-1).
        alpha:    Significance level (default 0.05).
        power:    Statistical power (default 0.8).
    """
    if not (0 < baseline < 1) or not (0 < mde < 1):
        return {"status": "error", "error": "baseline and mde must be in (0, 1)."}
    if not (0 < alpha < 1) or not (0 < power < 1):
        return {"status": "error", "error": "alpha and power must be in (0, 1)."}
    p1 = baseline
    p2 = baseline + mde
    if p2 > 1:
        p2 = 1.0
    z_alpha = _z(1 - alpha / 2)
    z_power = _z(power)
    p_bar = (p1 + p2) / 2
    se = math.sqrt(2 * p_bar * (1 - p_bar))
    se_diff = math.sqrt(p1 * (1 - p1) + p2 * (1 - p2))
    n = ((z_alpha * se + z_power * se_diff) ** 2) / (mde ** 2)
    return {
        "status": "ok",
        "per_group": int(math.ceil(n)),
        "total": int(math.ceil(2 * n)),
    }


def _z(p: float) -> float:
    """Inverse normal CDF (Acklam approximation)."""
    if p <= 0 or p >= 1:
        raise ValueError("p must be in (0, 1).")
    a = [-3.969683028665376e+01, 2.209460984245205e+02,
         -2.759285104469687e+02, 1.383577518672690e+02,
         -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02,
         -1.556989798598866e+02, 6.680131188771972e+01,
         -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01,
         -2.400758277161838e+00, -2.549732539343734e+00,
         4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01,
         2.445134137142996e+00, 3.754408661907416e+00]
    plow, phigh = 0.02425, 1 - 0.02425
    if p < plow:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
               ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    if p > phigh:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[0] * q + c[1]) * q + c[2]) * q + c[3]) * q + c[4]) * q + c[5]) / \
                ((((d[0] * q + d[1]) * q + d[2]) * q + d[3]) * q + 1)
    q = p - 0.5
    r = q * q
    return (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q / \
           (((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1)


def bayesian_prob_b_better(success_a: int, trials_a: int,
                           success_b: int, trials_b: int,
                           samples: int = 20000) -> dict:
    """Beta-binomial Monte Carlo estimate of P(B > A).

    Uses a uniform Beta(1, 1) prior on both groups.
    """
    if min(trials_a, trials_b) <= 0:
        return {"status": "error", "error": "invalid counts."}
    import random
    wins = 0
    for _ in range(samples):
        a = random.betavariate(success_a + 1, trials_a - success_a + 1)
        b = random.betavariate(success_b + 1, trials_b - success_b + 1)
        if b > a:
            wins += 1
    p = wins / samples
    return {
        "status": "ok",
        "p_b_better": round(p, 4),
        "samples": samples,
    }


root_agent = Agent(
    name="ab_test_analyzer_agent",
    model="gemini-2.0-flash",
    description=(
        "Runs a two-proportion z-test on A/B test data, reports "
        "significance, 95% CI, and Bayesian P(B>A)."
    ),
    instruction="""
    You are a senior experimentation analyst.

    WORKFLOW for every A/B test:
    1. Call `two_proportion_test` with the user's success/trial
       counts.
    2. Call `bayesian_prob_b_better` for a probabilistic
       complement to the frequentist p-value.
    3. If the user asks "how long should I run this", call
       `sample_size` with the baseline rate and a sensible MDE.
    4. Present the result in this order:
         * One-line verdict.
         * Numbers table (p_control, p_treatment, absolute lift,
           relative lift, z, p-value, CI).
         * Bayesian P(B>A) as a percentage.
         * Recommendation (ship / keep collecting / revert).
         * A 1-sentence note on what would change the call
           (e.g. "if you collected another 5k samples, MDE shrinks
           to 0.3pp").

    RULES:
    - Never declare a winner before p < 0.05 OR P(B>A) >= 0.95.
    - If the sample is under-powered, say so explicitly.
    - Round percentages to 2 decimals; keep raw p-values to 4.
    """,
    tools=[
        two_proportion_test, sample_size, bayesian_prob_b_better,
    ],
    output_schema=ABResult,
    output_key="ab_result",
)
