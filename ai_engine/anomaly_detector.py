"""
Anomaly Detector using IsolationForest (scikit-learn)
Pure local computation — no API needed.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


class AnomalyDetector:
    """Detects anomalous data points in time-series KPI data."""

    def __init__(self, contamination: float = 0.1, random_state: int = 42):
        self.contamination = contamination
        self.random_state = random_state
        self.model = IsolationForest(
            contamination=contamination,
            random_state=random_state,
            n_estimators=100
        )

    def detect(self, df: pd.DataFrame, value_col: str,
               time_col: str = None) -> dict:
        """
        Detect anomalies in a time-series column.

        Args:
            df: DataFrame with time-series data
            value_col: Column name to analyze
            time_col: Optional time column for labeling

        Returns:
            dict with anomaly flags, scores, and summary
        """
        if df.empty or value_col not in df.columns:
            return {'anomalies': [], 'anomaly_count': 0, 'scores': []}

        X = df[[value_col]].values.copy()
        X = X.reshape(-1, 1)

        if len(X) < 3:
            return {'anomalies': [], 'anomaly_count': 0, 'scores': []}

        df_copy = df.copy()
        df_copy['anomaly_flag'] = self.model.fit_predict(X)
        df_copy['anomaly_score'] = self.model.score_samples(X)

        anomalies = df_copy[df_copy['anomaly_flag'] == -1]

        result = []
        for _, row in anomalies.iterrows():
            mean_val = df[value_col].mean()
            std_val = df[value_col].std()
            deviation = (row[value_col] - mean_val) / std_val if std_val > 0 else 0

            label_time = ""
            if time_col and time_col in df.columns:
                label_time = str(row[time_col])

            result.append({
                'time': label_time,
                'value': float(row[value_col]),
                'deviation_sigma': round(deviation, 2),
                'direction': 'high' if deviation > 0 else 'low',
                'score': round(float(row['anomaly_score']), 4),
            })

        return {
            'anomalies': result,
            'anomaly_count': len(result),
            'scores': [round(float(s), 4) for s in df_copy['anomaly_score'].tolist()] if 'anomaly_score' in df_copy.columns else [],
        }

    def detect_multiple(self, df: pd.DataFrame,
                        value_cols: list,
                        time_col: str = None) -> dict:
        """Detect anomalies across multiple metrics simultaneously."""
        results = {}
        for col in value_cols:
            results[col] = self.detect(df, col, time_col)
        return results
