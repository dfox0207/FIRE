import copy
import random 
from typing import Dict, List, Tuple

import pandas as pd 

from projection_engine import projection_engine

def build_annual_summary(proj: pd.DataFrame) -> pd.DataFrame:
    annual = proj.copy()
    annual["Year"] = pd.to_datetime(annual["Date"]).dt.year

    agg_map = {
        "Income": "sum",
        "Income_Real": "sum",
        "Net_Income_Real": "sum",
        "Fed Tax": "sum",
        "VA Tax": "sum",
        "Total Tax":"sum",
        "Net_Worth": "last",
        "Net_Worth_Real": "last",
    }

    if "Medicare Tax" in annual.columns: agg_map["Medicare Tax"] = "sum"

    annual_summary = annual.groupby("Year", as_index=False).agg(agg_map)
    return annual_summary

def score_annual_projection(
    annual_summary: pd.DataFrame, 
    target_annual_net_income_real: float=120000.0
) -> float:

    min_annual_net = float(annual_summary["Net_Income_Real"].min())

    if min_annual_net < target_annual_net_income_real:
        shortfall = target_annual_net_income_real - min_annual_net
        return -1e12 - 1e6 * shortfall
    return float(annual_summary["Net_Income_Real"].sum())

def make_year_blocks(years: List[int], block_size: int =5) -> List[Tuple[int, int]]:
    years = sorted(years)
    blocks= []
    i = 0
    while i < len(years):
        start_year = years[i]
        end_year = years[min(i + block_size -1, len(years) - 1)]
        blocks.append((start_year, end_year))
        i += block_size
    return blocks

def build_block_policy(
    roth_targets_by_block: List[float],
    years: List[int],
    block_ranges: List[Tuple[int, int]],
    target_annual_net_income_real: float = 120000.0
) -> Dict[int, Dict[str, float]]:

    policy: Dict[int, Dict[str, float]] = {}

    for (start_year, end_year), roth_target in zip(block_ranges, roth_targets_by_block):
        for yr in years:
            if start_year <= yr <= end_year:
                policy[year] = {
                    "target_annual_net_income_real": float(target_annual_net_income_real),
                    "roth_target_ordinary_income_annual": float(roth_target),
                }
    return policy

def evaluate_policy(
    policy: Dict[int, Dict[str, float]],
    account_tax_map,
    rmd_table,
    start_bal,
    cf,
    income_streams,
    months,
    assumptions,
    balances_actuals,
    target_annual_net_income_real: float = 120000.0,
):

    assumptions_mod = copy.deepcopy(assumptions)
    assumptions_mod["withdrawal_type"] = "Optimizer"
    assumptions_mod["optimizer_policy"] = policy

    proj = projection_engine(
        account_tax_map=account_tax_map,
        rmd_table=rmd_table,
        start_bal=start_bal,
        cf=cf,
        income_streams=income_streams,
        months=months,
        assumptions=assumptions_mod,
        balances_actuals=balances_actuals,
    )

    annual_summary = build_annual_summary(proj)
    score = score_annual_projection(
        annual_summary,
        target_annual_net_income_real=target_annual_net_income_real,
    )

    return score, proj, annual_summary

def random_search_optimizer(
    account_tax_map,
    rmd_table,
    start_bal,
    cf,
    income_streams,
    months,
    assumptions,
    balances_actuals,
    target_annual_net_income_real: float=120000.0,
    block_size: int = 5,
    n_trials: int = 200,
    roth_min: float = 0.0,
    roth_max: float = 150000.0,
    seed: int =42,
):
    random.seed(seed)

    years = sorted(pd.to_datetime(months).year.unique().tolist())
    block_ranges = make_year_blocks(years, block_size=block_size)

    best_score = float("-inf")
    best_policy = None 
    best_proj = None 
    best_annual_summary = None 

    for trial in range(n_trials):
        roth_targets_by_block = [
            random.uniform(roth_min, roth_max) for _ in block_ranges
        ]

        policy = build_block_policy(
            roth_targets_by_block = roth_targets_by_block,
            years=years,
            block_ranges=block_ranges,
            target_annual_net_income_real=target_annual_net_income_real,
        )

        score, proj, annual_summary = evaluate_policy(
            policy=policy,
            account_tax_map=account_tax_map,
            rmd_table=rmd_table,
            start_bal=start_bal,
            cf=cf,
            income_streams=income_streams,
            months=months,
            assumptions=assumptions,
            balances_actuals=balances_actuals,
            target_annual_net_income_real=target_annual_net_income_real,
        )

        if score > best_score:
            best_score = score 
            best_policy = policy 
            best_proj = proj 
            best_annual_summary=annual_summary

            print(
                f"New best trial= {trial} "
                f"Score= {best_score:,.2f} "
                f"min annual net = {best_annual_summary['Net_Income_Real'].min():,.2f}"
            )
    
    return {
        "best_score": best_score,
        "best_policy": best_policy,
        "best_projection": best_proj,
        "best_annual_summary": best_annual_summary,
        "block_ranges": block_ranges,
    }

