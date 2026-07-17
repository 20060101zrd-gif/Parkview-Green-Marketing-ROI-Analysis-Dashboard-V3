"""
Year-over-Year (YoY) and Month-over-Month (MoM) comparison engine.
"""

import pandas as pd
import numpy as np


class ComparisonEngine:
    """Calculate YoY and MoM deltas for any time-series metric."""

    @staticmethod
    def calc_mom(current_value: float, previous_value: float) -> float:
        """Month-over-Month change percentage."""
        if previous_value == 0:
            return 0.0
        return round((current_value - previous_value) / previous_value * 100, 2)

    @staticmethod
    def calc_yoy(current_value: float, prev_year_value: float) -> float:
        """Year-over-Year change percentage."""
        if prev_year_value == 0:
            return 0.0
        return round((current_value - prev_year_value) / prev_year_value * 100, 2)

    @staticmethod
    def calc_period_comparison(
        df: pd.DataFrame,
        date_col: str,
        value_col: str,
        current_start,
        current_end,
        prev_start,
        prev_end
    ) -> dict:
        """Compare two periods and return the delta."""
        current = df[
            (df[date_col] >= pd.Timestamp(current_start)) &
            (df[date_col] <= pd.Timestamp(current_end))
        ][value_col].sum()

        previous = df[
            (df[date_col] >= pd.Timestamp(prev_start)) &
            (df[date_col] <= pd.Timestamp(prev_end))
        ][value_col].sum()

        pct_change = ComparisonEngine.calc_yoy(current, previous)

        return {
            'current': float(current),
            'previous': float(previous),
            'change_pct': pct_change,
            'direction': 'up' if pct_change >= 0 else 'down',
        }

    @staticmethod
    def safe_change_pct(current, previous) -> float:
        """Safe percentage change — handles zero division."""
        if previous == 0:
            return 0.0
        return round((current - previous) / previous * 100, 1)
