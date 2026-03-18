"""
Federated Averaging (FedAvg) — McMahan et al., 2017.

The central server aggregates model parameters from N clients.
Raw data NEVER leaves the client; only parameter tensors are shared.

Aggregation formula:
    θ_global = Σ (n_k / n_total) * θ_k
    where n_k = number of local data points for client k
"""

import numpy as np
from typing import List, Tuple
from app.ml.model import NeuralNetwork


def federated_average(
    client_params: List[dict], client_sizes: List[int]
) -> dict:
    """
    Compute the weighted average of model parameters.

    Args:
        client_params: list of parameter dicts, one per client
        client_sizes:  list of local dataset sizes (same order as client_params)

    Returns:
        Aggregated parameter dict
    """
    if not client_params:
        raise ValueError("No client parameters to aggregate.")

    total = sum(client_sizes)
    keys = client_params[0].keys()
    averaged = {}

    for key in keys:
        weighted_sum = sum(
            np.array(params[key]) * size
            for params, size in zip(client_params, client_sizes)
        )
        averaged[key] = (weighted_sum / total).tolist()

    return averaged


def simulate_local_training(
    model: NeuralNetwork,
    X: np.ndarray,
    y: np.ndarray,
    epochs: int = 10,
    lr: float = 0.01,
) -> Tuple[dict, dict]:
    """
    Simulate one client's local training for a single FL round.

    The global model parameters are copied to the local model,
    trained on local data, then the updated parameters are returned.
    Raw data X and y remain local — only params are returned.

    Returns:
        (updated_params, training_stats)
    """
    local_model = NeuralNetwork()
    local_model.set_params(model.get_params())  # Initialise from global

    stats = local_model.train(X, y, epochs=epochs, lr=lr)
    return local_model.get_params(), stats
