"""Small Spotify library adapter used by the Streamlit application."""

from __future__ import annotations

from typing import Any


class DataCollector:
    """Read track metadata while keeping pagination behavior testable."""

    def __init__(self, spotify_client: Any):
        self.sp = spotify_client

    def get_saved_tracks(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return at most ``limit`` saved tracks across Spotify pages.

        Spotify caps each `/me/tracks` request at 50. The old implementation
        treated ``limit`` as a page size and accidentally fetched the full
        library; this method treats it as a total count.
        """
        if limit < 1:
            return []
        results = self.sp.current_user_saved_tracks(limit=min(limit, 50))
        tracks: list[dict[str, Any]] = []

        while results:
            for row in results.get("items", []):
                # `track` is the current /me/tracks shape; accepting `item`
                # makes the boundary tolerant of Spotify's generic item naming.
                track = row.get("track") or row.get("item")
                if not track or not track.get("id"):
                    continue
                tracks.append(self._track(track))
                if len(tracks) == limit:
                    return tracks
            if not results.get("next"):
                break
            results = self.sp.next(results)
        return tracks

    @staticmethod
    def _track(track: dict[str, Any]) -> dict[str, Any]:
        album = track.get("album") or {}
        return {
            "id": track["id"],
            "name": track.get("name", "Unknown track"),
            "artists": [artist.get("name", "Unknown artist") for artist in track.get("artists", [])],
            "album": album.get("name", ""),
            "uri": track.get("uri"),
            "external_url": (track.get("external_urls") or {}).get("spotify"),
        }
