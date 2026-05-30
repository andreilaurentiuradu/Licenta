"""
End-to-end Federated Learning simulation.

Splits the Kaggle dataset into N_CLUBS partitions (each = one sports club),
runs FL_ROUNDS of FedAvg and compares against centralized training.

Usage:
    cd services/fl-service
    python -m fl.simulate                           # default 4 clubs, 10 rounds
    python -m fl.simulate --clubs 6 --rounds 20    # custom
    python -m fl.simulate --data path/to/football_data.csv

Dataset: place football_data.csv in services/fl-service/data/
"""

import argparse
import numpy as np
import pandas as pd
from pathlib import Path
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report
from sklearn.model_selection import train_test_split

from .model import FEATURES, TARGET, preprocess
from .server import FLServer
from .client import FLClient

DEFAULT_DATA   = Path(__file__).parent.parent / 'data' / 'football_data.csv'
DEFAULT_CLUBS  = 4
DEFAULT_ROUNDS = 10


# ── Helpers ────────────────────────────────────────────────────────────────

def load(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    return preprocess(df)


def centralized_baseline(df: pd.DataFrame) -> tuple:
    """Train a single model on all data — upper-bound reference."""
    X = df[FEATURES].values
    y = df[TARGET].values
    X_tr, X_te, y_tr, y_te = train_test_split(X, y, test_size=0.15, random_state=42)
    model = LogisticRegression(max_iter=1000, random_state=42)
    model.fit(X_tr, y_tr)
    acc = accuracy_score(y_te, model.predict(X_te))
    return acc, model


# ── Simulation ─────────────────────────────────────────────────────────────

def run(data_path: Path, n_clubs: int, fl_rounds: int):
    print("=" * 55)
    print(" LawrAnalyzer — Federated Learning Simulation")
    print("=" * 55)

    df = load(data_path)
    print(f"\nDataset loaded: {len(df)} players · {len(df.columns)} features")
    print(f"Clubs: {n_clubs}  ·  FL rounds: {fl_rounds}\n")

    # ── Centralized baseline ──────────────────────────────────────────────
    baseline_acc, _ = centralized_baseline(df)
    print(f"Centralized baseline accuracy : {baseline_acc:.5f}")
    print("-" * 55)

    # ── Shared held-out test set (not given to any club) ──────────────────
    df_train, df_test = train_test_split(df, test_size=0.15, random_state=99)
    X_test = df_test[FEATURES].values
    y_test = df_test[TARGET].values

    # ── Partition training data across clubs ──────────────────────────────
    club_dfs = np.array_split(df_train.sample(frac=1, random_state=42), n_clubs)
    clients  = [FLClient(f"club_{i+1}", d) for i, d in enumerate(club_dfs)]

    for c in clients:
        print(f"  {c.club_id}: {len(c.data)} players  "
              f"(injury rate: {c.data[TARGET].mean():.0%})")

    print(f"\n{'Round':<8} {'Global Acc':>12} {'vs Baseline':>13}")
    print("-" * 35)

    # ── FL rounds ─────────────────────────────────────────────────────────
    server = FLServer(n_features=len(FEATURES))

    for round_n in range(1, fl_rounds + 1):
        g_coef, g_intercept = server.get_global_params()

        updates = [client.train(g_coef, g_intercept) for client in clients]
        server.aggregate(updates)

        acc   = server.evaluate(X_test, y_test)
        delta = acc - baseline_acc
        sign  = '+' if delta >= 0 else ''
        print(f"{round_n:<8} {acc:>12.5f} {sign+f'{delta:.5f}':>13}")

    # ── Final report ──────────────────────────────────────────────────────
    final_acc = server.history[-1][1]
    print("\n" + "=" * 55)
    print(f"Centralized accuracy  : {baseline_acc:.5f}")
    print(f"FL final accuracy     : {final_acc:.5f}  (round {fl_rounds})")
    print(f"Gap                   : {final_acc - baseline_acc:+.5f}")
    print("\nKey privacy guarantee : raw player data never left any club.")
    print("Only model weights (coef + intercept) were shared with the server.")
    print("=" * 55)

    return server


# ── CLI ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='FL simulation for injury prediction')
    parser.add_argument('--data',   default=str(DEFAULT_DATA),  help='Path to data.csv')
    parser.add_argument('--clubs',  type=int, default=DEFAULT_CLUBS,  help='Number of clubs')
    parser.add_argument('--rounds', type=int, default=DEFAULT_ROUNDS, help='FL rounds')
    args = parser.parse_args()

    run(Path(args.data), args.clubs, args.rounds)
