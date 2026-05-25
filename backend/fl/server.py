"""
FedAvg aggregation server.

Round protocol:
  1. Server broadcasts global parameters (coef, intercept) to all clubs.
  2. Each club trains locally and returns (coef, intercept, n_samples).
  3. Server computes weighted average → updated global parameters.

FedAvg formula:
    θ_global = Σ_k (n_k / n_total) × θ_k
"""

import numpy as np
from typing import List, Tuple


Update = Tuple[np.ndarray, np.ndarray, int]   # (coef, intercept, n_samples)


def fed_avg(updates: List[Update]) -> Tuple[np.ndarray, np.ndarray]:
    """Compute federated weighted average of model parameters."""
    total            = sum(n for _, _, n in updates)
    global_coef      = sum(coef * n       for coef, _,         n in updates) / total
    global_intercept = sum(intercept * n  for _,    intercept, n in updates) / total
    return global_coef, global_intercept


class FLServer:
    """
    Central FL server — holds the global model and runs FedAvg each round.

    Usage:
        server = FLServer(n_features=12)
        for round_n in range(FL_ROUNDS):
            params   = server.get_global_params()
            updates  = [client.train(*params) for client in clients]
            server.aggregate(updates)
    """

    def __init__(self, n_features: int):
        self.global_coef      = np.zeros((1, n_features))
        self.global_intercept = np.zeros(1)
        self.round            = 0
        self.history: List[Tuple[int, float]] = []   # (round, accuracy)

    def get_global_params(self) -> Tuple[np.ndarray, np.ndarray]:
        return self.global_coef.copy(), self.global_intercept.copy()

    def aggregate(self, updates: List[Update]) -> Tuple[np.ndarray, np.ndarray]:
        self.global_coef, self.global_intercept = fed_avg(updates)
        self.round += 1
        return self.global_coef, self.global_intercept

    def evaluate(self, X_test: np.ndarray, y_test: np.ndarray) -> float:
        """Score the current global model on a held-out test set."""
        from .model import build_model, set_params
        from sklearn.metrics import accuracy_score

        model = build_model()
        set_params(model, self.global_coef, self.global_intercept)
        acc = accuracy_score(y_test, model.predict(X_test))
        self.history.append((self.round, acc))
        return acc
