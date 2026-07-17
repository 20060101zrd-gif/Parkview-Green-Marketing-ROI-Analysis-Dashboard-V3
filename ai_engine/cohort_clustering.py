"""
Cohort Clusterer using KMeans (scikit-learn)
Automatically discovers natural customer segments from data,
replacing hardcoded if-else threshold rules.
"""

import numpy as np
import pandas as pd
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler


class CohortClusterer:
    """KMeans-based automatic cohort segmentation."""

    def __init__(self, n_clusters: int = 4, random_state: int = 42):
        self.n_clusters = n_clusters
        self.random_state = random_state
        self.scaler = StandardScaler()
        self.model = KMeans(
            n_clusters=n_clusters,
            random_state=random_state,
            n_init=10
        )

    def cluster(self, df: pd.DataFrame,
                feature_cols: list) -> pd.DataFrame:
        """
        Cluster records based on selected features.

        Args:
            df: DataFrame with cohort data
            feature_cols: Columns used for clustering (e.g. avg_coupons, atv, redeem_rate)

        Returns:
            DataFrame with added 'cluster' and 'cluster_label' columns
        """
        if df.empty or len(feature_cols) < 2:
            df_out = df.copy()
            df_out['cluster'] = 0
            df_out['cluster_label'] = 'Default'
            return df_out

        available = [c for c in feature_cols if c in df.columns]
        if len(available) < 2:
            df_out = df.copy()
            df_out['cluster'] = 0
            df_out['cluster_label'] = 'Default'
            return df_out

        X = df[available].fillna(0).values
        X_scaled = self.scaler.fit_transform(X)

        df_out = df.copy()
        df_out['cluster'] = self.model.fit_predict(X_scaled)

        # Auto-label clusters based on centroid characteristics
        centroids = self.model.cluster_centers_
        labels = self._label_clusters(centroids, available)

        df_out['cluster_label'] = df_out['cluster'].map(labels)
        return df_out

    def _label_clusters(self, centroids: np.ndarray,
                        feature_names: list) -> dict:
        """Generate human-readable cluster labels from centroids."""
        labels = {}
        for i, centroid in enumerate(centroids):
            # Determine if this is high-value or low-value
            feat_dict = dict(zip(feature_names, centroid))

            atv_idx = None
            redeem_idx = None
            for j, name in enumerate(feature_names):
                if 'atv' in name.lower():
                    atv_idx = j
                if 'redeem' in name.lower():
                    redeem_idx = j

            atv_val = centroid[atv_idx] if atv_idx is not None else 0
            redeem_val = centroid[redeem_idx] if redeem_idx is not None else 0

            if atv_val > 0.5 and redeem_val > 0.5:
                label = f'Cluster {i+1}: High-ROI Conversion'
            elif atv_val > 0.5:
                label = f'Cluster {i+1}: High-Value / Low-Sensitivity'
            elif redeem_val > 0.5:
                label = f'Cluster {i+1}: High-Sensitivity / Low-Value'
            else:
                label = f'Cluster {i+1}: Baseline'

            labels[i] = label
        return labels

    def get_cluster_profiles(self, df: pd.DataFrame,
                             feature_cols: list) -> dict:
        """Return statistical profiles for each cluster."""
        if 'cluster' not in df.columns:
            return {}

        profiles = {}
        for cluster_id in sorted(df['cluster'].unique()):
            subset = df[df['cluster'] == cluster_id]
            profile = {'size': len(subset)}

            for col in feature_cols:
                if col in subset.columns:
                    profile[f'{col}_mean'] = round(float(subset[col].mean()), 2)
                    profile[f'{col}_median'] = round(float(subset[col].median()), 2)

            if 'cluster_label' in subset.columns:
                profile['label'] = subset['cluster_label'].iloc[0]

            profiles[int(cluster_id)] = profile

        return profiles
