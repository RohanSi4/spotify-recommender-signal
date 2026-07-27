import { SignalApp } from "@/components/signal-app";
import { SignalMark } from "@/components/signal-mark";

export default function Home() {
  return (
    <main>
      <header className="site-header">
        <a className="brand" href="#top" aria-label="Signal home"><SignalMark compact /><span>Signal</span></a>
        <nav aria-label="Page links">
          <a href="#try-it">Try it</a>
          <a href="#method">How it works</a>
          <a href="https://github.com/RohanSi4/spotify-recommender-signal" target="_blank" rel="noreferrer">GitHub <span aria-hidden="true">↗</span></a>
        </nav>
      </header>

      <section className="hero" id="top">
        <div className="hero-copy">
          <p className="eyebrow"><span /> Music discovery that starts with you</p>
          <h1>Good taste in.<br /><em>Better songs out.</em></h1>
          <p className="hero-lede">
            Start with any song on Spotify and follow the artist connections somewhere new. Or connect your account for a personal mix that keeps finding different ways through your taste.
          </p>
          <a className="hero-cta" href="#try-it">Find something good <span aria-hidden="true">↓</span></a>
        </div>

        <div className="hero-art" aria-hidden="true">
          <div className="orbit orbit-one" /><div className="orbit orbit-two" />
          <div className="vinyl">
            <div className="vinyl-ring vinyl-ring-one" /><div className="vinyl-ring vinyl-ring-two" />
            <div className="vinyl-label"><SignalMark /><b>signal</b><span>play something good</span></div>
          </div>
          <p>Real songs<br />Live search<br />Clear connections</p>
        </div>
      </section>

      <section className="trust-strip" aria-label="Product facts">
        <p><strong>Every song is real</strong> Search the live Spotify catalog</p>
        <p><strong>No account required</strong> Start with any track right now</p>
        <p><strong>Personal without getting stuck</strong> New mixes avoid earlier picks</p>
      </section>

      <section className="workspace" id="try-it">
        <div className="section-intro">
          <p className="eyebrow"><span /> Try Signal</p>
          <h2>What have you been listening to?</h2>
          <p>Give Signal one real song and it will build a path through releases, featured artists, and nearby corners of Spotify.</p>
        </div>
        <SignalApp />
      </section>

      <section className="method" id="method">
        <div><p className="eyebrow"><span /> How it works</p><h2>Less magic box.<br />More good digging.</h2></div>
        <ol>
          <li><span>01</span><div><strong>Start anywhere</strong><p>Search Spotify for a song you really like, not one from a tiny preset list.</p></div></li>
          <li><span>02</span><div><strong>Follow the connections</strong><p>Signal checks releases, collaborations, and your short, medium, and longtime Spotify favorites.</p></div></li>
          <li><span>03</span><div><strong>Know why it showed up</strong><p>Each pick tells you the actual artist or release connection. No made-up match percentage.</p></div></li>
        </ol>
      </section>

      <section className="disclosure">
        <SignalMark />
        <div>
          <p className="eyebrow">Built honestly</p>
          <h2>Real Spotify songs, without pretending the API does more than it does.</h2>
          <p>
            Spotify retired the recommendation and audio-analysis endpoints for most new developer apps. Signal now works with the live catalog and your actual top songs instead. Personal mixes rotate through different artists, releases, and collaborators, while a small browser-only history keeps earlier picks out of the way. Public search works for everyone. Spotify currently limits account connections on new apps to five invited listeners, so personalized mixes are a small beta for now.
          </p>
          <a href="https://developer.spotify.com/documentation/web-api/concepts/quota-modes" target="_blank" rel="noreferrer">Read Spotify&apos;s access rules <span aria-hidden="true">↗</span></a>
        </div>
      </section>

      <footer>
        <a className="brand" href="#top"><SignalMark compact /><span>Signal</span></a>
        <p>Designed and built by Rohan Singh</p>
        <a href="https://github.com/RohanSi4/spotify-recommender-signal" target="_blank" rel="noreferrer">View the code ↗</a>
      </footer>
    </main>
  );
}
