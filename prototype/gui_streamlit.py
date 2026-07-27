"""Streamlit interface for the offline-first Spotify recommender."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from data_collector import DataCollector
from demo_data import build_demo_catalog
from recommender import MOOD_PROFILES, RecommendationError, SpotifyRecommender
from spotify_token import get_spotify_client

st.set_page_config(
    page_title="Signal / Music Recommender",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --signal: #b8ff5a; --ink: #f4f2ec; --muted: #9b9b93; }
    .stApp { background: #0b0d0c; color: var(--ink); }
    [data-testid="stSidebar"] { background: #111411; border-right: 1px solid #272b27; }
    .hero { border: 1px solid #30352f; border-radius: 22px; padding: 2.3rem 2.5rem;
            background: radial-gradient(circle at 85% 15%, #24351c 0, #121612 32%, #0f120f 70%); }
    .eyebrow { color: var(--signal); font: 600 .72rem/1.2 monospace; letter-spacing: .18em; }
    .hero h1 { font-size: clamp(2.7rem, 7vw, 5.6rem); line-height: .92; margin: .7rem 0 1.1rem;
               letter-spacing: -.06em; max-width: 900px; }
    .hero p { color: #b7bbb4; max-width: 650px; font-size: 1.04rem; }
    .status-pill { display: inline-block; border: 1px solid #41513a; color: #cefba4; padding: .35rem .65rem;
                   border-radius: 99px; font: .72rem monospace; margin-top: 1rem; }
    .track { border-top: 1px solid #2a2e29; padding: 1rem 0; }
    .track-name { font-weight: 650; font-size: 1.05rem; }
    .track-meta { color: var(--muted); font-size: .83rem; margin-top: .2rem; }
    .score { color: var(--signal); font: .78rem monospace; }
    .fineprint { color: #777b75; font-size: .74rem; }
    div.stButton > button { border-radius: 999px; min-height: 2.8rem; font-weight: 650; }
    div[data-baseweb="select"] > div { border-radius: 12px; }
    </style>
    """,
    unsafe_allow_html=True,
)


