"""
Two-layer neural network implemented in pure NumPy.
Architecture: n_features → n_hidden (ReLU) → 1 (Sigmoid)

Designed for Federated Learning: weights/biases are the shareable parameters.
Only these model parameters (never raw data) are sent to the central server.
"""

import numpy as np
import json


# Feature ordering used throughout the system
POSITION_CLASSES = ["Defender", "Forward", "Goalkeeper", "Midfielder"]
NUMERICAL_FEATURES = [
    "Age",
    "Height_cm",
    "Weight_kg",
    "BMI",
    "Training_Hours_Per_Week",
    "Matches_Played_Past_Season",
    "Previous_Injury_Count",
    "Knee_Strength_Score",
    "Hamstring_Flexibility",
    "Reaction_Time_ms",
    "Balance_Test_Score",
    "Sprint_Speed_10m_s",
    "Agility_Score",
    "Sleep_Hours_Per_Night",
    "Stress_Level_Score",
    "Nutrition_Quality_Score",
    "Warmup_Routine_Adherence",
]
# Total = 17 numerical + 4 one-hot position = 21
N_FEATURES = len(NUMERICAL_FEATURES) + len(POSITION_CLASSES)  # 21
N_HIDDEN = 32


class NeuralNetwork:
    """Binary classifier: predicts injury probability (0–1)."""

    def __init__(self, n_features: int = N_FEATURES, n_hidden: int = N_HIDDEN, seed: int = 42):
        rng = np.random.default_rng(seed)
        # Xavier (Glorot) initialisation
        self.W1 = rng.standard_normal((n_features, n_hidden)) * np.sqrt(2.0 / n_features)
        self.b1 = np.zeros(n_hidden)
        self.W2 = rng.standard_normal((n_hidden, 1)) * np.sqrt(2.0 / n_hidden)
        self.b2 = np.zeros(1)
        # Saved during forward pass for backprop
        self._Z1 = self._A1 = self._Z2 = self._A2 = None

    # ------------------------------------------------------------------
    # Forward / backward
    # ------------------------------------------------------------------

    def _relu(self, z):
        return np.maximum(0.0, z)

    def _sigmoid(self, z):
        return 1.0 / (1.0 + np.exp(-np.clip(z, -500, 500)))

    def forward(self, X: np.ndarray) -> np.ndarray:
        self._Z1 = X @ self.W1 + self.b1
        self._A1 = self._relu(self._Z1)
        self._Z2 = self._A1 @ self.W2 + self.b2
        self._A2 = self._sigmoid(self._Z2)
        return self._A2

    def _binary_crossentropy(self, y_pred: np.ndarray, y_true: np.ndarray) -> float:
        eps = 1e-8
        y_true = y_true.reshape(-1, 1)
        return float(-np.mean(y_true * np.log(y_pred + eps) + (1 - y_true) * np.log(1 - y_pred + eps)))

    def backward(self, X: np.ndarray, y_true: np.ndarray, lr: float = 0.01):
        m = X.shape[0]
        y_true = y_true.reshape(-1, 1)

        dZ2 = self._A2 - y_true
        dW2 = self._A1.T @ dZ2 / m
        db2 = dZ2.mean(axis=0)

        dA1 = dZ2 @ self.W2.T
        dZ1 = dA1 * (self._Z1 > 0)
        dW1 = X.T @ dZ1 / m
        db1 = dZ1.mean(axis=0)

        self.W1 -= lr * dW1
        self.b1 -= lr * db1
        self.W2 -= lr * dW2
        self.b2 -= lr * db2

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def train(
        self, X: np.ndarray, y: np.ndarray, epochs: int = 10, lr: float = 0.01
    ) -> dict:
        """Train for `epochs` epochs; returns final loss and accuracy."""
        losses = []
        for _ in range(epochs):
            y_pred = self.forward(X)
            loss = self._binary_crossentropy(y_pred, y)
            losses.append(loss)
            self.backward(X, y, lr)

        final_pred = (self.forward(X) >= 0.5).astype(int).flatten()
        accuracy = float(np.mean(final_pred == y))
        return {"loss": losses[-1], "accuracy": accuracy, "loss_history": losses}

    # ------------------------------------------------------------------
    # Inference
    # ------------------------------------------------------------------

    def predict_proba(self, X: np.ndarray) -> np.ndarray:
        return self.forward(X).flatten()

    def predict(self, X: np.ndarray) -> np.ndarray:
        return (self.predict_proba(X) >= 0.5).astype(int)

    # ------------------------------------------------------------------
    # Serialisation — only params, never data
    # ------------------------------------------------------------------

    def get_params(self) -> dict:
        return {
            "W1": self.W1.tolist(),
            "b1": self.b1.tolist(),
            "W2": self.W2.tolist(),
            "b2": self.b2.tolist(),
        }

    def set_params(self, params: dict):
        self.W1 = np.array(params["W1"])
        self.b1 = np.array(params["b1"])
        self.W2 = np.array(params["W2"])
        self.b2 = np.array(params["b2"])

    def save(self, path: str):
        with open(path, "w") as f:
            json.dump(self.get_params(), f)

    def load(self, path: str):
        with open(path, "r") as f:
            self.set_params(json.load(f))
