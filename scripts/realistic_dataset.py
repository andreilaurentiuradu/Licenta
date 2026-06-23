"""
Turns the synthetic dataset (too easily separable, ~95% accuracy) into a more
realistic one, in two orthogonal and interpretable ways:

  1. Class imbalance — subsamples the positive class (injury) so that the base
     rate (majority class = no injury) is ~`--baseline`. Reflects that, in
     reality, most seasons do not end with a serious injury.

  2. Label noise — randomly swaps labels between classes, preserving the per-class
     counts (positive<->negative swap). Reflects real-world uncertainty: the same
     metrics may or may not lead to an injury. This caps the achievable accuracy.

The feature columns are NOT modified — they stay realistic athlete metrics. Only
the label is changed and rows are subsampled.

Reports the base rate and the 5-fold cross-validated accuracy/recall, using the
EXACT preprocessing and model of the application (fl.model), so the figure is the
one the fl-service bootstrap will also reproduce.
"""

import argparse
import sys

import numpy as np
import pandas as pd

TARGET = "Injury_Next_Season"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--inp", required=True, help="input CSV")
    ap.add_argument("--out", required=True, help="output CSV")
    ap.add_argument("--baseline", type=float, default=0.57,
                    help="desired majority-class (no-injury) share")
    ap.add_argument("--noise", type=float, default=0.26,
                    help="fraction of labels swapped (keeps per-class counts)")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--fl-path", default="services/fl-service",
                    help="path to the fl package (for app-identical evaluation)")
    a = ap.parse_args()
    rng = np.random.default_rng(a.seed)

    df = pd.read_csv(a.inp)
    y = df[TARGET].astype(int).values
    pos_idx = np.where(y == 1)[0]
    neg_idx = np.where(y == 0)[0]
    n_neg = len(neg_idx)

    # 1) Imbalance: keep all negatives, subsample positives
    target_pos = int(round(n_neg * (1 - a.baseline) / a.baseline))
    target_pos = min(target_pos, len(pos_idx))
    keep_pos = rng.choice(pos_idx, size=target_pos, replace=False)
    keep = np.sort(np.concatenate([neg_idx, keep_pos]))
    d = df.iloc[keep].reset_index(drop=True)

    # 2) Label noise, preserving per-class counts (swap k positives <-> k negatives)
    yy = d[TARGET].astype(int).values.copy()
    n = len(yy)
    k = int(round(a.noise * n / 2))
    p_ix = np.where(yy == 1)[0]
    n_ix = np.where(yy == 0)[0]
    k = min(k, len(p_ix), len(n_ix))
    flip_p = rng.choice(p_ix, size=k, replace=False)
    flip_n = rng.choice(n_ix, size=k, replace=False)
    yy[flip_p] = 0
    yy[flip_n] = 1
    d[TARGET] = yy

    # shuffle rows
    d = d.sample(frac=1.0, random_state=a.seed).reset_index(drop=True)
    d.to_csv(a.out, index=False)

    base = np.bincount(yy).max() / len(yy)
    print(f"[data] rows={n}  base_rate={base:.3f}  "
          f"positive_rate={(yy == 1).mean():.3f}  labels_swapped={2 * k} ({2 * k / n:.1%})")

    # App-identical evaluation
    try:
        sys.path.insert(0, a.fl_path)
        from fl.model import FEATURES, preprocess, build_model
        from sklearn.model_selection import cross_val_score
        dd = preprocess(d.copy())
        X = dd[FEATURES].values
        Y = dd[TARGET].astype(int).values
        acc = cross_val_score(build_model(), X, Y, cv=5, scoring="accuracy")
        rec = cross_val_score(build_model(), X, Y, cv=5, scoring="recall")
        print(f"[eval] 5-fold CV  accuracy={acc.mean():.3f}±{acc.std():.3f}  "
              f"recall={rec.mean():.3f}  (baseline={base:.3f}, "
              f"+{(acc.mean() - base) * 100:.1f} pp)")
        # exactly what the UI shows: bootstrap = single 15% split (seed 42)
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, recall_score
        Xtr, Xte, ytr, yte = train_test_split(X, Y, test_size=0.15,
                                              random_state=42, stratify=Y)
        bm = build_model(); bm.fit(Xtr, ytr)
        pred = bm.predict(Xte)
        print(f"[eval] bootstrap (15%% split, seed 42 — exact UI)  "
              f"accuracy={accuracy_score(yte, pred):.3f}  recall={recall_score(yte, pred):.3f}")
    except Exception as exc:
        print("[eval] skipped:", exc)


if __name__ == "__main__":
    main()
