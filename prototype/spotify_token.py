"""
Spotify authentication module.
"""

import os

from dotenv import load_dotenv
from spotipy import Spotify
from spotipy.oauth2 import SpotifyOAuth

# Load environment variables
load_dotenv()


class SpotifyConfigurationError(ValueError):
    """Spotify OAuth configuration is incomplete."""


def get_spotify_client() -> Spotify:
    """
    Initialize and return a Spotify client with authentication.

    Returns:
        Authenticated Spotify client
    """
    client_id = os.getenv("SPOTIFY_CLIENT_ID")
    client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
    redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

    if not all([client_id, client_secret, redirect_uri]):
        missing = [
            name
            for name, value in {
                "SPOTIFY_CLIENT_ID": client_id,
                "SPOTIFY_CLIENT_SECRET": client_secret,
                "SPOTIFY_REDIRECT_URI": redirect_uri,
            }.items()
            if not value
        ]
        raise SpotifyConfigurationError("Missing Spotify OAuth settings: " + ", ".join(missing))

    # Request only the scopes exercised by the current UI.
    scope = "playlist-modify-private user-library-read "

    sp = Spotify(
        auth_manager=SpotifyOAuth(
            client_id=client_id,
            client_secret=client_secret,
            redirect_uri=redirect_uri,
            scope=scope,
            cache_path=".spotify_cache",
        )
    )

    return sp


if __name__ == "__main__":
    # Test authentication
    sp = get_spotify_client()
    user = sp.current_user()
    print(f"✓ Authenticated as: {user['display_name']}")

    # Test call
    playlists = sp.current_user_playlists(limit=5)
    print("\nYour Playlists:")
    for pl in playlists["items"]:
        print(f"  - {pl['name']} ({pl['tracks']['total']} tracks)")
