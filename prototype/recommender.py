"""Testable recommendation core plus a thin Spotify API adapter.

The ranking code in :class:`RecommendationEngine` is deliberately independent
of Spotipy.  This keeps recommendation behavior reproducible and lets the app
run in demo mode without credentials or network access.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

import numpy as np

Track = dict[str, Any]


class RecommendationError(RuntimeError):
    """A user-actionable recommendation failure."""


class SpotifyCapabilityError(RecommendationError):
    """The connected Spotify app cannot use a required legacy capability."""


@dataclass(frozen=True)
class FeatureSpec:
    minimum: float
    maximum: float
    weight: float


# Key and mode are intentionally excluded: treating their integer encodings as
# continuous distances creates false musical similarity.
FEATURE_SPECS: dict[str, FeatureSpec] = {
    "danceability": FeatureSpec(0.0, 1.0, 1.1),
    "energy": FeatureSpec(0.0, 1.0, 1.3),
    "loudness": FeatureSpec(-60.0, 0.0, 0.5),
    "speechiness": FeatureSpec(0.0, 1.0, 0.6),
    "acousticness": FeatureSpec(0.0, 1.0, 0.9),
    "instrumentalness": FeatureSpec(0.0, 1.0, 0.7),
    "liveness": FeatureSpec(0.0, 1.0, 0.4),
    "valence": FeatureSpec(0.0, 1.0, 1.2),
    "tempo": FeatureSpec(40.0, 220.0, 0.8),
}


MOOD_PROFILES: dict[str, dict[str, float]] = {
    "happy": {"valence": 0.82, "energy": 0.68, "danceability": 0.72, "tempo": 124},
    "sad": {"valence": 0.18, "energy": 0.30, "acousticness": 0.62, "tempo": 78},
    "energetic": {"energy": 0.92, "danceability": 0.68, "tempo": 150, "valence": 0.65},
    "calm": {"energy": 0.22, "acousticness": 0.78, "speechiness": 0.08, "tempo": 76},
    "relaxed": {"energy": 0.30, "acousticness": 0.68, "valence": 0.55, "tempo": 88},
    "party": {"danceability": 0.90, "energy": 0.86, "valence": 0.76, "tempo": 128},
    "focus": {"energy": 0.38, "instrumentalness": 0.78, "speechiness": 0.04, "tempo": 100},
    "workout": {"energy": 0.96, "danceability": 0.78, "tempo": 156, "valence": 0.62},
    "romantic": {"valence": 0.62, "energy": 0.42, "acousticness": 0.52, "tempo": 96},
}


def _features(track: Mapping[str, Any]) -> Mapping[str, Any] | None:
    value = track.get("features")
    return value if isinstance(value, Mapping) else None


class RecommendationEngine:
    """Rank candidate tracks using normalized, weighted audio features."""

    feature_names = tuple(FEATURE_SPECS)

    def vectorize(self, features: Mapping[str, Any]) -> np.ndarray:
        """Return a clipped 0–1 feature vector, rejecting incomplete rows."""
        values: list[float] = []
        for name, spec in FEATURE_SPECS.items():
            raw = features.get(name)
            if raw is None:
                raise ValueError(f"missing audio feature: {name}")
            try:
                numeric = float(raw)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"invalid audio feature: {name}") from exc
            scaled = (numeric - spec.minimum) / (spec.maximum - spec.minimum)
            values.append(float(np.clip(scaled, 0.0, 1.0)))
        return np.asarray(values, dtype=float)

    @property
    def weights(self) -> np.ndarray:
        return np.asarray([spec.weight for spec in FEATURE_SPECS.values()], dtype=float)

    def similarity(self, left: np.ndarray, right: np.ndarray) -> float:
        """Weighted Euclidean similarity bounded to ``(0, 1]``."""
        distance = float(np.sqrt(np.average((left - right) ** 2, weights=self.weights)))
        return 1.0 / (1.0 + distance)

    def recommend(
        self,
        seed_tracks: Sequence[Mapping[str, Any]],
        candidates: Sequence[Mapping[str, Any]],
        limit: int = 20,
    ) -> list[Track]:
        """Rank candidates against the centroid of one or more seed tracks.

        Seed tracks are excluded by ID. Invalid/incomplete candidates are
        skipped and output order is deterministic for tied scores.
        """
        if limit < 1:
            raise ValueError("limit must be at least 1")
        seed_vectors = [self.vectorize(value) for track in seed_tracks if (value := _features(track))]
        if not seed_vectors:
            raise RecommendationError("No seed track has a complete audio-feature vector.")

        centroid = np.mean(seed_vectors, axis=0)
        seed_ids = {str(track.get("id")) for track in seed_tracks if track.get("id")}
        ranked: list[Track] = []
        seen: set[str] = set()
        for index, candidate in enumerate(candidates):
            candidate_id = str(candidate.get("id") or f"candidate-{index}")
            if candidate_id in seed_ids or candidate_id in seen:
                continue
            seen.add(candidate_id)
            candidate_features = _features(candidate)
            if not candidate_features:
                continue
            try:
                vector = self.vectorize(candidate_features)
            except ValueError:
                continue
            result = dict(candidate)
            result["score"] = round(self.similarity(centroid, vector), 6)
            result["match_reasons"] = self._match_reasons(centroid, vector)
            ranked.append(result)

        ranked.sort(key=lambda track: (-float(track["score"]), str(track.get("id", ""))))
        return ranked[:limit]

    def recommend_for_mood(
        self,
        mood: str,
        candidates: Sequence[Mapping[str, Any]],
        limit: int = 20,
    ) -> list[Track]:
        mood_key = mood.strip().lower()
        if mood_key not in MOOD_PROFILES:
            choices = ", ".join(sorted(MOOD_PROFILES))
            raise ValueError(f"Unknown mood '{mood}'. Choose one of: {choices}.")
        baseline = {name: (spec.minimum + spec.maximum) / 2 for name, spec in FEATURE_SPECS.items()}
        baseline.update(MOOD_PROFILES[mood_key])
        seed: Track = {"id": f"mood:{mood_key}", "features": baseline}
        results = self.recommend([seed], candidates, limit)
        for track in results:
            track["mood"] = mood_key
        return results

    def _match_reasons(self, target: np.ndarray, candidate: np.ndarray) -> list[str]:
        differences = np.abs(target - candidate)
        closest = np.argsort(differences)[:2]
        labels = {
            "danceability": "danceability",
            "energy": "energy",
            "loudness": "intensity",
            "speechiness": "vocal style",
            "acousticness": "acoustic texture",
            "instrumentalness": "instrumental profile",
            "liveness": "live feel",
            "valence": "mood",
            "tempo": "tempo",
        }
        return [f"similar {labels[self.feature_names[index]]}" for index in closest]


class SpotifyRecommender:
    """Spotify-backed facade around :class:`RecommendationEngine`.

    ``spotify_client`` may be ``None`` for demo/offline use.
    """

    def __init__(self, spotify_client: Any | None = None, engine: RecommendationEngine | None = None):
        self.sp = spotify_client
        self.engine = engine or RecommendationEngine()

    def _require_client(self) -> Any:
        if self.sp is None:
            raise RecommendationError(
                "Spotify is not connected; use demo mode or configure OAuth credentials."
            )
        return self.sp

    def _attach_features(self, tracks: Sequence[Mapping[str, Any]]) -> list[Track]:
        """Attach missing features with batched calls when the app has access."""
        output = [dict(track) for track in tracks]
        missing = [track for track in output if track.get("id") and not _features(track)]
        if not missing:
            return output
        client = self._require_client()
        by_id: dict[str, Mapping[str, Any]] = {}
        try:
            for start in range(0, len(missing), 100):
                batch = missing[start : start + 100]
                ids = [str(track["id"]) for track in batch]
                rows = client.audio_features(ids) or []
                by_id.update({track_id: row for track_id, row in zip(ids, rows, strict=False) if row})
        except Exception as exc:
            raise SpotifyCapabilityError(
                "Spotify did not provide audio features. New/development-mode apps no longer have "
                "access to this endpoint; demo mode remains fully functional."
            ) from exc
        for track in output:
            if not _features(track) and str(track.get("id")) in by_id:
                track["features"] = dict(by_id[str(track["id"])])
        return output

    def content_based_recommendations(
        self,
        seed_tracks: Sequence[Mapping[str, Any]],
        user_tracks: Sequence[Mapping[str, Any]],
        num_recommendations: int = 20,
        similarity_metric: str = "weighted-euclidean",
    ) -> list[Track]:
        if similarity_metric != "weighted-euclidean":
            raise ValueError("Only the documented 'weighted-euclidean' metric is supported.")
        # Kept for CLI compatibility; the corrected implementation excludes
        # only seeds, not the entire candidate library.
        seeds = self._attach_features(seed_tracks)
        candidates = self._attach_features(user_tracks)
        return self.engine.recommend(seeds, candidates, num_recommendations)

    def mood_based_recommendations(
        self,
        mood: str,
        candidates: Sequence[Mapping[str, Any]],
        limit: int = 20,
    ) -> list[Track]:
        return self.engine.recommend_for_mood(mood, self._attach_features(candidates), limit)

    def get_spotify_recommendations(
        self,
        seed_tracks: Sequence[str] | None = None,
        seed_artists: Sequence[str] | None = None,
        seed_genres: Sequence[str] | None = None,
        limit: int = 20,
        **target_features: Any,
    ) -> list[Track]:
        """Call Spotify's restricted Recommendations endpoint for legacy apps."""
        seeds: list[tuple[str, str]] = []
        seeds.extend(("track", value) for value in (seed_tracks or []))
        seeds.extend(("artist", value) for value in (seed_artists or []))
        seeds.extend(("genre", value) for value in (seed_genres or []))
        if not seeds:
            raise ValueError("At least one recommendation seed is required.")
        seeds = seeds[:5]
        kwargs = {
            "seed_tracks": [value for kind, value in seeds if kind == "track"] or None,
            "seed_artists": [value for kind, value in seeds if kind == "artist"] or None,
            "seed_genres": [value for kind, value in seeds if kind == "genre"] or None,
            "limit": min(max(int(limit), 1), 100),
            **target_features,
        }
        try:
            response = self._require_client().recommendations(**kwargs)
        except RecommendationError:
            raise
        except Exception as exc:
            raise SpotifyCapabilityError(
                "Spotify Recommendations is unavailable to new and development-mode apps."
            ) from exc
        return [self._spotify_track(track) for track in response.get("tracks", [])]

    @staticmethod
    def _spotify_track(track: Mapping[str, Any]) -> Track:
        return {
            "id": track.get("id"),
            "name": track.get("name", "Unknown track"),
            "artists": [artist.get("name", "Unknown artist") for artist in track.get("artists", [])],
            "album": (track.get("album") or {}).get("name", ""),
            "uri": track.get("uri"),
            "external_url": (track.get("external_urls") or {}).get("spotify"),
        }


def reciprocal_rank_hit_rate(
    tracks: Sequence[Mapping[str, Any]],
    label_key: str = "label",
    k: int = 5,
) -> tuple[float, float]:
    """Leave-one-out hit-rate@k and mean reciprocal rank for labeled fixtures."""
    engine = RecommendationEngine()
    hits = 0
    reciprocal_ranks: list[float] = []
    evaluated = 0
    for seed in tracks:
        label = seed.get(label_key)
        if label is None:
            continue
        ranked = engine.recommend([seed], tracks, k)
        evaluated += 1
        rank = next((index for index, item in enumerate(ranked, 1) if item.get(label_key) == label), None)
        if rank is not None:
            hits += 1
            reciprocal_ranks.append(1.0 / rank)
        else:
            reciprocal_ranks.append(0.0)
    if not evaluated:
        raise ValueError("evaluation data has no labeled tracks")
    return hits / evaluated, float(np.mean(reciprocal_ranks))
