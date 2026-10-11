"""Original, dependency-free logistic regression on explicitly synthetic data.

The mathematical method is credited to Andrew Ng's CS229 lecture notes in
SOURCE_CREDITS.txt. No implementation from those notes is copied.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import random

FEATURE_NAMES = ("error_rate", "hint_rate", "slow_rate")
SEED = 631


@dataclass(frozen=True, slots=True)
class Profile:
    """An immutable aggregate profile, not a record of an actual person."""

    identifier: str
    split: str
    features: tuple[float, float, float]
    label: int


def sigmoid(value: float) -> float:
    """Use two equivalent branches to avoid overflow for extreme logits."""
    if value >= 0:
        return 1 / (1 + math.exp(-value))
    exponential = math.exp(value)
    return exponential / (1 + exponential)


def generate_profiles() -> list[Profile]:
    generator = random.Random(SEED)
    profiles = []
    for index in range(320):
        features = tuple(round(generator.random(), 6) for _ in FEATURE_NAMES)
        # This is an invented teaching policy, not an empirically validated label.
        label = int(3 * features[0] + 2 * features[1] + features[2] >= 2.75)
        profiles.append(Profile(f"synthetic-{index:03d}", "train" if index < 240 else "test", features, label))
    return profiles


def predict(weights: list[float], bias: float, features: tuple[float, ...]) -> float:
    if len(weights) != 3 or len(features) != 3:
        raise ValueError("Exactly three features and weights are required.")
    if any(not math.isfinite(value) or not 0 <= value <= 1 for value in features):
        raise ValueError("Features must be finite numbers between zero and one.")
    if any(not math.isfinite(value) for value in [*weights, bias]):
        raise ValueError("Model parameters must be finite.")
    return sigmoid(bias + sum(weight * value for weight, value in zip(weights, features)))


def train(profiles: list[Profile], iterations: int = 2500) -> tuple[list[float], float]:
    """Fit batch gradients with L2 regularization using training rows only."""
    if not profiles or any(row.split != "train" for row in profiles):
        raise ValueError("Training requires a nonempty training-only split.")
    if iterations < 1:
        raise ValueError("At least one training iteration is required.")
    weights, bias = [0.0, 0.0, 0.0], 0.0
    rate, regularization = 0.8, 0.001
    for _ in range(iterations):
        gradients, bias_gradient = [0.0, 0.0, 0.0], 0.0
        for row in profiles:
            difference = predict(weights, bias, row.features) - row.label
            bias_gradient += difference
            for index, value in enumerate(row.features):
                gradients[index] += difference * value
        for index in range(3):
            weights[index] -= rate * (gradients[index] / len(profiles) + regularization * weights[index])
        bias -= rate * bias_gradient / len(profiles)
    return weights, bias


def build_model() -> dict:
    profiles = generate_profiles()
    training = [row for row in profiles if row.split == "train"]
    testing = [row for row in profiles if row.split == "test"]
    weights, bias = train(training)
    correct = sum((predict(weights, bias, row.features) >= 0.5) == bool(row.label) for row in testing)
    return {
        "schema_version": 1,
        "algorithm": "logistic_regression",
        "feature_names": list(FEATURE_NAMES),
        "weights": weights,
        "bias": bias,
        "training": {"seed": SEED, "rows": len(training), "iterations": 2500, "learning_rate": 0.8, "l2": 0.001},
        "evaluation": {"test_rows": len(testing), "correct": correct, "accuracy": correct / len(testing)},
        "disclosure": "Trained and evaluated only on invented synthetic profiles. Scores are not calibrated probabilities of real learning needs.",
    }


def models_equivalent(actual: dict, expected: dict) -> bool:
    """Compare metadata exactly and parameters within cross-platform libm noise.

    Python on macOS and Linux may differ in the last few bits of math.exp.
    This tolerance permits those differences without masking a changed model.
    """
    try:
        actual_metadata, expected_metadata = dict(actual), dict(expected)
        actual_weights = actual_metadata.pop("weights")
        expected_weights = expected_metadata.pop("weights")
        actual_bias = actual_metadata.pop("bias")
        expected_bias = expected_metadata.pop("bias")
        if type(actual_metadata.get("schema_version")) is not int:
            return False
        if not isinstance(actual_weights, list) or len(actual_weights) != 3:
            return False
        actual_parameters = [*actual_weights, actual_bias]
        expected_parameters = [*expected_weights, expected_bias]
        return actual_metadata == expected_metadata and all(
            type(value) in (int, float)
            and math.isfinite(value)
            and math.isclose(value, reference, rel_tol=0, abs_tol=1e-10)
            for value, reference in zip(actual_parameters, expected_parameters, strict=True)
        )
    except (KeyError, TypeError, ValueError):
        return False
