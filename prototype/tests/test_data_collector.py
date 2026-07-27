from data_collector import DataCollector


class FakeSpotify:
    def current_user(self):
        return {"id": "user"}

    def current_user_saved_tracks(self, limit):
        return {
            "items": [
                {
                    "track": {
                        "id": f"id-{index}",
                        "name": f"Track {index}",
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                        "uri": f"spotify:track:{index}",
                    }
                }
                for index in range(limit)
            ],
            "next": "page-2",
        }

    def next(self, _results):
        return {
            "items": [
                {
                    "track": {
                        "id": f"later-{index}",
                        "name": "Later",
                        "artists": [{"name": "Artist"}],
                        "album": {"name": "Album"},
                        "uri": "spotify:track:later",
                    }
                }
                for index in range(50)
            ],
            "next": None,
        }


def test_saved_tracks_respects_requested_total_limit() -> None:
    tracks = DataCollector(FakeSpotify()).get_saved_tracks(limit=60)
    assert len(tracks) == 60
