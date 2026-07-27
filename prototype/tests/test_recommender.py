from __future__ import annotations

from demo_data import build_demo_catalog
from recommender import (
    RecommendationEngine,
    RecommendationError,
    SpotifyCapabilityError,
    SpotifyRecommender,
    reciprocal_rank_hit_rate,
)


def test_recommendation_excludes_seed_and_is_sorted() -> None:
    catalog = build_demo_catalog(tracks_per_mood=3)
    results = RecommendationEngine().recommend([catalog[0]], catalog, limit=5)
    assert catalog[0]["id"] not in {track["id"] for track in results}
    assert [track["score"] for track in results] == sorted(
        [track["score"] for track in results], reverse=True
    )
    assert all(track["match_reasons"] for track in results)


def test_content_regression_does_not_exclude_entire_candidate_library() -> None:
    catalog = build_demo_catalog(tracks_per_mood=2)
    results = SpotifyRecommender().content_based_recommendations([catalog[0]], catalog, 4)
    assert len(results) == 4


def test_mood_ranking_validates_input() -> None:
    catalog = build_demo_catalog(tracks_per_mood=2)
    engine = RecommendationEngine()
    assert all(track["mood"] == "focus" for track in engine.recommend_for_mood("focus", catalog, 3))
    try:
        engine.recommend_for_mood("confused", catalog)
    except ValueError as exc:
        assert "Unknown mood" in str(exc)
    else:
        raise AssertionError("unknown mood should fail")


def test_incomplete_candidates_are_skipped() -> None:
    catalog = build_demo_catalog(tracks_per_mood=2)
    broken = {"id": "broken", "features": {"energy": 0.5}}
    results = RecommendationEngine().recommend([catalog[0]], [broken, catalog[1]], 5)
    assert [track["id"] for track in results] == [catalog[1]["id"]]


def test_evaluation_is_deterministic_and_labeled() -> None:
    catalog = build_demo_catalog()
    first = reciprocal_rank_hit_rate(catalog, k=5)
    second = reciprocal_rank_hit_rate(catalog, k=5)
    assert first == second
    assert first[0] >= 0.90


class FailingSpotify:
    def audio_features(self, _ids):
        raise RuntimeError("403 Forbidden")


def test_restricted_audio_features_has_actionable_error() -> None:
    catalog = build_demo_catalog(tracks_per_mood=1)
    seed = {key: value for key, value in catalog[0].items() if key != "features"}
    try:
        SpotifyRecommender(FailingSpotify()).content_based_recommendations([seed], catalog)
    except SpotifyCapabilityError as exc:
        assert "demo mode" in str(exc)
    else:
        raise AssertionError("restricted feature access should fail clearly")


def test_missing_client_error_is_actionable() -> None:
    try:
        SpotifyRecommender().get_spotify_recommendations(seed_tracks=["one"])
    except RecommendationError as exc:
        assert "demo mode" in str(exc)
    else:
        raise AssertionError("missing client should fail clearly")
