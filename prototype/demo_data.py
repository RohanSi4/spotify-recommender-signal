"""Deterministic, synthetic catalog used by demos, tests, and benchmarks."""

from __future__ import annotations

from typing import Any

import numpy as np

from recommender import FEATURE_SPECS, MOOD_PROFILES

TITLES = (
    "Afterglow Avenue",
    "Blue Hour Letters",
    "Circuit Breaker",
    "Quiet Tides",
    "Sunday Static",
    "Neon Kitchen",
    "Deep Work Drift",
    "Last Rep",
    "Velvet Polaroid",
)


def build_demo_catalog(seed: int = 20260714, tracks_per_mood: int = 8) -> list[dict[str, Any]]:
    """Build stable pseudo-tracks around the documented mood profiles.

    The data is synthetic by design: it is safe to publish and useful for
    regression testing, but must not be presented as real-world model quality.
    """
    rng = np.random.default_rng(seed)
    catalog: list[dict[str, Any]] = []
    for mood_index, (mood, profile) in enumerate(MOOD_PROFILES.items()):
        for item_index in range(tracks_per_mood):
            features: dict[str, float] = {}
            for name, spec in FEATURE_SPECS.items():
                center = profile.get(name, (spec.minimum + spec.maximum) / 2)
                scale = (spec.maximum - spec.minimum) * (0.025 if name == "tempo" else 0.045)
                features[name] = round(
                    float(np.clip(rng.normal(center, scale), spec.minimum, spec.maximum)), 5
                )
            catalog.append(
                {
                    "id": f"demo-{mood}-{item_index + 1:02d}",
                    "name": f"{TITLES[mood_index]} {item_index + 1:02d}",
                    "artists": [f"Demo Artist {chr(65 + mood_index)}"],
                    "album": "Offline Evaluation Set",
                    "uri": None,
                    "label": mood,
                    "features": features,
                }
            )
    return catalog