def _init_state() -> None:
    defaults = {
        "spotify_client": None,
        "spotify_user": None,
        "spotify_tracks": [],
        "last_results": [],
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def _connect() -> None:
    try:
        with st.spinner("Opening Spotify authorization…"):
            client = get_spotify_client()
            user = client.current_user()
            tracks = DataCollector(client).get_saved_tracks(limit=200)
        st.session_state.spotify_client = client
        st.session_state.spotify_user = user
        st.session_state.spotify_tracks = tracks
        st.success(f"Connected as {user.get('display_name') or 'Spotify user'}.")
    except Exception as exc:
        # OAuth/API text can contain implementation detail; keep the UI useful
        # and put the actionable setup in the README.
        st.error("Spotify connection failed. Check the three OAuth settings and your app allowlist.")
        st.caption(str(exc))


def _demo_workspace() -> tuple[list[dict[str, Any]], SpotifyRecommender]:
    return build_demo_catalog(), SpotifyRecommender()


def _spotify_workspace() -> tuple[list[dict[str, Any]], SpotifyRecommender] | None:
    client = st.session_state.spotify_client
    if client is None:
        return None
    return st.session_state.spotify_tracks, SpotifyRecommender(client)


def _render_results(results: list[dict[str, Any]]) -> None:
    st.session_state.last_results = results
    st.markdown("### Ranked signals")
    if not results:
        st.info("No eligible candidates were found. Try a different seed or mood.")
        return
    for index, track in enumerate(results, 1):
        artist = escape(", ".join(track.get("artists") or ["Unknown artist"]))
        name = escape(str(track.get("name", "Unknown track")))
        score = float(track.get("score", 0))
        reasons = escape(" · ".join(track.get("match_reasons", [])))
        st.markdown(
            f"""
            <div class="track">
              <div class="score">{index:02d} / FEATURE SIM {score:.0%}</div>
              <div class="track-name">{name}</div>
              <div class="track-meta">{artist} &nbsp;·&nbsp; {reasons}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )


def _create_playlist() -> None:
    client = st.session_state.spotify_client
    results = st.session_state.last_results
    uris = [track["uri"] for track in results if track.get("uri")]
    if not client or not uris:
        st.warning("Connect Spotify and generate Spotify-backed results before exporting.")
        return
    try:
        # Spotipy 2.25 still targets Spotify's endpoints removed in February
        # 2026, so use its authenticated transport with the current paths.
        playlist = client._post(
            "me/playlists",
            payload={
                "name": "Signal recommendations",
                "public": False,
                "description": "Ranked locally by the Signal audio-feature recommender.",
            },
        )
        for start in range(0, len(uris), 100):
            client._post(
                f"playlists/{playlist['id']}/items",
                payload={"uris": uris[start : start + 100]},
            )
        url = (playlist.get("external_urls") or {}).get("spotify")
        st.success("Private playlist created." + (f" [Open it in Spotify]({url})" if url else ""))
    except Exception as exc:
        st.error(f"Spotify could not create the playlist: {exc}")


def main() -> None:
    _init_state()

    with st.sidebar:
        st.markdown("## ◉ SIGNAL")
        st.caption("A transparent, offline-first recommendation experiment.")
        source = st.radio("Data source", ["Demo catalog", "My Spotify"], index=0)
        st.divider()
        if source == "My Spotify":
            if st.session_state.spotify_client is None:
                if st.button("Connect Spotify", type="primary", use_container_width=True):
                    _connect()
            else:
                user = st.session_state.spotify_user or {}
                st.success(f"Connected · {user.get('display_name', 'Spotify user')}")
                st.metric("Library candidates", len(st.session_state.spotify_tracks))
        else:
            st.success("Offline demo · no credentials")
            st.metric("Synthetic candidates", len(build_demo_catalog()))
        st.divider()
        st.caption(
            "Ranking happens locally. Spotify is used only for OAuth, library access, and playlist export."
        )

    st.markdown(
        """
        <section class="hero">
          <div class="eyebrow">AUDIO FEATURE RETRIEVAL / 01</div>
          <h1>Find the next track by its signal.</h1>
          <p>Pick a sonic reference or describe the energy. The engine normalizes nine audio dimensions,
          builds a target profile, and shows why each result landed where it did.</p>
          <span class="status-pill">● DETERMINISTIC RANKING</span>
        </section>
        """,
        unsafe_allow_html=True,
    )

    if source == "Demo catalog":
        catalog, recommender = _demo_workspace()
        st.info(
            "Portfolio demo: the catalog is deterministic synthetic data, not a claim about real-user accuracy."
        )
    else:
        workspace = _spotify_workspace()
        if workspace is None:
            st.markdown("### Connect to begin")
            st.write("Use the button in the sidebar. Demo mode remains available without credentials.")
            return
        catalog, recommender = workspace

    tab_seed, tab_mood, tab_method = st.tabs(["Reference track", "Mood profile", "How it works"])
    with tab_seed:
        st.markdown("### Choose a reference")
        if not catalog:
            st.warning("This source has no tracks to rank.")
        else:
            labels = {
                f"{track.get('name')} · {', '.join(track.get('artists', []))}": track for track in catalog
            }
            col_input, col_limit = st.columns([4, 1])
            with col_input:
                selected = st.selectbox("Reference track", list(labels), label_visibility="collapsed")
            with col_limit:
                limit = st.selectbox("Results", [5, 10, 15, 20], index=1)
            if st.button("Rank similar tracks", type="primary", use_container_width=True):
                try:
                    results = recommender.content_based_recommendations([labels[selected]], catalog, limit)
                    _render_results(results)
                except RecommendationError as exc:
                    st.error(str(exc))

    with tab_mood:
        st.markdown("### Shape the energy")
        col_mood, col_limit = st.columns([4, 1])
        with col_mood:
            mood = st.selectbox("Mood", list(MOOD_PROFILES), format_func=str.title)
        with col_limit:
            mood_limit = st.selectbox("Results", [5, 10, 15, 20], index=1, key="mood-limit")
        profile = MOOD_PROFILES[mood]
        st.caption(" · ".join(f"{name} {value}" for name, value in profile.items()))
        if st.button("Rank for this mood", type="primary", use_container_width=True):
            try:
                results = recommender.mood_based_recommendations(mood, catalog, mood_limit)
                _render_results(results)
            except RecommendationError as exc:
                st.error(str(exc))

    with tab_method:
        left, right = st.columns(2)
        with left:
            st.markdown("#### Pipeline")
            st.markdown(
                "1. Validate feature completeness\n2. Normalize each dimension to 0–1\n3. Weight perceptual features\n4. Rank by centroid distance"
            )
        with right:
            st.markdown("#### Honest scope")
            st.write(
                "The offline evaluator is a regression check on labeled synthetic clusters. It is not a user study or production relevance benchmark."
            )

    if source == "My Spotify" and st.session_state.last_results:
        st.divider()
        if st.button("Export last results to a private playlist"):
            _create_playlist()

    st.markdown(
        '<p class="fineprint">Built as an explainable retrieval system. Spotify endpoint access varies by app quota mode.</p>',
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
