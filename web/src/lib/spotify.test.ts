import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { recommendFromSpotifyTrack } from "./spotify";

/**
 * These tests cover the ranking core: collaborator discovery, the quality
 * penalty model, deduping, and the diversity caps. Spotify is mocked at the
 * fetch boundary so the traversal runs exactly as it does in production.
 */

type FakeArtist = { id: string; name: string };

type AlbumJson = {
  id: string;
  name: string;
  release_date: string;
  images: { url: string; width: number | null; height: number | null }[];
  external_urls: { spotify: string };
};

type TrackJson = {
  id: string;
  name: string;
  artists: FakeArtist[];
  duration_ms: number;
  explicit: boolean;
  external_urls: { spotify: string };
};

type CatalogEntry = { album: AlbumJson; tracks: TrackJson[] };

type World = {
  seed: TrackJson & { album: AlbumJson };
  catalogs: Record<string, CatalogEntry[]>;
};

const SEED = { id: "artistS", name: "Seed Artist" };
const ALPHA = { id: "artistA", name: "Alpha" };
const BRAVO = { id: "artistB", name: "Bravo" };
const CHARLIE = { id: "artistC", name: "Charlie" };
const DELTA = { id: "artistD", name: "Delta" };

function album(id: string): AlbumJson {
  return {
    id,
    name: `Album ${id}`,
    release_date: "2024-01-01",
    images: [{ url: `https://img.test/${id}.jpg`, width: 640, height: 640 }],
    external_urls: { spotify: `https://open.spotify.com/album/${id}` },
  };
}

function track(
  id: string,
  name: string,
  artists: FakeArtist[] = [SEED],
  durationMs = 210_000,
): TrackJson {
  return {
    id,
    name,
    artists,
    duration_ms: durationMs,
    explicit: false,
    external_urls: { spotify: `https://open.spotify.com/track/${id}` },
  };
}

function jsonResponse(body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status: 200,
    headers: { "content-type": "application/json" },
  });
}

/** Mock Spotify at the fetch boundary and record every path requested. */
function installSpotify(world: World): string[] {
  const requested: string[] = [];
  const albumTracks = new Map<string, TrackJson[]>();
  for (const entries of Object.values(world.catalogs)) {
    for (const entry of entries) albumTracks.set(entry.album.id, entry.tracks);
  }

  const fetchMock = vi.fn(async (input: RequestInfo | URL): Promise<Response> => {
    const url = typeof input === "string"
      ? input
      : input instanceof URL ? input.toString() : input.url;

    if (url.startsWith("https://accounts.spotify.com/api/token")) {
      return jsonResponse({ access_token: "test-token", token_type: "Bearer", expires_in: 3600 });
    }

    const path = url.replace("https://api.spotify.com/v1", "");
    requested.push(path);

    if (path.startsWith("/tracks/")) return jsonResponse(world.seed);

    const artistAlbums = /^\/artists\/([^/]+)\/albums/.exec(path);
    if (artistAlbums) {
      const entries = world.catalogs[decodeURIComponent(artistAlbums[1])] ?? [];
      return jsonResponse({ items: entries.map((entry) => entry.album) });
    }

    const tracksOfAlbum = /^\/albums\/([^/]+)\/tracks/.exec(path);
    if (tracksOfAlbum) {
      return jsonResponse({ items: albumTracks.get(decodeURIComponent(tracksOfAlbum[1])) ?? [] });
    }

    return new Response("unexpected path", { status: 404 });
  });

  vi.stubGlobal("fetch", fetchMock);
  return requested;
}

/** Build a catalog for one artist from [albumId, tracks] pairs. */
function catalog(...albums: [string, TrackJson[]][]): CatalogEntry[] {
  return albums.map(([id, tracks]) => ({ album: album(id), tracks }));
}

function names(recommendations: { track: { name: string } }[]): string[] {
  return recommendations.map((entry) => entry.track.name);
}

beforeEach(() => {
  vi.stubEnv("SPOTIFY_CLIENT_ID", "test-client-id");
  vi.stubEnv("SPOTIFY_CLIENT_SECRET", "test-client-secret");
});

