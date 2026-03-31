# Interdimensional Cable — Bumps & Station IDs

## Concept

Between tracks, Liquidsoap inserts short audio clips that worldbuild the station.
Each station has its own DJ persona, aesthetic, and lore. Listeners don't just hear
music — they hear it the way someone in that dimension would.

## Bump Types

### 1. Station IDs (5-15 sec)
Cold opens that establish where you are.
> "You're locked in to Gormax FM, broadcasting live from Relay Station 7
> in the Maricu System. If you can hear this, your antenna survived the flare."

### 2. DJ Chatter (10-30 sec)
The DJ reacts to the music, takes fake calls, complains about interdimensional conditions.
> "That was Mercury, off the Hyperdrive Boogie compilation. Beautiful stuff.
> We got a caller from the Goop Zone — no wait, lost 'em. Ionic discharge again.
> Anyway, next up..."

### 3. Fake Ads (15-45 sec)
We already have these! The marketing dept and interdimensional cable ad systems
slot right in. Existing ElevenLabs voices + catalog.

### 4. Emergency Broadcasts (5-10 sec, rare)
> "⚠️ ATTENTION: Cronenberg activity detected in sectors 7 through 12.
> Avoid all portal travel until further notice. This has been a Council advisory."

### 5. Listener Dedications (10-20 sec)
> "This next one goes out to Krombopulos Michael. You know what you did, buddy.
> Here's Neptune II."

## Voice Assignments (ElevenLabs roster)

| Station | DJ Voice | Persona |
|---|---|---|
| C-137 Void Lounge | Bill | Late-night host, warm, philosophical |
| K-22β Neon Drift FM | Charlie | Energetic Aussie, hypes everything |
| J-19ζ7 Blips & Hits | Jessica | Playful morning DJ |
| Σ-12 Council Elevator | Laura | Dry corporate announcements |
| NULL Portal Static | Eric | Smooth, mysterious |
| R-2ω Cronenberg Classic | Callum | Unhinged, chaotic |
| Gormax FM (space funk) | Bill or Lily | Trucker radio, gravel-warm |

## Generation Flow

1. Liquidsoap hits a track transition
2. Calls a bump script: `generate-bump.sh --station "gormax-fm" --prev-track "Mercury" --next-track "Saturn"`
3. Script calls LLM (Haiku — cheap, fast) with station persona + context
4. LLM returns bump text (< 100 words)
5. ElevenLabs TTS with assigned voice
6. MP3 cached, fed back to Liquidsoap
7. Station ID bumps pre-generated and rotated; DJ chatter is live

## Pre-generation Strategy

- Generate 20-30 station IDs per station at setup time (cheap, reusable)
- DJ chatter generated live per transition (needs prev/next track context)
- Fake ads pulled from existing marketing dept cache
- Emergency broadcasts pre-generated, inserted randomly (~1 per hour)

## Directory Structure

```
stream/bumps/
  gormax-fm/
    station-ids/     # pre-generated rotation
    dj-chatter/      # live-generated, cached after first play
    emergencies/     # pre-generated, rare insertion
  void-lounge/
    ...
  shared/
    ads/             # symlink to tools/ads/cache + interdimensional-ads
```
