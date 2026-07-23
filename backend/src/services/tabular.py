"""表形式データのプロファイル・相関・軽量ベースライン学習（DS / 受託向け）。"""
from __future__ import annotations

import csv
import io
import math
from typing import Any

import numpy as np


def _parse_csv(text: str) -> tuple[list[str], list[list[str]]]:
    reader = csv.reader(io.StringIO(text.strip()))
    rows = [r for r in reader if any(cell.strip() for cell in r)]
    if not rows:
        raise ValueError("empty CSV")
    header = [h.strip() or f"col_{i}" for i, h in enumerate(rows[0])]
    data = rows[1:]
    return header, data


def _to_float_matrix(header: list[str], data: list[list[str]], target: str | None):
    cols = list(range(len(header)))
    target_idx = header.index(target) if target and target in header else None
    feature_idx = [i for i in cols if i != target_idx]

    X_rows: list[list[float]] = []
    y_vals: list[float] = []
    kept = 0
    for row in data:
        if len(row) < len(header):
            row = row + [""] * (len(header) - len(row))
        try:
            feats = [float(row[i]) for i in feature_idx]
            if target_idx is not None:
                y_vals.append(float(row[target_idx]))
            X_rows.append(feats)
            kept += 1
        except ValueError:
            continue
    if not X_rows:
        raise ValueError("no numeric rows available")
    X = np.asarray(X_rows, dtype=float)
    y = np.asarray(y_vals, dtype=float) if target_idx is not None else None
    feature_names = [header[i] for i in feature_idx]
    return X, y, feature_names, kept


def profile_tabular(csv_text: str) -> dict[str, Any]:
    """CSV の列型・統計量・カテゴリ上位をプロファイルする。"""
    header, data = _parse_csv(csv_text)
    n = len(data)
    columns = []
    for i, name in enumerate(header):
        vals = []
        cats: dict[str, int] = {}
        for row in data:
            if i >= len(row):
                continue
            cell = row[i].strip()
            if not cell:
                continue
            try:
                vals.append(float(cell))
            except ValueError:
                cats[cell] = cats.get(cell, 0) + 1
        col: dict[str, Any] = {
            "name": name,
            "non_null": len(vals) + sum(cats.values()),
            "numeric": len(vals) > 0 and len(vals) >= sum(cats.values()),
        }
        if vals:
            arr = np.asarray(vals, dtype=float)
            col.update(
                {
                    "mean": round(float(arr.mean()), 4),
                    "std": round(float(arr.std()), 4),
                    "min": round(float(arr.min()), 4),
                    "max": round(float(arr.max()), 4),
                }
            )
        if cats:
            top = sorted(cats.items(), key=lambda x: -x[1])[:5]
            col["top_categories"] = [{"value": k, "count": v} for k, v in top]
        columns.append(col)
    return {
        "modality": "tabular",
        "n_rows": n,
        "n_columns": len(header),
        "columns": columns,
    }


def correlate_numeric(csv_text: str, max_cols: int = 8) -> dict[str, Any]:
    """数値列のピアソン相関行列を計算する。"""
    header, data = _parse_csv(csv_text)
    X, _, feature_names, kept = _to_float_matrix(header, data, target=None)
    if X.shape[1] == 0:
        raise ValueError("no numeric columns")
    X = X[:, :max_cols]
    names = feature_names[:max_cols]
    # ピアソン相関
    Xc = X - X.mean(axis=0)
    std = X.std(axis=0)
    std[std == 0] = 1.0
    Zn = Xc / std
    corr = (Zn.T @ Zn) / max(len(X) - 1, 1)
    matrix = [[round(float(corr[i, j]), 3) for j in range(len(names))] for i in range(len(names))]
    return {
        "modality": "tabular",
        "n_rows_used": kept,
        "features": names,
        "correlation": matrix,
    }


def train_tabular_baseline(
    csv_text: str,
    *,
    target: str,
    task: str = "auto",
) -> dict[str, Any]:
    """
    軽量な本番化ベースライン学習。
    回帰: 閉形式リッジ / 分類: 0/1 ラベルへの線形閾値モデル。
    """
    header, data = _parse_csv(csv_text)
    if target not in header:
        raise ValueError(f"target column not found: {target}")
    X, y, feature_names, kept = _to_float_matrix(header, data, target=target)
    if y is None or kept < 4:
        raise ValueError("need at least 4 numeric labeled rows")

    # 80/20 シャッフル分割
    rng = np.random.default_rng(42)
    idx = rng.permutation(len(X))
    cut = max(1, int(len(X) * 0.8))
    tr, te = idx[:cut], idx[cut:]
    if len(te) == 0:
        te = tr[-1:]
        tr = tr[:-1]
    Xtr, Xte, ytr, yte = X[tr], X[te], y[tr], y[te]

    unique = set(np.unique(y).tolist())
    is_cls = task == "classification" or (task == "auto" and unique <= {0.0, 1.0})
    # バイアス項
    Xtr_b = np.c_[np.ones(len(Xtr)), Xtr]
    Xte_b = np.c_[np.ones(len(Xte)), Xte]
    lam = 1e-2
    A = Xtr_b.T @ Xtr_b + lam * np.eye(Xtr_b.shape[1])
    w = np.linalg.solve(A, Xtr_b.T @ ytr)
    pred = Xte_b @ w

    if is_cls:
        yhat = (pred >= 0.5).astype(float)
        acc = float((yhat == yte).mean())
        metrics = {"task": "classification", "accuracy": round(acc, 4), "threshold": 0.5}
    else:
        mse = float(np.mean((pred - yte) ** 2))
        mae = float(np.mean(np.abs(pred - yte)))
        ss_res = float(np.sum((yte - pred) ** 2))
        ss_tot = float(np.sum((yte - yte.mean()) ** 2)) or 1.0
        r2 = 1.0 - ss_res / ss_tot
        metrics = {
            "task": "regression",
            "mse": round(mse, 4),
            "mae": round(mae, 4),
            "r2": round(r2, 4),
        }

    coefs = {
        "intercept": round(float(w[0]), 6),
        "coefficients": {
            feature_names[i]: round(float(w[i + 1]), 6) for i in range(len(feature_names))
        },
    }
    return {
        "modality": "tabular",
        "target": target,
        "n_rows_used": kept,
        "n_train": int(len(tr)),
        "n_test": int(len(te)),
        "features": feature_names,
        "metrics": metrics,
        "model": {"type": "ridge_linear", **coefs},
        "ready_for_registry": True,
    }


def synthesize_demo_csv(n: int = 80) -> str:
    """Deterministic demo table for NLP/画像と並べたテーブル分析デモ。"""
    rng = np.random.default_rng(7)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["age", "tenure_months", "tickets", "nps", "churn"])
    for _ in range(n):
        age = rng.integers(22, 65)
        tenure = rng.integers(1, 60)
        tickets = rng.integers(0, 12)
        nps = rng.integers(1, 11)
        # 単純な潜在ルール
        logit = -2.0 + 0.03 * tickets + 0.04 * (10 - nps) - 0.02 * tenure
        churn = 1 if (1 / (1 + math.exp(-logit))) > 0.5 else 0
        # ノイズ付与
        if rng.random() < 0.08:
            churn = 1 - churn
        w.writerow([age, tenure, tickets, nps, churn])
    return buf.getvalue()