afterEach(() => {
  vi.unstubAllEnvs();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

describe("collaborator discovery", () => {
  it("follows the most frequent collaborators and ignores the long tail", async () => {
    const requested = installSpotify({
      seed: { ...track("seedTrack", "Seed Song"), album: album("albumSeed") },
      catalogs: {
        artistS: catalog(["albumS1", [
          track("s1", "Feature One", [SEED, ALPHA]),
          track("s2", "Feature Two", [SEED, ALPHA]),
          track("s3", "Feature Three", [SEED, ALPHA]),
          track("s4", "Feature Four", [SEED, BRAVO]),
          track("s5", "Feature Five", [SEED, BRAVO]),
          track("s6", "Feature Six", [SEED, CHARLIE]),
          track("s7", "Feature Seven", [SEED, DELTA]),
        ]]),
        artistA: catalog(["albumA1", [track("a1", "Alpha Solo", [ALPHA])]]),
        artistB: catalog(["albumB1", [track("b1", "Bravo Solo", [BRAVO])]]),
        artistC: catalog(["albumC1", [track("c1", "Charlie Solo", [CHARLIE])]]),
        artistD: catalog(["albumD1", [track("d1", "Delta Solo", [DELTA])]]),
      },
    });

    const { recommendations } = await recommendFromSpotifyTrack("seedTrack");

    // Alpha (3 co-appearances) and Bravo (2) outrank the two artists tied at 1,
    // and only the top three collaborators are ever fetched.
    const fetchedArtists = requested.filter((path) => path.includes("/albums?"));
    expect(fetchedArtists.some((path) => path.startsWith("/artists/artistA/"))).toBe(true);
    expect(fetchedArtists.some((path) => path.startsWith("/artists/artistB/"))).toBe(true);
    expect(fetchedArtists.some((path) => path.startsWith("/artists/artistC/"))).toBe(true);
    expect(fetchedArtists.some((path) => path.startsWith("/artists/artistD/"))).toBe(false);

    expect(names(recommendations)).toContain("Alpha Solo");
    expect(names(recommendations)).not.toContain("Delta Solo");
  });

  it("explains a collaborator pick by naming the artist that connected it", async () => {
    installSpotify({
      seed: { ...track("seedTrack", "Seed Song"), album: album("albumSeed") },
      catalogs: {
        artistS: catalog(["albumS1", [track("s1", "Feature One", [SEED, ALPHA])]]),
        artistA: catalog(["albumA1", [track("a1", "Alpha Solo", [ALPHA])]]),
      },
    });

    const { recommendations } = await recommendFromSpotifyTrack("seedTrack");
    const alphaPick = recommendations.find((entry) => entry.track.name === "Alpha Solo");

    expect(alphaPick?.reasons).toContain("connected through Alpha");
    expect(alphaPick?.connection).toBe("connected");

    const ownPick = recommendations.find((entry) => entry.track.name === "Feature One");
    expect(ownPick?.reasons).toContain("more from Seed Artist");
    expect(ownPick?.connection).toBe("closest");
  });
});

describe("quality penalty model", () => {
  it("drops filler, karaoke, and very short tracks but keeps a live cut", async () => {
    installSpotify({
      seed: { ...track("seedTrack", "Seed Song"), album: album("albumSeed") },
      catalogs: {
        artistS: catalog(
          ["albumP1", [track("p1", "Clean Cut"), track("p2", "Album Interlude")]],
          ["albumP2", [track("p3", "Clean Cut Karaoke"), track("p4", "Brief Tune", [SEED], 60_000)]],
          ["albumP3", [track("p5", "Short Enough", [SEED], 100_000), track("p6", "Clean Cut Live")]],
        ),
      },
    });

    const { recommendations } = await recommendFromSpotifyTrack("seedTrack");

    expect(names(recommendations).sort()).toEqual(
      ["Clean Cut", "Clean Cut Live", "Short Enough"],
    );
    // The interlude and the karaoke version both cross the exclusion threshold,
    // and a 60 second track is treated as filler.
    expect(names(recommendations)).not.toContain("Album Interlude");
    expect(names(recommendations)).not.toContain("Clean Cut Karaoke");
    expect(names(recommendations)).not.toContain("Brief Tune");
  });

  it("stops penalizing filler when the seed itself is that kind of track", async () => {
    installSpotify({
      seed: { ...track("seedTrack", "The Intro"), album: album("albumSeed") },
      catalogs: {
        artistS: catalog(["albumQ1", [track("q1", "Album Interlude"), track("q2", "Clean Cut")]]),
      },
    });

    const { recommendations } = await recommendFromSpotifyTrack("seedTrack");

    expect(names(recommendations)).toContain("Album Interlude");
  });
});

describe("diversity caps", () => {
  it("limits how much one artist and one album can take over the mix", async () => {
    installSpotify({
      seed: { ...track("seedTrack", "Seed Song"), album: album("albumSeed") },
      catalogs: {
        artistS: catalog(
          ["albumR1", [
            track("r1", "One"), track("r2", "Two"), track("r3", "Three"), track("r4", "Four"),
          ]],
          ["albumR2", [
            track("r5", "Five"), track("r6", "Six"), track("r7", "Seven"), track("r8", "Eight"),
          ]],
          ["albumR3", [
            track("r9", "Nine"), track("r10", "Ten"), track("r11", "Eleven"), track("r12", "Twelve"),
          ]],
        ),
      },
    });

    const { recommendations } = await recommendFromSpotifyTrack("seedTrack");

    // Four is the per-artist cap for the seed artist, and no album may supply
    // more than two of them, so twelve eligible tracks collapse to four.
    expect(recommendations).toHaveLength(4);

    const perAlbum = new Map<string, number>();
    for (const entry of recommendations) {
      perAlbum.set(entry.track.album, (perAlbum.get(entry.track.album) ?? 0) + 1);
    }
    expect(Math.max(...perAlbum.values())).toBeLessThanOrEqual(2);
    expect(recommendations.every((entry) => entry.connection === "closest")).toBe(true);
  });
});

describe("result payload", () => {
  it("drops the seed, collapses duplicate titles, and never exposes a score", async () => {
    installSpotify({
      seed: { ...track("seedTrack", "Anchor"), album: album("albumD1") },
      catalogs: {
        artistS: catalog(
          ["albumD1", [track("seedTrack", "Anchor"), track("d2", "Other Song")]],
          ["albumD2", [track("d3", "Other Song"), track("d4", "Third Song")]],
        ),
      },
    });

    const { seed, recommendations } = await recommendFromSpotifyTrack("seedTrack");

    expect(seed.name).toBe("Anchor");
    expect(recommendations.map((entry) => entry.track.id)).not.toContain("seedTrack");
    // The same title reissued on a second album is only offered once.
    expect(names(recommendations)).toEqual(["Other Song", "Third Song"]);

    // The product promise is that a pick is explained by a real connection and
    // never by an invented similarity number, so nothing numeric may leak.
    for (const entry of recommendations) {
      expect(Object.keys(entry).sort()).toEqual(["connection", "reasons", "track"]);
      expect(entry.reasons.length).toBeGreaterThan(0);
    }
  });
});
