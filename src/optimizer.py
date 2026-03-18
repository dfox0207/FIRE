from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Tuple

import numpy as np 
import pandas as pd 

from projection_engine import projection_engine

@dataclass
class OptimizationResult:
    best_params: List[float]
    best_score: float
    best_policy: Dict[int, Dict[str, float]]
    best_projection: pd.DataFrame

def build_block_policy(
    params: List[float],
    years: Iterable[int],
    block_ranges: List[Tuple[int, int]],
) -> Dict[int, Dict[str, float]]:

    n_blocks = len(block_ranges)
    if len(params) != 2 * n_blocks:
        raise ValueError(
            f"Expected {2 * n_blocks} params for {n_blocks} blocks, got {len(params)}"
        )
    
    income_targets = params[:n_blocks]
    roth_targets = params[n_blocks:]

    policy: Dict[int, Dict[str, float]] = {}
    years_set = set(int(y) for y in years)

    for i, (start_year, end_year) in enumerate(block_ranges):
        for year in range(start_year, end_year + 1):
            if year not in years_set:
                continue
            policy[year] = {
                "target_net_income_real": float(income_targets[i]),
                "roth_target_ordinary_income": float(roth_targets[i]),
            }
    return policy

def score_projection(
    proj: pd.DataFrame,
    min_monthly_income_real: float = 10000.0,
    objective: str = "terminal_wealth",
) -> float:

    if proj.empty:
        return -1e18
    
    min_income = float(proj["Net_Income_Real"].min())

    if min_income < min_monthly_income_real:
        shortfall = min_monthly_income_real - min_income
        return -1e12 - 1e6 * shortfall

    if objective == "terminal_wealth":
        return float(proj["Net_Worth_Real"].iloc[-1])
    
    if objective == "lifetime_net_income":
        return float(proj["Net_Income_Real"].sum())
    
    raise ValueError(f"Unsupported objective: {objective}")

def evaluate_policy(
    policy: Dict[int, Dict[str, float]],
    *,
    start_bal,
    cf,
    months,
    assumptions: Dict[str, Any],
    account_tax_map,
    rmd_table,
    balances_actuals=None,
    min_monthly_income_real: float = 10000.0,
    objective: str = "terminal_wealth",
) -> Tuple[float, pd.DataFrame]:

    assumptions_mod = deepcopy(assumptions)
    assumptions_mod["withdrawal_type"] = "optimizer"

    proj = projection_engine(
        start_bal=start_bal,
        cf=cf,
        months=months,
        assumptions= assumptions_mod,
        balances_actuals=balances_actuals,
        account_tax_map=account_tax_map,
        rmd_table=rmd_table,
    )

    if not isinstance(proj, pd.DataFrame):
        proj = pd.DataFrame(proj)

    score = score_projection(
        proj,
        min_monthly_income_real=min_monthly_income_real,
        objective=objective,
    )

    return score, proj

def random_search_optimizer(
    *,
    start_bal,
    cf,
    months,
    assumptions: Dict[str, Any],
    account_tax_map,
    rmd_table,
    balances_actuals=None,
    block_ranges: List[Tuple[int, int]] | None=None,
    n_iter: int = 300,
    min_monthly_income_real: float = 10000.0,
    objective: str = "terminal_wealth",
    income_bounds: Tuple[float, float]=(0.0, 150000.0),
    seed: int = 42,
    verbose: bool = True,
) -> OptimizationResult:

    if block_ranges is None:
        block_ranges = [
            (int(months[0].year), 2034),
            (2035, 2044),
            (2045, int(months[-1].year)),
        ]
    
    years = sorted({int(m.year) for m in months})
    rng = np.random.default_rng(seed)

    n_blocks=len(block_ranges)
    best_score = -1e18
    best_params: List[float] | None=None
    best_policy: Dict[int, Dict[str, float]] | None=None

    for i in range(n_iter):
        income_params = rng.uniform(income_bounds[0], income_bounds[1], size=n_blocks)
        roth_params = rng.uniform(roth_bounds[0], roth_bounds[1], size=n_blocks)

        params = list(income_params) + list(roth_params)
        policy = build_block_policy(params, years, block_ranges)

        score, proj = evaluate_policy(
            policy,
            start_bal=start_bal,
            cf=cf,
            months=months,
            assumptions=assumptions,
            balances_actuals=balances_actuals,
            account_tax_map=account_tax_map,
            rmd_table=rmd_table,
            min_monthly_income_real=min_monthly_income_real,
            objective=objective,
        )

        if score > best_score:
            best_score = score
            best_params = params
            best_policy = policy
            best_projection = proj

            if verbose:
                print(
                    f"New best at iter {i + 1}/{n_iter}: "
                    f"Score={best_score:,.2f}, params={best_params}"
                )
        
    if best_params is None or best_policy is None or best_projection is None:
        raise RunTimeError("Optimizer failed to produce any candidate result.")

    return OptimizationResult(
        best_params=best_params,
        best_score=best_score,
        best_policy=best_policy,
        best_projection=best_projection,
    )    

def pretty_print_policy(policy: Dict[int, Dict[str, float]]) -> None:
    years = sorted(policy.keys())
    for y in years:
        p = policy[y]
        print(
            f"{y}: "
            f"target_net_income_real={p['target_net_income_real']:,.0f}"
        )

    