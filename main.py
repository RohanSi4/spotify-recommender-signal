"""Command-line interface for the offline-first recommendation engine."""

from __future__ import annotations

import argparse

from demo_data import build_demo_catalog
from evaluate import evaluate
from recommender import MOOD_PROFILES, RecommendationEngine


def _print_tracks(tracks: list[dict]) -> None:
    for index, track in enumerate(tracks, 1):
        artist = ", ".join(track.get("artists", []))
        reasons = ", ".join(track.get("match_reasons", []))
        print(f"{index:>2}. {track['name']} by {artist} ({track['score']:.1%}; {reasons})")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mood", choices=sorted(MOOD_PROFILES), default="focus")
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--benchmark", action="store_true")
    args = parser.parse_args()

    if args.benchmark:
        result = evaluate()
        for key, value in result.items():
            print(f"{key}: {value}")
        return

    catalog = build_demo_catalog()
    results = RecommendationEngine().recommend_for_mood(args.mood, catalog, args.limit)
    print(f"Offline demo · {args.mood} mood\n")
    _print_tracks(results)


if __name__ == "__main__":
    main()
