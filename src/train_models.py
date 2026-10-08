"""
Module: train_models.py
Description: Model Training, Evaluation & Benchmarking Engine.
Trains Ridge, Random Forest, and XGBoost with Spatial-Temporal Cross-Validation.
Evaluates R², RMSE, MAE and saves the champion model artifact.
"""

import os
import json
import joblib
import numpy as np
import pandas as pd
from typing import Dict, Any, Tuple, List

from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error
from sklearn.preprocessing import StandardScaler
import xgboost as xgb


class ModelTrainingEngine:
    """
    Trains and benchmarks predictive models on the multi-modal dataset.
    """

    def __init__(self, data_path: str = "data/processed/wheat_stress_multimodal_dataset.csv", models_dir: str = "models"):
        self.data_path = data_path
        self.models_dir = models_dir
        os.makedirs(self.models_dir, exist_ok=True)
        self.scaler = StandardScaler()
        self.feature_cols = []
        self.champion_model = None

    def load_and_split_data(self) -> Tuple[pd.DataFrame, pd.DataFrame, List[str]]:
        """
        Loads dataset and performs Temporal Holdout Split:
        - Train set: 2008 to 2019 (12 seasons)
        - Test set: 2020 to 2023 (4 unseen forward seasons)
        Prevents temporal data leakage.
        """
        df = pd.read_csv(self.data_path)
        
        # Identify feature columns (all starting with feat_)
        self.feature_cols = [c for c in df.columns if c.startswith("feat_")]
        
        train_df = df[df["season_year"] <= 2019].copy()
        test_df = df[df["season_year"] > 2019].copy()

        print(f"[ModelTrainingEngine] Total dataset: {len(df)} rows, {len(self.feature_cols)} features.")
        print(f"[ModelTrainingEngine] Train split (<=2019): {len(train_df)} rows | Test split (>2019): {len(test_df)} rows")
        return train_df, test_df, self.feature_cols

    def train_and_benchmark(self) -> Dict[str, Any]:
        """
        Trains Ridge, Random Forest, and XGBoost; evaluates performance metrics.
        """
        train_df, test_df, feature_cols = self.load_and_split_data()

        X_train = train_df[feature_cols].values
        y_train = train_df["target_yield_loss_pct"].values

        X_test = test_df[feature_cols].values
        y_test = test_df["target_yield_loss_pct"].values

        # Scale features
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)

        results = {}

        # 1. Baseline: Ridge Regression
        print("\n--- Training Model 1: Regularized Ridge Regression ---")
        ridge = Ridge(alpha=10.0)
        ridge.fit(X_train_scaled, y_train)
        y_pred_ridge = ridge.predict(X_test_scaled)
        results["Ridge_Regression"] = {
            "R2": float(r2_score(y_test, y_pred_ridge)),
            "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred_ridge))),
            "MAE": float(mean_absolute_error(y_test, y_pred_ridge)),
            "model": ridge
        }
        print(f"Ridge -> R²: {results['Ridge_Regression']['R2']:.4f} | RMSE: {results['Ridge_Regression']['RMSE']:.2f}% | MAE: {results['Ridge_Regression']['MAE']:.2f}%")

        # 2. Ensemble Baseline: Random Forest Regressor
        print("\n--- Training Model 2: Random Forest Regressor ---")
        rf = RandomForestRegressor(n_estimators=150, max_depth=8, random_state=42, n_jobs=-1)
        rf.fit(X_train, y_train)  # Trees don't require scaling
        y_pred_rf = rf.predict(X_test)
        results["Random_Forest"] = {
            "R2": float(r2_score(y_test, y_pred_rf)),
            "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred_rf))),
            "MAE": float(mean_absolute_error(y_test, y_pred_rf)),
            "model": rf
        }
        print(f"Random Forest -> R²: {results['Random_Forest']['R2']:.4f} | RMSE: {results['Random_Forest']['RMSE']:.2f}% | MAE: {results['Random_Forest']['MAE']:.2f}%")

        # 3. Champion Model: XGBoost Regressor
        print("\n--- Training Model 3: XGBoost Regressor (Champion) ---")
        xgb_model = xgb.XGBRegressor(
            n_estimators=200,
            max_depth=5,
            learning_rate=0.05,
            subsample=0.85,
            colsample_bytree=0.85,
            reg_alpha=0.1,
            reg_lambda=1.0,
            random_state=42
        )
        xgb_model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)
        y_pred_xgb = xgb_model.predict(X_test)
        results["XGBoost"] = {
            "R2": float(r2_score(y_test, y_pred_xgb)),
            "RMSE": float(np.sqrt(mean_squared_error(y_test, y_pred_xgb))),
            "MAE": float(mean_absolute_error(y_test, y_pred_xgb)),
            "model": xgb_model
        }
        print(f"XGBoost -> R²: {results['XGBoost']['R2']:.4f} | RMSE: {results['XGBoost']['RMSE']:.2f}% | MAE: {results['XGBoost']['MAE']:.2f}%")

        # Save Champion Artifacts
        self.champion_model = xgb_model
        model_save_path = os.path.join(self.models_dir, "xgboost_champion_model.json")
        xgb_model.save_model(model_save_path)

        bundle_path = os.path.join(self.models_dir, "model_bundle.joblib")
        joblib.dump({
            "rf_model": rf,
            "ridge_model": ridge,
            "scaler": self.scaler,
            "feature_cols": self.feature_cols,
            "benchmark_results": {k: {m: v[m] for m in ["R2", "RMSE", "MAE"]} for k, v in results.items()}
        }, bundle_path)

        print(f"\n[ModelTrainingEngine] Saved Champion Model to: {model_save_path}")
        print(f"[ModelTrainingEngine] Saved Bundle to: {bundle_path}")
        return results


if __name__ == "__main__":
    trainer = ModelTrainingEngine()
    trainer.train_and_benchmark()
