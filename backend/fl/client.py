"""
FL client — represents one sports club training on its local player data.

In production each club runs this client inside their own infrastructure.
Raw player data never leaves the club; only (coef, intercept, n_samples)
are returned to the server.
"""

import numpy as np
import pandas as pd
from sklearn.metrics import accuracy_score

from .model import build_model, get_params, set_params, FEATURES, TARGET


class FLClient:
    """
    Simulates one club's local FL participant.

    Parameters
    ----------
    club_id : str
        Unique club identifier (e.g. Keycloak coach sub or club name).
    data : pd.DataFrame
        Local player dataset — stays on-premise, never shared.
    """

    def __init__(self, club_id: str, data: pd.DataFrame):
        self.club_id = club_id
        self.data    = data.reset_index(drop=True)
        self.model   = build_model()

    # ── FL interface ───────────────────────────────────────────────────────

    def train(
        self,
        global_coef: np.ndarray,
        global_intercept: np.ndarray,
    ):
        """
        Receive global parameters, fine-tune on local data, return update.

        Returns
        -------
        (coef, intercept, n_samples) — only model weights are sent back,
        never the raw player data.
        """
        X = self.data[FEATURES].values
        y = self.data[TARGET].values

        set_params(self.model, global_coef, global_intercept)
        self.model.fit(X, y)

        coef, intercept = get_params(self.model)
        return coef, intercept, len(y)

    def local_accuracy(self) -> float:
        """Evaluate current local model on local data (for logging only)."""
        X = self.data[FEATURES].values
        y = self.data[TARGET].values
        return accuracy_score(y, self.model.predict(X))

    def __repr__(self):
        return f"FLClient(club_id={self.club_id!r}, n_players={len(self.data)})"
